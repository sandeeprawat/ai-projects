from __future__ import annotations

from typing import List, Dict, Any
from openai import AzureOpenAI
from .config import Settings
from markdown_it import MarkdownIt

_md = MarkdownIt()

def _md_to_html(md_text: str) -> str:
    return _md.render(md_text)

def synthesize_report(symbols: List[str], sources_per_symbol: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calls Azure OpenAI to synthesize a detailed stock research report with citations.
    sources_per_symbol: [{ "symbol": "AAPL", "sources": [ { "title": str, "url": str, "excerpt": str }, ... ] }, ...]
    Returns: { "title": str, "markdown": str, "html": str, "citations": [ { "n": int, "title": str, "url": str } ] }
    """
    if not Settings.AZURE_OPENAI_ENDPOINT or not Settings.AZURE_OPENAI_API_KEY or not Settings.AZURE_OPENAI_DEPLOYMENT:
        raise RuntimeError("Azure OpenAI configuration missing (endpoint/key/deployment).")

    client = AzureOpenAI(
        azure_endpoint=Settings.AZURE_OPENAI_ENDPOINT,
        api_key=Settings.AZURE_OPENAI_API_KEY,
        api_version=Settings.AZURE_OPENAI_API_VERSION,
    )

    # Flatten and enumerate citations
    flat_sources: List[Dict[str, str]] = []
    for entry in sources_per_symbol:
        symbol = entry.get("symbol")
        for s in entry.get("sources", [])[:8]:
            flat_sources.append({
                "symbol": symbol,
                "title": (s.get("title") or "")[:200],
                "url": s.get("url") or "",
                "excerpt": (s.get("excerpt") or "")[:1200],
            })
    # Deduplicate by URL while keeping order
    seen = set()
    unique_sources = []
    for s in flat_sources:
        u = s["url"]
        if u and u not in seen:
            unique_sources.append(s)
            seen.add(u)
    citations = [{"n": i + 1, "title": s["title"], "url": s["url"]} for i, s in enumerate(unique_sources)]

    system_prompt = (
        "You are a financial research analyst. Produce a thorough, factual, and impartial report covering:\n"
        "- Company overview and recent developments\n"
        "- Financials, growth, margins, balance sheet, cash flows\n"
        "- Valuation (multiples, comps), catalysts, and risks\n"
        "- Technical/price action context if material\n"
        "Cite sources inline using bracketed numbers like [1], [2], ... referencing the bibliography.\n"
        "Only cite when a claim comes from a specific source. Summaries and opinions should be clearly marked.\n"
        "Write for a professional audience. Avoid hallucinations. If uncertain, state limitations."
    )

    sources_text_lines = []
    for i, s in enumerate(unique_sources[:20], start=1):
        sources_text_lines.append(f"[{i}] {s['title']} - {s['url']}\nExcerpt: {s['excerpt']}")
    sources_text = "\n\n".join(sources_text_lines)

    user_prompt = (
        f"Symbols: {', '.join(symbols)}\n\n"
        "Use the following curated web excerpts to write a comprehensive multi-section report. "
        "Include an executive summary at the top, then detailed sections. "
        "Finish with a bibliography listing the numbered sources exactly as [n] Title - URL.\n\n"
        f"Sources:\n{sources_text}"
    )

    resp = client.chat.completions.create(
        model=Settings.AZURE_OPENAI_DEPLOYMENT,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=3000,
    )
    content = (resp.choices[0].message.content or "").strip()

    title = f"Stock Research Report: {', '.join(symbols)}"
    html = _md_to_html(content)

    return {
        "title": title,
        "markdown": content,
        "html": html,
        "citations": citations,
    }
