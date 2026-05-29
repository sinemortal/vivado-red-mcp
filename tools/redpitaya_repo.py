"""RedPitaya-FPGA repository integration — PS+PL build flow.

These tools drive the canonical RedPitaya build flow instead of rebuilding the
Zynq PS7 from scratch. The RedPitaya-FPGA repo ships `prj/<name>/ip/systemZ10.tcl`
— a `write_bd_tcl` export of a fully-configured, board-validated PS7 block design
(DDR3, MIO, clocks). The build script sources it verbatim, so the PS backbone is
guaranteed-good.

Flow (see data/docs/redpitaya_ps_pl_flow.md):
  rp_setup_workspace  -> isolated copy of the repo
  rp_list_projects    -> enumerate prj/* (v0.94, barebones, axi4lite, ...)
  rp_build_project    -> run red_pitaya_vivado_project_Z10.tcl + synth/impl/bitstream
  rp_create_custom_project -> clone a base project for custom PL logic

Distinct from `create_redpitaya_project_rtl` (pure RTL, no PS) in tools/redpitaya.py.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from mcp.types import Tool

from ..parsers import truncate_response, verify_run_status
from ._common import err, require_args, require_project_open
from .redpitaya import write_cfgmem

# Build/scratch dirs not worth copying into a workspace.
_COPY_IGNORE = shutil.ignore_patterns(
    ".git", "__pycache__", "*.jou", "*.log", "*.str", "*.dmp",
    "project", "out", ".Xil", "*.cache", "vivado_projects",
)

TOOLS = [
    Tool(
        name="rp_setup_workspace",
        description=(
            "Copy a RedPitaya-FPGA repo into an isolated workspace so builds don't "
            "touch the pristine checkout. Idempotent — pass force=true to recopy. "
            "No Vivado session required."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to the RedPitaya-FPGA checkout (contains prj/, rtl/, brd/, *.tcl)",
                },
                "workspace_path": {
                    "type": "string",
                    "description": "Destination workspace dir. Default: <repo_parent>/redpitaya_mcp_workspace",
                },
                "force": {
                    "type": "boolean",
                    "description": "If true, delete and recopy an existing workspace (default: false)",
                },
            },
            "required": ["repo_path"],
        },
    ),
    Tool(
        name="rp_list_projects",
        description=(
            "List projects under prj/ of a RedPitaya workspace or repo. Flags which "
            "are Z10-capable (have ip/systemZ10.tcl). No Vivado session required."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Workspace or repo root (the dir that contains prj/)",
                }
            },
            "required": ["path"],
        },
    ),
    Tool(
        name="rp_workspace_info",
        description="Report workspace state: projects present and which already have a built bitstream.",
        inputSchema={
            "type": "object",
            "properties": {
                "workspace_path": {"type": "string"}
            },
            "required": ["workspace_path"],
        },
    ),
    Tool(
        name="rp_create_custom_project",
        description=(
            "Clone an existing prj/<base> into prj/<name> inside the workspace, ready "
            "for custom PL logic. Returns the rtl/ dir and red_pitaya_top path to edit. "
            "No Vivado session required."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "workspace_path": {"type": "string"},
                "base_project": {
                    "type": "string",
                    "description": "Existing project to clone (e.g. 'v0.94', 'barebones')",
                },
                "name": {"type": "string", "description": "New project name"},
            },
            "required": ["workspace_path", "base_project", "name"],
        },
    ),
    Tool(
        name="rp_build_project",
        description=(
            "Build a RedPitaya PS+PL project end-to-end: run the project-mode setup "
            "TCL (creates the PS7 block design via systemZ10.tcl), then synthesis, "
            "implementation and write_bitstream, then generate the .bit.bin. Returns "
            "{stage, xpr_path, bit_path, bin_path, timing}. Requires start_session first."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "workspace_path": {"type": "string"},
                "project": {
                    "type": "string",
                    "description": "Project under prj/ to build (e.g. 'v0.94', 'barebones')",
                },
                "model": {
                    "type": "string",
                    "description": "Board model — only 'Z10' supported (default: Z10)",
                },
                "defines": {
                    "type": "string",
                    "description": "Extra Verilog defines passed as tclarg 1 (default: empty)",
                },
                "jobs": {"type": "integer", "description": "Parallel jobs for synth/impl (default: 4)"},
                "setup_timeout": {"type": "integer", "description": "Project-setup TCL timeout s (default: 900)"},
                "synth_timeout": {"type": "integer", "description": "Synthesis timeout s (default: 2400)"},
                "impl_timeout": {"type": "integer", "description": "Implementation timeout s (default: 5400)"},
                "synth_flags": {
                    "type": "string",
                    "description": "Extra synth_design flags via STEPS.SYNTH_DESIGN.ARGS.MORE_OPTIONS. Default empty. RedPitaya canonical for reproducibility: '-flatten_hierarchy none -bufg 16 -keep_equivalent_registers' (NOTE: those preserve hierarchy/BUFG count for debug; on xc7z010-1 they typically hurt QoR vs defaults).",
                },
            },
            "required": ["workspace_path", "project"],
        },
    ),
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _default_workspace(repo_path: str) -> str:
    return str(Path(repo_path).resolve().parent / "redpitaya_mcp_workspace")


def _is_repo_root(path: Path) -> bool:
    return (path / "prj").is_dir() and any(path.glob("red_pitaya_vivado_project_*.tcl"))


def _project_dirs(root: Path) -> list[Path]:
    prj = root / "prj"
    if not prj.is_dir():
        return []
    return sorted(p for p in prj.iterdir() if p.is_dir())


# ---------------------------------------------------------------------------
# handlers
# ---------------------------------------------------------------------------

def _rp_setup_workspace(session, args):
    if (e := require_args(args, "repo_path")):
        return e
    repo = Path(args["repo_path"])
    if not repo.is_dir():
        return err(f"repo_path not found: {repo}")
    if not _is_repo_root(repo):
        return err(
            f"{repo} does not look like a RedPitaya-FPGA repo "
            f"(missing prj/ or red_pitaya_vivado_project_*.tcl)"
        )

    workspace = Path(args.get("workspace_path") or _default_workspace(str(repo)))
    force = args.get("force", False)

    if workspace.exists():
        if not force:
            return {
                "success": True,
                "workspace_path": str(workspace),
                "status": "already_exists",
                "message": "Workspace already present. Pass force=true to recopy.",
                "projects": [p.name for p in _project_dirs(workspace)],
            }
        shutil.rmtree(workspace)

    try:
        shutil.copytree(repo, workspace, ignore=_COPY_IGNORE)
    except OSError as ex:
        return err(f"copy failed: {ex}", workspace_path=str(workspace))

    return {
        "success": True,
        "workspace_path": str(workspace),
        "status": "copied",
        "source_repo": str(repo),
        "projects": [p.name for p in _project_dirs(workspace)],
    }


def _rp_list_projects(session, args):
    if (e := require_args(args, "path")):
        return e
    root = Path(args["path"])
    if not root.is_dir():
        return err(f"path not found: {root}")

    projects = []
    for p in _project_dirs(root):
        systemz10 = p / "ip" / "systemZ10.tcl"
        rtl_dir = p / "rtl"
        rtl_count = len(list(rtl_dir.glob("*.sv")) + list(rtl_dir.glob("*.v"))) if rtl_dir.is_dir() else 0
        projects.append({
            "name": p.name,
            "z10_capable": systemz10.is_file(),
            "rtl_files": rtl_count,
            "has_ip_dir": (p / "ip").is_dir(),
        })
    return {"success": True, "root": str(root), "count": len(projects), "projects": projects}


def _rp_workspace_info(session, args):
    if (e := require_args(args, "workspace_path")):
        return e
    ws = Path(args["workspace_path"])
    if not ws.is_dir():
        return err(f"workspace not found: {ws}")

    projects = []
    for p in _project_dirs(ws):
        bit = p / "project" / "redpitaya.runs" / "impl_1" / "red_pitaya_top.bit"
        projects.append({
            "name": p.name,
            "built": bit.is_file(),
            "bit_path": str(bit) if bit.is_file() else None,
        })
    return {
        "success": True,
        "workspace_path": str(ws),
        "is_repo_root": _is_repo_root(ws),
        "projects": projects,
    }


def _rp_create_custom_project(session, args):
    if (e := require_args(args, "workspace_path", "base_project", "name")):
        return e
    ws = Path(args["workspace_path"])
    base = ws / "prj" / args["base_project"]
    dest = ws / "prj" / args["name"]

    if not base.is_dir():
        return err(
            f"base project not found: {base}",
            available=[p.name for p in _project_dirs(ws)],
        )
    if dest.exists():
        return err(f"destination project already exists: {dest}")

    try:
        shutil.copytree(base, dest, ignore=_COPY_IGNORE)
    except OSError as ex:
        return err(f"copy failed: {ex}")

    rtl_dir = dest / "rtl"
    top = None
    for cand in ("red_pitaya_top.sv", "red_pitaya_top.v"):
        if (rtl_dir / cand).is_file():
            top = str(rtl_dir / cand)
            break

    return {
        "success": True,
        "project": args["name"],
        "project_dir": str(dest),
        "rtl_dir": str(rtl_dir),
        "top_file": top,
        "message": (
            "Edit the top file / add RTL under rtl_dir, then call rp_build_project. "
            "The PS7 block design stays intact (built from ip/systemZ10.tcl)."
        ),
    }


def _rp_build_project(session, args):
    if (e := require_project_open(session)):  # only checks the session is running
        return e
    if (e := require_args(args, "workspace_path", "project")):
        return e

    ws = Path(args["workspace_path"])
    project = args["project"]
    model = args.get("model", "Z10")
    defines = args.get("defines", "")
    jobs = args.get("jobs", 4)
    setup_timeout = args.get("setup_timeout", 900)
    synth_timeout = args.get("synth_timeout", 2400)
    impl_timeout = args.get("impl_timeout", 5400)
    synth_flags = args.get("synth_flags", "")

    if model != "Z10":
        return err(f"Only model 'Z10' is supported, got '{model}'")
    if not ws.is_dir():
        return err(f"workspace not found: {ws}")

    setup_tcl = ws / f"red_pitaya_vivado_project_{model}.tcl"
    if not setup_tcl.is_file():
        return err(f"setup script not found: {setup_tcl}")
    prj_dir = ws / "prj" / project
    if not prj_dir.is_dir():
        return err(
            f"project not found: {prj_dir}",
            available=[p.name for p in _project_dirs(ws)],
        )

    ws_posix = ws.resolve().as_posix()

    def _fail(stage, payload):
        return {"success": False, "stage": stage, **payload}

    # 1. Project setup — replicate the RedPitaya project-mode flow. The script
    #    reads $argv and does `cd prj/$prj_name` itself, then sources systemZ10.tcl.
    #    Close any previously-open project first: building two different projects
    #    back-to-back in the same Vivado session causes systemZ10.tcl validation
    #    to fail on stale PS7 state (CAN peripheral divisor out of range).
    setup_cmd = (
        f"foreach p [get_projects -quiet] {{ close_project -quiet }}; "
        f"cd {{{ws_posix}}}; "
        f"set argv [list {{{project}}} {{{defines}}}]; "
        f"set argc 2; "
        f"source {{red_pitaya_vivado_project_{model}.tcl}}"
    )
    r = session.run_tcl(setup_cmd, timeout_override=setup_timeout)
    if not r.success:
        return _fail("project_setup", {
            "error": r.output,
            "hint": "systemZ10.tcl / project-mode setup failed",
        })

    xpr_path = f"{prj_dir.resolve().as_posix()}/project/redpitaya.xpr"
    runs_dir = f"{prj_dir.resolve().as_posix()}/project/redpitaya.runs"

    # 1b. Apply canonical RedPitaya synth flags (project-mode setup TCL skips them;
    #     they're only in the non-project batch TCL). Required for QoR on heavy designs.
    if synth_flags:
        session.run_tcl(
            f'set_property -name {{STEPS.SYNTH_DESIGN.ARGS.MORE OPTIONS}} '
            f'-value {{{synth_flags}}} -objects [get_runs synth_1]',
            timeout_override=30,
        )

    # 2. Synthesis
    r = session.run_tcl(
        f"reset_run synth_1; launch_runs synth_1 -jobs {jobs}; wait_on_run synth_1",
        timeout_override=synth_timeout,
    )
    sv = verify_run_status(session, "synth_1")
    if not sv["actually_succeeded"]:
        return _fail("synthesis", {
            "error": "synthesis failed",
            "run_status": sv["status"],
            "run_progress": sv["progress"],
            "xpr_path": xpr_path,
            "next_actions": ["call get_synthesis_errors_parsed", "call get_messages"],
        })

    # 3. Implementation + bitstream
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
            "xpr_path": xpr_path,
            "next_actions": ["call get_timing_summary", "call get_timing_paths"],
        })

    # 4. Locate bitstream (top module is red_pitaya_top in the RedPitaya flow)
    bit_path = f"{runs_dir}/impl_1/red_pitaya_top.bit"
    if not Path(bit_path).exists():
        return _fail("locate_bitstream", {
            "error": f"bitstream not found at {bit_path}",
            "xpr_path": xpr_path,
        })

    # 5. cfgmem -> .bit.bin
    cfg = write_cfgmem(session, bit_path)
    bin_final = cfg.get("output_path") if cfg.get("success") else None
    if not cfg.get("success") or not (bin_final and Path(bin_final).exists()):
        return _fail("generate_cfgmem", {
            "error": cfg.get("error", "cfgmem output not found"),
            "xpr_path": xpr_path,
            "bit_path": bit_path,
        })

    # 6. Post-impl summary (best effort)
    session.run_tcl("open_run impl_1 -name impl_1", timeout_override=120)
    timing = session.run_tcl(
        "report_timing_summary -no_header -no_detailed_paths -return_string",
        timeout_override=60,
    )

    return {
        "success": True,
        "stage": "done",
        "project": project,
        "workspace_path": str(ws),
        "xpr_path": xpr_path,
        "bit_path": bit_path,
        "bin_path": bin_final,
        "timing_summary_raw": truncate_response(timing.output, 2000),
        "deploy_hint": (
            f"deploy_to_redpitaya bit_bin_path={bin_final} host=<redpitaya-ip>"
        ),
    }


HANDLERS = {
    "rp_setup_workspace": _rp_setup_workspace,
    "rp_list_projects": _rp_list_projects,
    "rp_workspace_info": _rp_workspace_info,
    "rp_create_custom_project": _rp_create_custom_project,
    "rp_build_project": _rp_build_project,
}
