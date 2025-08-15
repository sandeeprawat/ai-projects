from __future__ import annotations

import json
from typing import Dict, Optional

import azure.functions as func

from ..common.auth import get_user_context
from ..common.cosmos import get_report, delete_report
from ..common.config import Settings
from ..common.blob import delete_blob

async def main(req: func.HttpRequest) -> func.HttpResponse:
    user = get_user_context(dict(req.headers))
    user_id = user.get("userId") or "dev-user"

    report_id = (req.route_params or {}).get("id")
    if not report_id:
        return func.HttpResponse(
            json.dumps({"error": "report id is required"}),
            status_code=400,
            mimetype="application/json",
        )

    doc: Optional[Dict] = get_report(report_id, user_id)
    if not doc:
        return func.HttpResponse(
            json.dumps({"error": "report not found"}),
            status_code=404,
            mimetype="application/json",
        )

    # Best-effort delete of blobs
    container = Settings.REPORTS_CONTAINER or "reports"
    blob_paths: Dict[str, str] = doc.get("blobPaths") or {}
    for k in ("md", "html", "pdf"):
        p = blob_paths.get(k)
        if p:
            try:
                delete_blob(container, p)
            except Exception:
                pass

    deleted = delete_report(report_id, user_id) is not None

    return func.HttpResponse(
        json.dumps({"deleted": bool(deleted), "reportId": report_id}),
        status_code=200 if deleted else 404,
        mimetype="application/json",
    )
