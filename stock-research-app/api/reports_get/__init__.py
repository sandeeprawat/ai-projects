# Get a single report metadata + signed URLs (HTTP GET /api/reports/{id})
from __future__ import annotations

import json
from typing import Optional, Dict

import azure.functions as func

from ...common.auth import get_user_context
from ...common.cosmos import get_report
from ...common.config import Settings
from ...common.blob import make_read_sas_url

async def main(req: func.HttpRequest) -> func.HttpResponse:
    user = get_user_context(dict(req.headers))
    user_id = user.get("userId") or "dev-user"

    report_id = (req.route_params or {}).get("id")
    if not report_id:
        return func.HttpResponse(
            json.dumps({"error": "report id is required in route"}),
            status_code=400,
            mimetype="application/json",
        )

    doc = get_report(report_id, user_id)
    if not doc:
        return func.HttpResponse(
            json.dumps({"error": "report not found"}),
            status_code=404,
            mimetype="application/json",
        )

    container = Settings.REPORTS_CONTAINER or "reports"
    blob_paths: Dict[str, str] = doc.get("blobPaths") or {}

    signed = {}
    for k in ("md", "html", "pdf"):
        p = blob_paths.get(k)
        if p:
            try:
                signed[k] = make_read_sas_url(container, p)
            except Exception:
                signed[k] = None

    return func.HttpResponse(
        json.dumps({
            **doc,
            "signedUrls": signed
        }),
        status_code=200,
        mimetype="application/json",
    )
