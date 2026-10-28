"""Report file management — temp dir, IDs, cache.

Reports too large for inline response (>8KB) get written to /tmp/vivado_red_mcp/
and referenced by an 8-char ID. Old files are GC'd after REPORT_CACHE_HOURS.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path("/tmp/vivado_red_mcp")
REPORT_CACHE_HOURS = 1

# In-memory cache: report_id -> {file_path, report_type, created, size_bytes, line_count}
_report_cache: dict[str, dict] = {}


def ensure_reports_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now().timestamp() - (REPORT_CACHE_HOURS * 3600)
    for report_file in REPORTS_DIR.glob("*.txt"):
        try:
            if report_file.stat().st_mtime < cutoff:
                report_file.unlink()
                _report_cache.pop(report_file.stem, None)
        except OSError:
            pass
    return REPORTS_DIR


def generate_report_id() -> str:
    return str(uuid.uuid4())[:8]


def cache_report(report_id: str, file_path: Path, report_type: str) -> dict:
    stat = file_path.stat()
    line_count = sum(1 for _ in open(file_path))
    meta = {
        "file_path": str(file_path),
        "report_type": report_type,
        "created": datetime.now().isoformat(),
        "size_bytes": stat.st_size,
        "line_count": line_count,
    }
    _report_cache[report_id] = meta
    return meta


def lookup_report(report_id: str) -> dict | None:
    return _report_cache.get(report_id)
