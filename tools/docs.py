"""Vivado documentation lookup — bundled markdown summaries under data/docs/.

Each topic markdown file embeds the upstream AMD/Xilinx UG URL and a focused
synthesis of the relevant section. Use this when an LLM needs to reason about
Vivado behaviour without browsing the web.
"""

from __future__ import annotations

from pathlib import Path

from mcp.types import Tool

DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "docs"

KNOWN_TOPICS = [
    "block_design",
    "ps7_zynq",
    "timing_constraints",
    "synthesis_strategies",
    "simulation_xsim",
    "red_pitaya_125_14",
    "redpitaya_ps_pl_flow",
    "tcl_quoting",
    "hw_manager",
    "ip_integrator",
    "pitfalls_2020_1",
]

TOOLS = [
    Tool(
        name="get_vivado_doc",
        description=(
            "Look up a topical Vivado documentation summary bundled with this server. "
            "Returns markdown content + upstream URL. Known topics: block_design, "
            "ps7_zynq, timing_constraints, synthesis_strategies, simulation_xsim, "
            "red_pitaya_125_14, redpitaya_ps_pl_flow, tcl_quoting, hw_manager, "
            "ip_integrator, pitfalls_2020_1."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic name; see KNOWN_TOPICS in the tool description",
                },
                "version": {
                    "type": "string",
                    "description": "Target Vivado version (cosmetic, default '2020.1')",
                },
            },
            "required": ["topic"],
        },
    ),
    Tool(
        name="list_vivado_docs",
        description="List the bundled Vivado documentation topics.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
]


def _list_vivado_docs(session, args):
    topics: list[dict] = []
    for t in KNOWN_TOPICS:
        path = DOCS_DIR / f"{t}.md"
        topics.append({
            "topic": t,
            "available": path.exists(),
            "path": str(path) if path.exists() else None,
        })
    return {"success": True, "count": len(topics), "topics": topics}


def _get_vivado_doc(session, args):
    topic = args.get("topic", "")
    version = args.get("version", "2020.1")
    path = DOCS_DIR / f"{topic}.md"
    if not path.exists():
        return {
            "success": False,
            "error": f"Unknown topic '{topic}'. Known: {KNOWN_TOPICS}",
        }
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as ex:
        return {"success": False, "error": f"Could not read {path}: {ex}"}
    return {
        "success": True,
        "topic": topic,
        "version": version,
        "path": str(path),
        "content": content,
        "size_chars": len(content),
    }


HANDLERS = {
    "get_vivado_doc": _get_vivado_doc,
    "list_vivado_docs": _list_vivado_docs,
}
