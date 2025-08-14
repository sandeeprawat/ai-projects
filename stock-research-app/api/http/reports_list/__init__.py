# List reports for current user (HTTP GET /api/reports?scheduleId=...)
from __future__ import annotations

import json
from typing import Optional

import azure.functions as func

from ...common.auth import get_user_context
from ...common.cosmos import list_reports_for_user

async def main(req: func.HttpRequest) -> func.HttpResponse:
    user = get_user_context(dict(req.headers))
    user_id = user.get("userId") or "dev-user"

    schedule_id: Optional[str] = req.params.get("scheduleId")
    limit_raw = req.params.get("limit")
    try:
        limit = int(limit_raw) if limit_raw else 50
    except Exception:
        limit = 50

    items = list(list_reports_for_user(user_id=user_id, schedule_id=schedule_id, limit=limit))
    return func.HttpResponse(
        json.dumps(items),
        status_code=200,
        mimetype="application/json",
    )
