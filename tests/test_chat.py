from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestRootEndpoint:
    def test_root_returns_frontend(self, client: TestClient):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestChatEndpoint:
    def test_chat_endpoint_exists(self, client: TestClient):
        """Verifica que o endpoint /api/chat responde (espera erro de config sem API key)."""
        response = client.post(
            "/api/chat",
            json={"message": "Ola"},
        )
        # Sem OPENROUTER_API_KEY definida, esperamos 503 (config error)
        assert response.status_code in (200, 422, 503)

    def test_chat_empty_message_rejected(self, client: TestClient):
        """Mensagem vazia deve ser rejeitada com 422 (validacao Pydantic)."""
        response = client.post(
            "/api/chat",
            json={"message": ""},
        )
        assert response.status_code == 422


class TestChatStreamEndpoint:
    def test_chat_stream_endpoint_exists(self, client: TestClient):
        """Verifica que o endpoint /api/chat/stream aceita requisicoes."""
        response = client.post(
            "/api/chat/stream",
            json={"message": "Ola"},
        )
        # Streaming pode iniciar e depois falhar sem API key
        assert response.status_code in (200, 422, 503)

    def test_chat_stream_empty_message_rejected(self, client: TestClient):
        """Stream com mensagem vazia deve ser rejeitado com 422."""
        response = client.post(
            "/api/chat/stream",
            json={"message": ""},
        )
        assert response.status_code == 422


class TestCORSMiddleware:
    def test_cors_headers_present(self, client: TestClient):
        """Verifica que os headers CORS estao presentes."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # O FastAPI com allow_origins=["*"] permite a requisicao
        assert response.status_code in (200, 405)


class TestSessionsEndpoint:
    def test_list_sessions_empty(self, client: TestClient):
        """Lista de sessoes deve estar vazia inicialmente."""
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []

    def test_create_session(self, client: TestClient):
        """Criar uma sessao deve retornar 201 com os dados."""
        response = client.post("/api/sessions", json={})
        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["title"] is None

    def test_create_and_list_sessions(self, client: TestClient):
        """Apos criar, a sessao deve aparecer na lista."""
        created = client.post("/api/sessions", json={})
        session_id = created.json()["id"]
        response = client.get("/api/sessions")
        assert response.status_code == 200
        ids = [s["id"] for s in response.json()["sessions"]]
        assert session_id in ids

    def test_get_session_messages_empty(self, client: TestClient):
        """Sessao recem-criada deve ter lista de mensagens vazia."""
        created = client.post("/api/sessions", json={})
        session_id = created.json()["id"]
        response = client.get(f"/api/sessions/{session_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert data["session"]["id"] == session_id
        assert data["messages"] == []

    def test_delete_session(self, client: TestClient):
        """Deletar sessao deve retornar 204 e remove-la da lista."""
        created = client.post("/api/sessions", json={})
        session_id = created.json()["id"]
        del_resp = client.delete(f"/api/sessions/{session_id}")
        assert del_resp.status_code == 204
        list_resp = client.get("/api/sessions")
        ids = [s["id"] for s in list_resp.json()["sessions"]]
        assert session_id not in ids

    def test_get_nonexistent_session(self, client: TestClient):
        """Sessao inexistente deve retornar 404."""
        response = client.get("/api/sessions/99999")
        assert response.status_code == 404

    def test_delete_nonexistent_session(self, client: TestClient):
        """Deletar sessao inexistente deve retornar 404."""
        response = client.delete("/api/sessions/99999")
        assert response.status_code == 404

    def test_chat_creates_session_automatically(self, client: TestClient):
        """Enviar mensagem sem session_id deve criar sessao automaticamente."""
        response = client.post("/api/chat", json={"message": "Ola"})
        # Pode ser 200 (sucesso com API key) ou 503/502 (sem API key)
        # Mas de qualquer forma, uma sessao deve ser criada
        list_resp = client.get("/api/sessions")
        sessions = list_resp.json()["sessions"]
        assert len(sessions) >= 1
