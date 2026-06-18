from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestRegister:
    def test_register_success(self, client: TestClient):
        response = client.post(
            "/api/auth/register",
            json={"email": "novo@teste.com", "password": "senha123"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["email"] == "novo@teste.com"
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email(self, client: TestClient):
        client.post(
            "/api/auth/register",
            json={"email": "duplicado@teste.com", "password": "senha123"},
        )
        response = client.post(
            "/api/auth/register",
            json={"email": "duplicado@teste.com", "password": "outrasenha"},
        )
        assert response.status_code == 409
        assert "ja cadastrado" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client: TestClient):
        response = client.post(
            "/api/auth/register",
            json={"email": "email-invalido", "password": "senha123"},
        )
        assert response.status_code == 422

    def test_register_short_password(self, client: TestClient):
        response = client.post(
            "/api/auth/register",
            json={"email": "valido@teste.com", "password": "abc"},
        )
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, client: TestClient):
        client.post(
            "/api/auth/register",
            json={"email": "login@teste.com", "password": "minhasenha"},
        )
        response = client.post(
            "/api/auth/login",
            json={"email": "login@teste.com", "password": "minhasenha"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["email"] == "login@teste.com"

    def test_login_wrong_password(self, client: TestClient):
        client.post(
            "/api/auth/register",
            json={"email": "login2@teste.com", "password": "senhacorreta"},
        )
        response = client.post(
            "/api/auth/login",
            json={"email": "login2@teste.com", "password": "senhaerrada"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_email(self, client: TestClient):
        response = client.post(
            "/api/auth/login",
            json={"email": "naoexiste@teste.com", "password": "qualquer"},
        )
        assert response.status_code == 401


class TestAuthMiddleware:
    def test_me_without_token(self, client: TestClient):
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_with_valid_token(self, client: TestClient):
        resp = client.post(
            "/api/auth/register",
            json={"email": "me@teste.com", "password": "senha123"},
        )
        token = resp.json()["access_token"]

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "me@teste.com"

    def test_me_with_invalid_token(self, client: TestClient):
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer token.invalido.aqui"},
        )
        assert response.status_code == 401


class TestLogout:
    def test_logout_without_token(self, client: TestClient):
        response = client.post("/api/auth/logout")
        assert response.status_code == 401

    def test_logout_with_valid_token(self, client: TestClient):
        resp = client.post(
            "/api/auth/register",
            json={"email": "logout@teste.com", "password": "senha123"},
        )
        token = resp.json()["access_token"]

        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Logout realizado com sucesso"