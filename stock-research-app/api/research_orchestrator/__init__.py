# Orchestrator for deep research workflow
# Deterministic orchestration: calls activities to fetch context, synthesize report, save it, and optionally email.

import logging
import azure.durable_functions as df

logger = logging.getLogger(__name__)


def orchestrator_function(context: df.DurableOrchestrationContext):
    # Input contract:
    # {
    #   "scheduleId": "uuid",
    #   "symbols": ["AAPL","MSFT"],
    #   "runId": "uuid",
    #   "emailTo": ["user@example.com"] (optional)
    # }
    input_ = context.get_input() or {}
    schedule_id = input_.get("scheduleId")
    symbols = input_.get("symbols", [])
    run_id = input_.get("runId")
    email_to = input_.get("emailTo", [])
    user_id = input_.get("userId")
    attach_pdf = bool(input_.get("attachPdf", False))
    deep_research = bool(input_.get("deepResearch", False))
    prompt = (input_.get("prompt") or "")
    schedule_title = (input_.get("scheduleTitle") or "")

    sources_per_symbol = []
    if symbols:
        for s in symbols:
            src = yield context.call_activity("fetch_context", {"symbol": s})
            sources_per_symbol.append({"symbol": s, "sources": src})
    elif prompt:
        src = yield context.call_activity("fetch_context", {"prompt": prompt})
        sources_per_symbol.append({"prompt": prompt, "sources": src})
    else:
        # nothing to do
        return {"status": "no-input", "reportId": None, "runId": run_id, "scheduleId": schedule_id}

    report = yield context.call_activity("synthesize_report", {
        "symbols": symbols,
        "sources": sources_per_symbol,
        "prompt": prompt,
        "deepResearch": deep_research
    })

    saved = yield context.call_activity("save_report", {
        "runId": run_id,
        "scheduleId": schedule_id,
        "report": report,
        "emailTo": email_to,
        "userId": user_id,
        "symbols": symbols,
        "prompt": prompt,
        "attachPdf": attach_pdf,
        "scheduleTitle": schedule_title
    })

    if saved.get("emailTo"):
        email_result = yield context.call_activity("send_email", saved)
        logger.info(f"Orchestrator: Email send result: {email_result}")

    return {"status": "ok", "reportId": saved.get("reportId"), "runId": run_id, "scheduleId": schedule_id}


main = df.Orchestrator.create(orchestrator_function)
