from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Session as ChatSession
from backend.schemas.session import (
    ChatMessageOut,
    GenerateTitleRequest,
    GenerateTitleResponse,
    SessionCreate,
    SessionOut,
    SessionWithMessages,
)
from backend.services.openrouter import OpenRouterConfigError, generate_title


router = APIRouter()


@router.post("/api/sessions", response_model=SessionOut, status_code=201)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)) -> SessionOut:
    session = ChatSession(title=payload.title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/api/sessions", response_model=list[SessionOut])
def list_sessions(db: Session = Depends(get_db)) -> list[SessionOut]:
    sessions = (
        db.query(ChatSession)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    return sessions


@router.get("/api/sessions/{session_id}", response_model=SessionWithMessages)
def get_session(session_id: int, db: Session = Depends(get_db)) -> SessionWithMessages:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/api/sessions/generate-title", response_model=GenerateTitleResponse)
async def generate_session_title(
    payload: GenerateTitleRequest, db: Session = Depends(get_db)
) -> GenerateTitleResponse:
    try:
        title = await generate_title(user_message=payload.message)
    except OpenRouterConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if payload.session_id is not None:
        session = db.query(ChatSession).filter(ChatSession.id == payload.session_id).first()
        if session:
            session.title = title
            db.commit()

    return GenerateTitleResponse(title=title)


@router.get("/api/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
def get_session_messages(session_id: int, db: Session = Depends(get_db)) -> list[ChatMessageOut]:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.messages


@router.delete("/api/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)) -> Response:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return Response(status_code=204)