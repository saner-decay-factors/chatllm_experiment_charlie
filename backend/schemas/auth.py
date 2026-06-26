from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class SignupRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not EMAIL_RE.match(v):
            raise ValueError("Email invalido")
        return v


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not EMAIL_RE.match(v):
            raise ValueError("Email invalido")
        return v


class AuthResponse(BaseModel):
    user_id: int
    email: str
    token: str


class LogoutResponse(BaseModel):
    ok: bool