from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SessionSummaryOut(BaseModel):
    id: int
    session_key: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime


class SessionListOut(BaseModel):
    sessions: list[SessionSummaryOut]
    total: int


class SessionMessagesOut(BaseModel):
    session_key: str
    title: str | None = None
    messages: list[dict]
    total: int
    page: int
    page_size: int