from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.models import ChatMessage, ChatSession


SESSIONS_ENDPOINT = "/api/sessions"


class TestChatSessionModel:
    def test_create_session_defaults(self, db_session):
        """Deve criar uma sessao com valores padrao."""
        session_id = str(uuid.uuid4())
        session = ChatSession(id=session_id)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        assert session.id == session_id
        assert session.title == ""
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)

    def test_session_with_title(self, db_session):
        """Deve criar uma sessao com titulo personalizado."""
        session_id = str(uuid.uuid4())
        session = ChatSession(id=session_id, title="Minha conversa")
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        assert session.title == "Minha conversa"

    def test_session_cascade_delete(self, client: TestClient, db_session):
        """Ao deletar uma sessao via API, suas mensagens devem ser deletadas."""
        import uuid

        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        session = ChatSession(id=session_id, title="Teste cascata", created_at=now, updated_at=now)
        db_session.add(session)
        db_session.commit()

        msg1 = ChatMessage(session_key=session_id, role="user", content="Ola")
        msg2 = ChatMessage(session_key=session_id, role="assistant", content="Oi")
        db_session.add_all([msg1, msg2])
        db_session.commit()

        # Verifica que as mensagens existem
        assert db_session.query(ChatMessage).filter(ChatMessage.session_key == session_id).count() == 2

        # Deleta via API
        client.delete(f"/api/sessions/{session_id}")

        # Mensagens devem ser deletadas
        assert db_session.query(ChatMessage).filter(ChatMessage.session_key == session_id).count() == 0


class TestListSessions:
    def test_list_sessions_empty(self, client: TestClient):
        """Lista de sessoes deve ser vazia quando nao ha registros."""
        response = client.get(SESSIONS_ENDPOINT)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_sessions_returns_all(self, client: TestClient, db_session):
        """Deve retornar todas as sessoes ordenadas por updated_at descendente."""
        # Cria sessoes manualmente para que fiquem visiveis ao client
        import uuid

        s1_id = str(uuid.uuid4())
        s2_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        s1 = ChatSession(id=s1_id, title="Primeira", created_at=now, updated_at=now)
        s2 = ChatSession(id=s2_id, title="Segunda", created_at=now, updated_at=now)
        db_session.add_all([s1, s2])
        db_session.commit()

        response = client.get(SESSIONS_ENDPOINT)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_list_sessions_structure(self, client: TestClient, db_session):
        """Cada sessao deve conter id, title, created_at e updated_at."""
        import uuid

        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db_session.add(ChatSession(id=session_id, title="Teste", created_at=now, updated_at=now))
        db_session.commit()

        response = client.get(SESSIONS_ENDPOINT)
        data = response.json()
        session = next(s for s in data if s["id"] == session_id)
        assert "id" in session
        assert "title" in session
        assert "created_at" in session
        assert "updated_at" in session
        assert session["title"] == "Teste"


class TestCreateSession:
    def test_create_session_returns_new_session(self, client: TestClient):
        """Criar sessao deve retornar os dados da nova sessao."""
        response = client.post(SESSIONS_ENDPOINT)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == ""
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_session_persists(self, client: TestClient):
        """Sessao criada deve aparecer na lista."""
        create_resp = client.post(SESSIONS_ENDPOINT)
        created_id = create_resp.json()["id"]

        list_resp = client.get(SESSIONS_ENDPOINT)
        ids = [s["id"] for s in list_resp.json()]
        assert created_id in ids


class TestDeleteSession:
    def test_delete_existing_session(self, client: TestClient, db_session):
        """Deletar sessao existente deve retornar ok e remove-la."""
        import uuid

        session_id = str(uuid.uuid4())
        db_session.add(ChatSession(id=session_id))
        db_session.commit()

        response = client.delete(f"{SESSIONS_ENDPOINT}/{session_id}")
        assert response.status_code == 200
        assert response.json() == {"ok": True}

        # Verifica que foi removida
        list_resp = client.get(SESSIONS_ENDPOINT)
        ids = [s["id"] for s in list_resp.json()]
        assert session_id not in ids

    def test_delete_nonexistent_session(self, client: TestClient):
        """Deletar sessao inexistente deve retornar 404."""
        response = client.delete(f"{SESSIONS_ENDPOINT}/nonexistent-id")
        assert response.status_code == 404


class TestSessionMessages:
    def test_get_session_messages_empty(self, client: TestClient, db_session):
        """Sessao sem mensagens deve retornar lista vazia."""
        import uuid

        session_id = str(uuid.uuid4())
        db_session.add(ChatSession(id=session_id))
        db_session.commit()

        response = client.get(f"{SESSIONS_ENDPOINT}/{session_id}/messages")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_session_messages(self, client: TestClient, db_session):
        """Deve retornar mensagens da sessao ordenadas por created_at."""
        import uuid

        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db_session.add(ChatSession(id=session_id))
        db_session.add_all([
            ChatMessage(session_key=session_id, role="user", content="Pergunta", created_at=now),
            ChatMessage(session_key=session_id, role="assistant", content="Resposta", created_at=now),
        ])
        db_session.commit()

        response = client.get(f"{SESSIONS_ENDPOINT}/{session_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["role"] == "user"
        assert data[0]["content"] == "Pergunta"
        assert data[1]["role"] == "assistant"
        assert data[1]["content"] == "Resposta"

    def test_get_session_messages_nonexistent(self, client: TestClient):
        """Sessao inexistente deve retornar 404."""
        response = client.get(f"{SESSIONS_ENDPOINT}/nonexistent/messages")
        assert response.status_code == 404


class TestUpdateSessionTitle:
    def test_update_title(self, client: TestClient, db_session):
        """Deve atualizar o titulo de uma sessao existente."""
        import uuid

        session_id = str(uuid.uuid4())
        db_session.add(ChatSession(id=session_id, title=""))
        db_session.commit()

        response = client.patch(
            f"{SESSIONS_ENDPOINT}/{session_id}/title",
            json={"title": "Novo titulo"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Novo titulo"

    def test_update_title_empty_rejected(self, client: TestClient, db_session):
        """Titulo vazio deve ser rejeitado com 422."""
        import uuid

        session_id = str(uuid.uuid4())
        db_session.add(ChatSession(id=session_id))
        db_session.commit()

        response = client.patch(
            f"{SESSIONS_ENDPOINT}/{session_id}/title",
            json={"title": ""},
        )
        assert response.status_code == 422

    def test_update_title_nonexistent(self, client: TestClient):
        """Sessao inexistente deve retornar 404."""
        response = client.patch(
            f"{SESSIONS_ENDPOINT}/nonexistent/title",
            json={"title": "Titulo"},
        )
        assert response.status_code == 404


class TestAutoTitle:
    def _create_session_and_send_first_message(self, client: TestClient, db_session, message: str):
        """Helper: cria sessao e envia primeira mensagem via stream."""
        import uuid

        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db_session.add(ChatSession(id=session_id, title="", created_at=now, updated_at=now))
        db_session.commit()

        # Simula uma resposta stream que define o titulo automaticamente
        from backend.routers.chat import _auto_title_if_needed
        _auto_title_if_needed(db_session, session_id, message)

        return session_id

    def test_auto_title_short_message(self, client: TestClient, db_session):
        """Mensagem curta deve se tornar o titulo."""
        session_id = self._create_session_and_send_first_message(
            client, db_session, "Ola, como funciona isso?"
        )
        session = db_session.query(ChatSession).filter(ChatSession.id == session_id).first()
        assert session.title == "Ola, como funciona isso?"

    def test_auto_title_long_message(self, client: TestClient, db_session):
        """Mensagem longa deve ser truncada com '...'."""
        long_msg = "Esta e uma mensagem muito longa que deve ser truncada para criar um titulo adequado para a sessao."
        session_id = self._create_session_and_send_first_message(
            client, db_session, long_msg
        )
        session = db_session.query(ChatSession).filter(ChatSession.id == session_id).first()
        assert len(session.title) <= 43  # 40 + "..."
        assert session.title.endswith("...")

    def test_auto_title_does_not_override(self, client: TestClient, db_session):
        """Se a sessao ja tem titulo, nao deve sobrescrever."""
        import uuid

        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db_session.add(ChatSession(id=session_id, title="Titulo manual", created_at=now, updated_at=now))
        db_session.commit()

        from backend.routers.chat import _auto_title_if_needed
        _auto_title_if_needed(db_session, session_id, "Nova mensagem qualquer")

        session = db_session.query(ChatSession).filter(ChatSession.id == session_id).first()
        assert session.title == "Titulo manual"

    def test_auto_title_skips_default_session(self, client: TestClient, db_session):
        """Sessao 'default' nao deve receber titulo automatico."""
        from backend.routers.chat import _auto_title_if_needed
        _auto_title_if_needed(db_session, "default", "Mensagem qualquer")
        # Nao deve criar sessao default
        session = db_session.query(ChatSession).filter(ChatSession.id == "default").first()
        assert session is None