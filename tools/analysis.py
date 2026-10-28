"""Reports & analysis — timing summary/paths, utilization, clocks, messages."""

from __future__ import annotations

from mcp.types import Tool

from ..parsers import (
    MAX_RESPONSE_CHARS,
    parse_messages,
    parse_timing_paths_summary,
    parse_timing_summary,
    parse_utilization,
    truncate_response,
)
from ._common import require_project_open, run_design_cmd

TOOLS = [
    Tool(
        name="get_timing_summary",
        description=(
            "Get timing summary (WNS, TNS, WHS, THS). Returns parsed metrics by default. "
            "Use generate_full_report for raw output."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "report_type": {
                    "type": "string",
                    "description": "summary (default), setup, hold, or all",
                },
                "detail_level": {
                    "type": "string",
                    "enum": ["summary", "standard", "full"],
                    "description": "summary | standard (+ truncated raw) | full (+ complete raw)",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="get_timing_paths",
        description=(
            "Get failing/critical timing paths. Returns structured summary by default; "
            "use detail_level=standard|full for the raw text too."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "num_paths": {"type": "integer", "description": "Number of paths (default: 10)"},
                "slack_threshold": {
                    "type": "number",
                    "description": "Only show paths with slack < this (default: 0 = failing paths)",
                },
                "path_type": {"type": "string", "description": "setup (default) or hold"},
                "from_pin": {"type": "string", "description": "Filter -from pattern"},
                "to_pin": {"type": "string", "description": "Filter -to pattern"},
                "through": {"type": "string", "description": "Filter -through pattern"},
                "clock": {"type": "string", "description": "Filter by clock domain"},
                "detail_level": {
                    "type": "string",
                    "enum": ["summary", "standard", "full"],
                    "description": "summary (default) | standard | full",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="get_utilization",
        description=(
            "Resource utilization (LUT/FF/BRAM/DSP/IO). Parsed only by default."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "hierarchical": {"type": "boolean", "description": "Hierarchical breakdown (default: false)"},
                "detail_level": {"type": "string", "enum": ["summary", "standard", "full"]},
                "module_filter": {"type": "string", "description": "Wildcard for hierarchical filter"},
                "threshold_percent": {
                    "type": "number",
                    "description": "Mark resources below this util%% as below_threshold",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="get_clocks",
        description="Get clock information and constraints (report_clocks).",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="get_messages",
        description="Get Vivado messages filtered by severity (error/critical/warning/all).",
        inputSchema={
            "type": "object",
            "properties": {
                "severity": {
                    "type": "string",
                    "description": "all (default) | error | critical | warning",
                }
            },
            "required": [],
        },
    ),
]


def _apply_detail(parsed: dict, raw_key: str, detail_level: str) -> None:
    """Mutate parsed dict to drop/truncate raw output per detail_level."""
    if detail_level == "summary":
        parsed.pop(raw_key, None)
        return
    if raw_key not in parsed:
        return
    max_chars = MAX_RESPONSE_CHARS // 2 if detail_level == "standard" else MAX_RESPONSE_CHARS
    t = truncate_response(parsed[raw_key], max_chars)
    parsed[raw_key] = t["content"]
    if t["truncated"]:
        parsed["raw_truncated"] = True
        parsed["raw_total_chars"] = t["total_chars"]
        if detail_level == "full":
            parsed["truncation_message"] = t["truncation_message"]


def _get_timing_summary(session, args):
    if (e := require_project_open(session)):
        return e
    detail_level = args.get("detail_level", "summary")
    r = run_design_cmd(session, "report_timing_summary -no_header -return_string")
    parsed = parse_timing_summary(r.output)
    parsed["success"] = r.success
    parsed["elapsed_ms"] = r.elapsed_ms
    if r.opened_run:
        parsed["opened_run"] = r.opened_run
    if not r.success:
        parsed["error"] = r.output
    _apply_detail(parsed, "raw", detail_level)
    return parsed


def _get_timing_paths(session, args):
    if (e := require_project_open(session)):
        return e
    num_paths = args.get("num_paths", 10)
    slack_threshold = args.get("slack_threshold", 0)
    path_type = args.get("path_type", "setup")
    detail_level = args.get("detail_level", "summary")

    delay_type = "max" if path_type == "setup" else "min"
    cmd = (
        f"report_timing -delay_type {delay_type} -max_paths {num_paths} "
        f"-slack_lesser_than {slack_threshold}"
    )
    for k, opt in [("from_pin", "-from"), ("to_pin", "-to"), ("through", "-through")]:
        v = args.get(k)
        if v:
            cmd += f" {opt} {{{v}}}"
    clock = args.get("clock")
    if clock:
        cmd += f" -filter {{CLOCK == {clock}}}"
    cmd += " -return_string"

    r = run_design_cmd(session, cmd)

    response = {
        "success": r.success,
        "elapsed_ms": r.elapsed_ms,
        "filters_applied": {
            "path_type": path_type,
            "num_paths": num_paths,
            "slack_threshold": slack_threshold,
        },
    }
    for k in ["from_pin", "to_pin", "through", "clock"]:
        if args.get(k):
            response["filters_applied"][k] = args[k]

    if r.success:
        paths = parse_timing_paths_summary(r.output, max_paths=num_paths)
        response["paths"] = paths
        response["path_count"] = len(paths)
        if detail_level != "summary":
            t = truncate_response(
                r.output,
                MAX_RESPONSE_CHARS // 2 if detail_level == "standard" else MAX_RESPONSE_CHARS,
            )
            response["raw"] = t["content"]
            if t["truncated"]:
                response["raw_truncated"] = True
                response["raw_total_chars"] = t["total_chars"]
                if detail_level == "full":
                    response["truncation_message"] = t["truncation_message"]
    else:
        response["error"] = r.output
    return response


def _get_utilization(session, args):
    if (e := require_project_open(session)):
        return e
    hierarchical = args.get("hierarchical", False)
    detail_level = args.get("detail_level", "summary")
    module_filter = args.get("module_filter")
    threshold_percent = args.get("threshold_percent")

    cmd = "report_utilization -return_string"
    if hierarchical:
        cmd += " -hierarchical"
        if module_filter:
            cmd += f" -hierarchical_pattern {{{module_filter}}}"
    r = run_design_cmd(session, cmd)
    parsed = parse_utilization(r.output)
    parsed["success"] = r.success
    parsed["elapsed_ms"] = r.elapsed_ms
    if r.opened_run:
        parsed["opened_run"] = r.opened_run
    if not r.success:
        parsed["error"] = r.output

    if threshold_percent is not None:
        for res in ["lut", "ff", "bram", "dsp", "io"]:
            if parsed.get(res) and parsed[res]["percent"] < threshold_percent:
                parsed[res]["below_threshold"] = True

    _apply_detail(parsed, "raw", detail_level)
    return parsed


def _get_clocks(session, args):
    if (e := require_project_open(session)):
        return e
    r = run_design_cmd(session, "report_clocks -return_string")
    return {"success": r.success, "clocks": r.output, "elapsed_ms": r.elapsed_ms}


def _get_messages(session, args):
    if (e := require_project_open(session)):
        return e
    severity = args.get("severity", "all")
    r = session.run_tcl("get_msg_config -rules")
    parsed = parse_messages(r.output)
    if severity != "all":
        filtered = {
            "error": parsed["errors"],
            "critical": parsed["critical_warnings"],
            "warning": parsed["warnings"],
        }.get(severity, [])
        parsed = {severity: filtered, "raw": parsed["raw"]}
    parsed["success"] = r.success
    return parsed


HANDLERS = {
    "get_timing_summary": _get_timing_summary,
    "get_timing_paths": _get_timing_paths,
    "get_utilization": _get_utilization,
    "get_clocks": _get_clocks,
    "get_messages": _get_messages,
}
