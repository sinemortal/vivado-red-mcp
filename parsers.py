"""Parsers for Vivado text reports + response helpers.

Extracted from server.py during the refactor that split the monolithic
dispatcher into a `tools/` package. Importable from any tool module.
"""

from __future__ import annotations

import re

MAX_RESPONSE_CHARS = 8000


def truncate_response(content: str, max_chars: int = MAX_RESPONSE_CHARS) -> dict:
    total_chars = len(content)
    total_lines = content.count("\n") + 1

    if total_chars <= max_chars:
        return {
            "content": content,
            "truncated": False,
            "total_chars": total_chars,
            "total_lines": total_lines,
        }

    truncated_content = content[:max_chars]
    last_newline = truncated_content.rfind("\n")
    if last_newline > max_chars * 0.8:
        truncated_content = truncated_content[:last_newline]

    truncated_lines = truncated_content.count("\n") + 1
    return {
        "content": truncated_content,
        "truncated": True,
        "total_chars": total_chars,
        "total_lines": total_lines,
        "returned_chars": len(truncated_content),
        "returned_lines": truncated_lines,
        "truncation_message": (
            f"Output truncated ({total_chars:,} chars -> "
            f"{len(truncated_content):,} chars). Use generate_full_report for "
            f"complete output."
        ),
    }


def verify_run_status(session, run_name: str) -> dict:
    """Query Vivado run STATUS/PROGRESS properties (ground truth)."""
    status_result = session.run_tcl(f"get_property STATUS [get_runs {run_name}]")
    progress_result = session.run_tcl(f"get_property PROGRESS [get_runs {run_name}]")

    status = status_result.output.strip() if status_result.success else "unknown"
    progress = progress_result.output.strip() if progress_result.success else "unknown"
    status_lower = status.lower()
    return {
        "run_name": run_name,
        "status": status,
        "progress": progress,
        "actually_succeeded": "complete" in status_lower,
        "actually_failed": "error" in status_lower,
    }


def get_hierarchy_depth(path: str) -> int:
    return path.count("/")


def parse_timing_summary(output: str) -> dict:
    result = {
        "wns": None,
        "tns": None,
        "whs": None,
        "ths": None,
        "wpws": None,
        "tpws": None,
        "failing_endpoints": 0,
        "met": False,
        "raw": output,
    }

    # report_timing_summary prints the "Design Timing Summary" as a table:
    #     WNS(ns)  TNS(ns)  TNS Failing Endpoints  TNS Total Endpoints  WHS(ns) ...
    #     -------  -------  ---------------------  -------------------  ------- ...
    #       5.493    0.000                      0                   26    0.252 ...
    # (12 columns: WNS TNS fail total | WHS THS fail total | WPWS TPWS fail total)
    # A group with no paths prints NA (e.g. a PS-only design has only pulse
    # width checks); those values stay None.
    table = re.search(r"^\s*WNS\(ns\)\s+TNS\(ns\).*\n\s*-[-\s]*\n\s*(.+)$", output, re.MULTILINE)
    if table:
        cols = table.group(1).split()
        if len(cols) >= 12:
            def num(i, cast=float):
                try:
                    return cast(cols[i])
                except ValueError:  # "NA"
                    return None
            result["wns"], result["tns"] = num(0), num(1)
            result["whs"], result["ths"] = num(4), num(5)
            result["wpws"], result["tpws"] = num(8), num(9)
            result["failing_endpoints"] = sum(
                n for n in (num(2, int), num(6, int), num(10, int)) if n
            )
    else:
        # Fallback for "WNS(ns) : x" style output.
        for key in ("wns", "tns", "whs", "ths", "wpws", "tpws"):
            m = re.search(rf"{key.upper()}\(ns\)\s*:\s*([-\d.]+)", output)
            if m:
                result[key] = float(m.group(1))
        fail_match = re.search(r"(\d+)\s+failing\s+endpoint", output, re.IGNORECASE)
        if fail_match:
            result["failing_endpoints"] = int(fail_match.group(1))

    # Met = every reported slack is non-negative. A fully unconstrained design
    # (all NA) is not "met": there is nothing checking it.
    slacks = [result[k] for k in ("wns", "whs", "wpws") if result[k] is not None]
    if slacks:
        result["met"] = all(s >= 0 for s in slacks)

    return result


def parse_utilization(output: str) -> dict:
    result = {
        "lut": {"used": 0, "available": 0, "percent": 0},
        "ff": {"used": 0, "available": 0, "percent": 0},
        "bram": {"used": 0, "available": 0, "percent": 0},
        "dsp": {"used": 0, "available": 0, "percent": 0},
        "io": {"used": 0, "available": 0, "percent": 0},
        "raw": output,
    }

    # Row layout: | Site Type | Used | Fixed | [Prohibited] | Available | Util% |
    # "Prohibited" only exists in newer releases (absent in 2020.1); Util% can
    # be "<0.01" for tiny designs.
    num = r"(\d+(?:\.\d+)?)"
    row = rf"\s*\|\s*{num}\s*\|\s*\d+(?:\.\d+)?\s*\|(?:\s*\d+(?:\.\d+)?\s*\|)?\s*{num}\s*\|\s*<?\s*([\d.]+)"
    patterns = {
        "lut": r"(?:Slice LUTs|CLB LUTs)" + row,
        "ff": r"(?:Slice Registers|CLB Registers)" + row,
        "bram": r"Block RAM Tile" + row,
        "dsp": r"DSPs?" + row,
        "io": r"(?:Bonded IOB|Bonded User I/O)" + row,
    }

    for resource, pattern in patterns.items():
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            result[resource]["used"] = float(match.group(1))
            result[resource]["available"] = float(match.group(2))
            result[resource]["percent"] = float(match.group(3))

    return result


def parse_messages(output: str) -> dict:
    result = {
        "errors": [],
        "critical_warnings": [],
        "warnings": [],
        "info": [],
        "raw": output,
    }
    for line in output.split("\n"):
        line = line.strip()
        if re.match(r"ERROR:", line):
            result["errors"].append(line)
        elif re.match(r"CRITICAL WARNING:", line):
            result["critical_warnings"].append(line)
        elif re.match(r"WARNING:", line):
            result["warnings"].append(line)
        elif re.match(r"INFO:", line):
            result["info"].append(line)
    return result


def parse_timing_paths_summary(output: str, max_paths: int = 5) -> list[dict]:
    paths: list[dict] = []
    path_blocks = re.split(r"\n(?=Slack\s*(?:\([A-Z]+\))?\s*:)", output)

    for block in path_blocks:
        if not block.strip() or "Slack" not in block:
            continue

        path_info: dict = {}
        slack_match = re.search(r"Slack\s*(?:\([A-Z]+\))?\s*:\s*([-\d.]+)\s*ns", block)
        if slack_match:
            path_info["slack"] = float(slack_match.group(1))

        for key, pat in [
            ("source", r"Source:\s*(\S+)"),
            ("destination", r"Destination:\s*(\S+)"),
            ("source_clock", r"Source Clock:\s*(\S+)"),
            ("dest_clock", r"Destination Clock:\s*(\S+)"),
        ]:
            m = re.search(pat, block)
            if m:
                path_info[key] = m.group(1)

        for key, pat in [
            ("requirement", r"Requirement:\s*([-\d.]+)\s*ns"),
            ("data_path_delay", r"Data Path Delay:\s*([-\d.]+)\s*ns"),
        ]:
            m = re.search(pat, block)
            if m:
                path_info[key] = float(m.group(1))

        m = re.search(r"Logic Levels:\s*(\d+)", block)
        if m:
            path_info["logic_levels"] = int(m.group(1))

        if "slack" in path_info:
            paths.append(path_info)
        if len(paths) >= max_paths:
            break

    return paths


def parse_drc_violations(output: str) -> list[dict]:
    """Parse `report_drc` text output into structured violations."""
    violations: list[dict] = []
    current: dict | None = None
    for line in output.splitlines():
        m = re.match(
            r"^(?P<sev>CRITICAL WARNING|WARNING|ERROR|INFO)\s*:\s*\[(?P<code>[^\]]+)\]\s*(?P<msg>.+)$",
            line.strip(),
        )
        if m:
            if current:
                violations.append(current)
            current = {
                "severity": m.group("sev"),
                "code": m.group("code"),
                "message": m.group("msg").strip(),
            }
        elif current and line.strip():
            current["message"] += " " + line.strip()
    if current:
        violations.append(current)
    return violations


def parse_power_summary(output: str) -> dict:
    """Best-effort parse of `report_power` total power lines."""
    result: dict = {"total_w": None, "dynamic_w": None, "static_w": None, "raw": output}
    m = re.search(r"Total On-Chip Power.*?([\d.]+)\s*W", output, re.IGNORECASE | re.DOTALL)
    if m:
        result["total_w"] = float(m.group(1))
    m = re.search(r"Dynamic.*?([\d.]+)\s*W", output, re.IGNORECASE)
    if m:
        result["dynamic_w"] = float(m.group(1))
    m = re.search(r"Device Static.*?([\d.]+)\s*W", output, re.IGNORECASE)
    if m:
        result["static_w"] = float(m.group(1))
    return result
