"""Advanced reports — power, DRC, methodology, QoR, clock interaction.

Each tool writes the full Vivado output to /tmp/vivado_mcp/ (cached with a
report_id) and returns structured parsed data plus a truncated inline preview.
Use `read_report_section` with the returned report_id for the full text.
"""

from __future__ import annotations

from pathlib import Path

from mcp.types import Tool

from ..parsers import (
    MAX_RESPONSE_CHARS,
    parse_drc_violations,
    parse_power_summary,
    truncate_response,
)
from ..reports import REPORTS_DIR, cache_report, ensure_reports_dir, generate_report_id
from ._common import require_project_open, run_design_cmd

TOOLS = [
    Tool(
        name="report_power",
        description=(
            "Run report_power and return parsed totals (total/dynamic/static W) + a "
            "truncated raw block. Full output stored at /tmp/vivado_mcp/."
        ),
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="report_drc",
        description=(
            "Run report_drc and return parsed violations list (severity/code/message). "
            "Use after place_design/route_design to catch design-rule problems."
        ),
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="report_methodology",
        description=(
            "Run report_methodology (UltraFast methodology checks). Returns violation "
            "list grouped by severity."
        ),
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="report_qor_assessment",
        description="Run report_qor_assessment (overall design quality score).",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="report_clock_interaction",
        description=(
            "Run report_clock_interaction to find cross-clock paths (timed/async/"
            "unconstrained)."
        ),
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
]


def _run_with_file(session, kind: str, tcl_template: str, timeout: int = 300):
    ensure_reports_dir()
    rid = generate_report_id()
    out_file = REPORTS_DIR / f"{kind}_{rid}.txt"
    cmd = tcl_template.format(file=out_file)
    r = run_design_cmd(session, cmd, timeout=timeout)
    text = ""
    if out_file.exists():
        try:
            text = out_file.read_text(errors="replace")
            cache_report(rid, out_file, kind)
        except OSError:
            pass
    return r, rid, str(out_file), text


def _report_power(session, args):
    if (e := require_project_open(session)):
        return e
    r, rid, path, text = _run_with_file(session, "power", "report_power -file {{{file}}}")
    parsed = parse_power_summary(text)
    inline = truncate_response(text, MAX_RESPONSE_CHARS // 2)
    return {
        "success": r.success,
        "report_id": rid,
        "file_path": path,
        "total_w": parsed["total_w"],
        "dynamic_w": parsed["dynamic_w"],
        "static_w": parsed["static_w"],
        "raw_preview": inline["content"],
        "raw_truncated": inline["truncated"],
        "elapsed_ms": r.elapsed_ms,
    }


def _report_drc(session, args):
    if (e := require_project_open(session)):
        return e
    r, rid, path, text = _run_with_file(session, "drc", "report_drc -file {{{file}}}")
    violations = parse_drc_violations(text)
    by_sev: dict = {}
    for v in violations:
        by_sev.setdefault(v["severity"], []).append(v)
    inline = truncate_response(text, MAX_RESPONSE_CHARS // 2)
    return {
        "success": r.success and not by_sev.get("ERROR"),
        "report_id": rid,
        "file_path": path,
        "violation_count": len(violations),
        "by_severity": {k: len(v) for k, v in by_sev.items()},
        "violations": violations[:50],
        "raw_preview": inline["content"],
        "raw_truncated": inline["truncated"],
        "elapsed_ms": r.elapsed_ms,
    }


def _report_methodology(session, args):
    if (e := require_project_open(session)):
        return e
    r, rid, path, text = _run_with_file(
        session, "methodology", "report_methodology -file {{{file}}}", timeout=600
    )
    violations = parse_drc_violations(text)  # same line format as DRC
    by_sev: dict = {}
    for v in violations:
        by_sev.setdefault(v["severity"], []).append(v)
    inline = truncate_response(text, MAX_RESPONSE_CHARS // 2)
    return {
        "success": r.success,
        "report_id": rid,
        "file_path": path,
        "violation_count": len(violations),
        "by_severity": {k: len(v) for k, v in by_sev.items()},
        "violations": violations[:50],
        "raw_preview": inline["content"],
        "raw_truncated": inline["truncated"],
        "elapsed_ms": r.elapsed_ms,
    }


def _report_qor(session, args):
    if (e := require_project_open(session)):
        return e
    r, rid, path, text = _run_with_file(
        session, "qor", "report_qor_assessment -file {{{file}}}", timeout=300
    )
    inline = truncate_response(text, MAX_RESPONSE_CHARS)
    return {
        "success": r.success,
        "report_id": rid,
        "file_path": path,
        "raw_preview": inline["content"],
        "raw_truncated": inline["truncated"],
        "elapsed_ms": r.elapsed_ms,
    }


def _report_clock_interaction(session, args):
    if (e := require_project_open(session)):
        return e
    r, rid, path, text = _run_with_file(
        session,
        "clock_interaction",
        "report_clock_interaction -file {{{file}}}",
        timeout=180,
    )
    inline = truncate_response(text, MAX_RESPONSE_CHARS)
    return {
        "success": r.success,
        "report_id": rid,
        "file_path": path,
        "raw_preview": inline["content"],
        "raw_truncated": inline["truncated"],
        "elapsed_ms": r.elapsed_ms,
    }


HANDLERS = {
    "report_power": _report_power,
    "report_drc": _report_drc,
    "report_methodology": _report_methodology,
    "report_qor_assessment": _report_qor,
    "report_clock_interaction": _report_clock_interaction,
}
