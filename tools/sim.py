"""Simulation (xsim) tools — 15 tool covering launch/run/probe/breakpoint."""

from __future__ import annotations

from mcp.types import Tool

from ._common import require_project_open

TOOLS = [
    Tool(
        name="launch_simulation",
        description="Launch xsim in behavioral/post-synth/post-impl mode.",
        inputSchema={
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": [
                        "behavioral",
                        "post_synth_func",
                        "post_synth_timing",
                        "post_impl_func",
                        "post_impl_timing",
                    ],
                    "description": "Simulation mode (default: behavioral)",
                }
            },
            "required": [],
        },
    ),
    Tool(
        name="run_simulation",
        description="Run the simulation for a specified time (e.g. 100ns, 1us, all).",
        inputSchema={
            "type": "object",
            "properties": {
                "time": {"type": "string", "description": "100ns | 1us | 10ms | all"}
            },
            "required": ["time"],
        },
    ),
    Tool(
        name="restart_simulation",
        description="Restart the simulation from time 0.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="close_simulation",
        description="Close the current simulation.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="get_simulation_time",
        description="Get the current simulation time (current_time).",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="get_signal_value",
        description="Get current value of a signal in simulation.",
        inputSchema={
            "type": "object",
            "properties": {
                "signal": {"type": "string", "description": "Hierarchical signal path"},
                "radix": {
                    "type": "string",
                    "enum": ["bin", "hex", "dec", "unsigned", "ascii"],
                    "description": "Display radix (default: hex)",
                },
            },
            "required": ["signal"],
        },
    ),
    Tool(
        name="get_signal_values",
        description="Get values of multiple signals matching a wildcard pattern (max 50).",
        inputSchema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Signal pattern, e.g. /tb/dut/*"},
                "radix": {
                    "type": "string",
                    "enum": ["bin", "hex", "dec", "unsigned", "ascii"],
                },
            },
            "required": ["pattern"],
        },
    ),
    Tool(
        name="add_signals_to_wave",
        description="Add signals to the waveform viewer.",
        inputSchema={
            "type": "object",
            "properties": {
                "signals": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["signals"],
        },
    ),
    Tool(
        name="set_simulation_top",
        description="Set the top-level testbench module for simulation.",
        inputSchema={
            "type": "object",
            "properties": {
                "top_module": {"type": "string"},
                "fileset": {"type": "string", "description": "default: sim_1"},
            },
            "required": ["top_module"],
        },
    ),
    Tool(
        name="get_simulation_objects",
        description="List simulation objects in a scope (signals/ports/internal).",
        inputSchema={
            "type": "object",
            "properties": {
                "scope": {"type": "string", "description": "default: /"},
                "filter": {"type": "string", "enum": ["all", "signals", "ports", "internal"]},
            },
            "required": [],
        },
    ),
    Tool(
        name="get_scopes",
        description="List child scopes (hierarchy) in the simulation.",
        inputSchema={
            "type": "object",
            "properties": {
                "parent": {"type": "string", "description": "default: /"}
            },
            "required": [],
        },
    ),
    Tool(
        name="step_simulation",
        description="Step simulation by delta cycles.",
        inputSchema={
            "type": "object",
            "properties": {"count": {"type": "integer", "description": "default: 1"}},
            "required": [],
        },
    ),
    Tool(
        name="add_breakpoint",
        description="Add a breakpoint on signal edge or change.",
        inputSchema={
            "type": "object",
            "properties": {
                "signal": {"type": "string"},
                "condition": {"type": "string", "enum": ["posedge", "negedge", "change"]},
            },
            "required": ["signal"],
        },
    ),
    Tool(
        name="remove_breakpoints",
        description="Remove all breakpoints (remove_bps -all).",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="get_simulation_messages",
        description="Get simulation log messages filtered by severity.",
        inputSchema={
            "type": "object",
            "properties": {
                "severity": {"type": "string", "enum": ["all", "error", "warning", "info"]}
            },
            "required": [],
        },
    ),
]


_MODE_MAP = {
    "behavioral": "behav",
    "post_synth_func": "synth -type func",
    "post_synth_timing": "synth -type timing",
    "post_impl_func": "impl -type func",
    "post_impl_timing": "impl -type timing",
}


def _launch(session, args):
    if (e := require_project_open(session)):
        return e
    mode = args.get("mode", "behavioral")
    sim_mode = _MODE_MAP.get(mode, "behav")
    r = session.run_tcl(f"launch_simulation -mode {sim_mode}")
    return {
        "success": r.success,
        "message": r.output or f"Simulation launched in {mode} mode",
        "elapsed_ms": r.elapsed_ms,
    }


def _run(session, args):
    if (e := require_project_open(session)):
        return e
    t = args.get("time", "100ns")
    r = session.run_tcl("run -all" if t.lower() == "all" else f"run {t}")
    return {"success": r.success, "output": r.output, "elapsed_ms": r.elapsed_ms}


def _restart(session, args):
    if (e := require_project_open(session)):
        return e
    r = session.run_tcl("restart")
    return {
        "success": r.success,
        "message": "Simulation restarted" if r.success else r.output,
        "elapsed_ms": r.elapsed_ms,
    }


def _close(session, args):
    if (e := require_project_open(session)):
        return e
    r = session.run_tcl("close_sim")
    return {
        "success": r.success,
        "message": "Simulation closed" if r.success else r.output,
        "elapsed_ms": r.elapsed_ms,
    }


def _current_time(session, args):
    if (e := require_project_open(session)):
        return e
    r = session.run_tcl("current_time")
    return {"success": r.success, "time": r.output.strip() if r.success else None, "elapsed_ms": r.elapsed_ms}


def _get_value(session, args):
    if (e := require_project_open(session)):
        return e
    signal = args.get("signal", "")
    radix = args.get("radix", "hex")
    r = session.run_tcl(f"get_value -radix {radix} {{{signal}}}")
    return {
        "success": r.success,
        "signal": signal,
        "value": r.output.strip() if r.success else None,
        "radix": radix,
        "elapsed_ms": r.elapsed_ms,
    }


def _get_values(session, args):
    if (e := require_project_open(session)):
        return e
    pattern = args.get("pattern", "/*")
    radix = args.get("radix", "hex")
    sr = session.run_tcl(f"get_objects -filter {{TYPE == signal || TYPE == port}} {{{pattern}}}")
    if not (sr.success and sr.output.strip()):
        return {"success": False, "error": "No signals found matching pattern", "elapsed_ms": sr.elapsed_ms}
    values = {}
    for sig in sr.output.strip().split()[:50]:
        vr = session.run_tcl(f"get_value -radix {radix} {{{sig}}}")
        if vr.success:
            values[sig] = vr.output.strip()
    return {"success": True, "values": values, "radix": radix, "elapsed_ms": sr.elapsed_ms}


def _add_wave(session, args):
    if (e := require_project_open(session)):
        return e
    signals = args.get("signals", [])
    if isinstance(signals, str):
        signals = [signals]
    results = []
    for sig in signals:
        r = session.run_tcl(f"add_wave {{{sig}}}")
        results.append({"signal": sig, "success": r.success})
    return {"success": all(r["success"] for r in results), "results": results}


def _set_top(session, args):
    if (e := require_project_open(session)):
        return e
    top = args.get("top_module", "")
    fileset = args.get("fileset", "sim_1")
    r = session.run_tcl(f"set_property top {top} [get_filesets {fileset}]")
    return {
        "success": r.success,
        "message": f"Set simulation top to {top}" if r.success else r.output,
        "elapsed_ms": r.elapsed_ms,
    }


def _get_objects(session, args):
    if (e := require_project_open(session)):
        return e
    scope = args.get("scope", "/")
    obj_filter = args.get("filter", "all")
    filter_map = {
        "all": "",
        "signals": "-filter {TYPE == signal}",
        "ports": "-filter {TYPE == port}",
        "internal": "-filter {TYPE == signal && IS_PORT == false}",
    }
    fs = filter_map.get(obj_filter, "")
    r = session.run_tcl(f"get_objects {fs} {{{scope}/*}}")
    objects = r.output.strip().split() if r.success and r.output.strip() else []
    return {
        "success": r.success,
        "scope": scope,
        "objects": objects,
        "count": len(objects),
        "elapsed_ms": r.elapsed_ms,
    }


def _get_scopes(session, args):
    if (e := require_project_open(session)):
        return e
    parent = args.get("parent", "/")
    r = session.run_tcl(f"get_scopes {{{parent}/*}}")
    scopes = r.output.strip().split() if r.success and r.output.strip() else []
    return {
        "success": r.success,
        "parent": parent,
        "scopes": scopes,
        "count": len(scopes),
        "elapsed_ms": r.elapsed_ms,
    }


def _step(session, args):
    if (e := require_project_open(session)):
        return e
    count = args.get("count", 1)
    r = session.run_tcl(f"step {count}")
    return {"success": r.success, "output": r.output, "elapsed_ms": r.elapsed_ms}


def _add_bp(session, args):
    if (e := require_project_open(session)):
        return e
    signal = args.get("signal", "")
    condition = args.get("condition", "change")
    cond = {"posedge": "-posedge", "negedge": "-negedge", "change": ""}.get(condition, "")
    r = session.run_tcl(f"add_bp {cond} {{{signal}}}")
    return {
        "success": r.success,
        "signal": signal,
        "condition": condition,
        "message": r.output or f"Breakpoint added on {signal}",
        "elapsed_ms": r.elapsed_ms,
    }


def _remove_bps(session, args):
    if (e := require_project_open(session)):
        return e
    r = session.run_tcl("remove_bps -all")
    return {
        "success": r.success,
        "message": "All breakpoints removed" if r.success else r.output,
        "elapsed_ms": r.elapsed_ms,
    }


def _sim_messages(session, args):
    if (e := require_project_open(session)):
        return e
    severity = args.get("severity", "all")
    if severity == "all":
        r = session.run_tcl("get_msg_config -count")
    else:
        r = session.run_tcl(f"get_msg_config -count -severity {{{severity}}}")
    return {"success": r.success, "messages": r.output, "elapsed_ms": r.elapsed_ms}


HANDLERS = {
    "launch_simulation": _launch,
    "run_simulation": _run,
    "restart_simulation": _restart,
    "close_simulation": _close,
    "get_simulation_time": _current_time,
    "get_signal_value": _get_value,
    "get_signal_values": _get_values,
    "add_signals_to_wave": _add_wave,
    "set_simulation_top": _set_top,
    "get_simulation_objects": _get_objects,
    "get_scopes": _get_scopes,
    "step_simulation": _step,
    "add_breakpoint": _add_bp,
    "remove_breakpoints": _remove_bps,
    "get_simulation_messages": _sim_messages,
}
