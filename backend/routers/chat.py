from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, ChatSession
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.openrouter import OpenRouterConfigError, generate_reply, generate_title, stream_reply


async def _auto_title(db: Session, session_key: str, user_msg: str, assistant_reply: str) -> None:
    """Generate a contextual title using the LLM based on the first exchange."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.session_key == session_key)
        .first()
    )
    if session and not session.title_generated:
        try:
            title = await generate_title(user_message=user_msg, assistant_reply=assistant_reply)
            session.title = title
        except Exception:
            session.title = user_msg.strip()[:50] + ("..." if len(user_msg.strip()) > 50 else "")
        session.title_generated = True


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
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

    session_key = payload.session_key
    db.add(
        ChatMessage(
            session_key=session_key,
            role="user",
            content=payload.message,
            model=resolved_model,
        )
    )
    db.add(
        ChatMessage(
            session_key=session_key,
            role="assistant",
            content=reply,
            model=resolved_model,
        )
    )
    _touch_session(db, session_key)
    await _auto_title(db, session_key, payload.message, reply)
    db.commit()

    return ChatResponse(reply=reply, model=resolved_model)


@router.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT
    session_key = payload.session_key

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
            db.add(
                ChatMessage(
                    session_key=session_key,
                    role="user",
                    content=payload.message,
                    model=resolved_model,
                )
            )
            db.add(
                ChatMessage(
                    session_key=session_key,
                    role="assistant",
                    content=full_reply,
                    model=resolved_model,
                )
            )
            _touch_session(db, session_key)
            await _auto_title(db, session_key, payload.message, full_reply)
            db.commit()

        yield f"data: {json.dumps({'done': True}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


def _touch_session(db: Session, session_key: str) -> None:
    """Update the session's updated_at timestamp."""
    from datetime import datetime, timezone

    session = (
        db.query(ChatSession)
        .filter(ChatSession.session_key == session_key)
        .first()
    )
    if session:
        session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
