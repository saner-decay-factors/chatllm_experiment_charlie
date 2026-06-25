from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.schemas.session import SessionCreate, SessionOut, SessionWithMessages, ChatMessageOut


class TestSessionCreate:
    def test_default_title(self):
        s = SessionCreate()
        assert s.title == "New Chat"

    def test_custom_title(self):
        s = SessionCreate(title="My Session")
        assert s.title == "My Session"


class TestSessionOut:
    def test_valid(self):
        s = SessionOut(id=1, title="Test", created_at="2025-01-01T00:00:00")
        assert s.id == 1
        assert s.title == "Test"

    def test_missing_field(self):
        with pytest.raises(ValidationError):
            SessionOut(id=1, title="Test")


class TestChatMessageOut:
    def test_valid(self):
        m = ChatMessageOut(
            id=1,
            session_id=1,
            role="user",
            content="Hello",
            model="gpt-4o",
            created_at="2025-01-01T00:00:00",
        )
        assert m.role == "user"


class TestSessionWithMessages:
    def test_valid(self):
        s = SessionWithMessages(
            id=1,
            title="Test",
            created_at="2025-01-01T00:00:00",
            messages=[
                ChatMessageOut(
                    id=1,
                    session_id=1,
                    role="user",
                    content="Hi",
                    model="gpt-4o",
                    created_at="2025-01-01T00:00:00",
                )
            ],
        )
        assert len(s.messages) == 1
        assert s.messages[0].content == "Hi"