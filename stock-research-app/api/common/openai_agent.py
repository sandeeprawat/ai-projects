from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional
from markdown_it import MarkdownIt

try:
    # Azure OpenAI SDK via OpenAI 1.x
    from openai import AzureOpenAI  # type: ignore
except Exception:  # pragma: no cover
    AzureOpenAI = None  # type: ignore

from .config import Settings

_md = MarkdownIt("commonmark")

def _build_prompt(symbols: List[str], sources_per_symbol: List[Dict[str, Any]], user_prompt: Optional[str] = None) -> str:
    lines: List[str] = []
    lines.append("You are an equity research assistant. Create a concise but detailed research brief.")
    lines.append("")
    if user_prompt:
        lines.append("User Research Prompt:")
        lines.append(user_prompt)
        lines.append("")
    lines.append(f"Symbols: {', '.join(symbols)}" if symbols else "Symbols: (provided via prompt)")
    lines.append("")
    for entry in sources_per_symbol:
        sym = entry.get("symbol") or ""
        lines.append(f"Sources for {sym}:")
        for s in entry.get("sources") or []:
            title = s.get("title") or ""
            url = s.get("url") or ""
            excerpt = (s.get("excerpt") or "").strip()
            lines.append(f"- {title} ({url})")
            if excerpt:
                lines.append(f"  Excerpt: {excerpt[:500]}")
        lines.append("")
    lines.append("Output markdown with sections: Overview, Recent Developments, Financials, Risks, Outlook.")
    lines.append("Cite sources inline as [n] and provide a Citations list at the end with title + URL.")
    return "\n".join(lines)

def _fallback_report(symbols: List[str], sources_per_symbol: List[Dict[str, Any]], user_prompt: Optional[str] = None) -> Tuple[str, str, List[Dict[str, str]]]:
    title = f"Stock Research Report: {', '.join(symbols) or 'Prompted'}"
    citations: List[Dict[str, str]] = []
    idx = 1
    sections: List[str] = [f"# {title}", ""]
    sections.append("## Overview")
    sections.append("This is a locally generated summary (no Azure OpenAI configured).")
    if user_prompt:
        sections.append("")
        sections.append("## User Prompt")
        sections.append(user_prompt)
        sections.append("")
    sections.append("")
    for entry in sources_per_symbol:
        sym = entry.get("symbol") or ""
        sections.append(f"## {sym} - Recent Sources")
        for s in entry.get("sources") or []:
            t = s.get("title") or "Source"
            u = s.get("url") or ""
            ex = (s.get("excerpt") or "").strip()
            if u:
                citations.append({"title": t, "url": u})
                sections.append(f"- {t} [{idx}]")
                if ex:
                    sections.append(f"  - {ex[:300]}")
                idx += 1
        sections.append("")
    if citations:
        sections.append("## Citations")
        for i, c in enumerate(citations, start=1):
            sections.append(f"[{i}] {c.get('title')}: {c.get('url')}")
    md = "\n".join(sections)
    return title, md, citations

def synthesize_report(symbols: List[str], sources_per_symbol: List[Dict[str, Any]], user_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns: {"title": str, "markdown": str, "html": str, "citations": [...]}
    """
    api_key = Settings.AZURE_OPENAI_API_KEY
    endpoint = Settings.AZURE_OPENAI_ENDPOINT
    api_version = Settings.AZURE_OPENAI_API_VERSION
    deployment = Settings.AZURE_OPENAI_DEPLOYMENT

    # Fallback to offline summary if not configured
    if not (AzureOpenAI and api_key and endpoint and deployment):
        title, md, citations = _fallback_report(symbols, sources_per_symbol, user_prompt)
        html = _md.render(md)
        return {"title": title, "markdown": md, "html": html, "citations": citations}

    prompt = _build_prompt(symbols, sources_per_symbol, user_prompt)
    client = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)

    try:
        completion = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are a helpful financial research assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=2000,
        )
        text = (completion.choices[0].message.content or "").strip()
        if not text:
            # Guard rail
            title, md, citations = _fallback_report(symbols, sources_per_symbol, user_prompt)
            html = _md.render(md)
            return {"title": title, "markdown": md, "html": html, "citations": citations}

        # Try to infer a title as first H1
        title_line = next((line.strip("# ").strip() for line in text.splitlines() if line.startswith("# ")), None)
        title = title_line or f"Stock Research Report: {', '.join(symbols)}"
        md = text
        html = _md.render(md)

        # Build naive citations list from sources we provided
        citations: List[Dict[str, str]] = []
        for entry in sources_per_symbol:
            for s in entry.get("sources") or []:
                u = s.get("url")
                t = s.get("title") or "Source"
                if u:
                    citations.append({"title": t, "url": u})
        return {"title": title, "markdown": md, "html": html, "citations": citations}
    except Exception:
        # On any error, fallback
        title, md, citations = _fallback_report(symbols, sources_per_symbol, user_prompt)
        html = _md.render(md)
        return {"title": title, "markdown": md, "html": html, "citations": citations}
