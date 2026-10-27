"""Red Pitaya specific tools + cfgmem + load_board_xdc."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from mcp.types import Tool

from ..boards import DEFAULT_PART, list_bundled_boards, load_board_info, resolve_board_xdc
from ..parsers import (
    parse_timing_summary,
    parse_utilization,
    truncate_response,
    verify_run_status,
)
from ._common import err, require_args, require_project_open

TOOLS = [
    Tool(
        name="load_board_xdc",
        description=(
            "Resolve a bundled board XDC and attach it to the current project. "
            "Standalone wrapper over get_board_info + add_constraints."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "board": {"type": "string", "description": "Board id, e.g. 'red_pitaya_125_14'"},
                "variant": {
                    "type": "string",
                    "description": "XDC variant id (e.g. 'leds_min', 'full'). Default: 'full'",
                },
            },
            "required": ["board"],
        },
    ),
    Tool(
        name="generate_cfgmem",
        description=(
            "Convert a .bit into a raw binary image (.bit.bin) loadable via "
            "/dev/xdevcfg on the Red Pitaya. Use after generate_bitstream."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "bit_file": {"type": "string", "description": "Absolute path to input .bit"},
                "output": {"type": "string", "description": "Output .bit.bin path (default: <bit_file>.bin)"},
            },
            "required": ["bit_file"],
        },
    ),
    Tool(
        name="get_synthesis_errors_parsed",
        description=(
            "Return structured errors and critical warnings from a run (default: synth_1). "
            "Use after run_synthesis fails to get a clean actionable list."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "run": {"type": "string", "description": "default: synth_1"},
                "max_items": {"type": "integer", "description": "default: 50"},
            },
            "required": [],
        },
    ),
    Tool(
        name="create_redpitaya_project_rtl",
        description=(
            "One-shot composite: create project -> add HDL sources -> apply XDC -> "
            "synth -> impl -> write_bitstream -> generate .bit.bin. Stops on the first "
            "failing stage and returns a structured payload."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "directory": {"type": "string"},
                "verilog_files": {"type": "array", "items": {"type": "string"}},
                "top_module": {"type": "string"},
                "board": {"type": "string", "description": "default: red_pitaya_125_14"},
                "xdc_variant": {
                    "type": "string",
                    "enum": ["leds_min", "full", "custom"],
                },
                "extra_xdc_files": {"type": "array", "items": {"type": "string"}},
                "synth_flags": {"type": "string"},
                "jobs": {"type": "integer"},
                "synth_timeout": {"type": "integer"},
                "impl_timeout": {"type": "integer"},
            },
            "required": ["name", "directory", "verilog_files", "top_module"],
        },
    ),
]


def _load_board_xdc(session, args):
    if (e := require_project_open(session)):
        return e
    board = args.get("board", "")
    variant = args.get("variant", "full")
    info = load_board_info(board)
    if info is None:
        return err(
            f"Unknown board '{board}'", available=[b["board"] for b in list_bundled_boards()]
        )
    xdc = resolve_board_xdc(board, variant)
    if not xdc:
        return err(
            f"Board '{board}' has no XDC variant '{variant}'",
            available_variants=list((info.get("xdc_variants") or {}).keys()),
        )
    r = session.run_tcl(f"add_files -fileset constrs_1 [list {{{xdc}}}]", timeout_override=30)
    return {
        "success": r.success,
        "board": board,
        "variant": variant,
        "xdc_path": xdc,
        "output": r.output,
        "elapsed_ms": r.elapsed_ms,
    }


def write_cfgmem(session, bit_file: str, output: str | None = None) -> dict:
    """Convert a .bit to a raw .bit.bin via write_cfgmem.

    Shared by _generate_cfgmem, the create_redpitaya_project_rtl composite and
    redpitaya_repo's rp_build_project.

    Vivado's `write_cfgmem -loadbit` parser does its OWN word-split on the value,
    ignoring Tcl braces. For paths with spaces we must `cd` to the .bit's
    directory and pass a relative filename. See pitfalls_2020_1.md.
    """
    output = output or f"{bit_file}.bin"
    bit_path = Path(bit_file)
    out_path = Path(output)
    bit_dir = bit_path.parent.as_posix()
    bit_name = bit_path.name
    out_arg = out_path.as_posix() if out_path.is_absolute() else out_path.name

    cmd = (
        f'cd {{{bit_dir}}}; '
        f'write_cfgmem -force -format bin -interface smapx32 '
        f'-disablebitswap -loadbit "up 0x0 {bit_name}" {{{out_arg}}}'
    )
    r = session.run_tcl(cmd, timeout_override=120)
    if not r.success:
        return {"success": False, "error": r.output, "bit_file": bit_file}

    candidates = [
        out_path,
        Path(bit_dir) / out_path.name,
        Path(str(out_path) + ".bin"),
        Path(bit_dir) / (out_path.name + ".bin"),
    ]
    produced = next((p for p in candidates if p.exists()), None)
    return {
        "success": True,
        "bit_file": bit_file,
        "output_path": str(produced) if produced else output,
        "size_bytes": produced.stat().st_size if produced else None,
        "elapsed_ms": r.elapsed_ms,
    }


def _generate_cfgmem(session, args):
    if (e := require_project_open(session)):
        return e
    bit_file = args.get("bit_file", "")
    if not bit_file:
        return err("'bit_file' is required")
    if not Path(bit_file).exists():
        return err(f"Input .bit file not found: {bit_file}")
    return write_cfgmem(session, bit_file, args.get("output"))


def _get_synthesis_errors_parsed(session, args):
    if (e := require_project_open(session)):
        return e
    run = args.get("run", "synth_1")
    max_items = args.get("max_items", 50)
    tcl = (
        f'set msgs [get_messages -severity {{ERROR}} -severity {{CRITICAL WARNING}}]; '
        f'if {{[llength $msgs] == 0}} {{ puts "NO_MESSAGES" }} else {{ '
        f'foreach m $msgs {{ puts "MSG|$m" }} }}'
    )
    r = session.run_tcl(tcl, timeout_override=60)

    errors: list[dict] = []
    warnings: list[dict] = []
    for line in r.output.splitlines():
        if not line.startswith("MSG|"):
            continue
        body = line[4:].strip()
        m = re.match(
            r"(?P<sev>ERROR|CRITICAL WARNING|WARNING)\s*:\s*"
            r"(?:\[(?P<code>[^\]]+)\]\s*)?"
            r"(?P<msg>.*?)"
            r"(?:\s*\[(?P<loc>[^\]]+)\])?$",
            body,
        )
        entry = {
            "severity": m.group("sev") if m else "UNKNOWN",
            "code": m.group("code") if m else None,
            "message": m.group("msg") if m else body,
            "location": m.group("loc") if m else None,
        }
        (errors if entry["severity"] == "ERROR" else warnings).append(entry)
        if len(errors) + len(warnings) >= max_items:
            break

    return {
        "success": True,
        "run": run,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "truncated": (len(errors) + len(warnings)) >= max_items,
    }


def _create_redpitaya_project_rtl(session, args):
    if (e := require_project_open(session)):
        return e
    if (e := require_args(args, "name", "directory", "verilog_files", "top_module")):
        return e

    proj_name = args["name"]
    parent_dir = args["directory"]
    verilog_files = args["verilog_files"]
    top_module = args["top_module"]
    board = args.get("board", "red_pitaya_125_14")
    xdc_variant = args.get("xdc_variant", "leds_min")
    extra_xdc = args.get("extra_xdc_files") or []
    synth_flags = args.get(
        "synth_flags", "-flatten_hierarchy none -bufg 16 -keep_equivalent_registers"
    )
    jobs = args.get("jobs", 4)
    synth_timeout = args.get("synth_timeout", 2400)
    impl_timeout = args.get("impl_timeout", 5400)

    info = load_board_info(board)
    if info is None:
        return {
            "success": False,
            "stage": "resolve_board",
            "error": f"Unknown board '{board}'. Known: {[b['board'] for b in list_bundled_boards()]}",
        }

    xdc_paths: list[str] = []
    if xdc_variant != "custom":
        base_xdc = resolve_board_xdc(board, xdc_variant)
        if not base_xdc:
            return {
                "success": False,
                "stage": "resolve_board",
                "error": f"Board '{board}' has no XDC variant '{xdc_variant}'.",
            }
        xdc_paths.append(base_xdc)
    xdc_paths.extend(extra_xdc)
    if not xdc_paths:
        return {
            "success": False,
            "stage": "resolve_board",
            "error": "xdc_variant='custom' requires extra_xdc_files",
        }

    part = info.get("part", DEFAULT_PART)
    started = datetime.utcnow()

    def _fail(stage: str, payload: dict):
        return {
            "success": False,
            "stage": stage,
            "project_open": session.is_running,
            **payload,
        }

    try:
        Path(parent_dir).mkdir(parents=True, exist_ok=True)
    except OSError as ex:
        return _fail("create_project", {"error": f"mkdir failed: {ex}"})

    proj_dir = f"{parent_dir}/{proj_name}"
    project_file = f"{proj_dir}/{proj_name}.xpr"

    r = session.run_tcl(
        f"create_project {proj_name} {{{proj_dir}}} -part {part} -force",
        timeout_override=120,
    )
    if not r.success:
        return _fail("create_project", {"error": r.output})
    session.current_project = project_file
    session.run_tcl("set_property target_language Verilog [current_project]", timeout_override=30)

    file_list = " ".join(f"{{{f}}}" for f in verilog_files)
    r = session.run_tcl(f"add_files -fileset sources_1 [list {file_list}]", timeout_override=60)
    if not r.success:
        return _fail("add_sources", {"error": r.output, "project_file": project_file})

    r = session.run_tcl(
        f"set_property top {top_module} [get_filesets sources_1]; "
        f"update_compile_order -fileset sources_1",
        timeout_override=30,
    )
    if not r.success:
        return _fail("set_top", {"error": r.output, "project_file": project_file})

    xdc_list = " ".join(f"{{{f}}}" for f in xdc_paths)
    r = session.run_tcl(f"add_files -fileset constrs_1 [list {xdc_list}]", timeout_override=30)
    if not r.success:
        return _fail("add_constraints", {"error": r.output, "project_file": project_file})

    if synth_flags:
        session.run_tcl(
            f'set_property -name {{STEPS.SYNTH_DESIGN.ARGS.MORE OPTIONS}} '
            f'-value {{{synth_flags}}} -objects [get_runs synth_1]',
            timeout_override=30,
        )

    r = session.run_tcl(
        f"reset_run synth_1; launch_runs synth_1 -jobs {jobs}; wait_on_run synth_1",
        timeout_override=synth_timeout,
    )
    sv = verify_run_status(session, "synth_1")
    if not sv["actually_succeeded"]:
        err_msgs = session.run_tcl(
            'foreach m [get_messages -severity {ERROR}] { puts "MSG|$m" }',
            timeout_override=30,
        )
        return _fail("synthesis", {
            "error": "synthesis failed",
            "run_status": sv["status"],
            "run_progress": sv["progress"],
            "project_file": project_file,
            "raw_messages": err_msgs.output,
            "next_actions": [
                "call get_synthesis_errors_parsed for structured errors",
                "call get_messages for the full log",
            ],
        })

    r = session.run_tcl(
        f"launch_runs impl_1 -to_step write_bitstream -jobs {jobs}; wait_on_run impl_1",
        timeout_override=impl_timeout,
    )
    iv = verify_run_status(session, "impl_1")
    if not iv["actually_succeeded"]:
        return _fail("implementation", {
            "error": "implementation failed",
            "run_status": iv["status"],
            "run_progress": iv["progress"],
            "project_file": project_file,
            "next_actions": [
                "call get_timing_summary to see slack",
                "call get_timing_paths for critical paths",
            ],
        })

    bit_path = f"{proj_dir}/{proj_name}.runs/impl_1/{top_module}.bit"
    if not Path(bit_path).exists():
        return _fail("locate_bitstream", {
            "error": f"Expected bitstream not found at {bit_path}",
            "project_file": project_file,
        })

    cfg = write_cfgmem(session, bit_path)
    bin_final = cfg.get("output_path") if cfg.get("success") else None
    if not cfg.get("success") or bin_final is None or not Path(bin_final).exists():
        return _fail("generate_cfgmem", {
            "error": cfg.get("error", "cfgmem output not found"),
            "project_file": project_file,
            "bit_path": bit_path,
        })

    # report_* commands need an in-memory design. After wait_on_run only the
    # checkpoint is on disk — open it first.
    session.run_tcl("open_run impl_1 -name impl_1", timeout_override=120)
    timing = session.run_tcl(
        "report_timing_summary -no_header -no_detailed_paths -return_string",
        timeout_override=60,
    )
    util = session.run_tcl("report_utilization -return_string", timeout_override=60)
    elapsed_s = (datetime.utcnow() - started).total_seconds()

    return {
        "success": True,
        "stage": "done",
        "project_file": project_file,
        "bit_path": bit_path,
        "bin_path": bin_final,
        "board": board,
        "part": part,
        "top_module": top_module,
        "xdc_variant": xdc_variant,
        "xdc_files": xdc_paths,
        "elapsed_seconds": round(elapsed_s, 1),
        # The raw report opens with ~2 KB of timer settings, so the truncated
        # text alone rarely reaches the WNS/WHS table: return parsed values too.
        "timing_summary": {k: v for k, v in parse_timing_summary(timing.output).items() if k != "raw"},
        "utilization": {k: v for k, v in parse_utilization(util.output).items() if k != "raw"},
        "timing_summary_raw": truncate_response(timing.output, 2000),
        "utilization_raw": truncate_response(util.output, 2000),
        "deploy_hint": (
            f"scp {bin_final} root@<redpitaya>:/tmp/ && "
            f"ssh root@<redpitaya> 'cat /tmp/{Path(bin_final).name} > /dev/xdevcfg'"
        ),
    }


HANDLERS = {
    "load_board_xdc": _load_board_xdc,
    "generate_cfgmem": _generate_cfgmem,
    "get_synthesis_errors_parsed": _get_synthesis_errors_parsed,
    "create_redpitaya_project_rtl": _create_redpitaya_project_rtl,
}
