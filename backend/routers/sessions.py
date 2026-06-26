from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ChatMessage, ChatSession, User
from backend.routers.auth import get_current_user

router = APIRouter()


def _delete_session_messages(db: Session, session_id: str) -> None:
    db.query(ChatMessage).filter(ChatMessage.session_key == session_id).delete()
    db.commit()


def _user_filter(user: Optional[User]) -> dict:
    """Retorna filtro baseado em autenticacao do usuario."""
    if user is not None:
        return {"user_id": user.id}
    return {}


@router.get("/api/sessions")
def list_sessions(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> list[dict]:
    query = db.query(ChatSession)

    if current_user is not None:
        query = query.filter(ChatSession.user_id == current_user.id)
    else:
        query = query.filter(ChatSession.user_id.is_(None))

    sessions = query.order_by(ChatSession.updated_at.desc()).all()
    return [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in sessions
    ]


@router.post("/api/sessions")
def create_session(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> dict:
    import uuid

    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    session = ChatSession(
        id=session_id,
        title="",
        user_id=current_user.id if current_user is not None else None,
        created_at=now,
        updated_at=now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


@router.delete("/api/sessions/{session_id}")
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> dict:
    query = db.query(ChatSession).filter(ChatSession.id == session_id)
    if current_user is not None:
        query = query.filter(ChatSession.user_id == current_user.id)

    session = query.first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    _delete_session_messages(db, session_id)
    db.delete(session)
    db.commit()
    return {"ok": True}


@router.get("/api/sessions/{session_id}/messages")
def list_session_messages(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> list[dict]:
    query = db.query(ChatSession).filter(ChatSession.id == session_id)
    if current_user is not None:
        query = query.filter(ChatSession.user_id == current_user.id)

    session = query.first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_key == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "model": m.model,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.patch("/api/sessions/{session_id}/title")
def update_session_title(
    session_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> dict:
    query = db.query(ChatSession).filter(ChatSession.id == session_id)
    if current_user is not None:
        query = query.filter(ChatSession.user_id == current_user.id)

    session = query.first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    title = payload.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="Titulo nao pode ser vazio")
    session.title = title
    session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(session)
    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }