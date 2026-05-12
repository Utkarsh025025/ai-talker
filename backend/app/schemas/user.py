"""Pydantic schemas for User endpoints."""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ── Request schemas ─────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    """Payload for POST /api/auth/register."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    """Payload for POST /api/auth/login."""
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """Payload for POST /api/auth/refresh."""
    refresh_token: str


# ── Response schemas ────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """Public representation of a user (no password)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """JWT token pair returned on login/register."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
