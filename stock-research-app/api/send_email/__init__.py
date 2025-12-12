from __future__ import annotations

import base64
import logging
from typing import Dict, Any, List, Optional

from azure.communication.email import EmailClient

from ..common.config import Settings
from ..common.blob import make_read_sas_url, _svc

logger = logging.getLogger(__name__)

def _download_blob_bytes(container: str, blob_path: str) -> Optional[bytes]:
    try:
        svc = _svc()
        bc = svc.get_blob_client(container=container, blob=blob_path)
        stream = bc.download_blob(max_concurrency=1)
        data = stream.readall()
        logger.info(f"_download_blob_bytes: Downloaded {len(data)} bytes from {blob_path}")
        return data
    except Exception as e:
        logger.error(f"_download_blob_bytes: Failed to download {blob_path}: {str(e)}", exc_info=True)
        return None

def _download_blob_text(container: str, blob_path: str) -> Optional[str]:
    """Download blob content as text (for HTML/MD files)"""
    try:
        data = _download_blob_bytes(container, blob_path)
        if data:
            return data.decode('utf-8')
        logger.warning(f"_download_blob_text: No data returned for {blob_path}")
        return None
    except Exception as e:
        logger.error(f"_download_blob_text: Failed to download {blob_path}: {str(e)}")
        return None

def main(input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity: send_email
    Input: {
      "reportId": str,
      "blobPaths": {"md": str, "html": str, "pdf": str?},
      "emailTo": [str, ...],
      "title": str,
      "userId": str
    }
    Behavior: If ACS settings are missing or no recipients, no-ops and returns {"sent": False}.
    """
    input = input or {}
    recipients: List[str] = [x for x in (input.get("emailTo") or []) if isinstance(x, str) and x.strip()]
    title: str = input.get("title") or "Stock Research Report"
    blob_paths: Dict[str, str] = input.get("blobPaths") or {}
    container = Settings.REPORTS_CONTAINER or "reports"

    if not recipients:
        logger.warning("send_email: No recipients provided")
        return {"sent": False, "reason": "no recipients"}

    if not Settings.ACS_CONNECTION_STRING or not Settings.EMAIL_SENDER:
        # No-op if email service is not configured
        logger.warning(f"send_email: Email service not configured (ACS: {bool(Settings.ACS_CONNECTION_STRING)}, Sender: {bool(Settings.EMAIL_SENDER)})")
        return {"sent": False, "reason": "email service not configured"}

    # Build signed links
    md_path = blob_paths.get("md")
    html_path = blob_paths.get("html")
    pdf_path = blob_paths.get("pdf")

    md_url = make_read_sas_url(container, md_path) if md_path else None
    html_url = make_read_sas_url(container, html_path) if html_path else None
    pdf_url = make_read_sas_url(container, pdf_path) if pdf_path else None

    # Try to download and embed the full HTML report
    html_content = None
    if html_path:
        logger.info(f"send_email: Attempting to download HTML from: {html_path}")
        html_content = _download_blob_text(container, html_path)
        if html_content:
            logger.info(f"send_email: Successfully downloaded HTML ({len(html_content)} chars)")
        else:
            logger.warning(f"send_email: Failed to download HTML content from {html_path}")
    else:
        logger.warning(f"send_email: No HTML path provided in blobPaths")
    
    if html_content:
        # Use the full HTML report as email body
        # Wrap it in a container with links to other formats at the top
        body_html = f"""
<div style="font-family: system-ui, -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px;">
  <div style="background: #f5f5f5; padding: 12px; margin-bottom: 20px; border-radius: 6px; border-left: 4px solid #0066cc;">
    <p style="margin: 0 0 8px 0; font-weight: bold;">📊 {title}</p>
    <p style="margin: 0; font-size: 14px; color: #666;">Your stock research report is ready. Download other formats:</p>
    <div style="margin-top: 8px;">
"""
        if md_url:
            body_html += f'<a href="{md_url}" style="margin-right: 12px; color: #0066cc;">📄 Markdown</a>'
        if pdf_url:
            body_html += f'<a href="{pdf_url}" style="margin-right: 12px; color: #0066cc;">📕 PDF</a>'
        body_html += """
    </div>
  </div>
  <div style="border-top: 2px solid #eee; padding-top: 20px;">
"""
        body_html += html_content
        body_html += """
  </div>
</div>
"""
    else:
        # Fallback to links-only format if HTML not available
        html_parts = [
            f"<h2>{title}</h2>",
            "<p>Your scheduled stock research report is ready.</p>",
            "<ul>"
        ]
        if html_url:
            html_parts.append(f'<li>HTML: <a href="{html_url}">{html_url}</a></li>')
        if md_url:
            html_parts.append(f'<li>Markdown: <a href="{md_url}">{md_url}</a></li>')
        if pdf_url:
            html_parts.append(f'<li>PDF: <a href="{pdf_url}">{pdf_url}</a></li>')
        html_parts.append("</ul>")
        body_html = "\n".join(html_parts)

    # Optionally attach PDF bytes if present
    attachments: List[dict] = []
    if pdf_path:
        pdf_bytes = _download_blob_bytes(container, pdf_path)
        if pdf_bytes:
            attachments.append({
                "name": "report.pdf",
                "contentType": "application/pdf",
                "contentInBase64": base64.b64encode(pdf_bytes).decode("utf-8"),
            })

    to_list = [{"address": x} for x in recipients]
    message: Dict[str, Any] = {
        "senderAddress": Settings.EMAIL_SENDER,
        "content": {"subject": f"[Stock Research] {title}", "html": body_html},
        "recipients": {"to": to_list},
    }
    if attachments:
        message["attachments"] = attachments

    logger.info(f"send_email: Sending to {len(recipients)} recipient(s), subject: {message['content']['subject']}, has_pdf: {bool(attachments)}")
    
    client = EmailClient.from_connection_string(Settings.ACS_CONNECTION_STRING)
    try:
        poller = client.begin_send(message)
        # wait up to 60s for send to complete (no-op if service returns immediately)
        result = poller.result(60)
        logger.info(f"send_email: Email sent successfully, message_id: {getattr(result, 'message_id', 'unknown')}")
        return {"sent": True}
    except Exception as e:
        logger.error(f"send_email: Failed to send email: {str(e)}", exc_info=True)
        return {"sent": False, "error": str(e)}
