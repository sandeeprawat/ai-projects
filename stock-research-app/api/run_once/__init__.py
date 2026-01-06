# Run a report once immediately (HTTP POST /api/run-once)
# Does not create a schedule - just runs a one-off research report
from __future__ import annotations

import json
from typing import Any, Dict, List

import azure.functions as func
import azure.durable_functions as df

from ..common.auth import get_user_context
from ..common.models import Run
from ..common.cosmos import create_run as cosmos_create_run


async def main(req: func.HttpRequest, starter: str) -> func.HttpResponse:
    user = get_user_context(dict(req.headers))
    user_id = user.get("userId") or "dev-user"

    # Parse request body
    try:
        body = req.get_json() or {}
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            status_code=400,
            mimetype="application/json",
        )

    symbols: List[str] = body.get("symbols") or []
    prompt: str = body.get("prompt") or ""
    email_to: List[str] = body.get("emailTo") or []
    attach_pdf: bool = bool(body.get("attachPdf", False))
    deep_research: bool = bool(body.get("deepResearch", False))

    # Validate: need at least symbols or prompt
    if not symbols and not prompt:
        return func.HttpResponse(
            json.dumps({"error": "Either 'symbols' or 'prompt' is required"}),
            status_code=400,
            mimetype="application/json",
        )

    # Create a run record (with a placeholder scheduleId for one-off runs)
    run = Run(scheduleId="one-off", userId=user_id)
    run_doc = cosmos_create_run(run)

    # Prepare orchestration input
    orch_input: Dict[str, Any] = {
        "scheduleId": "one-off",
        "symbols": symbols,
        "prompt": prompt,
        "runId": run_doc["id"],
        "emailTo": email_to,
        "userId": user_id,
        "attachPdf": attach_pdf,
        "deepResearch": deep_research,
    }

    client = df.DurableOrchestrationClient(starter)
    instance_id = await client.start_new("research_orchestrator", None, orch_input)

    return func.HttpResponse(
        json.dumps({
            "instanceId": instance_id,
            "runId": run_doc["id"],
            "message": "One-off research started"
        }),
        status_code=202,
        mimetype="application/json",
    )
