"""Bundled-board metadata helpers (Red Pitaya + future boards).

Reads JSON files from `data/boards/` and resolves XDC paths.
Works without a live Vivado session.
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_PART = "xc7z010clg400-1"  # Zynq 7010 on Red Pitaya STEMlab 125-14
BUNDLED_DATA_DIR = Path(__file__).parent / "data"
BUNDLED_BOARDS_DIR = BUNDLED_DATA_DIR / "boards"


def list_bundled_boards() -> list[dict]:
    if not BUNDLED_BOARDS_DIR.exists():
        return []
    out: list[dict] = []
    for info_file in sorted(BUNDLED_BOARDS_DIR.glob("*_info.json")):
        try:
            data = json.loads(info_file.read_text())
            out.append({
                "board": data.get("board", info_file.stem.replace("_info", "")),
                "display_name": data.get("display_name"),
                "part": data.get("part"),
            })
        except (OSError, json.JSONDecodeError):
            continue
    return out


def load_board_info(board: str) -> dict | None:
    info_file = BUNDLED_BOARDS_DIR / f"{board}_info.json"
    if not info_file.exists():
        return None
    try:
        data = json.loads(info_file.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    for variant in (data.get("xdc_variants") or {}).values():
        rel = variant.get("file")
        if rel:
            variant["absolute_path"] = str((BUNDLED_BOARDS_DIR / rel).resolve())
    return data


def resolve_board_xdc(board: str, variant: str) -> str | None:
    info = load_board_info(board)
    if not info:
        return None
    variants = info.get("xdc_variants") or {}
    v = variants.get(variant)
    if not v:
        return None
    return v.get("absolute_path")
