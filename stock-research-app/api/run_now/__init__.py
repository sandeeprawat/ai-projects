# Run a schedule now (HTTP POST /api/schedules/{id}/run)
from __future__ import annotations

import json
from typing import Any, Dict

import azure.functions as func
import azure.durable_functions as df

from ..common.auth import get_user_context
from ..common.models import Run
from ..common.cosmos import get_schedule as cosmos_get_schedule, create_run as cosmos_create_run

async def main(req: func.HttpRequest, starter: str) -> func.HttpResponse:
    user = get_user_context(dict(req.headers))
    user_id = user.get("userId") or "dev-user"

    schedule_id = (req.route_params or {}).get("id")
    if not schedule_id:
        return func.HttpResponse(
            json.dumps({"error": "schedule id is required in route"}),
            status_code=400,
            mimetype="application/json",
        )

    sched = cosmos_get_schedule(schedule_id, user_id)
    if not sched:
        return func.HttpResponse(
            json.dumps({"error": "schedule not found"}),
            status_code=404,
            mimetype="application/json",
        )

    # Create a run record
    run = Run(scheduleId=schedule_id, userId=user_id)
    run_doc = cosmos_create_run(run)

    # Prepare orchestration input
    symbols = sched.get("symbols") or []
    prompt = (sched.get("prompt") or "")
    email = (sched.get("email") or {})
    email_to = email.get("to") or []
    attach_pdf = bool(email.get("attachPdf", False))
    deep_research = bool(sched.get("deepResearch", False))

    orch_input: Dict[str, Any] = {
        "scheduleId": schedule_id,
        "symbols": symbols,
        "prompt": prompt,
        "runId": run_doc["id"],
        "emailTo": email_to,
        "userId": user_id,
        "attachPdf": attach_pdf,
        "deepResearch": deep_research,
        "scheduleTitle": sched.get("title") or "",
    }

    client = df.DurableOrchestrationClient(starter)
    instance_id = await client.start_new("research_orchestrator", None, orch_input)

    return func.HttpResponse(
        json.dumps({
            "instanceId": instance_id,
            "runId": run_doc["id"],
            "scheduleId": schedule_id
        }),
        status_code=202,
        mimetype="application/json",
    )
