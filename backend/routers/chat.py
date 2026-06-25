from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import MODEL_OPTIONS, OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, ChatSession
from backend.schemas.chat import ChatRequest, ChatResponse, MessageOut, SessionOut
from backend.services.openrouter import OpenRouterConfigError, generate_reply, stream_reply


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def _resolve_session(session_key: str | None, db: Session) -> tuple[str, int | None]:
    """Get or create a session, returns (session_key, session_id)."""
    if session_key:
        session = db.query(ChatSession).filter(ChatSession.session_key == session_key).first()
        if not session:
            session = ChatSession(session_key=session_key, title="Nova conversa")
            db.add(session)
            db.commit()
            db.refresh(session)
        return session.session_key, session.id

    # Generate a new session key
    new_key = str(uuid.uuid4())
    session = ChatSession(session_key=new_key, title="Nova conversa")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session.session_key, session.id


def _resolve_model(model_name: str | None) -> str:
    """Resolve model from user-friendly name to OpenRouter model string."""
    if not model_name:
        return OPENROUTER_MODEL_DEFAULT
    if model_name in MODEL_OPTIONS:
        return MODEL_OPTIONS[model_name]
    return model_name


@router.get("/api/sessions")
def list_sessions(db: Session = Depends(get_db)) -> list[SessionOut]:
    sessions = (
        db.query(ChatSession)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    result = []
    for s in sessions:
        msg_count = db.query(ChatMessage).filter(ChatMessage.session_key == s.session_key).count()
        result.append(
            SessionOut(
                session_key=s.session_key,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=msg_count,
            )
        )
    return result


@router.get("/api/sessions/{session_key}/messages")
def get_session_messages(session_key: str, db: Session = Depends(get_db)) -> list[MessageOut]:
    session = db.query(ChatSession).filter(ChatSession.session_key == session_key).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_key == session_key)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        MessageOut(
            id=m.id,
            role=m.role,
            content=m.content,
            model=m.model,
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.delete("/api/sessions/{session_key}")
def delete_session(session_key: str, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.session_key == session_key).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    db.delete(session)
    db.commit()
    return {"status": "ok"}


@router.patch("/api/sessions/{session_key}")
def update_session(session_key: str, payload: dict, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.session_key == session_key).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    if "title" in payload:
        session.title = payload["title"]
    db.commit()
    return {"status": "ok"}


@router.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    session_key, session_id = _resolve_session(payload.session_key, db)
    resolved_model = _resolve_model(payload.model)

    try:
        reply, model_name = await generate_reply(
            user_message=payload.message,
            history=[item.model_dump() for item in payload.history],
            model=resolved_model,
        )
    except OpenRouterConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    final_model = model_name or resolved_model

    db.add(ChatMessage(session_key=session_key, session_id=session_id, role="user", content=payload.message, model=final_model))
    db.add(ChatMessage(session_key=session_key, session_id=session_id, role="assistant", content=reply, model=final_model))

    # Auto-title: use first user message as title
    session = db.query(ChatSession).filter(ChatSession.session_key == session_key).first()
    if session and session.title == "Nova conversa":
        session.title = payload.message[:80] + ("..." if len(payload.message) > 80 else "")
    db.commit()

    return ChatResponse(reply=reply, model=final_model)


@router.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    session_key, session_id = _resolve_session(payload.session_key, db)
    resolved_model = _resolve_model(payload.model)

    async def event_generator():
        full_reply = ""
        try:
            async for delta in stream_reply(
                user_message=payload.message,
                history=[item.model_dump() for item in payload.history],
                model=resolved_model,
            ):
                full_reply += delta
                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=True)}\n\n"
        except OpenRouterConfigError as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=True)}\n\n"
            return
        except RuntimeError as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=True)}\n\n"
            return

        if full_reply.strip():
            db.add(
                ChatMessage(
                    session_key=session_key,
                    session_id=session_id,
                    role="user",
                    content=payload.message,
                    model=resolved_model,
                )
            )
            db.add(
                ChatMessage(
                    session_key=session_key,
                    session_id=session_id,
                    role="assistant",
                    content=full_reply,
                    model=resolved_model,
                )
            )

            # Auto-title
            session = db.query(ChatSession).filter(ChatSession.session_key == session_key).first()
            if session and session.title == "Nova conversa":
                session.title = payload.message[:80] + ("..." if len(payload.message) > 80 else "")
            db.commit()

        yield f"data: {json.dumps({'done': True, 'session_key': session_key}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/api/models")
def list_models() -> dict:
    return {"models": list(MODEL_OPTIONS.keys()), "default": OPENROUTER_MODEL_DEFAULT}
