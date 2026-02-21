# Delete tracked stock (HTTP DELETE /api/tracked-stocks/{id})
from __future__ import annotations

import json
import azure.functions as func

from ..common.auth import get_user_context
from ..common.cosmos import delete_tracked_stock


async def main(req: func.HttpRequest) -> func.HttpResponse:
    user = get_user_context(dict(req.headers))
    user_id = user.get("userId") or "dev-user"

    stock_id = req.route_params.get("id", "")
    if not stock_id:
        return func.HttpResponse(
            json.dumps({"error": "Stock id is required"}),
            status_code=400,
            mimetype="application/json",
        )

    deleted = delete_tracked_stock(stock_id, user_id)

    if not deleted:
        return func.HttpResponse(
            json.dumps({"error": "Tracked stock not found"}),
            status_code=404,
            mimetype="application/json",
        )

    return func.HttpResponse(
        json.dumps({"deleted": True, "stockId": stock_id}),
        status_code=200,
        mimetype="application/json",
    )
