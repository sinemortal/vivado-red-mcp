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

Entry point: `python -m vivado_red_mcp` (or `vivado-red-mcp` after pip install).
"""

from __future__ import annotations

import json
import os
import sys
import threading

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


def _start_autofetch_redpitaya() -> None:
    """On server start, download the RedPitaya-FPGA repo into the cwd if absent.

    Runs in a daemon thread so a large/slow download never blocks the MCP stdio
    handshake. All logging goes to stderr — stdout is reserved for JSON-RPC.
    Disable with the env var VIVADO_MCP_NO_AUTOFETCH.
    """
    if os.environ.get("VIVADO_MCP_NO_AUTOFETCH"):
        return

    from .tools.redpitaya_repo import autofetch_redpitaya_repo

    def _run() -> None:
        try:
            r = autofetch_redpitaya_repo()
            if r and r.get("success"):
                print(
                    f"[vivado-red-mcp] RedPitaya-FPGA: {r.get('status')} -> {r.get('repo_path')}",
                    file=sys.stderr, flush=True,
                )
            elif r:
                print(
                    f"[vivado-red-mcp] RedPitaya-FPGA autofetch failed: {r.get('error')}",
                    file=sys.stderr, flush=True,
                )
        except Exception as ex:  # noqa: BLE001 - never crash the server thread
            print(f"[vivado-red-mcp] RedPitaya-FPGA autofetch error: {ex}", file=sys.stderr, flush=True)

    threading.Thread(target=_run, name="rp-autofetch", daemon=True).start()


async def main():
    _start_autofetch_redpitaya()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
