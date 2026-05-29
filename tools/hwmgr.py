"""Hardware Manager — JTAG bitstream programming.

Reference: UG908 §Programming the Device.
For Red Pitaya the canonical deploy path is `scp .bit.bin + /dev/xdevcfg`;
HW Manager is useful when a Xilinx JTAG cable (Platform Cable USB II / FTDI)
is plugged into the JTAG header on the board.
"""

from __future__ import annotations

from pathlib import Path

from mcp.types import Tool

from ._common import err, require_args, require_project_open

TOOLS = [
    Tool(
        name="open_hw_manager",
        description="Open the Hardware Manager (no JTAG connection yet).",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="close_hw_manager",
        description="Close the Hardware Manager.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="connect_hw_server",
        description=(
            "Connect to a hw_server (cs_server). Default URL is localhost:3121 — the "
            "value Vivado uses when running hw_server locally."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "host:port (default: localhost:3121)",
                }
            },
            "required": [],
        },
    ),
    Tool(
        name="refresh_hw_device",
        description=(
            "Refresh the currently selected hardware device (re-reads JTAG chain "
            "state). Call after re-plugging a cable."
        ),
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="program_device",
        description=(
            "Program a .bit onto the first device on the JTAG chain. Sequence: "
            "open_hw_target -> set PROGRAM.FILE -> program_hw_devices. The hardware "
            "must already be connected (`open_hw_manager` + `connect_hw_server`)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "bit_file": {"type": "string", "description": "Absolute path to .bit"},
                "probes_file": {
                    "type": "string",
                    "description": "Optional ILA probes .ltx file",
                },
            },
            "required": ["bit_file"],
        },
    ),
]


def _open_hw(session, args):
    if (e := require_project_open(session)):
        return e
    r = session.run_tcl("open_hw_manager", timeout_override=30)
    return {"success": r.success, "output": r.output}


def _close_hw(session, args):
    if (e := require_project_open(session)):
        return e
    r = session.run_tcl("close_hw_manager", timeout_override=30)
    return {"success": r.success, "output": r.output}


def _connect_hw_server(session, args):
    if (e := require_project_open(session)):
        return e
    url = args.get("url", "localhost:3121")
    r = session.run_tcl(f"connect_hw_server -url {url}", timeout_override=30)
    return {"success": r.success, "url": url, "output": r.output}


def _refresh_hw_device(session, args):
    if (e := require_project_open(session)):
        return e
    r = session.run_tcl("refresh_hw_device [current_hw_device]", timeout_override=30)
    return {"success": r.success, "output": r.output}


def _program_device(session, args):
    if (e := require_project_open(session)):
        return e
    if (e := require_args(args, "bit_file")):
        return e
    bit = args["bit_file"]
    if not Path(bit).exists():
        return err(f".bit file not found: {bit}")
    probes = args.get("probes_file")

    cmds = ["open_hw_target", "current_hw_device [lindex [get_hw_devices] 0]"]
    cmds.append(f"set_property PROGRAM.FILE {{{bit}}} [current_hw_device]")
    if probes:
        cmds.append(f"set_property PROBES.FILE {{{probes}}} [current_hw_device]")
    cmds.append("program_hw_devices [current_hw_device]")
    cmds.append("refresh_hw_device [current_hw_device]")

    r = session.run_tcl("; ".join(cmds), timeout_override=180)
    return {"success": r.success, "bit_file": bit, "probes_file": probes, "output": r.output}


HANDLERS = {
    "open_hw_manager": _open_hw,
    "close_hw_manager": _close_hw,
    "connect_hw_server": _connect_hw_server,
    "refresh_hw_device": _refresh_hw_device,
    "program_device": _program_device,
}
