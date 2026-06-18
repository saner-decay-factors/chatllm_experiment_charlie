from __future__ import annotations

import bcrypt
import jwt
import pytest

from backend.services.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from backend.config import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM


class TestHashPassword:
    def test_hash_returns_string(self):
        hashed = hash_password("minha-senha-segura")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_differs_from_plain(self):
        hashed = hash_password("minha-senha-segura")
        assert hashed != "minha-senha-segura"

    def test_hash_includes_bcrypt_prefix(self):
        hashed = hash_password("teste")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")


class TestVerifyPassword:
    def test_correct_password(self):
        hashed = hash_password("senha-correta")
        assert verify_password("senha-correta", hashed) is True

    def test_incorrect_password(self):
        hashed = hash_password("senha-correta")
        assert verify_password("senha-errada", hashed) is False

    def test_empty_password_fails(self):
        hashed = hash_password("senha-correta")
        assert verify_password("", hashed) is False


class TestCreateAccessToken:
    def test_returns_string_token(self):
        token = create_access_token(email="teste@example.com", user_id=1)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_valid_payload(self):
        token = create_access_token(email="user@example.com", user_id=42)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "user@example.com"
        assert payload["user_id"] == 42

    def test_token_has_expiration(self):
        token = create_access_token(email="a@b.com", user_id=1)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload
        assert "iat" in payload


class TestDecodeAccessToken:
    def test_decodes_valid_token(self):
        token = create_access_token(email="teste@teste.com", user_id=7)
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "teste@teste.com"
        assert payload["user_id"] == 7

    def test_returns_none_for_expired_token(self):
        import time
        from datetime import datetime, timedelta, timezone

        payload = {
            "sub": "expired@test.com",
            "user_id": 1,
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        result = decode_access_token(token)
        assert result is None

    def test_returns_none_for_garbage_token(self):
        result = decode_access_token("not.a.valid.token")
        assert result is None

    def test_returns_none_for_empty_string(self):
        result = decode_access_token("")
        assert result is None