"""Feature request log — persisted in data/feature_requests.json."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from mcp.types import Tool

FEATURE_REQUESTS_FILE = Path(__file__).resolve().parent.parent / "data" / "feature_requests.json"

TOOLS = [
    Tool(
        name="request_feature",
        description="Submit a feature request for the Vivado MCP server (persisted on disk).",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short title"},
                "description": {"type": "string", "description": "What you need and why"},
                "use_case": {"type": "string", "description": "Task that prompted the request"},
                "priority": {"type": "string", "enum": ["low", "medium", "high"]},
            },
            "required": ["title", "description"],
        },
    ),
    Tool(
        name="list_feature_requests",
        description="List all submitted feature requests.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
]


def _load() -> list[dict]:
    if FEATURE_REQUESTS_FILE.exists():
        try:
            return json.loads(FEATURE_REQUESTS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save(reqs: list[dict]) -> None:
    FEATURE_REQUESTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    FEATURE_REQUESTS_FILE.write_text(json.dumps(reqs, indent=2))


def _request_feature(session, args):
    reqs = _load()
    req = {
        "id": len(reqs) + 1,
        "title": args.get("title", ""),
        "description": args.get("description", ""),
        "use_case": args.get("use_case", ""),
        "priority": args.get("priority", "medium"),
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
    }
    reqs.append(req)
    _save(reqs)
    return {"success": True, "message": f"Feature request #{req['id']} submitted: {req['title']}", "request": req}


def _list_feature_requests(session, args):
    reqs = _load()
    return {"success": True, "total": len(reqs), "requests": reqs}


HANDLERS = {
    "request_feature": _request_feature,
    "list_feature_requests": _list_feature_requests,
}
