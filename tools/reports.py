"""Report file management tools — generate_full_report, read_report_section."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from mcp.types import Tool

from ..reports import REPORTS_DIR, cache_report, ensure_reports_dir, generate_report_id, lookup_report
from ._common import err, require_project_open

TOOLS = [
    Tool(
        name="generate_full_report",
        description=(
            "Generate a full Vivado report to a file. Use when inline reports get "
            "truncated or you need the complete output. Returns a report_id usable with "
            "read_report_section."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "report_type": {
                    "type": "string",
                    "enum": [
                        "timing",
                        "timing_summary",
                        "utilization",
                        "hierarchy",
                        "clocks",
                        "power",
                        "drc",
                        "methodology",
                        "qor_assessment",
                    ],
                },
                "options": {
                    "type": "object",
                    "description": "Report-specific options (e.g. {hierarchical: true})",
                },
                "output_file": {
                    "type": "string",
                    "description": "Optional custom output path",
                },
            },
            "required": ["report_type"],
        },
    ),
    Tool(
        name="read_report_section",
        description=(
            "Read a section of a previously generated report. Provide report_id (from "
            "generate_full_report) or a direct file_path."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "report_id": {"type": "string"},
                "file_path": {"type": "string"},
                "start_line": {"type": "integer", "description": "1-indexed (default: 1)"},
                "num_lines": {"type": "integer", "description": "default: 100"},
                "search_pattern": {
                    "type": "string",
                    "description": "Regex to locate a section; returns context around first match",
                },
            },
            "required": [],
        },
    ),
]

_REPORT_COMMANDS = {
    "timing": "report_timing -max_paths 100",
    "timing_summary": "report_timing_summary",
    "utilization": "report_utilization",
    "hierarchy": "report_hierarchy",
    "clocks": "report_clocks",
    "power": "report_power",
    "drc": "report_drc",
    "methodology": "report_methodology",
    "qor_assessment": "report_qor_assessment",
}


def _generate_full_report(session, args):
    if (e := require_project_open(session)):
        return e
    report_type = args.get("report_type", "timing")
    options = args.get("options") or {}
    output_file = args.get("output_file")

    ensure_reports_dir()
    report_id = generate_report_id()
    file_path = Path(output_file) if output_file else REPORTS_DIR / f"{report_type}_{report_id}.txt"

    base_cmd = _REPORT_COMMANDS.get(report_type, f"report_{report_type}")
    if report_type == "utilization" and options.get("hierarchical"):
        base_cmd += " -hierarchical"
    if report_type == "timing" and options.get("num_paths"):
        base_cmd = base_cmd.replace("-max_paths 100", f"-max_paths {options['num_paths']}")

    cmd = f"{base_cmd} -file {{{file_path}}}"
    r = session.run_tcl(cmd)
    if not r.success:
        return {"success": False, "error": r.output, "elapsed_ms": r.elapsed_ms}

    try:
        meta = cache_report(report_id, file_path, report_type)
        return {
            "success": True,
            "report_id": report_id,
            "file_path": str(file_path),
            "report_type": report_type,
            "size_bytes": meta["size_bytes"],
            "line_count": meta["line_count"],
            "message": f"Report written to {file_path}. Use read_report_section to read portions.",
            "elapsed_ms": r.elapsed_ms,
        }
    except OSError as ex:
        return {
            "success": False,
            "error": f"Report generated but could not read file info: {ex}",
            "file_path": str(file_path),
            "elapsed_ms": r.elapsed_ms,
        }


def _read_report_section(session, args):
    report_id = args.get("report_id")
    file_path = args.get("file_path")
    start_line = args.get("start_line", 1)
    num_lines = args.get("num_lines", 100)
    search_pattern = args.get("search_pattern")

    if report_id:
        meta = lookup_report(report_id)
        if meta:
            file_path = meta["file_path"]
        else:
            possible = list(REPORTS_DIR.glob(f"*_{report_id}.txt"))
            if possible:
                file_path = str(possible[0])
            else:
                return err(f"Report ID '{report_id}' not found in cache or reports directory")

    if not file_path:
        return err("Either report_id or file_path must be provided")

    file_path_p = Path(file_path)
    if not file_path_p.exists():
        return err(f"File not found: {file_path}")

    try:
        with open(file_path_p) as f:
            all_lines = f.readlines()
    except OSError as ex:
        return err(f"Error reading file: {ex}")

    total_lines = len(all_lines)
    if search_pattern:
        pattern = re.compile(search_pattern, re.IGNORECASE)
        found = False
        for i, line in enumerate(all_lines):
            if pattern.search(line):
                context_before = num_lines // 4
                start_line = max(1, i + 1 - context_before)
                found = True
                break
        if not found:
            return {
                "success": True,
                "warning": f"Pattern '{search_pattern}' not found in file",
                "total_lines": total_lines,
                "file_path": str(file_path_p),
            }

    start_idx = max(0, start_line - 1)
    end_idx = min(total_lines, start_idx + num_lines)
    selected = all_lines[start_idx:end_idx]

    return {
        "success": True,
        "file_path": str(file_path_p),
        "start_line": start_idx + 1,
        "end_line": end_idx,
        "total_lines": total_lines,
        "returned_lines": len(selected),
        "content": "".join(selected),
    }


HANDLERS = {
    "generate_full_report": _generate_full_report,
    "read_report_section": _read_report_section,
}
