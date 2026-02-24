# Timer-driven scheduler: checks due schedules and starts orchestrations
from __future__ import annotations

import json
from typing import Any, Dict

import azure.functions as func
import azure.durable_functions as df

from ..common.models import Recurrence, compute_next_run_utc, Run
from ..common.cosmos import (
    list_due_schedules,
    update_schedule_next_run,
    create_run as cosmos_create_run,
)
from ..common.auth import get_user_context  # not used here, but kept for parity

async def main(mytimer: func.TimerRequest, starter: str) -> None:
    # Determine "now" in ISO for query (server time assumed UTC on Azure Functions)
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    # Find due schedules (active and nextRunAt <= now)
    due = list_due_schedules(now_iso, limit=50)

    client = df.DurableOrchestrationClient(starter)

    for sched in due:
        try:
            schedule_id = sched.get("id")
            user_id = sched.get("userId")
            symbols = sched.get("symbols") or []
            prompt = (sched.get("prompt") or "")
            email = sched.get("email") or {}
            email_to = email.get("to") or []
            attach_pdf = bool(email.get("attachPdf", False))

            # Create a run record
            run = Run(scheduleId=schedule_id, userId=user_id)
            run_doc = cosmos_create_run(run)

            # Start orchestration
            orch_input: Dict[str, Any] = {
                "scheduleId": schedule_id,
                "symbols": symbols,
                "prompt": prompt,
                "runId": run_doc["id"],
                "emailTo": email_to,
                "userId": user_id,
                "attachPdf": attach_pdf,
                "scheduleTitle": sched.get("title") or "",
            }
            await client.start_new("research_orchestrator", None, orch_input)

            # Compute and update next run
            rec = Recurrence(**(sched.get("recurrence") or {}))
            next_iso = compute_next_run_utc(rec)
            update_schedule_next_run(schedule_id, user_id, next_iso)
        except Exception:
            # Swallow per-schedule errors to keep the loop robust
            continue
