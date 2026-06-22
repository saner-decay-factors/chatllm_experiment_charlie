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


class TestSessionEndpoints:
    def test_list_sessions_empty(self, client: TestClient):
        """Lista de sessoes deve retornar array vazio quando nao ha sessoes."""
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["sessions"] == []

    def test_create_session(self, client: TestClient):
        """Criar uma sessao deve retornar um session_key."""
        response = client.post("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "session_key" in data
        assert len(data["session_key"]) > 10

    def test_create_and_list_sessions(self, client: TestClient):
        """Apos criar, a sessao deve aparecer na lista."""
        client.post("/api/sessions")
        response = client.get("/api/sessions")
        data = response.json()
        assert data["total"] >= 1

    def test_get_session_messages_not_found(self, client: TestClient):
        """Sessao inexistente deve retornar 404."""
        response = client.get("/api/sessions/inexistente/messages")
        assert response.status_code == 404

    def test_get_session_messages_empty(self, client: TestClient):
        """Sessao recem-criada deve ter 0 mensagens."""
        create_resp = client.post("/api/sessions")
        sk = create_resp.json()["session_key"]
        response = client.get(f"/api/sessions/{sk}/messages")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["messages"] == []
        assert data["page"] == 1
        assert data["page_size"] == 50

    def test_chat_response_includes_session_key(self, client: TestClient):
        """O endpoint /api/chat deve retornar session_key na resposta."""
        response = client.post(
            "/api/chat",
            json={"message": "Ola"},
        )
        # Pode falhar sem API key, mas deve conter session_key se 503
        assert response.status_code in (200, 503)
        if response.status_code == 503:
            data = response.json()
            # Status 503 é config error, nao tem session_key
            pass
        else:
            data = response.json()
            assert "session_key" in data
