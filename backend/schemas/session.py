from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    title: str = "New Chat"


class SessionOut(BaseModel):
    id: int
    title: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    model: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionWithMessages(SessionOut):
    messages: list[ChatMessageOut]


class GenerateTitleRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: int | None = None


class GenerateTitleResponse(BaseModel):
    title: str