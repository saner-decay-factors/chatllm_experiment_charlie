from __future__ import annotations

import hashlib
import os
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import AuthToken, User
from backend.schemas.auth import AuthResponse, LoginRequest, LogoutResponse, SignupRequest

router = APIRouter()

# Numero de rounds do bcrypt (12 rounds = ~250ms no hardware moderno)
BCRYPT_ROUNDS = 12

# Tamanho do token de sessao em bytes (64 hex chars)
TOKEN_BYTES = 32


def _hash_password(password: str) -> str:
    """Gera hash seguro usando bcrypt com sal incorporado."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
    ).decode("utf-8")


def _check_password(password: str, password_hash: str) -> bool:
    """Verifica a senha contra o hash armazenado."""
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


def _generate_token() -> str:
    """Gera um token de sessao aleatorio."""
    return hashlib.sha256(os.urandom(TOKEN_BYTES)).hexdigest()


def get_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Dependencia que extrai o usuario autenticado do header Authorization.

    Retorna None se nao houver token (endpoints anonimos).
    Dispara 401 se o token for invalido.
    """
    if not authorization:
        return None

    # Aceita tanto "Bearer <token>" quanto apenas "<token>"
    token_str = authorization
    if token_str.startswith("Bearer "):
        token_str = token_str[7:]

    token_str = token_str.strip()
    if not token_str:
        return None

    token = (
        db.query(AuthToken)
        .filter(AuthToken.token == token_str, AuthToken.is_active == True)
        .first()
    )
    if not token:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado")

    user = db.query(User).filter(User.id == token.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado")

    return user


def require_user(
    current_user: Optional[User] = Depends(get_current_user),
) -> User:
    """Dependencia que exige autenticacao (dispara 401 se nao autenticado)."""
    if current_user is None:
        raise HTTPException(status_code=401, detail="Autenticacao necessaria")
    return current_user


@router.post("/api/auth/signup", response_model=AuthResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Cadastra um novo usuario."""
    # Verifica se email ja esta em uso
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email ja cadastrado")

    # Cria usuario
    user = User(
        email=payload.email,
        password_hash=_hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Gera token de sessao
    token = AuthToken(
        user_id=user.id,
        token=_generate_token(),
    )
    db.add(token)
    db.commit()

    return AuthResponse(user_id=user.id, email=user.email, token=token.token)


@router.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Autentica um usuario existente."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    if not _check_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    # Gera novo token de sessao
    token = AuthToken(
        user_id=user.id,
        token=_generate_token(),
    )
    db.add(token)
    db.commit()

    return AuthResponse(user_id=user.id, email=user.email, token=token.token)


@router.post("/api/auth/logout", response_model=LogoutResponse)
def logout(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
) -> LogoutResponse:
    """Invalida todos os tokens ativos do usuario (logout de todas as sessoes)."""
    tokens = (
        db.query(AuthToken)
        .filter(AuthToken.user_id == current_user.id, AuthToken.is_active == True)
        .all()
    )
    for t in tokens:
        t.is_active = False
    db.commit()
    return LogoutResponse(ok=True)


@router.get("/api/auth/me")
def get_me(current_user: User = Depends(require_user)) -> dict:
    """Retorna dados do usuario autenticado."""
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "created_at": current_user.created_at.isoformat(),
    }