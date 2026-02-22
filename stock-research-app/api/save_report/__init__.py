from __future__ import annotations

import logging
from typing import Dict, Any
from datetime import datetime, timezone
from ..common.config import Settings
from ..common import blob as blob_util
from ..common import pdf as pdf_util
from ..common.models import Report, TrackedStock
from ..common.cosmos import save_report as cosmos_save_report, create_tracked_stock
from ..common.prices import fetch_prices, extract_stock_recommendations

logger = logging.getLogger(__name__)

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

    # Auto-track stocks in the performance dashboard
    if symbols or md:
        _auto_track_stocks(md, saved, user_id)

    return {
        "reportId": saved["id"],
        "blobPaths": blob_paths,
        "emailTo": email_to,
        "title": title,
        "userId": user_id
    }


def _auto_track_stocks(markdown: str, saved: Dict[str, Any], user_id: str) -> None:
    """Use GPT to check if the report is stock-related and extract recommended
    symbols from the output, then create tracked stock entries."""
    try:
        extraction = extract_stock_recommendations(markdown)
        if not extraction.get("isStockRelated"):
            logger.info("Report %s is not stock-related, skipping auto-track", saved.get("id"))
            return

        extracted_symbols = [
            s["symbol"].strip().upper()
            for s in extraction.get("stocks", [])
            if s.get("symbol", "").strip()
        ]
        if not extracted_symbols:
            logger.info("Report %s is stock-related but no symbols extracted", saved.get("id"))
            return

        rec_date = (saved.get("createdAt") or "")[:10]  # YYYY-MM-DD
        report_id = saved.get("id", "")
        report_title = saved.get("title", "")
        prices = fetch_prices(extracted_symbols)

        for sym in extracted_symbols:
            price = prices.get(sym)
            if price is None:
                logger.warning("Skipping auto-track for %s: price unavailable", sym)
                continue
            stock = TrackedStock(
                userId=user_id,
                symbol=sym,
                reportTitle=report_title,
                reportId=report_id,
                recommendationDate=rec_date,
                recommendationPrice=price,
            )
            create_tracked_stock(stock)
            logger.info("Auto-tracked %s at $%.2f from report %s", sym, price, report_id)
    except Exception as exc:
        logger.warning("Auto-track stocks failed (non-fatal): %s", exc)
