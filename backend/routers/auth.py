from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from backend.services.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_user,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/auth/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Cadastra um novo usuario e retorna token JWT."""
    # Verifica se email ja existe
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email ja cadastrado.")

    user = User(
        email=payload.email,
        nome=payload.nome,
        sobrenome=payload.sobrenome,
        idade=payload.idade,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    logger.info("Novo usuario cadastrado: %s", user.email)

    return TokenResponse(
        access_token=token,
        user=UserOut(
            id=user.id,
            email=user.email,
            nome=user.nome,
            sobrenome=user.sobrenome,
            idade=user.idade,
            created_at=user.created_at,
        ),
    )


@router.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Autentica usuario e retorna token JWT."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou senha invalidos.")

    token = create_access_token(user.id)
    logger.info("Usuario logado: %s", user.email)

    return TokenResponse(
        access_token=token,
        user=UserOut(
            id=user.id,
            email=user.email,
            nome=user.nome,
            sobrenome=user.sobrenome,
            idade=user.idade,
            created_at=user.created_at,
        ),
    )


@router.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(require_user)):
    """Retorna dados do usuario autenticado."""
    return UserOut(
        id=user.id,
        email=user.email,
        nome=user.nome,
        sobrenome=user.sobrenome,
        idade=user.idade,
        created_at=user.created_at,
    )