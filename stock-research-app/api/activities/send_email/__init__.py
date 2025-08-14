from __future__ import annotations

import base64
from typing import Dict, Any, List, Optional

from azure.communication.email import (
    EmailClient,
    EmailContent,
    EmailAddress,
    EmailMessage,
    EmailRecipients,
    EmailAttachment,
    EmailAttachmentType,
)
from azure.storage.blob import BlobServiceClient

from ...common.config import Settings, get_storage_connection_string
from ...common.blob import make_read_sas_url

def _download_blob_bytes(container: str, blob_path: str) -> Optional[bytes]:
    try:
        cs = get_storage_connection_string()
        svc = BlobServiceClient.from_connection_string(cs)
        bc = svc.get_blob_client(container=container, blob=blob_path)
        stream = bc.download_blob(max_concurrency=1)
        return stream.readall()
    except Exception:
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
        return {"sent": False, "reason": "no recipients"}

    if not Settings.ACS_CONNECTION_STRING or not Settings.EMAIL_SENDER:
        # No-op if email service is not configured
        return {"sent": False, "reason": "email service not configured"}

    # Build signed links
    md_path = blob_paths.get("md")
    html_path = blob_paths.get("html")
    pdf_path = blob_paths.get("pdf")

    md_url = make_read_sas_url(container, md_path) if md_path else None
    html_url = make_read_sas_url(container, html_path) if html_path else None
    pdf_url = make_read_sas_url(container, pdf_path) if pdf_path else None

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
    attachments: List[EmailAttachment] = []
    if pdf_path:
        pdf_bytes = _download_blob_bytes(container, pdf_path)
        if pdf_bytes:
            attachments.append(
                EmailAttachment(
                    name="report.pdf",
                    attachment_type=EmailAttachmentType.PDF,
                    content_bytes_base64=base64.b64encode(pdf_bytes).decode("utf-8"),
                )
            )

    to_list = [EmailAddress(email=x) for x in recipients]
    content = EmailContent(subject=f"[Stock Research] {title}", html=body_html)
    message = EmailMessage(
        sender=Settings.EMAIL_SENDER,
        content=content,
        recipients=EmailRecipients(to=to_list),
        attachments=attachments if attachments else None,
    )

    client = EmailClient.from_connection_string(Settings.ACS_CONNECTION_STRING)
    try:
        client.send(message)
        return {"sent": True}
    except Exception as e:
        return {"sent": False, "error": str(e)}
