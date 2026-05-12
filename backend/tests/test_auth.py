"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        response = await client.post(
            "/api/auth/register",
            json={"email": "new@example.com", "username": "newuser", "password": "Password123!"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "new@example.com"

    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/auth/register",
            json={"email": "testuser@example.com", "username": "other", "password": "Password123!"},
        )
        assert response.status_code == 400
        assert "Email" in response.json()["detail"]

    async def test_register_duplicate_username(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/auth/register",
            json={"email": "other@example.com", "username": "testuser", "password": "Password123!"},
        )
        assert response.status_code == 400

    async def test_register_short_password(self, client: AsyncClient):
        response = await client.post(
            "/api/auth/register",
            json={"email": "x@example.com", "username": "xuser", "password": "short"},
        )
        assert response.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient):
        response = await client.post(
            "/api/auth/register",
            json={"email": "not-an-email", "username": "xuser", "password": "Password123!"},
        )
        assert response.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/auth/login",
            json={"email": "testuser@example.com", "password": "SecurePass123!"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/auth/login",
            json={"email": "testuser@example.com", "password": "WrongPassword!"},
        )
        assert response.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient):
        response = await client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "Password123!"},
        )
        assert response.status_code == 401


class TestGetMe:
    async def test_get_me_authenticated(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["email"] == "testuser@example.com"

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/auth/me")
        assert response.status_code == 401

    async def test_get_me_invalid_token(self, client: AsyncClient):
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401


class TestRefreshToken:
    async def test_refresh_success(self, client: AsyncClient, test_user):
        login = await client.post(
            "/api/auth/login",
            json={"email": "testuser@example.com", "password": "SecurePass123!"},
        )
        refresh_token = login.json()["refresh_token"]
        response = await client.post(
            "/api/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_refresh_invalid_token(self, client: AsyncClient):
        response = await client.post(
            "/api/auth/refresh", json={"refresh_token": "bad.token"}
        )
        assert response.status_code == 401
