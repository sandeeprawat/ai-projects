# Fetch current prices for symbols (HTTP GET /api/tracked-stocks/prices?symbols=AAPL,MSFT&exchanges=,)
from __future__ import annotations

import json
import logging
import azure.functions as func

from ..common.auth import get_user_context

logger = logging.getLogger(__name__)

# yfinance suffix per exchange
_EXCHANGE_SUFFIX = {
    "NSE": ".NS",
    "BSE": ".BO",
}


def _fetch_prices(symbols: list[str], exchanges: list[str]) -> dict[str, float | None]:
    """Fetch current market prices via yfinance, applying exchange suffixes."""
    try:
        import yfinance as yf
        # Build yfinance tickers with exchange suffixes
        yf_map: dict[str, str] = {}  # yf_ticker -> original_symbol
        for sym, exch in zip(symbols, exchanges):
            suffix = _EXCHANGE_SUFFIX.get(exch.upper(), "") if exch else ""
            yf_ticker = f"{sym}{suffix}"
            yf_map[yf_ticker] = sym

        result: dict[str, float | None] = {}
        tickers = yf.Tickers(" ".join(yf_map.keys()))
        for yf_ticker, orig_sym in yf_map.items():
            try:
                info = tickers.tickers[yf_ticker].fast_info
                price = getattr(info, "last_price", None)
                result[orig_sym] = round(price, 2) if price else None
            except Exception:
                result[orig_sym] = None
        return result
    except Exception as exc:
        logger.warning("yfinance fetch failed: %s", exc)
        return {s: None for s in symbols}


async def main(req: func.HttpRequest) -> func.HttpResponse:
    get_user_context(dict(req.headers))  # auth check

    raw = req.params.get("symbols", "")
    symbols = [s.strip().upper() for s in raw.split(",") if s.strip()]
    raw_exch = req.params.get("exchanges", "")
    exchanges_list = [e.strip().upper() for e in raw_exch.split(",")]
    # Pad exchanges to match symbols length
    while len(exchanges_list) < len(symbols):
        exchanges_list.append("")

    if not symbols:
        return func.HttpResponse(
            json.dumps({"error": "symbols query parameter required (comma-separated)"}),
            status_code=400,
            mimetype="application/json",
        )

    symbols = symbols[:50]
    exchanges_list = exchanges_list[:50]
    prices = _fetch_prices(symbols, exchanges_list)

    return func.HttpResponse(
        json.dumps({"prices": prices}),
        status_code=200,
        mimetype="application/json",
    )
