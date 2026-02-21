# Fetch current prices for symbols (HTTP GET /api/tracked-stocks/prices?symbols=AAPL,MSFT)
from __future__ import annotations

import json
import logging
import azure.functions as func

from ..common.auth import get_user_context

logger = logging.getLogger(__name__)


def _fetch_prices(symbols: list[str]) -> dict[str, float | None]:
    """Fetch current market prices via yfinance."""
    try:
        import yfinance as yf
        result: dict[str, float | None] = {}
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


async def main(req: func.HttpRequest) -> func.HttpResponse:
    get_user_context(dict(req.headers))  # auth check

    raw = req.params.get("symbols", "")
    symbols = [s.strip().upper() for s in raw.split(",") if s.strip()]

    if not symbols:
        return func.HttpResponse(
            json.dumps({"error": "symbols query parameter required (comma-separated)"}),
            status_code=400,
            mimetype="application/json",
        )

    # Cap at 50 symbols per request
    symbols = symbols[:50]
    prices = _fetch_prices(symbols)

    return func.HttpResponse(
        json.dumps({"prices": prices}),
        status_code=200,
        mimetype="application/json",
    )
