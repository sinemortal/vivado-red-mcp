"""Design queries — hierarchy, ports, nets, cells."""

from __future__ import annotations

from mcp.types import Tool

from ..parsers import get_hierarchy_depth
from ._common import require_project_open

TOOLS = [
    Tool(
        name="get_design_hierarchy",
        description="Get the design hierarchy (modules and instances), optionally filtered.",
        inputSchema={
            "type": "object",
            "properties": {
                "max_depth": {"type": "integer", "description": "Max hierarchy depth (default: 3)"},
                "instance_pattern": {
                    "type": "string",
                    "description": "Wildcard pattern (e.g., '*cpu*', 'core/alu/*')",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="get_ports",
        description="Get top-level I/O ports of the design.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="get_nets",
        description="Search for nets by pattern (default '*').",
        inputSchema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Wildcard pattern (default: '*')"},
                "limit": {"type": "integer", "description": "Max results (default: 100)"},
            },
            "required": [],
        },
    ),
    Tool(
        name="get_cells",
        description="Search for cells/instances by pattern.",
        inputSchema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Wildcard pattern (default: '*')"},
                "limit": {"type": "integer", "description": "Max results (default: 100)"},
            },
            "required": [],
        },
    ),
]


def _get_design_hierarchy(session, args):
    if (e := require_project_open(session)):
        return e
    max_depth = args.get("max_depth", 3)
    pattern = args.get("instance_pattern", "*")
    r = session.run_tcl(f"get_cells -hierarchical {{{pattern}}}")
    if not (r.success and r.output.strip()):
        return {
            "success": r.success,
            "cells": [],
            "cell_count": 0,
            "error": r.output if not r.success else "No cells found",
            "elapsed_ms": r.elapsed_ms,
        }

    cells = r.output.strip().split()
    filtered = [c for c in cells if get_hierarchy_depth(c) <= max_depth]

    cell_refs = {}
    for c in filtered[:100]:
        rr = session.run_tcl(f"get_property REF_NAME [get_cells {{{c}}}]")
        if rr.success and rr.output.strip():
            cell_refs[c] = rr.output.strip()

    resp = {
        "success": True,
        "cells": filtered[:500],
        "cell_count": len(filtered),
        "cell_modules": cell_refs,
        "max_depth": max_depth,
        "elapsed_ms": r.elapsed_ms,
    }
    if len(filtered) > 500:
        resp["truncated"] = True
        resp["total_cells"] = len(filtered)
        resp["message"] = "Cell list truncated. Use instance_pattern to filter."
    return resp


def _get_ports(session, args):
    if (e := require_project_open(session)):
        return e
    r = session.run_tcl("get_ports *")
    return {"success": r.success, "ports": r.output.split() if r.success else [], "elapsed_ms": r.elapsed_ms}


def _get_nets(session, args):
    if (e := require_project_open(session)):
        return e
    pattern = args.get("pattern", "*")
    limit = args.get("limit", 100)
    r = session.run_tcl(f"lrange [get_nets {{{pattern}}}] 0 {limit - 1}")
    return {"success": r.success, "nets": r.output.split() if r.success else [], "elapsed_ms": r.elapsed_ms}


def _get_cells(session, args):
    if (e := require_project_open(session)):
        return e
    pattern = args.get("pattern", "*")
    limit = args.get("limit", 100)
    r = session.run_tcl(f"lrange [get_cells {{{pattern}}}] 0 {limit - 1}")
    return {"success": r.success, "cells": r.output.split() if r.success else [], "elapsed_ms": r.elapsed_ms}


HANDLERS = {
    "get_design_hierarchy": _get_design_hierarchy,
    "get_ports": _get_ports,
    "get_nets": _get_nets,
    "get_cells": _get_cells,
}
