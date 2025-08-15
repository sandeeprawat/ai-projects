from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import azure.functions as func

from ..common.config import Settings
from ..common.cosmos import list_all_reports, delete_report
from ..common.blob import delete_blob


def _parse_int(env_val: Optional[str], default: int = 0) -> int:
    try:
        if env_val is None:
            return default
        return int(str(env_val).strip())
    except Exception:
        return default


def main(mytimer: func.TimerRequest) -> None:
    """
    Timer Function: cleanup_reports
    Deletes report metadata and blobs older than REPORT_RETENTION_DAYS.
    No-op when REPORT_RETENTION_DAYS is 0 or missing.
    """
    days = _parse_int(getattr(Settings, "REPORT_RETENTION_DAYS", "0"), 0)
    if days <= 0:
        return

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    container = getattr(Settings, "REPORTS_CONTAINER", "reports") or "reports"

    all_reports: List[Dict[str, Any]] = list_all_reports()
    for r in all_reports:
        try:
            created = r.get("createdAt")
            if not created:
                # If missing timestamp, skip deletion for safety
                continue
            try:
                created_dt = datetime.fromisoformat(created)
            except Exception:
                # Non-ISO or unparsable - skip
                continue
            if created_dt > cutoff:
                continue

            # Delete blobs if present
            blob_paths: Dict[str, str] = r.get("blobPaths") or {}
            for k in ("md", "html", "pdf"):
                p = blob_paths.get(k)
                if p:
                    delete_blob(container, p)

            # Delete report doc
            rid = r.get("id")
            uid = r.get("userId")
            if rid and uid:
                delete_report(rid, uid)
        except Exception:
            # Best-effort cleanup; continue to next item
            continue
