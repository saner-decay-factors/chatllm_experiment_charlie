from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, ChatSession
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.openrouter import OpenRouterConfigError, generate_reply, stream_reply


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def _auto_title(user_message: str) -> str:
    """Gera um titulo automatico truncando a primeira mensagem do usuario."""
    cleaned = user_message.strip()
    if not cleaned:
        return "Nova conversa"
    # Trunca para no maximo 40 caracteres, quebrando em palavra completa
    if len(cleaned) <= 40:
        return cleaned
    # Tenta quebrar no ultimo espaco antes de 40
    truncated = cleaned[:40]
    last_space = truncated.rfind(" ")
    if last_space > 20:
        truncated = truncated[:last_space]
    return truncated + "..."


@router.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    session_id = payload.session_id or "default"
    try:
        reply, model_name = await generate_reply(
            user_message=payload.message,
            history=[item.model_dump() for item in payload.history],
            model=payload.model,
        )
    except OpenRouterConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    resolved_model = payload.model or model_name or OPENROUTER_MODEL_DEFAULT

    _persist_messages(db, session_id, payload.message, reply, resolved_model)
    _update_session_timestamp(db, session_id)
    _auto_title_if_needed(db, session_id, payload.message)

    return ChatResponse(reply=reply, model=resolved_model)


@router.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT
    session_id = payload.session_id or "default"

    async def event_generator():
        full_reply = ""
        try:
            async for delta in stream_reply(
                user_message=payload.message,
                history=[item.model_dump() for item in payload.history],
                model=payload.model,
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
            _persist_messages(db, session_id, payload.message, full_reply, resolved_model)
            _update_session_timestamp(db, session_id)
            # Auto-titulo se a sessao ainda nao tem titulo
            _auto_title_if_needed(db, session_id, payload.message)

        yield f"data: {json.dumps({'done': True}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


def _persist_messages(
    db: Session, session_id: str, user_msg: str, assistant_reply: str, model: str
) -> None:
    db.add(ChatMessage(session_key=session_id, role="user", content=user_msg, model=model))
    db.add(
        ChatMessage(session_key=session_id, role="assistant", content=assistant_reply, model=model)
    )
    db.commit()


def _update_session_timestamp(db: Session, session_id: str) -> None:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session:
        session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()


def _auto_title_if_needed(db: Session, session_id: str, user_message: str) -> None:
    if session_id == "default":
        return
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session or session.title:
        return
    title = _auto_title(user_message)
    session.title = title
    session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
