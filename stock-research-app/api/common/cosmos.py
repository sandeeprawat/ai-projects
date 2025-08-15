from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4
from datetime import datetime, timezone

from .models import Schedule, Run, Report

# Lightweight local JSON store used for local dev in place of Cosmos DB.
# File path: stock-research-app/.data/db.json
_DATA_DIR = Path(__file__).resolve().parents[2] / ".data"
_DATA_FILE = _DATA_DIR / "db.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ensure_store() -> Dict[str, Any]:
    if not _DATA_DIR.exists():
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _DATA_FILE.exists():
        initial = {"schedules": [], "runs": [], "reports": []}
        _DATA_FILE.write_text(json.dumps(initial, indent=2), encoding="utf-8")
        return initial
    try:
        return json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        initial = {"schedules": [], "runs": [], "reports": []}
        _DATA_FILE.write_text(json.dumps(initial, indent=2), encoding="utf-8")
        return initial


def _save_store(db: Dict[str, Any]) -> None:
    _DATA_FILE.write_text(json.dumps(db, indent=2), encoding="utf-8")


# Schedules

def create_schedule(sched: Schedule) -> Dict[str, Any]:
    db = _ensure_store()
    data = sched.dict()
    data["id"] = data.get("id") or str(uuid4())
    data["createdAt"] = _now_iso()
    # nextRunAt should be precomputed by caller; keep if present
    db["schedules"].append(data)
    _save_store(db)
    return data


def get_schedule(schedule_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    db = _ensure_store()
    for s in db.get("schedules", []):
        if s.get("id") == schedule_id and s.get("userId") == user_id:
            return s
    return None


def list_due_schedules(now_iso: str, limit: int = 50) -> List[Dict[str, Any]]:
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
    # Sort by nextRunAt asc
    due.sort(key=lambda x: (x.get("nextRunAt") or ""))
    return due[: max(0, int(limit or 0)) or 50]


def update_schedule_next_run(schedule_id: str, user_id: str, next_iso: str) -> bool:
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


# Runs

def create_run(run: Run) -> Dict[str, Any]:
    db = _ensure_store()
    data = run.dict()
    data["id"] = data.get("id") or str(uuid4())
    data["createdAt"] = _now_iso()
    db["runs"].append(data)
    _save_store(db)
    return data


# Reports

def save_report(report: Report) -> Dict[str, Any]:
    db = _ensure_store()
    data = report.dict()
    data["id"] = data.get("id") or str(uuid4())
    data["createdAt"] = data.get("createdAt") or _now_iso()
    db["reports"].append(data)
    _save_store(db)
    return data


def get_report(report_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    db = _ensure_store()
    for r in db.get("reports", []):
        if r.get("id") == report_id and r.get("userId") == user_id:
            return r
    return None


def list_reports_for_user(user_id: str, schedule_id: Optional[str] = None, limit: int = 50) -> Iterable[Dict[str, Any]]:
    db = _ensure_store()
    items: List[Dict[str, Any]] = []
    for r in db.get("reports", []):
        if r.get("userId") != user_id:
            continue
        if schedule_id and r.get("scheduleId") != schedule_id:
            continue
        items.append(r)
    # Sort newest first by createdAt
    items.sort(key=lambda x: (x.get("createdAt") or ""), reverse=True)
    return items[: max(0, int(limit or 0)) or 50]

def list_schedules_for_user(user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    db = _ensure_store()
    items: List[Dict[str, Any]] = []
    for s in db.get("schedules", []):
        if s.get("userId") != user_id:
            continue
        items.append(s)
    # Sort newest first by createdAt
    items.sort(key=lambda x: (x.get("createdAt") or ""), reverse=True)
    return items[: max(0, int(limit or 0)) or 100]

# Deletions and utilities

def delete_report(report_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Deletes a report document for a user. Returns the removed report doc, or None if not found.
    """
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

def delete_runs_for_schedule(schedule_id: str, user_id: str) -> int:
    """
    Deletes all run docs for a schedule/user. Returns number of deleted runs.
    """
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

def delete_schedule(schedule_id: str, user_id: str) -> bool:
    """
    Deletes a schedule for a user. Returns True if deleted, False if not found.
    Does not cascade delete reports/blobs; callers should do that explicitly.
    """
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

def list_all_reports() -> List[Dict[str, Any]]:
    """
    Returns all reports across users (for cleanup/maintenance tasks).
    """
    db = _ensure_store()
    return list(db.get("reports", []))
