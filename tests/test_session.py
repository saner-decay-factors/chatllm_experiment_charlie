from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import ChatMessage, Session as ChatSession


class TestCreateSession:
    def test_create_session_default_title(self, client: TestClient):
        response = client.post("/api/sessions", json={})
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Chat"
        assert "id" in data
        assert "created_at" in data

    def test_create_session_custom_title(self, client: TestClient):
        response = client.post("/api/sessions", json={"title": "My Chat"})
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "My Chat"


class TestListSessions:
    def test_list_sessions_empty(self, client: TestClient):
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_sessions_returns_created(self, client: TestClient):
        client.post("/api/sessions", json={"title": "Session A"})
        client.post("/api/sessions", json={"title": "Session B"})
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2


class TestGetSession:
    def test_get_session_not_found(self, client: TestClient):
        response = client.get("/api/sessions/9999")
        assert response.status_code == 404

    def test_get_session_with_messages(self, client: TestClient, db_session: Session):
        # Create session via API
        create_resp = client.post("/api/sessions", json={"title": "Detail Test"})
        session_id = create_resp.json()["id"]

        # Insert messages directly into DB (chat endpoint needs API key)
        db_session.add(ChatMessage(session_id=session_id, role="user", content="Hello", model="test"))
        db_session.add(ChatMessage(session_id=session_id, role="assistant", content="Hi!", model="test"))
        db_session.commit()

        # Get session detail
        response = client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert "messages" in data
        assert len(data["messages"]) >= 2


class TestDeleteSession:
    def test_delete_session_not_found(self, client: TestClient):
        response = client.delete("/api/sessions/9999")
        assert response.status_code == 404

    def test_delete_session_success(self, client: TestClient):
        create_resp = client.post("/api/sessions", json={"title": "To Delete"})
        session_id = create_resp.json()["id"]

        response = client.delete(f"/api/sessions/{session_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_resp = client.get(f"/api/sessions/{session_id}")
        assert get_resp.status_code == 404


class TestGetSessionMessages:
    def test_messages_not_found(self, client: TestClient):
        response = client.get("/api/sessions/9999/messages")
        assert response.status_code == 404

    def test_messages_empty_session(self, client: TestClient):
        create_resp = client.post("/api/sessions", json={"title": "Empty"})
        session_id = create_resp.json()["id"]
        response = client.get(f"/api/sessions/{session_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_messages_returns_all_messages(self, client: TestClient, db_session: Session):
        create_resp = client.post("/api/sessions", json={"title": "Msg Test"})
        session_id = create_resp.json()["id"]

        db_session.add(ChatMessage(session_id=session_id, role="user", content="Hello", model="test"))
        db_session.add(ChatMessage(session_id=session_id, role="assistant", content="Hi there!", model="test"))
        db_session.add(ChatMessage(session_id=session_id, role="user", content="How are you?", model="test"))
        db_session.commit()

        response = client.get(f"/api/sessions/{session_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["role"] == "user"
        assert data[0]["content"] == "Hello"
        assert data[1]["role"] == "assistant"
        assert data[1]["content"] == "Hi there!"
        assert data[2]["role"] == "user"
        assert data[2]["content"] == "How are you?"

    def test_messages_includes_correct_fields(self, client: TestClient, db_session: Session):
        create_resp = client.post("/api/sessions", json={"title": "Fields Test"})
        session_id = create_resp.json()["id"]

        db_session.add(ChatMessage(session_id=session_id, role="user", content="Test", model="test-model"))
        db_session.commit()

        response = client.get(f"/api/sessions/{session_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        msg = data[0]
        assert "id" in msg
        assert "session_id" in msg
        assert "role" in msg
        assert "content" in msg
        assert "model" in msg
        assert "created_at" in msg
        assert msg["session_id"] == session_id
        assert msg["model"] == "test-model"


class TestGenerateSessionTitle:
    def test_generate_title_no_api_key(self, client: TestClient):
        """Deve retornar 503 quando OPENROUTER_API_KEY nao esta definida."""
        from backend.services.openrouter import OpenRouterConfigError

        with patch("backend.routers.session.generate_title", side_effect=OpenRouterConfigError(
            "OPENROUTER_API_KEY nao definido. Configure em .env ou environment variables."
        )):
            response = client.post(
                "/api/sessions/generate-title",
                json={"message": "Hello world"},
            )
            assert response.status_code == 503
            data = response.json()
            assert "OPENROUTER_API_KEY" in data["detail"]

    def test_generate_title_returns_title(self, client: TestClient):
        """Deve retornar o titulo gerado pelo LLM mockado."""
        with patch("backend.routers.session.generate_title", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "Python Sorting Tips"

            response = client.post(
                "/api/sessions/generate-title",
                json={"message": "How do I sort a list in Python?"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Python Sorting Tips"
            mock_gen.assert_awaited_once_with(user_message="How do I sort a list in Python?")

    def test_generate_title_updates_session(self, client: TestClient, db_session: Session):
        """Deve atualizar o titulo da sessao quando session_id e fornecido."""
        create_resp = client.post("/api/sessions", json={"title": "Old Title"})
        session_id = create_resp.json()["id"]

        with patch("backend.routers.session.generate_title", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "New Generated Title"

            response = client.post(
                "/api/sessions/generate-title",
                json={"message": "Hello", "session_id": session_id},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "New Generated Title"

            # Verify session was updated in DB
            session = db_session.query(ChatSession).filter(ChatSession.id == session_id).first()
            assert session.title == "New Generated Title"

    def test_generate_title_unknown_session_returns_title_only(self, client: TestClient):
        """Deve retornar o titulo mesmo se o session_id nao existir (sem erro)."""
        with patch("backend.routers.session.generate_title", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "Some Title"

            response = client.post(
                "/api/sessions/generate-title",
                json={"message": "Hi", "session_id": 9999},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Some Title"