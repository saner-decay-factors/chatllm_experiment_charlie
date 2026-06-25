from __future__ import annotations

import secrets
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.hash import pbkdf2_sha256

from fastapi import Query

from backend.database import get_db
from backend.models import User, AuthToken
from backend.schemas.chat import AuthSignup, AuthLogin, AuthResponse


router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_current_user(token: str = Query(...), db: Session = Depends(get_db)) -> User:
    auth_token = db.query(AuthToken).filter(AuthToken.token == token).first()
    if not auth_token:
        raise HTTPException(status_code=401, detail="Token invalido.")
    user = db.query(User).filter(User.id == auth_token.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado.")
    return user


@router.post("/api/auth/signup", response_model=AuthResponse)
def signup(payload: AuthSignup, db: Session = Depends(get_db)) -> AuthResponse:
    email = payload.email.strip().lower()

    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Email invalido.")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email ja cadastrado.")

    password_hash = pbkdf2_sha256.hash(payload.password)
    user = User(email=email, hashed_password=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = secrets.token_hex(32)
    db.add(AuthToken(user_id=user.id, token=token))
    db.commit()

    return AuthResponse(token=token, email=user.email, user_id=user.id)


@router.post("/api/auth/login", response_model=AuthResponse)
def login(payload: AuthLogin, db: Session = Depends(get_db)) -> AuthResponse:
    email = payload.email.strip().lower()

    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Email invalido.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Email ou senha incorretos.")

    if not pbkdf2_sha256.verify(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos.")

    token = secrets.token_hex(32)
    db.add(AuthToken(user_id=user.id, token=token))
    db.commit()

    return AuthResponse(token=token, email=user.email, user_id=user.id)


@router.post("/api/auth/logout")
def logout(token: str | None = None, db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="Token nao fornecido.")
    auth_token = db.query(AuthToken).filter(AuthToken.token == token).first()
    if auth_token:
        db.delete(auth_token)
        db.commit()
    return {"status": "ok"}


@router.get("/api/auth/me")
def me(token: str | None = None, db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="Token nao fornecido.")
    auth_token = db.query(AuthToken).filter(AuthToken.token == token).first()
    if not auth_token:
        raise HTTPException(status_code=401, detail="Token invalido.")
    user = db.query(User).filter(User.id == auth_token.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado.")
    return {"email": user.email, "user_id": user.id}