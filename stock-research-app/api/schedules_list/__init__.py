# List schedules for current user (HTTP GET /api/schedules)
from __future__ import annotations

import json
import azure.functions as func

from ..common.auth import get_user_context
from ..common.cosmos import list_schedules_for_user

async def main(req: func.HttpRequest) -> func.HttpResponse:
    user = get_user_context(dict(req.headers))
    user_id = user.get("userId") or "dev-user"

    limit_raw = req.params.get("limit")
    try:
        limit = int(limit_raw) if limit_raw else 100
    except Exception:
        limit = 100

    items = list_schedules_for_user(user_id=user_id, limit=limit)

    return func.HttpResponse(
        json.dumps(items),
        status_code=200,
        mimetype="application/json",
    )
