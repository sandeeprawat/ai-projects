from __future__ import annotations

from typing import Dict, Any, Optional, Iterable
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from .config import Settings
from .models import Schedule, Run, Report

_client: Optional[CosmosClient] = None
_db = None
_containers: Dict[str, Any] = {}

def _get_client() -> CosmosClient:
    global _client
    if _client is None:
        if not Settings.COSMOS_DB_URL or not Settings.COSMOS_DB_KEY:
            raise RuntimeError("COSMOS_DB_URL and COSMOS_DB_KEY must be set.")
        _client = CosmosClient(Settings.COSMOS_DB_URL, credential=Settings.COSMOS_DB_KEY)
    return _client

def _get_db():
    global _db
    if _db is None:
        _db = _get_client().create_database_if_not_exists(id=Settings.COSMOS_DB_NAME)
    return _db

def _get_container(name: str):
    global _containers
    if name in _containers:
        return _containers[name]
    db = _get_db()
    # All containers partition on /userId for per-user isolation
    container = db.create_container_if_not_exists(
        id=name,
        partition_key=PartitionKey(path="/userId")
    )
    _containers[name] = container
    return container

def ensure_containers() -> None:
    _get_container(Settings.COSMOS_CONTAINER_SCHEDULES)
    _get_container(Settings.COSMOS_CONTAINER_RUNS)
    _get_container(Settings.COSMOS_CONTAINER_REPORTS)

def upsert_item(container_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
    container = _get_container(container_name)
    return container.upsert_item(item)

def read_item(container_name: str, item_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    container = _get_container(container_name)
    try:
        return container.read_item(item=item_id, partition_key=user_id)
    except exceptions.CosmosResourceNotFoundError:
        return None

def query_items(container_name: str, query: str, params: Optional[Iterable[Dict[str, Any]]] = None) -> Iterable[Dict[str, Any]]:
    container = _get_container(container_name)
    return container.query_items(query=query, parameters=params or [], enable_cross_partition_query=True)

# Domain helpers

def create_schedule(schedule: Schedule) -> Dict[str, Any]:
    ensure_containers()
    doc = schedule.model_dump()
    return upsert_item(Settings.COSMOS_CONTAINER_SCHEDULES, doc)

def get_schedule(schedule_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    return read_item(Settings.COSMOS_CONTAINER_SCHEDULES, schedule_id, user_id)

def create_run(run: Run) -> Dict[str, Any]:
    ensure_containers()
    doc = run.model_dump()
    return upsert_item(Settings.COSMOS_CONTAINER_RUNS, doc)

def update_run_status(run_id: str, user_id: str, status: str, duration_ms: Optional[int] = None, error: Optional[str] = None) -> Optional[Dict[str, Any]]:
    existing = read_item(Settings.COSMOS_CONTAINER_RUNS, run_id, user_id)
    if not existing:
        return None
    existing["status"] = status
    if duration_ms is not None:
        existing["durationMs"] = duration_ms
    if error is not None:
        existing["error"] = error
    return upsert_item(Settings.COSMOS_CONTAINER_RUNS, existing)

def save_report(report: Report) -> Dict[str, Any]:
    ensure_containers()
    doc = report.model_dump()
    return upsert_item(Settings.COSMOS_CONTAINER_REPORTS, doc)

# Additional domain helpers

def upsert_schedule_doc(schedule_doc: Dict[str, Any]) -> Dict[str, Any]:
    ensure_containers()
    return upsert_item(Settings.COSMOS_CONTAINER_SCHEDULES, schedule_doc)

def update_schedule_next_run(schedule_id: str, user_id: str, next_run_at_iso: str) -> Optional[Dict[str, Any]]:
    sched = read_item(Settings.COSMOS_CONTAINER_SCHEDULES, schedule_id, user_id)
    if not sched:
        return None
    sched["nextRunAt"] = next_run_at_iso
    return upsert_item(Settings.COSMOS_CONTAINER_SCHEDULES, sched)

def list_schedules_for_user(user_id: str, limit: int = 100) -> Iterable[Dict[str, Any]]:
    q = f"SELECT TOP {int(limit)} * FROM c WHERE c.userId = @uid ORDER BY c.createdAt DESC"
    return query_items(Settings.COSMOS_CONTAINER_SCHEDULES, q, [{"name": "@uid", "value": user_id}])

def list_due_schedules(now_iso: str, limit: int = 50) -> Iterable[Dict[str, Any]]:
    # Cross-partition query for active schedules due to run
    q = f"""
    SELECT TOP {int(limit)} * FROM c
    WHERE c.active = true AND IS_DEFINED(c.nextRunAt) AND c.nextRunAt <= @now
    ORDER BY c.nextRunAt ASC
    """
    return query_items(Settings.COSMOS_CONTAINER_SCHEDULES, q, [{"name": "@now", "value": now_iso}])

def list_reports_for_user(user_id: str, schedule_id: Optional[str] = None, limit: int = 50) -> Iterable[Dict[str, Any]]:
    if schedule_id:
        q = f"SELECT TOP {int(limit)} * FROM c WHERE c.userId = @uid AND c.scheduleId = @sid ORDER BY c.createdAt DESC"
        params = [{"name": "@uid", "value": user_id}, {"name": "@sid", "value": schedule_id}]
    else:
        q = f"SELECT TOP {int(limit)} * FROM c WHERE c.userId = @uid ORDER BY c.createdAt DESC"
        params = [{"name": "@uid", "value": user_id}]
    return query_items(Settings.COSMOS_CONTAINER_REPORTS, q, params)

def get_report(report_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    return read_item(Settings.COSMOS_CONTAINER_REPORTS, report_id, user_id)

def list_runs_for_user(user_id: str, schedule_id: Optional[str] = None, limit: int = 100) -> Iterable[Dict[str, Any]]:
    if schedule_id:
        q = f"SELECT TOP {int(limit)} * FROM c WHERE c.userId = @uid AND c.scheduleId = @sid ORDER BY c.startedAt DESC"
        params = [{"name": "@uid", "value": user_id}, {"name": "@sid", "value": schedule_id}]
    else:
        q = f"SELECT TOP {int(limit)} * FROM c WHERE c.userId = @uid ORDER BY c.startedAt DESC"
        params = [{"name": "@uid", "value": user_id}]
    return query_items(Settings.COSMOS_CONTAINER_RUNS, q, params)
