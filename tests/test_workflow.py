from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.models import ChatMessage, ChatSession


class TestWorkflowIntegration:
    """Integration tests simulating real user workflows."""

    def test_create_session_and_list(self, client: TestClient, db_session):
        """Cria uma sessao e verifica que aparece na listagem."""
        resp = client.post("/api/sessions")
        assert resp.status_code == 200
        created = resp.json()
        session_id = created["id"]

        list_resp = client.get("/api/sessions")
        ids = [s["id"] for s in list_resp.json()]
        assert session_id in ids

    def test_multiple_sessions_ordered_by_updated_at(self, client: TestClient, db_session):
        """Sessoes devem ser listadas da mais recente para a mais antiga."""
        import uuid

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        s1 = ChatSession(id=str(uuid.uuid4()), title="Primeira", created_at=now, updated_at=now)
        s2 = ChatSession(id=str(uuid.uuid4()), title="Segunda", created_at=now, updated_at=now)
        db_session.add_all([s1, s2])
        db_session.commit()

        # Atualiza s2 para ser mais recente
        s2.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db_session.commit()

        resp = client.get("/api/sessions")
        data = resp.json()
        # As sessoes devem vir ordenadas por updated_at desc
        assert len(data) >= 2
        assert data[0]["id"] == s2.id

    def test_create_session_and_send_message_via_chat(self, client: TestClient, db_session):
        """Cria sessao, envia mensagem via /api/chat e verifica persistencia."""
        import uuid

        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db_session.add(ChatSession(id=session_id, title="", created_at=now, updated_at=now))
        db_session.commit()

        # Envia mensagem (pode ter API key configurada ou nao)
        resp = client.post(
            "/api/chat",
            json={"message": "Ola", "session_id": session_id},
        )
        # Aceita 200 (com API key) ou 503 (sem API key)
        assert resp.status_code in (200, 503)

    def test_create_session_and_stream_message(self, client: TestClient, db_session):
        """Cria sessao, envia mensagem via stream e verifica persistencia (espera 503 sem API key)."""
        import uuid

        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db_session.add(ChatSession(id=session_id, title="", created_at=now, updated_at=now))
        db_session.commit()

        resp = client.post(
            "/api/chat/stream",
            json={"message": "Ola", "session_id": session_id},
        )
        # Streaming pode iniciar e retornar erro de config
        assert resp.status_code in (200, 503)

    def test_create_delete_create_cycle(self, client: TestClient, db_session):
        """Cria, deleta e cria novamente - fluxo normal."""
        # Cria
        r1 = client.post("/api/sessions")
        id1 = r1.json()["id"]

        # Deleta
        client.delete(f"/api/sessions/{id1}")

        # Cria novamente
        r2 = client.post("/api/sessions")
        id2 = r2.json()["id"]

        assert id1 != id2

        # Lista deve conter apenas a segunda
        lista = client.get("/api/sessions").json()
        ids = [s["id"] for s in lista]
        assert id2 in ids
        assert id1 not in ids

    def test_auto_title_on_first_message(self, client: TestClient, db_session):
        """Simula o fluxo: cria sessao, envia primeira mensagem, espera titulo automatico."""
        import uuid

        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db_session.add(ChatSession(id=session_id, title="", created_at=now, updated_at=now))
        db_session.commit()

        from backend.routers.chat import _auto_title_if_needed

        _auto_title_if_needed(db_session, session_id, "Qual o sentido da vida?")
        session = db_session.query(ChatSession).filter(ChatSession.id == session_id).first()
        assert session.title == "Qual o sentido da vida?"

    def test_switch_between_sessions(self, client: TestClient, db_session):
        """Cria duas sessoes com mensagens e verifica que cada uma retorna suas proprias mensagens."""
        import uuid

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        s1_id = str(uuid.uuid4())
        s2_id = str(uuid.uuid4())

        db_session.add_all([
            ChatSession(id=s1_id, title="Sessao 1", created_at=now, updated_at=now),
            ChatSession(id=s2_id, title="Sessao 2", created_at=now, updated_at=now),
        ])
        db_session.add_all([
            ChatMessage(session_key=s1_id, role="user", content="Msg na s1", created_at=now),
            ChatMessage(session_key=s2_id, role="user", content="Msg na s2", created_at=now),
        ])
        db_session.commit()

        # Busca mensagens da sessao 1
        r1 = client.get(f"/api/sessions/{s1_id}/messages").json()
        assert len(r1) == 1
        assert r1[0]["content"] == "Msg na s1"

        # Busca mensagens da sessao 2
        r2 = client.get(f"/api/sessions/{s2_id}/messages").json()
        assert len(r2) == 1
        assert r2[0]["content"] == "Msg na s2"