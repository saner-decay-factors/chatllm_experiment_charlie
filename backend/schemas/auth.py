from __future__ import annotations

from pydantic import BaseModel, Field


class AuthRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str


class UserInfo(BaseModel):
    email: str
    id: int