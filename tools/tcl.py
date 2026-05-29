"""Raw TCL escape hatch + script runner."""

from __future__ import annotations

from pathlib import Path

from mcp.types import Tool

from ._common import err, require_project_open

TOOLS = [
    Tool(
        name="run_tcl",
        description=(
            "Execute a raw TCL command in Vivado. Use for advanced ops not covered "
            "by other tools."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "TCL command to execute"},
                "timeout": {"type": "integer", "description": "Optional command timeout in seconds"},
            },
            "required": ["command"],
        },
    ),
    Tool(
        name="run_tcl_script",
        description=(
            "Source a .tcl script file in the Vivado session (uses `source` under the hood). "
            "Helpful for replaying canonical Red Pitaya / Xilinx reference scripts."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to .tcl script"},
                "timeout": {"type": "integer", "description": "Optional script timeout in seconds"},
            },
            "required": ["path"],
        },
    ),
]


def _run_tcl(session, args):
    if (e := require_project_open(session)):
        return e
    command = args.get("command", "")
    timeout = args.get("timeout")
    r = session.run_tcl(command, timeout_override=timeout)
    return {"success": r.success, "output": r.output, "elapsed_ms": r.elapsed_ms}


def _run_tcl_script(session, args):
    if (e := require_project_open(session)):
        return e
    path = args.get("path", "")
    if not path:
        return err("'path' is required")
    if not Path(path).exists():
        return err(f"Script not found: {path}")
    timeout = args.get("timeout", 600)
    r = session.run_tcl(f"source {{{path}}}", timeout_override=timeout)
    return {"success": r.success, "output": r.output, "elapsed_ms": r.elapsed_ms, "path": path}


HANDLERS = {
    "run_tcl": _run_tcl,
    "run_tcl_script": _run_tcl_script,
}
