from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.schemas.chat import ChatMessageIn, ChatRequest, ChatResponse
from backend.schemas.session import SessionListOut, SessionMessagesOut, SessionSummaryOut


class TestChatMessageIn:
    def test_valid_user_message(self):
        msg = ChatMessageIn(role="user", content="Ola!")
        assert msg.role == "user"
        assert msg.content == "Ola!"

    def test_valid_assistant_message(self):
        msg = ChatMessageIn(role="assistant", content="Resposta.")
        assert msg.role == "assistant"
        assert msg.content == "Resposta."

    def test_invalid_role(self):
        with pytest.raises(ValidationError):
            ChatMessageIn(role="system", content="Nao permitido")

    def test_empty_content(self):
        with pytest.raises(ValidationError):
            ChatMessageIn(role="user", content="")

    def test_content_too_long(self):
        with pytest.raises(ValidationError):
            ChatMessageIn(role="user", content="x" * 8001)


class TestChatRequest:
    def test_valid_request_minimal(self):
        req = ChatRequest(message="Hello")
        assert req.message == "Hello"
        assert req.model is None
        assert req.history == []
        assert req.session_key is None

    def test_valid_request_with_session_key(self):
        req = ChatRequest(message="Hi", session_key="abc-123")
        assert req.session_key == "abc-123"

    def test_valid_request_with_model(self):
        req = ChatRequest(message="Hi", model="openai/gpt-4o")
        assert req.model == "openai/gpt-4o"

    def test_valid_request_with_history(self):
        history = [
            ChatMessageIn(role="user", content="pergunta"),
            ChatMessageIn(role="assistant", content="resposta"),
        ]
        req = ChatRequest(message="continuacao", history=history)
        assert len(req.history) == 2
        assert req.history[0].role == "user"

    def test_empty_message(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="")

    def test_message_too_long(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="x" * 8001)

    def test_history_defaults_to_empty(self):
        req = ChatRequest(message="Hello")
        assert req.history == []


class TestChatResponse:
    def test_valid_response(self):
        resp = ChatResponse(reply="Resposta do modelo.", model="google/gemma-4-31b-it", session_key="abc-123")
        assert resp.reply == "Resposta do modelo."
        assert resp.model == "google/gemma-4-31b-it"
        assert resp.session_key == "abc-123"


class TestSessionSchemas:
    def test_session_summary_out(self):
        from datetime import datetime
        dt = datetime(2025, 1, 1, 12, 0, 0)
        summary = SessionSummaryOut(
            id=1, session_key="sk-1", title="Meu Chat",
            created_at=dt, updated_at=dt,
        )
        assert summary.title == "Meu Chat"
        assert summary.session_key == "sk-1"

    def test_session_summary_out_no_title(self):
        from datetime import datetime
        dt = datetime(2025, 1, 1, 12, 0, 0)
        summary = SessionSummaryOut(
            id=2, session_key="sk-2", title=None,
            created_at=dt, updated_at=dt,
        )
        assert summary.title is None

    def test_session_list_out(self):
        from datetime import datetime
        dt = datetime(2025, 1, 1, 12, 0, 0)
        summary = SessionSummaryOut(id=1, session_key="sk-1", title="Chat", created_at=dt, updated_at=dt)
        result = SessionListOut(sessions=[summary], total=1)
        assert result.total == 1
        assert len(result.sessions) == 1

    def test_session_messages_out(self):
        result = SessionMessagesOut(
            session_key="sk-1",
            title="Meu Chat",
            messages=[{"role": "user", "content": "Ola"}],
            total=1,
            page=1,
            page_size=50,
        )
        assert result.title == "Meu Chat"
        assert len(result.messages) == 1
