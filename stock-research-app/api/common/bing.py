from __future__ import annotations

from typing import Any, Dict, List, Optional
import re

import httpx
from bs4 import BeautifulSoup
try:
    from readability.readability import Document  # provided by readability-lxml
except Exception:
    Document = None  # type: ignore

from .config import Settings

def web_search(query: str, top_k: int = 6) -> List[Dict[str, str]]:
    """
    Uses Bing Web Search v7 if configured. Otherwise returns [].
    Output items: {"title": str, "url": str, "excerpt": str}
    """
    q = (query or "").strip()
    if not q:
        return []
    key = (Settings.BING_V7_KEY or "").strip()
    endpoint = (Settings.BING_V7_ENDPOINT or "https://api.bing.microsoft.com").rstrip("/")
    if not key:
        return []

    url = f"{endpoint}/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": key}
    params = {"q": q, "count": max(1, int(top_k or 1)), "textDecorations": False, "safeSearch": "Moderate"}
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(url, headers=headers, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception:
        return []

    items: List[Dict[str, str]] = []
    for it in (data.get("webPages") or {}).get("value", []):
        title = (it.get("name") or "").strip()
        link = (it.get("url") or "").strip()
        snippet = (it.get("snippet") or "").strip()
        if link:
            items.append({"title": title or link, "url": link, "excerpt": snippet})
        if len(items) >= top_k:
            break
    return items

def _strip_text(t: str) -> str:
    t = re.sub(r"\s+", " ", (t or "").strip())
    return t

def fetch_and_extract(url: str) -> Optional[Dict[str, str]]:
    """
    Fetches a URL and extracts a readable title + excerpt using readability-lxml.
    Returns {"title": str, "url": str, "excerpt": str} or None on failure.
    """
    u = (url or "").strip()
    if not u:
        return None
    try:
        with httpx.Client(follow_redirects=True, timeout=20.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
            r = client.get(u)
            r.raise_for_status()
            html = r.text
    except Exception:
        return {"title": u, "url": u, "excerpt": ""}

    if Document is not None:
        try:
            doc = Document(html)
            title = _strip_text(doc.short_title() or "") or u
            summary_html = doc.summary(html_partial=True)
            soup = BeautifulSoup(summary_html, "html.parser")
            text = _strip_text(soup.get_text(separator=" ").strip())
            excerpt = text[:700]
            return {"title": title, "url": u, "excerpt": excerpt}
        except Exception:
            pass
    try:
        # Fallback: crude extraction from full page
        soup = BeautifulSoup(html, "html.parser")
        title = _strip_text((soup.title.string if soup.title else "") or "") or u
        text = _strip_text(soup.get_text(separator=" ").strip())
        excerpt = text[:700]
        return {"title": title, "url": u, "excerpt": excerpt}
    except Exception:
        return {"title": u, "url": u, "excerpt": ""}
