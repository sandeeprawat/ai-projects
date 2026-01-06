# Update a schedule (HTTP PUT /api/schedules/{id})
from __future__ import annotations
import json

from ..common.auth import get_user_context
from ..common.cosmos import update_schedule
import azure.functions as func

def main(req):
    user = get_user_context(req.headers)
    user_id = user["userId"]
    schedule_id = req.route_params.get("id")
    body = req.get_json()

    found = update_schedule(schedule_id, user_id, body)

    if found:
        return func.HttpResponse(
            json.dumps({"message": "Schedule updated", "id": schedule_id}),
            status_code=200,
            mimetype="application/json"
        )
    else:
        return func.HttpResponse(
            json.dumps({"error": "Schedule not found"}),
            status_code=404,
            mimetype="application/json"
        )
