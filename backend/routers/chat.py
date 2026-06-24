from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, ChatSession, User
from backend.routers.auth import get_current_user
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.openrouter import OpenRouterConfigError, generate_reply, stream_reply


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ChatResponse:
    session_id = payload.session_id
    if session_id:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    else:
        session = ChatSession(title=None)
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id

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

    db.add(ChatMessage(session_id=session_id, role="user", content=payload.message, model=resolved_model))
    db.add(ChatMessage(session_id=session_id, role="assistant", content=reply, model=resolved_model))
    db.commit()

    _ensure_title_first_message(session_id=session_id, db=db)

    return ChatResponse(reply=reply, model=resolved_model, session_id=session_id)


def _ensure_title_first_message(*, session_id: int, db: Session) -> None:
    """Gera titulo automatico baseado na primeira mensagem do usuario se a sessao nao tiver titulo."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session or session.title:
        return
    first_user = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id, ChatMessage.role == "user")
        .order_by(ChatMessage.created_at.asc())
        .first()
    )
    if first_user and first_user.content.strip():
        max_len = 80
        title = first_user.content.strip()[:max_len]
        if len(first_user.content.strip()) > max_len:
            title += "..."
        session.title = title
        db.commit()


@router.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> StreamingResponse:
    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT

    # Sessao: usa existente ou cria nova
    session_id = getattr(payload, "session_id", None)
    if session_id:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    else:
        session = ChatSession(title=None)
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id

    async def event_generator():
        nonlocal session_id
        full_reply = ""
        try:
            async for delta in stream_reply(
                user_message=payload.message,
                history=[item.model_dump() for item in payload.history],
                model=payload.model,
            ):
                full_reply += delta
                yield f"data: {json.dumps({'delta': delta, 'session_id': session_id}, ensure_ascii=True)}\n\n"
        except OpenRouterConfigError as exc:
            yield f"data: {json.dumps({'error': str(exc), 'session_id': session_id}, ensure_ascii=True)}\n\n"
            return
        except RuntimeError as exc:
            yield f"data: {json.dumps({'error': str(exc), 'session_id': session_id}, ensure_ascii=True)}\n\n"
            return

        if full_reply.strip():
            db.add(
                ChatMessage(
                    session_id=session_id,
                    role="user",
                    content=payload.message,
                    model=resolved_model,
                )
            )
            db.add(
                ChatMessage(
                    session_id=session_id,
                    role="assistant",
                    content=full_reply,
                    model=resolved_model,
                )
            )
            db.commit()

            # Titulo automatico na primeira mensagem
            _ensure_title_first_message(session_id=session_id, db=db)

        yield f"data: {json.dumps({'done': True, 'session_id': session_id}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
