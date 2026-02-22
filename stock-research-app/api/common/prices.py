# Shared utility for fetching stock prices via yfinance
from __future__ import annotations

import logging
from typing import Dict, List, Optional

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
