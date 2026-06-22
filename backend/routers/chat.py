from __future__ import annotations

import json
import logging
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, ChatSession
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.schemas.session import SessionListOut, SessionMessagesOut, SessionSummaryOut
from backend.services.openrouter import (
    OpenRouterConfigError,
    generate_reply,
    generate_title,
    stream_reply,
)


router = APIRouter()


def _get_or_create_session(db: Session, session_key: str | None) -> ChatSession:
    """Retorna sessao existente ou cria uma nova."""
    if session_key:
        session = db.query(ChatSession).filter(ChatSession.session_key == session_key).first()
        if session:
            return session
    session = ChatSession()
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/sessions", response_model=SessionListOut)
def list_sessions(db: Session = Depends(get_db)):
    """Lista todas as sessoes de chat ordenadas pela mais recente."""
    sessions = (
        db.query(ChatSession)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    total = len(sessions)
    return SessionListOut(
        sessions=[
            SessionSummaryOut(
                id=s.id,
                session_key=s.session_key,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in sessions
        ],
        total=total,
    )


@router.get("/api/sessions/{session_key}/messages", response_model=SessionMessagesOut)
def get_session_messages(
    session_key: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retorna mensagens de uma sessao com paginacao."""
    session = db.query(ChatSession).filter(ChatSession.session_key == session_key).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada.")

    total = db.query(func.count(ChatMessage.id)).filter(
        ChatMessage.session_key == session_key
    ).scalar() or 0

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_key == session_key)
        .order_by(ChatMessage.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return SessionMessagesOut(
        session_key=session_key,
        title=session.title,
        messages=[
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "model": m.model,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/api/sessions")
def create_session(db: Session = Depends(get_db)):
    """Cria uma nova sessao de chat e retorna o session_key."""
    session = ChatSession()
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_key": session.session_key}


@router.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    session = _get_or_create_session(db, payload.session_key)

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

    # Persiste mensagens na sessao
    db.add(ChatMessage(session_key=session.session_key, role="user", content=payload.message, model=resolved_model))
    db.add(ChatMessage(session_key=session.session_key, role="assistant", content=reply, model=resolved_model))
    db.commit()

    # Gera titulo automatico se for a primeira mensagem da sessao
    if not session.title:
        try:
            title = await generate_title(user_message=payload.message, assistant_reply=reply)
        except Exception as exc:
            logger.warning("generate_title lançou exceção: %s", exc)
            title = None

        if title:
            session.title = title
            logger.info("Título gerado via API: '%s'", title)
        else:
            # Fallback local: primeiras palavras da mensagem do usuário
            words = payload.message.strip().split()
            fallback = " ".join(words[:5]).capitalize()
            if len(fallback) > 60:
                fallback = fallback[:57] + "..."
            session.title = fallback
            logger.info("Título gerado via fallback local: '%s'", fallback)

        db.commit()

    return ChatResponse(reply=reply, model=resolved_model, session_key=session.session_key)


@router.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    session = _get_or_create_session(db, payload.session_key)
    session_key = session.session_key
    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT

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
            db.commit()

            # Gera titulo automatico se for a primeira mensagem
            if not session.title:
                try:
                    title = await generate_title(
                        user_message=payload.message,
                        assistant_reply=full_reply,
                    )
                except Exception as exc:
                    logger.warning("generate_title lançou exceção (stream): %s", exc)
                    title = None

                if title:
                    session.title = title
                    logger.info("Título gerado via API (stream): '%s'", title)
                else:
                    # Fallback local: primeiras palavras da mensagem do usuário
                    words = payload.message.strip().split()
                    fallback = " ".join(words[:5]).capitalize()
                    if len(fallback) > 60:
                        fallback = fallback[:57] + "..."
                    session.title = fallback
                    logger.info("Título via fallback local (stream): '%s'", fallback)

                db.commit()
                db.refresh(session)
                logger.info("Título salvo no banco: '%s'", session.title)

        yield f"data: {json.dumps({'done': True, 'session_key': session_key}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
