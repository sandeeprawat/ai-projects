# Create tracked stock (HTTP POST /api/tracked-stocks)
from __future__ import annotations

import json
import azure.functions as func

from ..common.auth import get_user_context
from ..common.cosmos import create_tracked_stock
from ..common.models import TrackedStock


async def main(req: func.HttpRequest) -> func.HttpResponse:
    user = get_user_context(dict(req.headers))
    user_id = user.get("userId") or "dev-user"

    try:
        body = req.get_json()
    except Exception:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            status_code=400,
            mimetype="application/json",
        )

    symbol = (body.get("symbol") or "").strip().upper()
    recommendation_date = (body.get("recommendationDate") or "").strip()
    recommendation_price = body.get("recommendationPrice")

    if not symbol:
        return func.HttpResponse(
            json.dumps({"error": "symbol is required"}),
            status_code=400,
            mimetype="application/json",
        )
    if not recommendation_date:
        return func.HttpResponse(
            json.dumps({"error": "recommendationDate is required"}),
            status_code=400,
            mimetype="application/json",
        )
    if recommendation_price is None:
        return func.HttpResponse(
            json.dumps({"error": "recommendationPrice is required"}),
            status_code=400,
            mimetype="application/json",
        )

    try:
        price = float(recommendation_price)
    except (TypeError, ValueError):
        return func.HttpResponse(
            json.dumps({"error": "recommendationPrice must be a number"}),
            status_code=400,
            mimetype="application/json",
        )

    stock = TrackedStock(
        userId=user_id,
        symbol=symbol,
        reportTitle=body.get("reportTitle"),
        reportId=body.get("reportId"),
        recommendationDate=recommendation_date,
        recommendationPrice=price,
    )

    result = create_tracked_stock(stock)

    return func.HttpResponse(
        json.dumps(result),
        status_code=201,
        mimetype="application/json",
    )
