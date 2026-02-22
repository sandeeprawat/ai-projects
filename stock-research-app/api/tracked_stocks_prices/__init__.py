# Fetch current prices for symbols (HTTP GET /api/tracked-stocks/prices?symbols=AAPL,MSFT)
from __future__ import annotations

import json
import azure.functions as func

from ..common.auth import get_user_context
from ..common.prices import fetch_prices


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
    prices = fetch_prices(symbols)

    return func.HttpResponse(
        json.dumps({"prices": prices}),
        status_code=200,
        mimetype="application/json",
    )
