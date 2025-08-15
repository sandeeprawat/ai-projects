from __future__ import annotations

from io import BytesIO
from typing import Optional, List

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

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
        story.append(Paragraph(title, styles["Title"]))
        story.append(Spacer(1, 12))

    lines = (markdown_text or "").splitlines()
    for line in lines:
        text = line.strip()
        if not text:
            story.append(Spacer(1, 8))
            continue
        # naive heading detection
        if text.startswith("# "):
            story.append(Paragraph(text.lstrip("# ").strip(), styles["Heading1"]))
        elif text.startswith("## "):
            story.append(Paragraph(text.lstrip("# ").strip(), styles["Heading2"]))
        elif text.startswith("### "):
            story.append(Paragraph(text.lstrip("# ").strip(), styles["Heading3"]))
        else:
            # Paragraph supports a small HTML subset; escape angle brackets
            safe = (
                text.replace("&", "&")
                .replace("<", "<")
                .replace(">", ">")
            )
            story.append(Paragraph(safe, styles["BodyText"]))
    doc.build(story)
    return buf.getvalue()
