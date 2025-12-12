# Send email for an existing report (HTTP POST /api/reports/{id}/send-email)
from __future__ import annotations

import json
import logging
from typing import Dict, Any

import azure.functions as func
import azure.durable_functions as df

from ..common.auth import get_user_context
from ..common.cosmos import get_report
from ..common.config import Settings

logger = logging.getLogger(__name__)

async def main(req: func.HttpRequest, starter: str) -> func.HttpResponse:
    """
    POST /api/reports/{id}/send-email
    Body: {
      "emailTo": ["user@example.com", ...],
      "attachPdf": true/false (optional, default: true)
    }
    """
    user = get_user_context(dict(req.headers))
    user_id = user.get("userId") or "dev-user"

    report_id = (req.route_params or {}).get("id")
    if not report_id:
        return func.HttpResponse(
            json.dumps({"error": "report id is required in route"}),
            status_code=400,
            mimetype="application/json",
        )

    # Get the report
    doc = get_report(report_id, user_id)
    if not doc:
        return func.HttpResponse(
            json.dumps({"error": "report not found"}),
            status_code=404,
            mimetype="application/json",
        )

    # Parse request body
    try:
        body = req.get_json()
    except Exception:
        return func.HttpResponse(
            json.dumps({"error": "invalid JSON body"}),
            status_code=400,
            mimetype="application/json",
        )

    email_to = body.get("emailTo", [])
    if not email_to or not isinstance(email_to, list):
        return func.HttpResponse(
            json.dumps({"error": "emailTo is required and must be an array"}),
            status_code=400,
            mimetype="application/json",
        )

    # Validate email addresses
    valid_emails = [e for e in email_to if isinstance(e, str) and "@" in e and e.strip()]
    if not valid_emails:
        return func.HttpResponse(
            json.dumps({"error": "no valid email addresses provided"}),
            status_code=400,
            mimetype="application/json",
        )

    attach_pdf = body.get("attachPdf", True)

    # Prepare email input
    email_input: Dict[str, Any] = {
        "reportId": report_id,
        "blobPaths": doc.get("blobPaths", {}),
        "emailTo": valid_emails,
        "title": doc.get("title", "Stock Research Report"),
        "userId": user_id
    }

    # Check if email service is configured
    if not Settings.ACS_CONNECTION_STRING or not Settings.EMAIL_SENDER:
        logger.warning(f"Email service not configured. Report: {report_id}")
        return func.HttpResponse(
            json.dumps({
                "error": "Email service not configured",
                "reportId": report_id
            }),
            status_code=503,
            mimetype="application/json",
        )

    # Use Durable Functions client to invoke send_email activity directly
    client = df.DurableOrchestrationClient(starter)
    
    # Start a simple orchestrator that just sends the email
    instance_id = await client.start_new(
        "send_email_orchestrator",
        client_input=email_input
    )

    logger.info(f"Started email send orchestration {instance_id} for report {report_id} to {len(valid_emails)} recipient(s)")

    return func.HttpResponse(
        json.dumps({
            "message": "Email send initiated",
            "reportId": report_id,
            "instanceId": instance_id,
            "emailTo": valid_emails
        }),
        status_code=202,
        mimetype="application/json",
    )
