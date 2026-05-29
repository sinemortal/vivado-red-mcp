"""Vivado MCP Server — thin orchestrator.

The full tool catalogue lives in the `tools/` subpackage; this module just
wires it into the MCP runtime. See `tools/__init__.py` for the registry.

Architecture:
  - Each tool family (session, project, flow, analysis, design, sim, bd, ip,
    hwmgr, advanced_reports, redpitaya, tcl, docs, feature_requests, reports)
    is a module under `tools/` exposing TOOLS + HANDLERS.
  - `tools/__init__.py` aggregates them into ALL_TOOLS / ALL_HANDLERS and
    asserts every tool has a handler (and vice versa) at import time.
  - `list_tools` returns ALL_TOOLS, `call_tool` dispatches via ALL_HANDLERS,
    wrapping the dict result in TextContent.

Entry point: `python -m vivado_mcp` (or `vivado-mcp` after pip install).
"""

from __future__ import annotations

import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .tools import ALL_HANDLERS, ALL_TOOLS
from .vivado_session import get_session

server = Server("vivado")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return ALL_TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handler = ALL_HANDLERS.get(name)
    if handler is None:
        return [TextContent(type="text", text=json.dumps(
            {"success": False, "error": f"Unknown tool: {name}"}, indent=2
        ))]

    session = get_session()
    try:
        result = handler(session, arguments or {})
    except Exception as ex:  # noqa: BLE001 — surface tracebacks to the caller
        return [TextContent(type="text", text=json.dumps(
            {"success": False, "error": f"{type(ex).__name__}: {ex}", "tool": name},
            indent=2,
        ))]

    if not isinstance(result, dict):
        result = {"success": True, "value": result}
    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
