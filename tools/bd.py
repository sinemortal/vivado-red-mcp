"""Block Design (IP Integrator) tools.

Covers the standard Vivado 2020.1 IPI flow used by Red Pitaya / Zynq projects:
  create_bd_design -> add_ip_to_bd -> connect_bd_net / connect_bd_intf_net /
  apply_bd_automation -> validate_bd_design -> make_wrapper -> set top.

References:
  - UG994 (IP Integrator): https://docs.amd.com/v/u/2020.1-English/ug994-vivado-ip-subsystems
  - UG895 (System-Level Design Entry)
  - UG835 §create_bd_*, §apply_bd_automation
  - Red Pitaya canonical example: RedPitaya-FPGA/prj/*/ip/systemZ10.tcl
"""

from __future__ import annotations

from mcp.types import Tool

from ._common import err, require_args, require_project_open

TOOLS = [
    Tool(
        name="create_block_design",
        description=(
            "Create a new block design and make it current. Optionally sets the "
            "board_part property on the project beforehand (board_part requires the "
            "BSP to be installed in Vivado)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Block design name (no .bd)"},
                "board_part": {
                    "type": "string",
                    "description": "Optional vendor:board:part string (e.g. 'digilentinc.com:arty-a7-35:part0:1.0')",
                },
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="save_bd_design",
        description="Save the currently open block design to disk.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="close_bd_design",
        description="Close the currently open block design (without deleting).",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="list_bd_cells",
        description="List cells in the current block design (optionally filtered).",
        inputSchema={
            "type": "object",
            "properties": {
                "filter": {"type": "string", "description": "Wildcard pattern, default '*'"}
            },
            "required": [],
        },
    ),
    Tool(
        name="add_ip_to_bd",
        description=(
            "Add an IP core to the current block design (`create_bd_cell -type ip "
            "-vlnv ...`). If `config` is provided, the CONFIG.* keys are applied via "
            "set_property -dict."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "cell_name": {
                    "type": "string",
                    "description": "Instance name (e.g. 'processing_system7_0')",
                },
                "vlnv": {
                    "type": "string",
                    "description": "Vendor:Library:Name:Version (e.g. 'xilinx.com:ip:processing_system7:5.5')",
                },
                "config": {
                    "type": "object",
                    "description": "Dict of CONFIG.* properties (e.g. {'CONFIG.PCW_USE_M_AXI_GP0': '1'})",
                },
            },
            "required": ["cell_name", "vlnv"],
        },
    ),
    Tool(
        name="create_bd_port",
        description=(
            "Create a top-level port on the current block design. Scalar or vector "
            "(`from`/`to`) via create_bd_port, or an interface port when `vlnv` is "
            "given (create_bd_intf_port, e.g. the XADC "
            "'xilinx.com:interface:diff_analog_io_rtl:1.0'). Port names must match "
            "the constraints (XDC) of the board."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Port name (e.g. 'led_o')"},
                "direction": {
                    "type": "string",
                    "enum": ["I", "O", "IO"],
                    "description": "Direction for a plain port (default: I)",
                },
                "from": {"type": "integer", "description": "MSB index for a vector port (e.g. 7)"},
                "to": {"type": "integer", "description": "LSB index for a vector port (default: 0)"},
                "type": {
                    "type": "string",
                    "description": "Optional port type: clk, rst, ce, intr, data, undef",
                },
                "vlnv": {
                    "type": "string",
                    "description": "Interface VLNV: creates an interface port instead",
                },
                "mode": {
                    "type": "string",
                    "description": "Interface mode (default: Slave): Master, Slave, ...",
                },
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="add_module_to_bd",
        description=(
            "Add an RTL module (Verilog/VHDL already in the project, see add_sources) "
            "to the current block design as a module-reference cell "
            "(`create_bd_cell -type module -reference`). Optional `config` sets its "
            "parameters, e.g. {'CONFIG.WIDTH': '8'}; string parameters keep their "
            "quotes, e.g. {'CONFIG.init': '\"0011\"'}."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "module": {"type": "string", "description": "Top module name of the RTL"},
                "cell_name": {"type": "string", "description": "Instance name in the BD"},
                "config": {"type": "object", "description": "Dict of CONFIG.* parameters"},
            },
            "required": ["module", "cell_name"],
        },
    ),
    Tool(
        name="configure_bd_cell",
        description=(
            "Set CONFIG.* properties on an existing block-design cell "
            "(set_property -dict). Use for settings that must be applied after "
            "creation or in a separate step, e.g. importing a PS7 board preset: "
            "{'CONFIG.PCW_IMPORT_BOARD_PRESET': '<path>/red_pitaya.xml'}."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "cell_name": {"type": "string"},
                "config": {"type": "object", "description": "Dict of CONFIG.* properties"},
            },
            "required": ["cell_name", "config"],
        },
    ),
    Tool(
        name="connect_bd_net",
        description="Connect two scalar pins/ports in the current block design.",
        inputSchema={
            "type": "object",
            "properties": {
                "pin_from": {"type": "string", "description": "e.g. 'processing_system7_0/FCLK_CLK0'"},
                "pin_to": {"type": "string", "description": "e.g. 'axi_gpio_0/s_axi_aclk'"},
            },
            "required": ["pin_from", "pin_to"],
        },
    ),
    Tool(
        name="connect_bd_intf_net",
        description="Connect two AXI/interface pins in the current block design.",
        inputSchema={
            "type": "object",
            "properties": {
                "intf_from": {"type": "string", "description": "e.g. 'processing_system7_0/M_AXI_GP0'"},
                "intf_to": {"type": "string", "description": "e.g. 'axi_gpio_0/S_AXI'"},
            },
            "required": ["intf_from", "intf_to"],
        },
    ),
    Tool(
        name="auto_connect_axi",
        description=(
            "Use `apply_bd_automation -rule xilinx.com:bd_rule:axi4` to wire an AXI "
            "master to a slave (inserts AXI interconnect + clock/reset hookups)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "master": {"type": "string", "description": "AXI master intf pin"},
                "slave": {"type": "string", "description": "AXI slave intf pin"},
                "options": {
                    "type": "object",
                    "description": "Optional extra -config key/value pairs (e.g. {'Clk_master': 'Auto'})",
                },
            },
            "required": ["master", "slave"],
        },
    ),
    Tool(
        name="apply_ps7_preset",
        description=(
            "Apply the Zynq-7000 processing_system7 board preset to a PS7 cell — wires "
            "FIXED_IO / DDR / clocks per the board definition. Equivalent to clicking "
            "'Run Block Automation' on a freshly added PS7 in the GUI."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "cell": {
                    "type": "string",
                    "description": "PS7 cell name (default: 'processing_system7_0')",
                },
                "apply_board_preset": {
                    "type": "boolean",
                    "description": "Whether to apply the current board preset (default: true)",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="validate_block_design",
        description=(
            "Run validate_bd_design and return parsed status. Failures include "
            "unconnected pins, conflicting CONFIG values, or missing assignments."
        ),
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="regenerate_bd_layout",
        description="Regenerate the block design layout (cosmetic; useful before save).",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="assign_bd_address",
        description="Auto-assign addresses in the BD address editor (assign_bd_address).",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="generate_bd_wrapper",
        description=(
            "Generate the HDL wrapper for a block design and (by default) add it to "
            "sources_1 and set it as project top. Implements the canonical pattern: "
            "make_wrapper -files <bd> -top; add_files -norecurse <wrapper>; "
            "set_property top <wrapper> [current_fileset]; update_compile_order."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "bd_name": {"type": "string", "description": "Block design name (no .bd)"},
                "set_top": {"type": "boolean", "description": "Also set the wrapper as project top (default: true)"},
            },
            "required": ["bd_name"],
        },
    ),
]


def _create_block_design(session, args):
    if (e := require_project_open(session)):
        return e
    if (e := require_args(args, "name")):
        return e
    name = args["name"]
    board_part = args.get("board_part")

    if board_part:
        br = session.run_tcl(
            f"set_property board_part {board_part} [current_project]", timeout_override=30
        )
        if not br.success:
            return {"success": False, "stage": "set_board_part", "error": br.output}

    r = session.run_tcl(
        f"create_bd_design {{{name}}}; current_bd_design [get_bd_designs {name}]",
        timeout_override=60,
    )
    if not r.success:
        return {"success": False, "error": r.output, "elapsed_ms": r.elapsed_ms}
    return {"success": True, "bd_name": name, "board_part": board_part, "elapsed_ms": r.elapsed_ms}


def _save_bd(session, args):
    if (e := require_project_open(session)):
        return e
    r = session.run_tcl("save_bd_design", timeout_override=60)
    return {"success": r.success, "output": r.output, "elapsed_ms": r.elapsed_ms}


def _close_bd(session, args):
    if (e := require_project_open(session)):
        return e
    r = session.run_tcl("close_bd_design [current_bd_design]", timeout_override=30)
    return {"success": r.success, "output": r.output, "elapsed_ms": r.elapsed_ms}


def _list_bd_cells(session, args):
    if (e := require_project_open(session)):
        return e
    flt = args.get("filter", "*")
    r = session.run_tcl(f"get_bd_cells {{{flt}}}")
    cells = r.output.strip().split() if r.success and r.output.strip() else []
    return {"success": r.success, "filter": flt, "cells": cells, "count": len(cells)}


def _add_ip_to_bd(session, args):
    if (e := require_project_open(session)):
        return e
    if (e := require_args(args, "cell_name", "vlnv")):
        return e
    cell = args["cell_name"]
    vlnv = args["vlnv"]
    config = args.get("config") or {}

    r = session.run_tcl(f"create_bd_cell -type ip -vlnv {vlnv} {cell}", timeout_override=60)
    if not r.success:
        return {"success": False, "stage": "create_bd_cell", "error": r.output}

    if config:
        # Build `-dict {KEY VALUE KEY VALUE ...}` — Vivado expects bracketed list
        cr = session.run_tcl(_config_cmd(cell, config), timeout_override=60)
        if not cr.success:
            return {
                "success": False,
                "stage": "set_property",
                "error": cr.output,
                "cell": cell,
            }

    return {"success": True, "cell": cell, "vlnv": vlnv, "config_applied": len(config)}


def _config_cmd(cell: str, config: dict) -> str:
    kv = " ".join(f"{k} {{{v}}}" for k, v in config.items())
    return f"set_property -dict {{{kv}}} [get_bd_cells {{{cell}}}]"


def _create_bd_port(session, args):
    if (e := require_project_open(session)):
        return e
    if (e := require_args(args, "name")):
        return e
    name = args["name"]
    if args.get("vlnv"):
        mode = args.get("mode", "Slave")
        cmd = f"create_bd_intf_port -mode {mode} -vlnv {args['vlnv']} {{{name}}}"
    else:
        direction = args.get("direction", "I")
        if direction not in ("I", "O", "IO"):
            return err(f"direction must be I, O or IO, got {direction!r}")
        cmd = f"create_bd_port -dir {direction}"
        if args.get("from") is not None:
            cmd += f" -from {int(args['from'])} -to {int(args.get('to', 0))}"
        if args.get("type"):
            cmd += f" -type {args['type']}"
        cmd += f" {{{name}}}"
    r = session.run_tcl(cmd, timeout_override=30)
    if not r.success:
        return err(r.output, command=cmd)
    return {"success": True, "port": name, "command": cmd}


def _add_module_to_bd(session, args):
    if (e := require_project_open(session)):
        return e
    if (e := require_args(args, "module", "cell_name")):
        return e
    cell = args["cell_name"]
    r = session.run_tcl(
        f"create_bd_cell -type module -reference {{{args['module']}}} {{{cell}}}",
        timeout_override=120,
    )
    if not r.success:
        return {
            "success": False,
            "stage": "create_bd_cell",
            "error": r.output,
            "hint": "the module's source must be in the project first (add_sources)",
        }
    config = args.get("config") or {}
    if config:
        cr = session.run_tcl(_config_cmd(cell, config), timeout_override=60)
        if not cr.success:
            return {"success": False, "stage": "set_property", "error": cr.output, "cell": cell}
    return {"success": True, "cell": cell, "module": args["module"], "config_applied": len(config)}


def _configure_bd_cell(session, args):
    if (e := require_project_open(session)):
        return e
    if (e := require_args(args, "cell_name", "config")):
        return e
    r = session.run_tcl(_config_cmd(args["cell_name"], args["config"]), timeout_override=120)
    if not r.success:
        return err(r.output, cell=args["cell_name"])
    return {"success": True, "cell": args["cell_name"], "config_applied": len(args["config"])}


def _connect_bd_net(session, args):
    if (e := require_project_open(session)):
        return e
    if (e := require_args(args, "pin_from", "pin_to")):
        return e
    a = args["pin_from"]
    b = args["pin_to"]
    r = session.run_tcl(
        f"connect_bd_net [get_bd_pins {{{a}}}] [get_bd_pins {{{b}}}]",
        timeout_override=30,
    )
    return {"success": r.success, "pin_from": a, "pin_to": b, "output": r.output}


def _connect_bd_intf_net(session, args):
    if (e := require_project_open(session)):
        return e
    if (e := require_args(args, "intf_from", "intf_to")):
        return e
    a = args["intf_from"]
    b = args["intf_to"]
    r = session.run_tcl(
        f"connect_bd_intf_net [get_bd_intf_pins {{{a}}}] [get_bd_intf_pins {{{b}}}]",
        timeout_override=30,
    )
    return {"success": r.success, "intf_from": a, "intf_to": b, "output": r.output}


def _auto_connect_axi(session, args):
    if (e := require_project_open(session)):
        return e
    if (e := require_args(args, "master", "slave")):
        return e
    master = args["master"]
    slave = args["slave"]
    options = args.get("options") or {}

    cfg = {"Master": master, "Slave": slave, "Clk_master": "Auto", "Clk_slave": "Auto", "Clk_xbar": "Auto"}
    cfg.update(options)
    cfg_str = " ".join(f"{k} {{{v}}}" for k, v in cfg.items())

    cmd = (
        f"apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {{{cfg_str}}} "
        f"[get_bd_intf_pins {{{slave}}}]"
    )
    r = session.run_tcl(cmd, timeout_override=120)
    return {"success": r.success, "master": master, "slave": slave, "output": r.output}


def _apply_ps7_preset(session, args):
    if (e := require_project_open(session)):
        return e
    cell = args.get("cell", "processing_system7_0")
    preset = args.get("apply_board_preset", True)

    cfg = {
        "make_external": "FIXED_IO, DDR",
        "apply_board_preset": "1" if preset else "0",
        "Master": "Disable",
        "Slave": "Disable",
    }
    cfg_str = " ".join(f"{k} {{{v}}}" for k, v in cfg.items())
    cmd = (
        f"apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 "
        f"-config {{{cfg_str}}} [get_bd_cells {{{cell}}}]"
    )
    r = session.run_tcl(cmd, timeout_override=120)
    return {"success": r.success, "cell": cell, "output": r.output}


def _validate_bd(session, args):
    if (e := require_project_open(session)):
        return e
    r = session.run_tcl("validate_bd_design", timeout_override=120)
    # Vivado validate emits both warnings and errors as INFO/CRITICAL WARNING/ERROR
    # lines; classify them.
    errors = [ln for ln in r.output.splitlines() if "ERROR" in ln and "[BD" in ln]
    warnings = [ln for ln in r.output.splitlines() if "WARNING" in ln and "[BD" in ln]
    return {
        "success": r.success and not errors,
        "valid": r.success and not errors,
        "errors": errors,
        "warnings": warnings,
        "output": r.output,
        "elapsed_ms": r.elapsed_ms,
    }


def _regenerate_layout(session, args):
    if (e := require_project_open(session)):
        return e
    r = session.run_tcl("regenerate_bd_layout", timeout_override=60)
    return {"success": r.success, "output": r.output}


def _assign_bd_address(session, args):
    if (e := require_project_open(session)):
        return e
    r = session.run_tcl("assign_bd_address", timeout_override=60)
    return {"success": r.success, "output": r.output}


def _generate_bd_wrapper(session, args):
    if (e := require_project_open(session)):
        return e
    if (e := require_args(args, "bd_name")):
        return e
    bd_name = args["bd_name"]
    set_top = args.get("set_top", True)

    # make_wrapper creates the wrapper file and prints its absolute path on the
    # last non-blank line of stdout. It does NOT add the file to the fileset.
    r = session.run_tcl(
        f"make_wrapper -files [get_files {bd_name}.bd] -top",
        timeout_override=60,
    )
    if not r.success:
        return {"success": False, "stage": "make_wrapper", "error": r.output}

    # Parse wrapper path from make_wrapper output: pick the last line that ends
    # in <bd_name>_wrapper.v (Vivado 2020.1 prints it bare; older/newer print
    # extra status lines).
    wrapper_path = None
    for line in reversed(r.output.splitlines()):
        line = line.strip()
        if line.endswith(f"{bd_name}_wrapper.v") or line.endswith(f"{bd_name}_wrapper.vhd"):
            # Strip a leading "VHDL Output written to : " or similar prefix
            wrapper_path = line.split(":", 1)[-1].strip() if ":" in line and "/" not in line.split(":", 1)[0] else line
            # Handle Windows-style "C:/..." paths which contain a colon in the drive letter
            if line[1:3] == ":/" or line[1:3] == ":\\":
                wrapper_path = line
            break
    if not wrapper_path:
        return {
            "success": False,
            "stage": "locate_wrapper",
            "error": "Could not parse wrapper path from make_wrapper output",
            "make_wrapper_output": r.output,
        }

    add = session.run_tcl(
        f"add_files -norecurse [list {{{wrapper_path}}}]", timeout_override=30
    )
    if not add.success:
        return {
            "success": False,
            "stage": "add_files",
            "error": add.output,
            "wrapper_path": wrapper_path,
        }

    top_set = None
    if set_top:
        top = f"{bd_name}_wrapper"
        sr = session.run_tcl(
            f"set_property top {top} [current_fileset]; update_compile_order -fileset sources_1",
            timeout_override=30,
        )
        if sr.success:
            top_set = top
        else:
            return {
                "success": False,
                "stage": "set_top",
                "error": sr.output,
                "wrapper_path": wrapper_path,
            }

    return {
        "success": True,
        "bd_name": bd_name,
        "wrapper_path": wrapper_path,
        "top": top_set,
    }


HANDLERS = {
    "create_block_design": _create_block_design,
    "save_bd_design": _save_bd,
    "close_bd_design": _close_bd,
    "list_bd_cells": _list_bd_cells,
    "add_ip_to_bd": _add_ip_to_bd,
    "create_bd_port": _create_bd_port,
    "add_module_to_bd": _add_module_to_bd,
    "configure_bd_cell": _configure_bd_cell,
    "connect_bd_net": _connect_bd_net,
    "connect_bd_intf_net": _connect_bd_intf_net,
    "auto_connect_axi": _auto_connect_axi,
    "apply_ps7_preset": _apply_ps7_preset,
    "validate_block_design": _validate_bd,
    "regenerate_bd_layout": _regenerate_layout,
    "assign_bd_address": _assign_bd_address,
    "generate_bd_wrapper": _generate_bd_wrapper,
}
