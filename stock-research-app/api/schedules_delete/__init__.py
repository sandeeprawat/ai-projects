from __future__ import annotations

import json
from typing import Dict, Any, Iterable, Optional, List

import azure.functions as func

from ..common.auth import get_user_context
from ..common.cosmos import (
    get_schedule,
    list_reports_for_user,
    delete_report,
    delete_runs_for_schedule,
    delete_schedule,
)
from ..common.config import Settings
from ..common.blob import delete_blob

async def main(req: func.HttpRequest) -> func.HttpResponse:
    user = get_user_context(dict(req.headers))
    user_id = user.get("userId") or "dev-user"

    schedule_id = (req.route_params or {}).get("id")
    if not schedule_id:
        return func.HttpResponse(
            json.dumps({"error": "schedule id is required"}),
            status_code=400,
            mimetype="application/json",
        )

    sched = get_schedule(schedule_id, user_id)
    if not sched:
        return func.HttpResponse(
            json.dumps({"error": "schedule not found"}),
            status_code=404,
            mimetype="application/json",
        )

    container = Settings.REPORTS_CONTAINER or "reports"

    # Delete all reports for this schedule (blobs + docs)
    reports: List[Dict[str, Any]] = list(list_reports_for_user(user_id=user_id, schedule_id=schedule_id, limit=10000))
    for r in reports:
        try:
            blob_paths: Dict[str, str] = r.get("blobPaths") or {}
            for k in ("md", "html", "pdf"):
                p = blob_paths.get(k)
                if p:
                    delete_blob(container, p)
            rid = r.get("id")
            if rid:
                delete_report(rid, user_id)
        except Exception:
            # continue best-effort
            pass

    # Delete runs
    try:
        delete_runs_for_schedule(schedule_id, user_id)
    except Exception:
        pass

    # Delete schedule
    deleted = delete_schedule(schedule_id, user_id)

    return func.HttpResponse(
        json.dumps({"deleted": bool(deleted), "scheduleId": schedule_id}),
        status_code=200 if deleted else 404,
        mimetype="application/json",
    )
