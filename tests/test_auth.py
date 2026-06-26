from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.models import AuthToken, User


class TestSignup:
    ENDPOINT = "/api/auth/signup"

    def test_signup_success(self, client: TestClient):
        """Cadastro com dados validos deve retornar token."""
        resp = client.post(self.ENDPOINT, json={"email": "teste@test.com", "password": "123456"})
        assert resp.status_code == 200
        data = resp.json()
        assert "user_id" in data
        assert data["email"] == "teste@test.com"
        assert "token" in data
        assert len(data["token"]) == 64

    def test_signup_duplicate_email(self, client: TestClient, db_session):
        """Email duplicado deve retornar 409."""
        # Cria usuario
        from backend.models import User
        db_session.add(User(email="dup@test.com", password_hash="abc"))
        db_session.commit()

        resp = client.post(self.ENDPOINT, json={"email": "dup@test.com", "password": "123456"})
        assert resp.status_code == 409
        assert "ja cadastrado" in resp.json()["detail"]

    def test_signup_invalid_email(self, client: TestClient):
        """Email invalido deve retornar 422."""
        resp = client.post(self.ENDPOINT, json={"email": "invalido", "password": "123456"})
        assert resp.status_code == 422

    def test_signup_short_password(self, client: TestClient):
        """Senha muito curta deve retornar 422."""
        resp = client.post(self.ENDPOINT, json={"email": "valido@test.com", "password": "12345"})
        assert resp.status_code == 422


class TestLogin:
    ENDPOINT = "/api/auth/login"

    def _create_user(self, db_session):
        """Helper para criar usuario."""
        from backend.routers.auth import _hash_password
        user = User(email="user@test.com", password_hash=_hash_password("minha-senha"))
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    def test_login_success(self, client: TestClient, db_session):
        """Login com credenciais validas deve retornar token."""
        self._create_user(db_session)
        resp = client.post(self.ENDPOINT, json={"email": "user@test.com", "password": "minha-senha"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "user@test.com"
        assert "token" in data
        assert len(data["token"]) == 64

    def test_login_wrong_password(self, client: TestClient, db_session):
        """Senha incorreta deve retornar 401."""
        self._create_user(db_session)
        resp = client.post(self.ENDPOINT, json={"email": "user@test.com", "password": "senha-errada"})
        assert resp.status_code == 401
        assert "incorretos" in resp.json()["detail"]

    def test_login_wrong_email(self, client: TestClient):
        """Email inexistente deve retornar 401."""
        resp = client.post(self.ENDPOINT, json={"email": "nao-existe@test.com", "password": "123456"})
        assert resp.status_code == 401

    def test_login_invalid_email(self, client: TestClient):
        """Email com formato invalido deve retornar 422."""
        resp = client.post(self.ENDPOINT, json={"email": "invalido", "password": "123456"})
        assert resp.status_code == 422


class TestLogout:
    ENDPOINT = "/api/auth/logout"

    def _create_authenticated_user(self, client, db_session):
        """Helper que cria usuario + token e retorna token."""
        from backend.routers.auth import _generate_token, _hash_password
        user = User(email="logout@test.com", password_hash=_hash_password("123456"))
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token_str = _generate_token()
        token = AuthToken(user_id=user.id, token=token_str)
        db_session.add(token)
        db_session.commit()

        return user, token_str

    def test_logout_success(self, client: TestClient, db_session):
        """Logout com token valido deve invalidar o token."""
        user, token_str = self._create_authenticated_user(client, db_session)
        resp = client.post(self.ENDPOINT, headers={"Authorization": f"Bearer {token_str}"})
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

        # Token deve estar inativo
        token_db = db_session.query(AuthToken).filter(AuthToken.token == token_str).first()
        assert token_db is not None
        assert token_db.is_active is False

    def test_logout_without_token(self, client: TestClient):
        """Logout sem token deve retornar 401."""
        resp = client.post(self.ENDPOINT)
        assert resp.status_code == 401

    def test_logout_invalid_token(self, client: TestClient):
        """Logout com token invalido deve retornar 401."""
        resp = client.post(self.ENDPOINT, headers={"Authorization": "Bearer token-invalido"})
        assert resp.status_code == 401


class TestAuthMe:
    ENDPOINT = "/api/auth/me"

    def _create_authenticated_user(self, client, db_session):
        from backend.routers.auth import _generate_token, _hash_password
        user = User(email="me@test.com", password_hash=_hash_password("123456"))
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token_str = _generate_token()
        token = AuthToken(user_id=user.id, token=token_str)
        db_session.add(token)
        db_session.commit()

        return user, token_str

    def test_me_authenticated(self, client: TestClient, db_session):
        """Usuario autenticado deve ver seus dados."""
        user, token_str = self._create_authenticated_user(client, db_session)
        resp = client.get(self.ENDPOINT, headers={"Authorization": f"Bearer {token_str}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == user.id
        assert data["email"] == "me@test.com"

    def test_me_unauthenticated(self, client: TestClient):
        """Usuario nao autenticado deve receber 401."""
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 401


class TestSessionIsolation:
    """Verifica que usuarios diferentes veem apenas suas proprias sessoes."""

    def _create_user_with_token(self, db_session, email: str, password: str = "123456"):
        from backend.routers.auth import _generate_token, _hash_password
        user = User(email=email, password_hash=_hash_password(password))
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token_str = _generate_token()
        token = AuthToken(user_id=user.id, token=token_str)
        db_session.add(token)
        db_session.commit()

        return user, token_str

    def test_user_sessions_isolated(self, client: TestClient, db_session):
        """Usuario A nao ve sessoes do Usuario B."""
        from backend.models import ChatSession
        from datetime import datetime, timezone

        user_a, token_a = self._create_user_with_token(db_session, "a@test.com")
        user_b, token_b = self._create_user_with_token(db_session, "b@test.com")

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Cria sessao para usuario A
        db_session.add(ChatSession(id="session-a", user_id=user_a.id, title="Sessao A", created_at=now, updated_at=now))
        # Cria sessao para usuario B
        db_session.add(ChatSession(id="session-b", user_id=user_b.id, title="Sessao B", created_at=now, updated_at=now))
        db_session.commit()

        # Usuario A ve apenas sua sessao
        resp_a = client.get("/api/sessions", headers={"Authorization": f"Bearer {token_a}"})
        ids_a = [s["id"] for s in resp_a.json()]
        assert "session-a" in ids_a
        assert "session-b" not in ids_a

        # Usuario B ve apenas sua sessao
        resp_b = client.get("/api/sessions", headers={"Authorization": f"Bearer {token_b}"})
        ids_b = [s["id"] for s in resp_b.json()]
        assert "session-b" in ids_b
        assert "session-a" not in ids_b

    def test_message_isolation(self, client: TestClient, db_session):
        """Usuario A nao acessa mensagens da sessao do Usuario B."""
        from backend.models import ChatSession, ChatMessage
        from datetime import datetime, timezone

        user_a, token_a = self._create_user_with_token(db_session, "c@test.com")
        user_b, token_b = self._create_user_with_token(db_session, "d@test.com")

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        db_session.add(ChatSession(id="s-a", user_id=user_a.id, title="SA", created_at=now, updated_at=now))
        db_session.add(ChatSession(id="s-b", user_id=user_b.id, title="SB", created_at=now, updated_at=now))
        db_session.add(ChatMessage(session_key="s-b", role="user", content="msg secreta", created_at=now))
        db_session.commit()

        # Usuario A tenta acessar sessao do B
        resp = client.get("/api/sessions/s-b/messages", headers={"Authorization": f"Bearer {token_a}"})
        assert resp.status_code == 404


class TestSchemaValidation:
    ENDPOINT_SIGNUP = "/api/auth/signup"
    ENDPOINT_LOGIN = "/api/auth/login"

    def test_empty_payload(self, client: TestClient):
        """Payload vazio deve retornar 422."""
        for ep in [self.ENDPOINT_SIGNUP, self.ENDPOINT_LOGIN]:
            resp = client.post(ep, json={})
            assert resp.status_code == 422

    def test_missing_fields(self, client: TestClient):
        """Payload sem campos obrigatorios deve retornar 422."""
        for ep in [self.ENDPOINT_SIGNUP, self.ENDPOINT_LOGIN]:
            resp = client.post(ep, json={"email": "test@test.com"})
            assert resp.status_code == 422

            resp = client.post(ep, json={"password": "123456"})
            assert resp.status_code == 422