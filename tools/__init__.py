"""Aggregated tool registry for the Vivado MCP server.

Each submodule exposes:
- `TOOLS: list[mcp.types.Tool]` — schema declarations
- `HANDLERS: dict[str, Callable[[VivadoSession, dict], dict]]` — impl by name

This module merges them into `ALL_TOOLS` / `ALL_HANDLERS`. An import-time
assert guarantees every declared tool has a handler and vice versa, so
mismatches become loud at startup instead of silent at call time.
"""

from __future__ import annotations

from mcp.types import Tool

from . import (
    advanced_reports,
    analysis,
    bd,
    deploy,
    design,
    docs,
    feature_requests,
    flow,
    hwmgr,
    ip,
    project,
    redpitaya,
    redpitaya_repo,
    reports as report_mgmt,
    session,
    sim,
    tcl,
)

_MODULES = [
    session,
    project,
    flow,
    analysis,
    design,
    sim,
    tcl,
    bd,
    ip,
    hwmgr,
    advanced_reports,
    redpitaya,
    redpitaya_repo,
    deploy,
    docs,
    feature_requests,
    report_mgmt,
]

ALL_TOOLS: list[Tool] = []
ALL_HANDLERS: dict = {}

for _m in _MODULES:
    ALL_TOOLS.extend(getattr(_m, "TOOLS", []))
    ALL_HANDLERS.update(getattr(_m, "HANDLERS", {}))

# Coherence check — every declared tool must have a handler and vice versa.
_declared = {t.name for t in ALL_TOOLS}
_handled = set(ALL_HANDLERS.keys())
_missing_impl = _declared - _handled
_missing_decl = _handled - _declared
if _missing_impl or _missing_decl:
    raise RuntimeError(
        f"Tool registry inconsistency. Missing handlers: {sorted(_missing_impl)}; "
        f"missing declarations: {sorted(_missing_decl)}"
    )

__all__ = ["ALL_TOOLS", "ALL_HANDLERS"]
