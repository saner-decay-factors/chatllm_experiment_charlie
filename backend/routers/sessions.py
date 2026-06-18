from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ChatMessage, ChatSession
from backend.schemas.session import SessionOut

router = APIRouter()


@router.get("/api/sessions", response_model=list[SessionOut])
def list_sessions(db: Session = Depends(get_db)):
    sessions = (
        db.query(ChatSession)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return sessions


@router.post("/api/sessions", response_model=SessionOut, status_code=201)
def create_session(db: Session = Depends(get_db)):
    session_key = str(uuid.uuid4())
    session = ChatSession(session_key=session_key, title="Nova conversa")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.delete("/api/sessions/{session_key}", status_code=204)
def delete_session(session_key: str, db: Session = Depends(get_db)):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.session_key == session_key)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    db.query(ChatMessage).filter(
        ChatMessage.session_key == session_key
    ).delete()
    db.delete(session)
    db.commit()


@router.get("/api/sessions/{session_key}/messages")
def get_session_messages(session_key: str, db: Session = Depends(get_db)):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.session_key == session_key)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_key == session_key)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
        }
        for msg in messages
    ]


class GenerateTitleRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


@router.post("/api/sessions/{session_key}/generate-title", response_model=SessionOut)
def generate_session_title(
    session_key: str, payload: GenerateTitleRequest, db: Session = Depends(get_db)
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.session_key == session_key)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    # Simple title: use the first ~50 chars of the first message
    title = payload.message.strip()[:50]
    if len(payload.message.strip()) > 50:
        title += "..."

    session.title = title
    session.title_generated = True
    db.commit()
    db.refresh(session)
    return session