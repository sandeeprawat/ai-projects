from __future__ import annotations

from typing import Dict, Any, List
from ..common.openai_agent import synthesize_report as _synthesize

def main(input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity: synthesize_report
    Input: {"symbols": ["AAPL","MSFT"], "sources": [{ "symbol": "AAPL", "sources": [...] }, ...], "prompt": str?}
    Output: {"title": str, "markdown": str, "html": str, "citations": [...]}
    """
    input = input or {}
    symbols: List[str] = input.get("symbols") or []
    sources_per_symbol = input.get("sources") or []
    prompt: str = input.get("prompt") or ""
    deep_research: bool = bool(input.get("deepResearch", False))
    return _synthesize(symbols, sources_per_symbol, prompt or None, deep_research)
