"""Tests for security utilities: JWT encoding/decoding and password hashing."""

import pytest
from datetime import timedelta
from jose import jwt

from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token,
)
from app.config import get_settings

settings = get_settings()


class TestPasswordHashing:
    def test_hash_is_different_from_plain(self):
        hashed = hash_password("mypassword")
        assert hashed != "mypassword"

    def test_verify_correct_password(self):
        hashed = hash_password("secure123")
        assert verify_password("secure123", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("secure123")
        assert verify_password("wrongpass", hashed) is False

    def test_different_hashes_for_same_password(self):
        """bcrypt salts should produce different hashes each time."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2


class TestJWT:
    def test_create_access_token_contains_sub(self):
        token = create_access_token({"sub": "42"})
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "42"
        assert payload["type"] == "access"

    def test_create_refresh_token_contains_type(self):
        token = create_refresh_token({"sub": "1"})
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["type"] == "refresh"

    def test_decode_valid_token(self):
        token = create_access_token({"sub": "10"})
        payload = decode_token(token)
        assert payload["sub"] == "10"

    def test_decode_invalid_token_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_token("not.a.valid.token")
        assert exc_info.value.status_code == 401

    def test_custom_expiry(self):
        token = create_access_token({"sub": "5"}, expires_delta=timedelta(seconds=1))
        payload = decode_token(token)
        assert payload["sub"] == "5"
