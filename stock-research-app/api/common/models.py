from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
import uuid


RecurrenceType = Literal["daily", "weekly", "hours"]


class Recurrence(BaseModel):
    type: RecurrenceType
    # For daily: hour in 0-23 (UTC)
    hour: Optional[int] = None
    # For weekly: day of week 0-6 (Mon=0), hour in 0-23 (UTC)
    dow: Optional[int] = None
    # For hours: run every N hours
    interval: Optional[int] = None


class EmailSettings(BaseModel):
    to: List[str] = Field(default_factory=list)
    attachPdf: bool = False


class Schedule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    symbols: List[str]
    recurrence: Recurrence
    nextRunAt: Optional[str] = None  # ISO 8601 UTC
    email: Optional[EmailSettings] = Field(default_factory=EmailSettings)
    createdAt: str = Field(default_factory=lambda: now_iso())
    active: bool = True


class Run(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scheduleId: str
    userId: str
    startedAt: str = Field(default_factory=lambda: now_iso())
    status: Literal["queued", "running", "succeeded", "failed"] = "queued"
    durationMs: Optional[int] = None
    error: Optional[str] = None


class Report(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    runId: str
    scheduleId: str
    userId: str
    title: str
    symbols: List[str]
    period: Optional[str] = None
    summary: Optional[str] = None
    blobPaths: Dict[str, str] = Field(default_factory=dict)  # keys: md, html, pdf
    createdAt: str = Field(default_factory=lambda: now_iso())
    citations: List[Dict[str, Any]] = Field(default_factory=list)


def now_iso(dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.now(timezone.utc)
    return dt.replace(microsecond=0).isoformat()


def compute_next_run_utc(recurrence: Recurrence, from_dt: Optional[datetime] = None) -> str:
    """
    Compute the next run time in UTC for a given recurrence spec.
    """
    base = (from_dt or datetime.now(timezone.utc)).replace(second=0, microsecond=0)

    if recurrence.type == "hours":
        interval = max(1, (recurrence.interval or 24))
        return now_iso(base + timedelta(hours=interval))

    if recurrence.type == "daily":
        hour = 0 if recurrence.hour is None else max(0, min(23, recurrence.hour))
        candidate = base.replace(hour=hour, minute=0)
        if candidate <= base:
            candidate += timedelta(days=1)
        return now_iso(candidate)

    if recurrence.type == "weekly":
        # 0-6 (Mon=0)
        dow = 0 if recurrence.dow is None else max(0, min(6, recurrence.dow))
        hour = 0 if recurrence.hour is None else max(0, min(23, recurrence.hour))
        # Move to the target weekday
        days_ahead = (dow - base.weekday()) % 7
        candidate = base + timedelta(days=days_ahead)
        candidate = candidate.replace(hour=hour, minute=0)
        if candidate <= base:
            candidate += timedelta(days=7)
        return now_iso(candidate)

    # Fallback: one day later
    return now_iso(base + timedelta(days=1))
