from __future__ import annotations

from typing import Dict, Any, List
from ..common import bing

def main(input: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Activity: fetch_context
    Input:
      - {"prompt": "detailed research prompt ..."} OR
      - {"symbol": "AAPL"} (backward compatible)
    Output: [{"title": str, "url": str, "excerpt": str}, ...]
    """
    input = input or {}
    prompt = (input.get("prompt") or "").strip()
    symbol = (input.get("symbol") or "").strip()

    if prompt:
        query = prompt
    elif symbol:
        query = f"{symbol} stock latest news earnings financial results analysis"
    else:
        return []

    results = bing.web_search(query, top_k=6)
    sources: List[Dict[str, str]] = []
    for r in results:
        url = r.get("url")
        if not url:
            continue
        extracted = bing.fetch_and_extract(url)
        if extracted:
            sources.append(extracted)

    # De-dup by URL
    seen = set()
    uniq: List[Dict[str, str]] = []
    for s in sources:
        u = s.get("url")
        if u and u not in seen:
            uniq.append(s)
            seen.add(u)

    return uniq
