from __future__ import annotations

from io import BytesIO
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from markdown_it import MarkdownIt

_md = MarkdownIt()

def markdown_to_plain_lines(md_text: str):
    # Very simple: extract inline text lines from tokens
    tokens = _md.parse(md_text or "")
    lines = []
    current = []
    for t in tokens:
        if t.type == "inline" and t.content:
            current.append(t.content)
        if t.type in ("paragraph_close", "heading_close", "list_item_close"):
            if current:
                lines.append(" ".join(current))
                current = []
        if t.type == "bullet_list_close" or t.type == "ordered_list_close":
            lines.append("")  # blank line after list
        if t.type == "heading_open":
            # add a blank line before headings for spacing
            if lines and lines[-1] != "":
                lines.append("")
    if current:
        lines.append(" ".join(current))
    # Normalize: split long lines
    normalized = []
    for line in lines:
        if not line:
            normalized.append("")
            continue
        while len(line) > 100:
            normalized.append(line[:100])
            line = line[100:]
        normalized.append(line)
    return normalized

def markdown_to_pdf_bytes(md_text: str) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    width, height = LETTER
    left_margin = 40
    top = height - 40
    y = top
    line_height = 14

    for line in markdown_to_plain_lines(md_text):
        if y < 40:
            c.showPage()
            y = top
        c.drawString(left_margin, y, line)
        y -= line_height

    c.showPage()
    c.save()
    return buf.getvalue()
