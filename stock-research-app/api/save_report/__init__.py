from __future__ import annotations

from typing import Dict, Any
from datetime import datetime, timezone
from ..common.config import Settings
from ..common import blob as blob_util
from ..common import pdf as pdf_util
from ..common.models import Report
from ..common.cosmos import save_report as cosmos_save_report

def main(input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity: save_report
    Input:
      {
        "runId": str,
        "scheduleId": str,
        "userId": str,
        "prompt": str?,
        "symbols": [str, ...],
        "report": {"title": str, "markdown": str, "html": str, "citations": [...]},
        "emailTo": [str, ...],
        "attachPdf": bool
      }
    Output:
      {
        "reportId": str,
        "blobPaths": {"md": str, "html": str, "pdf": str?},
        "emailTo": [str, ...],
        "title": str,
        "userId": str
      }
    """
    input = input or {}
    run_id = input.get("runId")
    schedule_id = input.get("scheduleId")
    user_id = input.get("userId") or "dev-user"
    symbols = input.get("symbols") or []
    prompt = input.get("prompt") or None
    r = input.get("report") or {}
    title = r.get("title") or f"Deep Research Report"
    md = r.get("markdown") or ""
    html = r.get("html") or ""
    citations = r.get("citations") or []
    email_to = input.get("emailTo") or []
    attach_pdf = bool(input.get("attachPdf", False))

    container = Settings.REPORTS_CONTAINER or "reports"
    # {userId}/{scheduleId}/{runId}/report.* (path within the container)
    prefix = f"{user_id}/{schedule_id}/{run_id}".replace("//", "/")
    md_path = f"{prefix}/report.md"
    html_path = f"{prefix}/report.html"

    md_url = blob_util.upload_text(container, md_path, md, content_type="text/markdown; charset=utf-8")
    html_url = blob_util.upload_text(container, html_path, html, content_type="text/html; charset=utf-8")

    pdf_path = None
    pdf_url = None
    if attach_pdf:
        pdf_bytes = pdf_util.markdown_to_pdf_bytes(md or title)
        pdf_path = f"{prefix}/report.pdf"
        pdf_url = blob_util.upload_bytes(container, pdf_path, pdf_bytes, content_type="application/pdf")

    blob_paths = {"md": md_path, "html": html_path}
    if pdf_path:
        blob_paths["pdf"] = pdf_path

    report_doc = Report(
        runId=run_id,
        scheduleId=schedule_id,
        userId=user_id,
        title=title,
        prompt=prompt,
        symbols=symbols,
        summary=None,
        blobPaths=blob_paths,
        citations=citations,
    )
    saved = cosmos_save_report(report_doc)

    return {
        "reportId": saved["id"],
        "blobPaths": blob_paths,
        "emailTo": email_to,
        "title": title,
        "userId": user_id
    }
