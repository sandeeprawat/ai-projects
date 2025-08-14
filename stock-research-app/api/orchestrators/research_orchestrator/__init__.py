# Orchestrator for stock research workflow
# Deterministic orchestration: calls activities to fetch context, synthesize report, save it, and optionally email.

import azure.durable_functions as df


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

    sources_per_symbol = []
    for s in symbols:
        src = yield context.call_activity("fetch_context", {"symbol": s})
        sources_per_symbol.append({"symbol": s, "sources": src})

    report = yield context.call_activity("synthesize_report", {
        "symbols": symbols,
        "sources": sources_per_symbol
    })

    saved = yield context.call_activity("save_report", {
        "runId": run_id,
        "scheduleId": schedule_id,
        "report": report,
        "emailTo": email_to,
        "userId": user_id,
        "symbols": symbols,
        "attachPdf": attach_pdf
    })

    if saved.get("emailTo"):
        yield context.call_activity("send_email", saved)

    return {"status": "ok", "reportId": saved.get("reportId"), "runId": run_id, "scheduleId": schedule_id}


main = df.Orchestrator.create(orchestrator_function)
