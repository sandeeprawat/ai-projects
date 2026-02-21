from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EmailSettings(BaseModel):
    to: List[str] = Field(default_factory=list)
    attachPdf: bool = False


class Recurrence(BaseModel):
    # Supports: hourly/daily/weekly with interval
    cadence: str = Field(default="daily", description="hourly | daily | weekly")
    interval: int = Field(default=1, ge=1)
    # For daily/weekly times
    hour: Optional[int] = Field(default=9, ge=0, le=23)
    minute: Optional[int] = Field(default=0, ge=0, le=59)
    # For weekly (0=Mon .. 6=Sun)
    weekday: Optional[int] = Field(default=0, ge=0, le=6)


def compute_next_run_utc(rec: Recurrence, now: Optional[datetime] = None) -> str:
    now = now or datetime.now(timezone.utc)
    cadence = (rec.cadence or "daily").lower()
    interval = max(1, int(rec.interval or 1))
    hour = 0 if rec.hour is None else int(rec.hour)
    minute = 0 if rec.minute is None else int(rec.minute)

    if cadence == "hourly":
        return (now + timedelta(hours=interval)).replace(microsecond=0).isoformat()

    if cadence == "daily":
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target = target + timedelta(days=interval)
        return target.isoformat()

    if cadence == "weekly":
        wd = 0 if rec.weekday is None else int(rec.weekday)
        # find next occurrence of weekday at hour:minute
        days_ahead = (wd - now.weekday()) % 7
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
        if candidate <= now:
            candidate = candidate + timedelta(weeks=interval)
        return candidate.isoformat()

    # Fallback: run in 1 hour
    return (now + timedelta(hours=1)).replace(microsecond=0).isoformat()


class Schedule(BaseModel):
    id: Optional[str] = None
    userId: str
    prompt: Optional[str] = None
    symbols: List[str] = Field(default_factory=list)
    recurrence: Recurrence = Field(default_factory=Recurrence)
    email: EmailSettings = Field(default_factory=EmailSettings)
    deepResearch: bool = False
    active: bool = True
    nextRunAt: Optional[str] = None


class Run(BaseModel):
    id: Optional[str] = None
    scheduleId: str
    userId: str
    createdAt: Optional[str] = None
    status: str = "scheduled"


class Report(BaseModel):
    id: Optional[str] = None
    runId: str
    scheduleId: str
    userId: str
    title: str
    prompt: Optional[str] = None
    symbols: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    blobPaths: Dict[str, str] = Field(default_factory=dict)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "complete"
    createdAt: Optional[str] = None


class TrackedStock(BaseModel):
    id: Optional[str] = None
    userId: str
    symbol: str
    reportTitle: Optional[str] = None
    reportId: Optional[str] = None
    recommendationDate: str  # ISO date string (YYYY-MM-DD)
    recommendationPrice: float
    createdAt: Optional[str] = None
