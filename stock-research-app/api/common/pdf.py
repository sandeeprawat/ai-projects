from __future__ import annotations

import re
from io import BytesIO
from typing import Optional, List

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """Remove all HTML tags and decode common HTML entities."""
    text = _HTML_TAG_RE.sub("", text)
    for entity, char in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                         ("&quot;", '"'), ("&#39;", "'")):
        text = text.replace(entity, char)
    return text


def _escape_for_reportlab(text: str) -> str:
    """Escape special characters for ReportLab's Paragraph XML parser."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def markdown_to_pdf_bytes(markdown_text: str, title: Optional[str] = None) -> bytes:
    """
    Very lightweight Markdown->PDF: renders text as paragraphs.
    Headings starting with '#' are bolded by simple styling heuristics.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER)
    styles = getSampleStyleSheet()
    story: List = []

    if title:
        safe_title = _escape_for_reportlab(_strip_html(title))
        story.append(Paragraph(safe_title, styles["Title"]))
        story.append(Spacer(1, 12))

    lines = (markdown_text or "").splitlines()
    for line in lines:
        text = line.strip()
        if not text:
            story.append(Spacer(1, 8))
            continue
        # Strip any embedded HTML tags from AI-generated content
        text = _strip_html(text)
        # naive heading detection
        if text.startswith("### "):
            safe = _escape_for_reportlab(text[4:].strip())
            story.append(Paragraph(safe, styles["Heading3"]))
        elif text.startswith("## "):
            safe = _escape_for_reportlab(text[3:].strip())
            story.append(Paragraph(safe, styles["Heading2"]))
        elif text.startswith("# "):
            safe = _escape_for_reportlab(text[2:].strip())
            story.append(Paragraph(safe, styles["Heading1"]))
        else:
            safe = _escape_for_reportlab(text)
            story.append(Paragraph(safe, styles["BodyText"]))
    doc.build(story)
    return buf.getvalue()
