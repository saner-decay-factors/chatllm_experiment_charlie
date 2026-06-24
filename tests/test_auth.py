from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestRegister:
    def test_register_success(self, client: TestClient):
        response = client.post(
            "/api/auth/register",
            json={"email": "teste@example.com", "password": "12345678"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["token_type"] == "bearer"
        assert data["email"] == "teste@example.com"
        assert "access_token" in data

    def test_register_duplicate_email(self, client: TestClient):
        client.post(
            "/api/auth/register",
            json={"email": "dup@example.com", "password": "12345678"},
        )
        response = client.post(
            "/api/auth/register",
            json={"email": "dup@example.com", "password": "56785678"},
        )
        assert response.status_code == 409
        assert "ja cadastrado" in response.json()["detail"]

    def test_register_weak_password(self, client: TestClient):
        response = client.post(
            "/api/auth/register",
            json={"email": "weak@example.com", "password": "1234567"},
        )
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, client: TestClient):
        client.post(
            "/api/auth/register",
            json={"email": "login@example.com", "password": "12345678"},
        )
        response = client.post(
            "/api/auth/login",
            json={"email": "login@example.com", "password": "12345678"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["email"] == "login@example.com"

    def test_login_wrong_password(self, client: TestClient):
        client.post(
            "/api/auth/register",
            json={"email": "wrong@example.com", "password": "12345678"},
        )
        response = client.post(
            "/api/auth/login",
            json={"email": "wrong@example.com", "password": "wrongpwd"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        response = client.post(
            "/api/auth/login",
            json={"email": "noone@example.com", "password": "12345678"},
        )
        assert response.status_code == 401


class TestMe:
    def test_me_authenticated(self, client: TestClient):
        client.post(
            "/api/auth/register",
            json={"email": "me@example.com", "password": "12345678"},
        )
        login_resp = client.post(
            "/api/auth/login",
            json={"email": "me@example.com", "password": "12345678"},
        )
        token = login_resp.json()["access_token"]

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "me@example.com"

    def test_me_unauthenticated(self, client: TestClient):
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_invalid_token(self, client: TestClient):
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"},
        )
        assert response.status_code == 401


class TestLogout:
    def test_logout_authenticated(self, client: TestClient):
        client.post(
            "/api/auth/register",
            json={"email": "logout@example.com", "password": "12345678"},
        )
        login_resp = client.post(
            "/api/auth/login",
            json={"email": "logout@example.com", "password": "12345678"},
        )
        token = login_resp.json()["access_token"]

        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

    def test_logout_unauthenticated(self, client: TestClient):
        response = client.post("/api/auth/logout")
        assert response.status_code == 401