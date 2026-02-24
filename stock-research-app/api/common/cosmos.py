from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4
from datetime import datetime, timezone

from .models import Schedule, Run, Report, TrackedStock

# ─────────────────────────────────────────────────────────────────────────────
# Determine storage mode: Cosmos DB (cloud) vs local JSON file (dev)
# ─────────────────────────────────────────────────────────────────────────────

COSMOS_DB_URL = os.getenv("COSMOS_DB_URL", "")
COSMOS_DB_KEY = os.getenv("COSMOS_DB_KEY", "")
COSMOS_DB_NAME = os.getenv("COSMOS_DB_NAME", "stockresearch")

# Managed Identity settings
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")  # User-assigned managed identity

# Detect if running in Azure (WEBSITE_SITE_NAME is set by Azure App Service/Functions)
IS_RUNNING_IN_AZURE = bool(os.getenv("WEBSITE_SITE_NAME"))

# Allow explicit override via USE_LOCAL_STORAGE=true
USE_LOCAL_STORAGE = os.getenv("USE_LOCAL_STORAGE", "").lower() in ("true", "1", "yes")

# Use Cosmos DB only if:
# 1. Running in Azure AND COSMOS_DB_URL is set (will use Managed Identity), OR
# 2. Not forcing local storage AND COSMOS_DB_URL is set with a valid KEY
USE_COSMOS = bool(COSMOS_DB_URL) and not USE_LOCAL_STORAGE and (IS_RUNNING_IN_AZURE or bool(COSMOS_DB_KEY))

# Cosmos DB client (lazy init)
_cosmos_client = None
_cosmos_db = None
_containers: Dict[str, Any] = {}


def _get_cosmos_container(container_name: str):
    """Get or create a Cosmos DB container reference."""
    global _cosmos_client, _cosmos_db, _containers
    
    if container_name in _containers:
        return _containers[container_name]
    
    if _cosmos_client is None:
        from azure.cosmos import CosmosClient
        
        # Prefer Managed Identity in Azure, fall back to key-based auth
        if IS_RUNNING_IN_AZURE and not COSMOS_DB_KEY:
            # Use Managed Identity (user-assigned if client ID provided)
            if AZURE_CLIENT_ID:
                from azure.identity import ManagedIdentityCredential
                credential = ManagedIdentityCredential(client_id=AZURE_CLIENT_ID)
            else:
                from azure.identity import DefaultAzureCredential
                credential = DefaultAzureCredential()
            _cosmos_client = CosmosClient(COSMOS_DB_URL, credential=credential)
        elif COSMOS_DB_KEY:
            # Use key-based auth if key is provided
            _cosmos_client = CosmosClient(COSMOS_DB_URL, credential=COSMOS_DB_KEY)
        else:
            # Use AAD/Managed Identity auth as fallback
            from azure.identity import DefaultAzureCredential
            credential = DefaultAzureCredential()
            _cosmos_client = CosmosClient(COSMOS_DB_URL, credential=credential)
        
        _cosmos_db = _cosmos_client.get_database_client(COSMOS_DB_NAME)
    
    _containers[container_name] = _cosmos_db.get_container_client(container_name)
    return _containers[container_name]


# ─────────────────────────────────────────────────────────────────────────────
# Local file storage (for development)
# ─────────────────────────────────────────────────────────────────────────────

_DATA_DIR = Path(__file__).resolve().parents[2] / ".data"
_DATA_FILE = _DATA_DIR / "db.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ensure_store() -> Dict[str, Any]:
    """Local file store for development."""
    if not _DATA_DIR.exists():
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _DATA_FILE.exists():
        initial = {"schedules": [], "runs": [], "reports": [], "tracked_stocks": []}
        _DATA_FILE.write_text(json.dumps(initial, indent=2), encoding="utf-8")
        return initial
    try:
        data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        if "tracked_stocks" not in data:
            data["tracked_stocks"] = []
        return data
    except Exception:
        initial = {"schedules": [], "runs": [], "reports": [], "tracked_stocks": []}
        _DATA_FILE.write_text(json.dumps(initial, indent=2), encoding="utf-8")
        return initial


def _save_store(db: Dict[str, Any]) -> None:
    _DATA_FILE.write_text(json.dumps(db, indent=2), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Schedules
# ─────────────────────────────────────────────────────────────────────────────

def create_schedule(sched: Schedule) -> Dict[str, Any]:
    data = sched.model_dump()
    data["id"] = data.get("id") or str(uuid4())
    data["createdAt"] = _now_iso()
    
    if USE_COSMOS:
        container = _get_cosmos_container("schedules")
        container.create_item(body=data)
        return data
    else:
        db = _ensure_store()
        db["schedules"].append(data)
        _save_store(db)
        return data


def get_schedule(schedule_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    if USE_COSMOS:
        container = _get_cosmos_container("schedules")
        try:
            item = container.read_item(item=schedule_id, partition_key=user_id)
            return dict(item)
        except Exception:
            return None
    else:
        db = _ensure_store()
        for s in db.get("schedules", []):
            if s.get("id") == schedule_id and s.get("userId") == user_id:
                return s
        return None


def list_due_schedules(now_iso: str, limit: int = 50) -> List[Dict[str, Any]]:
    if USE_COSMOS:
        container = _get_cosmos_container("schedules")
        query = """
            SELECT * FROM c 
            WHERE c.active = true AND c.nextRunAt != null AND c.nextRunAt <= @now
            ORDER BY c.nextRunAt ASC
            OFFSET 0 LIMIT @limit
        """
        items = list(container.query_items(
            query=query,
            parameters=[
                {"name": "@now", "value": now_iso},
                {"name": "@limit", "value": limit}
            ],
            enable_cross_partition_query=True
        ))
        return [dict(i) for i in items]
    else:
        db = _ensure_store()
        due = []
        for s in db.get("schedules", []):
            try:
                if not s.get("active", True):
                    continue
                nra = s.get("nextRunAt")
                if not nra:
                    continue
                if nra <= now_iso:
                    due.append(s)
            except Exception:
                continue
        due.sort(key=lambda x: (x.get("nextRunAt") or ""))
        return due[:limit]


def update_schedule_next_run(schedule_id: str, user_id: str, next_iso: str) -> bool:
    if USE_COSMOS:
        container = _get_cosmos_container("schedules")
        try:
            item = container.read_item(item=schedule_id, partition_key=user_id)
            item["nextRunAt"] = next_iso
            container.replace_item(item=schedule_id, body=item)
            return True
        except Exception:
            return False
    else:
        db = _ensure_store()
        changed = False
        for s in db.get("schedules", []):
            if s.get("id") == schedule_id and s.get("userId") == user_id:
                s["nextRunAt"] = next_iso
                changed = True
                break
        if changed:
            _save_store(db)
        return changed


def list_schedules_for_user(user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    if USE_COSMOS:
        container = _get_cosmos_container("schedules")
        query = """
            SELECT * FROM c 
            WHERE c.userId = @userId
            ORDER BY c.createdAt DESC
            OFFSET 0 LIMIT @limit
        """
        items = list(container.query_items(
            query=query,
            parameters=[
                {"name": "@userId", "value": user_id},
                {"name": "@limit", "value": limit}
            ],
            enable_cross_partition_query=True
        ))
        return [dict(i) for i in items]
    else:
        db = _ensure_store()
        items: List[Dict[str, Any]] = []
        for s in db.get("schedules", []):
            if s.get("userId") != user_id:
                continue
            items.append(s)
        items.sort(key=lambda x: (x.get("createdAt") or ""), reverse=True)
        return items[:limit]


def delete_schedule(schedule_id: str, user_id: str) -> bool:
    if USE_COSMOS:
        container = _get_cosmos_container("schedules")
        try:
            container.delete_item(item=schedule_id, partition_key=user_id)
            return True
        except Exception:
            return False
    else:
        db = _ensure_store()
        schedules = db.get("schedules", [])
        kept: List[Dict[str, Any]] = []
        deleted = False
        for s in schedules:
            if s.get("id") == schedule_id and s.get("userId") == user_id:
                deleted = True
            else:
                kept.append(s)
        if not deleted:
            return False
        db["schedules"] = kept
        _save_store(db)
        return True


def update_schedule(schedule_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
    """Update a schedule with the given fields."""
    if USE_COSMOS:
        container = _get_cosmos_container("schedules")
        try:
            item = container.read_item(item=schedule_id, partition_key=user_id)
            item.update(updates)
            container.replace_item(item=schedule_id, body=item)
            return True
        except Exception:
            return False
    else:
        db = _ensure_store()
        changed = False
        for s in db.get("schedules", []):
            if s.get("id") == schedule_id and s.get("userId") == user_id:
                s.update(updates)
                changed = True
                break
        if changed:
            _save_store(db)
        return changed


# ─────────────────────────────────────────────────────────────────────────────
# Runs
# ─────────────────────────────────────────────────────────────────────────────

def create_run(run: Run) -> Dict[str, Any]:
    data = run.model_dump()
    data["id"] = data.get("id") or str(uuid4())
    data["createdAt"] = _now_iso()
    
    if USE_COSMOS:
        container = _get_cosmos_container("runs")
        container.create_item(body=data)
        return data
    else:
        db = _ensure_store()
        db["runs"].append(data)
        _save_store(db)
        return data


def delete_runs_for_schedule(schedule_id: str, user_id: str) -> int:
    if USE_COSMOS:
        container = _get_cosmos_container("runs")
        query = "SELECT * FROM c WHERE c.scheduleId = @scheduleId AND c.userId = @userId"
        items = list(container.query_items(
            query=query,
            parameters=[
                {"name": "@scheduleId", "value": schedule_id},
                {"name": "@userId", "value": user_id}
            ],
            enable_cross_partition_query=True
        ))
        deleted = 0
        for item in items:
            try:
                container.delete_item(item=item["id"], partition_key=user_id)
                deleted += 1
            except Exception:
                pass
        return deleted
    else:
        db = _ensure_store()
        runs = db.get("runs", [])
        kept: List[Dict[str, Any]] = []
        deleted = 0
        for r in runs:
            if r.get("scheduleId") == schedule_id and r.get("userId") == user_id:
                deleted += 1
            else:
                kept.append(r)
        db["runs"] = kept
        _save_store(db)
        return deleted


# ─────────────────────────────────────────────────────────────────────────────
# Reports
# ─────────────────────────────────────────────────────────────────────────────

def save_report(report: Report) -> Dict[str, Any]:
    data = report.model_dump()
    data["id"] = data.get("id") or str(uuid4())
    data["createdAt"] = data.get("createdAt") or _now_iso()
    
    if USE_COSMOS:
        container = _get_cosmos_container("reports")
        container.create_item(body=data)
        return data
    else:
        db = _ensure_store()
        db["reports"].append(data)
        _save_store(db)
        return data


def get_report(report_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    if USE_COSMOS:
        container = _get_cosmos_container("reports")
        try:
            item = container.read_item(item=report_id, partition_key=user_id)
            return dict(item)
        except Exception:
            return None
    else:
        db = _ensure_store()
        for r in db.get("reports", []):
            if r.get("id") == report_id and r.get("userId") == user_id:
                return r
        return None


def list_reports_for_user(user_id: str, schedule_id: Optional[str] = None, limit: int = 50) -> Iterable[Dict[str, Any]]:
    if USE_COSMOS:
        container = _get_cosmos_container("reports")
        if schedule_id:
            query = """
                SELECT * FROM c 
                WHERE c.userId = @userId AND c.scheduleId = @scheduleId
                ORDER BY c.createdAt DESC
                OFFSET 0 LIMIT @limit
            """
            params = [
                {"name": "@userId", "value": user_id},
                {"name": "@scheduleId", "value": schedule_id},
                {"name": "@limit", "value": limit}
            ]
        else:
            query = """
                SELECT * FROM c 
                WHERE c.userId = @userId
                ORDER BY c.createdAt DESC
                OFFSET 0 LIMIT @limit
            """
            params = [
                {"name": "@userId", "value": user_id},
                {"name": "@limit", "value": limit}
            ]
        items = list(container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True
        ))
        return [dict(i) for i in items]
    else:
        db = _ensure_store()
        items: List[Dict[str, Any]] = []
        for r in db.get("reports", []):
            if r.get("userId") != user_id:
                continue
            if schedule_id and r.get("scheduleId") != schedule_id:
                continue
            items.append(r)
        items.sort(key=lambda x: (x.get("createdAt") or ""), reverse=True)
        return items[:limit]


def delete_report(report_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    if USE_COSMOS:
        container = _get_cosmos_container("reports")
        try:
            item = container.read_item(item=report_id, partition_key=user_id)
            container.delete_item(item=report_id, partition_key=user_id)
            return dict(item)
        except Exception:
            return None
    else:
        db = _ensure_store()
        reports = db.get("reports", [])
        deleted: Optional[Dict[str, Any]] = None
        kept: List[Dict[str, Any]] = []
        for r in reports:
            if r.get("id") == report_id and r.get("userId") == user_id:
                deleted = r
            else:
                kept.append(r)
        if deleted is None:
            return None
        db["reports"] = kept
        _save_store(db)
        return deleted


def list_all_reports() -> List[Dict[str, Any]]:
    """Returns all reports across users (for cleanup/maintenance tasks)."""
    if USE_COSMOS:
        container = _get_cosmos_container("reports")
        query = "SELECT * FROM c"
        items = list(container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        return [dict(i) for i in items]
    else:
        db = _ensure_store()
        return list(db.get("reports", []))


# ─────────────────────────────────────────────────────────────────────────────
# Tracked Stocks
# ─────────────────────────────────────────────────────────────────────────────

def get_tracked_stock_by_symbol(user_id: str, symbol: str, report_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Return the existing tracked stock for a user+symbol+reportId, or None."""
    if USE_COSMOS:
        container = _get_cosmos_container("tracked_stocks")
        if report_id:
            query = "SELECT * FROM c WHERE c.userId = @userId AND c.symbol = @symbol AND c.reportId = @reportId"
            params = [
                {"name": "@userId", "value": user_id},
                {"name": "@symbol", "value": symbol},
                {"name": "@reportId", "value": report_id}
            ]
        else:
            query = "SELECT * FROM c WHERE c.userId = @userId AND c.symbol = @symbol AND (NOT IS_DEFINED(c.reportId) OR c.reportId = null)"
            params = [
                {"name": "@userId", "value": user_id},
                {"name": "@symbol", "value": symbol}
            ]
        items = list(container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True
        ))
        return dict(items[0]) if items else None
    else:
        db = _ensure_store()
        for ts in db.get("tracked_stocks", []):
            if ts.get("userId") == user_id and ts.get("symbol") == symbol:
                if report_id:
                    if ts.get("reportId") == report_id:
                        return ts
                else:
                    if not ts.get("reportId"):
                        return ts
        return None


def create_tracked_stock(stock: TrackedStock) -> Dict[str, Any]:
    """Create a tracked stock. Dedup by (userId, symbol, reportId)."""
    existing = get_tracked_stock_by_symbol(stock.userId, stock.symbol, stock.reportId)
    if existing:
        # Keep the earlier recommendation
        if existing.get("recommendationDate", "") <= stock.recommendationDate:
            return existing
        # New one is earlier – replace
        delete_tracked_stock(existing["id"], stock.userId)

    data = stock.model_dump()
    data["id"] = data.get("id") or str(uuid4())
    data["createdAt"] = _now_iso()

    if USE_COSMOS:
        container = _get_cosmos_container("tracked_stocks")
        container.create_item(body=data)
        return data
    else:
        db = _ensure_store()
        db["tracked_stocks"].append(data)
        _save_store(db)
        return data


def list_tracked_stocks_for_user(user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    if USE_COSMOS:
        container = _get_cosmos_container("tracked_stocks")
        query = """
            SELECT * FROM c
            WHERE c.userId = @userId
            ORDER BY c.symbol ASC
            OFFSET 0 LIMIT @limit
        """
        items = list(container.query_items(
            query=query,
            parameters=[
                {"name": "@userId", "value": user_id},
                {"name": "@limit", "value": limit}
            ],
            enable_cross_partition_query=True
        ))
        return [dict(i) for i in items]
    else:
        db = _ensure_store()
        items: List[Dict[str, Any]] = []
        for ts in db.get("tracked_stocks", []):
            if ts.get("userId") == user_id:
                items.append(ts)
        items.sort(key=lambda x: x.get("symbol", ""))
        return items[:limit]


def delete_tracked_stock(stock_id: str, user_id: str) -> bool:
    if USE_COSMOS:
        container = _get_cosmos_container("tracked_stocks")
        try:
            container.delete_item(item=stock_id, partition_key=user_id)
            return True
        except Exception:
            return False
    else:
        db = _ensure_store()
        stocks = db.get("tracked_stocks", [])
        kept: List[Dict[str, Any]] = []
        deleted = False
        for ts in stocks:
            if ts.get("id") == stock_id and ts.get("userId") == user_id:
                deleted = True
            else:
                kept.append(ts)
        if not deleted:
            return False
        db["tracked_stocks"] = kept
        _save_store(db)
        return True
