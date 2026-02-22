# Shared utility for fetching stock prices via yfinance
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def fetch_prices(symbols: List[str]) -> Dict[str, Optional[float]]:
    """Fetch current market prices via yfinance. Returns {symbol: price_or_None}."""
    if not symbols:
        return {}
    try:
        import yfinance as yf
        result: Dict[str, Optional[float]] = {}
        tickers = yf.Tickers(" ".join(symbols))
        for sym in symbols:
            try:
                info = tickers.tickers[sym].fast_info
                price = getattr(info, "last_price", None)
                result[sym] = round(price, 2) if price else None
            except Exception:
                result[sym] = None
        return result
    except Exception as exc:
        logger.warning("yfinance fetch failed: %s", exc)
        return {s: None for s in symbols}


def extract_stock_recommendations(markdown: str) -> Dict[str, Any]:
    """Use Azure OpenAI to determine if a report is stock-related and extract
    recommended stock ticker symbols from the report content.

    Returns:
        {"isStockRelated": bool, "stocks": [{"symbol": "AAPL"}, ...]}
    """
    from .config import Settings

    fallback: Dict[str, Any] = {"isStockRelated": False, "stocks": []}

    endpoint = Settings.AZURE_OPENAI_ENDPOINT
    api_key = Settings.AZURE_OPENAI_API_KEY
    api_version = Settings.AZURE_OPENAI_API_VERSION
    deployment = Settings.AZURE_OPENAI_DEPLOYMENT

    if not (endpoint and api_key and deployment):
        logger.warning("extract_stock_recommendations: OpenAI not configured")
        return fallback

    # Truncate to keep token usage reasonable
    content = markdown[:6000] if len(markdown) > 6000 else markdown

    system_msg = (
        "You analyse research reports. Determine if the report is about the stock market "
        "(individual stocks, equities, ETFs). If it is, extract every stock ticker symbol "
        "that the report recommends, analyses, or discusses as an investment.\n\n"
        "Respond ONLY with valid JSON, no markdown fences:\n"
        '{"isStockRelated": true/false, "stocks": [{"symbol": "AAPL"}, ...]}\n\n'
        "Rules:\n"
        "- Use uppercase US ticker symbols (e.g. AAPL, MSFT, TSLA).\n"
        "- Only include stocks the report substantively discusses, not passing mentions.\n"
        "- If the report is not about stocks/equities, return isStockRelated=false and empty stocks.\n"
    )

    try:
        from openai import AzureOpenAI
        client = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)
        completion = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": content},
            ],
            temperature=0.0,
            max_tokens=500,
        )
        raw = (completion.choices[0].message.content or "").strip()
        # Strip markdown fences if the model wraps the JSON
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        result = json.loads(raw)
        if not isinstance(result.get("stocks"), list):
            result["stocks"] = []
        return result
    except Exception as exc:
        logger.warning("extract_stock_recommendations failed: %s", exc)
        return fallback
