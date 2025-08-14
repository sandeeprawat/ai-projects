from __future__ import annotations

import re
from typing import List, Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup
from readability import Document
from .config import Settings

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

def web_search(query: str, top_k: int = 5, market: str = "en-US") -> List[Dict[str, str]]:
    """
    Uses Azure Bing Search v7 to fetch top results.
    Returns: [{title, url, snippet}]
    """
    key = Settings.BING_V7_KEY
    endpoint = Settings.BING_V7_ENDPOINT
    if not key or not endpoint:
        raise RuntimeError("Bing Search configuration missing (BING_V7_KEY/BING_V7_ENDPOINT).")

    url = f"{endpoint.rstrip('/')}/bing/v7.0/search"
    params = {"q": query, "count": top_k, "mkt": market, "responseFilter": "Webpages"}
    headers = {"Ocp-Apim-Subscription-Key": key, **DEFAULT_HEADERS}

    with httpx.Client(timeout=20) as client:
        r = client.get(url, params=params, headers=headers)
        r.raise_for_status()
        data = r.json()
        items = []
        for it in (data.get("webPages") or {}).get("value", []):
            items.append({
                "title": it.get("name", ""),
                "url": it.get("url", ""),
                "snippet": it.get("snippet", "")
            })
        return items

def fetch_and_extract(url: str, max_chars: int = 4000) -> Optional[Dict[str, str]]:
    """
    Fetches a URL and extracts the main content using readability.
    Returns {title, url, excerpt} or None on failure.
    """
    try:
        with httpx.Client(timeout=20, headers=DEFAULT_HEADERS, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
        doc = Document(html)
        title = doc.short_title() or ""
        content_html = doc.summary()
        soup = BeautifulSoup(content_html, "lxml")
        # Remove scripts/styles/navs
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        # Normalize whitespace
        text = re.sub(r"\s+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        excerpt = text[:max_chars]
        if not excerpt:
            return None
        return {"title": title, "url": url, "excerpt": excerpt}
    except Exception:
        return None
