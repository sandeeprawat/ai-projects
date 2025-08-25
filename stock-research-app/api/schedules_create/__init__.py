# Create a schedule (HTTP POST /api/schedules)
from __future__ import annotations

import json
from typing import Any, Dict, List

import azure.functions as func
import azure.durable_functions as df

from ..common.auth import get_user_context
from ..common.models import Schedule, Recurrence, EmailSettings, compute_next_run_utc
from ..common.cosmos import create_schedule as cosmos_create_schedule

async def main(req: func.HttpRequest, starter: str) -> func.HttpResponse:
    try:
        body: Dict[str, Any] = req.get_json()
    except Exception:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            status_code=400,
            mimetype="application/json",
        )

    user = get_user_context(dict(req.headers))
    user_id = user.get("userId") or "dev-user"

    prompt: str = (body.get("prompt") or "").strip()
    symbols_raw: List[str] = body.get("symbols") or []
    symbols = [s.strip().upper() for s in symbols_raw if isinstance(s, str) and s.strip()]
    if not prompt and not symbols:
        return func.HttpResponse(
            json.dumps({"error": "prompt is required (or provide symbols for backward compatibility)"}),
            status_code=400,
            mimetype="application/json",
        )

    rec_in = body.get("recurrence") or {}
    try:
        recurrence = Recurrence(**rec_in)
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": f"invalid recurrence: {str(e)}"}),
            status_code=400,
            mimetype="application/json",
        )

    email_in = body.get("email") or {}
    email = EmailSettings(
        to=[x for x in (email_in.get("to") or []) if isinstance(x, str) and x.strip()],
        attachPdf=bool(email_in.get("attachPdf", False)),
    )

    sched = Schedule(
        userId=user_id,
        prompt=prompt,
        symbols=symbols,
        recurrence=recurrence,
        email=email,
        deepResearch=bool(body.get("deepResearch", False)),
        active=bool(body.get("active", True)),
    )
    # compute next run
    sched.nextRunAt = compute_next_run_utc(recurrence)

    saved = cosmos_create_schedule(sched)

    return func.HttpResponse(
        json.dumps(saved),
        status_code=201,
        mimetype="application/json",
    )
