from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from backend.config import JWT_SECRET
from backend.database import get_db
from backend.models import User
from backend.schemas.auth import AuthRequest, AuthResponse, UserInfo

router = APIRouter()

SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 64


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    return f"{salt}${dk.hex()}"


def _verify_password(plain: str, stored: str) -> bool:
    salt, hash_hex = stored.split("$", 1)
    dk = hashlib.scrypt(
        plain.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    return dk.hex() == hash_hex


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _create_token(email: str) -> str:
    header = _b64url(json.dumps({"alg": "HS256"}).encode())
    payload = _b64url(
        json.dumps(
            {"sub": email, "exp": time.time() + 86400, "iat": time.time()}
        ).encode()
    )
    sig = hmac.new(
        JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256
    ).digest()
    return f"{header}.{payload}.{_b64url(sig)}"


def _decode_token(token: str) -> dict:
    """Decodifica e valida um token JWT HMAC-SHA256."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Formato de token invalido")

    header_b64, payload_b64, sig_b64 = parts

    expected_sig = hmac.new(
        JWT_SECRET.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256
    ).digest()

    # Comparacao segura contra timing attack
    if not hmac.compare_digest(expected_sig, base64.urlsafe_b64decode(sig_b64 + "==")):
        raise ValueError("Assinatura invalida")

    payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
    exp = payload.get("exp", 0)
    if time.time() > exp:
        raise ValueError("Token expirado")

    return payload


def get_current_user(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> User:
    """Dependency que extrai o usuario autenticado a partir do token JWT."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token nao fornecido")

    token = authorization.removeprefix("Bearer ")
    try:
        payload = _decode_token(token)
        email: str | None = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token invalido")
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Token invalido ou expirado")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado")
    return user


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@router.post("/api/auth/register", response_model=AuthResponse, status_code=201)
def register(payload: AuthRequest, db: Session = Depends(get_db)):
    email = _normalize_email(payload.email)

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email ja cadastrado")

    user = User(
        email=email,
        hashed_password=_hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = _create_token(user.email)
    return AuthResponse(access_token=token, email=user.email)


@router.post("/api/auth/login", response_model=AuthResponse)
def login(payload: AuthRequest, db: Session = Depends(get_db)):
    email = _normalize_email(payload.email)

    user = db.query(User).filter(User.email == email).first()
    if not user or not _verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    token = _create_token(user.email)
    return AuthResponse(access_token=token, email=user.email)


@router.post("/api/auth/logout", status_code=204)
def logout(current_user: User = Depends(get_current_user)):
    return None


@router.get("/api/auth/me", response_model=UserInfo)
def me(current_user: User = Depends(get_current_user)):
    return UserInfo(email=current_user.email, id=current_user.id)