"""Design flow tools — synthesis, implementation, bitstream."""

from __future__ import annotations

from mcp.types import Tool

from ..parsers import verify_run_status
from ._common import require_project_open

TOOLS = [
    Tool(
        name="run_synthesis",
        description=(
            "Run synthesis on the current project (reset_run -> launch_runs synth_1 "
            "-> wait_on_run). Returns ground-truth status from the run object, not "
            "just text parsing."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "jobs": {"type": "integer", "description": "Parallel jobs (default: 4)"},
                "timeout": {
                    "type": "integer",
                    "description": "Timeout seconds (default: 2400 = 40min). Increase for large designs.",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="run_implementation",
        description=(
            "Run implementation (opt_design -> place_design -> route_design). Returns "
            "ground-truth status from the impl_1 run object."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "jobs": {"type": "integer", "description": "Parallel jobs (default: 4)"},
                "timeout": {
                    "type": "integer",
                    "description": "Timeout seconds (default: 5400 = 90min).",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="generate_bitstream",
        description="Generate bitstream — `launch_runs impl_1 -to_step write_bitstream`.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
]


def _run_synthesis(session, args):
    if (e := require_project_open(session)):
        return e
    jobs = args.get("jobs", 4)
    timeout = args.get("timeout", 2400)
    r = session.run_tcl(
        f"reset_run synth_1; launch_runs synth_1 -jobs {jobs}; wait_on_run synth_1",
        timeout_override=timeout,
    )
    v = verify_run_status(session, "synth_1")
    out = {
        "success": v["actually_succeeded"],
        "output": r.output,
        "elapsed_ms": r.elapsed_ms,
        "run_status": v["status"],
        "run_progress": v["progress"],
    }
    if not r.success and v["actually_succeeded"]:
        out["note"] = "Output contained error-like strings but run completed successfully"
    return out


def _run_implementation(session, args):
    if (e := require_project_open(session)):
        return e
    jobs = args.get("jobs", 4)
    timeout = args.get("timeout", 5400)
    r = session.run_tcl(
        f"launch_runs impl_1 -jobs {jobs}; wait_on_run impl_1",
        timeout_override=timeout,
    )
    v = verify_run_status(session, "impl_1")
    out = {
        "success": v["actually_succeeded"],
        "output": r.output,
        "elapsed_ms": r.elapsed_ms,
        "run_status": v["status"],
        "run_progress": v["progress"],
    }
    if not r.success and v["actually_succeeded"]:
        out["note"] = "Output contained error-like strings but run completed successfully"
    return out


def _generate_bitstream(session, args):
    if (e := require_project_open(session)):
        return e
    r = session.run_tcl("launch_runs impl_1 -to_step write_bitstream; wait_on_run impl_1")
    return {"success": r.success, "output": r.output, "elapsed_ms": r.elapsed_ms}


HANDLERS = {
    "run_synthesis": _run_synthesis,
    "run_implementation": _run_implementation,
    "generate_bitstream": _generate_bitstream,
}
