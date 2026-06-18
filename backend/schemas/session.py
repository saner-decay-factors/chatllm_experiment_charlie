from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SessionCreate(BaseModel):
    session_key: str


class SessionRename(BaseModel):
    title: str


class SessionOut(BaseModel):
    id: int
    session_key: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}