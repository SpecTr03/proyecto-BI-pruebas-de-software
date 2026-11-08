"""Autenticación, JWT de aplicación y autorización por permisos."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Annotated, Callable
from urllib.parse import urlsplit

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from .neon_database import neon_database

TOKEN_TTL = timedelta(hours=8)
ALGORITHM = "HS256"
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "Administrador": frozenset({"dashboard:read", "users:read", "users:write", "reports:read"}),
    "Analista": frozenset({"dashboard:read", "reports:read"}),
    "Investigador": frozenset({"dashboard:read", "reports:read", "data:read"}),
}

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str
    role: str
    permissions: frozenset[str]


def _jwt_secret() -> str:
    secret = os.getenv("APP_JWT_SECRET")
    if not secret or len(secret) < 32:
        raise RuntimeError("APP_JWT_SECRET debe tener al menos 32 caracteres.")
    return secret


@lru_cache(maxsize=1)
def _neon_jwks_client() -> PyJWKClient:
    jwks_url = os.getenv("NEON_AUTH_JWKS_URL")
    if not jwks_url:
        raise RuntimeError("NEON_AUTH_JWKS_URL no está configurada.")
    return PyJWKClient(jwks_url)


def _neon_issuer() -> str:
    auth_url = os.getenv("NEON_AUTH_BASE_URL")
    if not auth_url:
        raise RuntimeError("NEON_AUTH_BASE_URL no está configurada.")
    parsed = urlsplit(auth_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def verify_neon_token(token: str) -> dict[str, object]:
    """Valida un JWT emitido por Neon Auth y devuelve sus claims."""
    try:
        signing_key = _neon_jwks_client().get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["EdDSA"],
            issuer=_neon_issuer(),
            audience=_neon_issuer(),
            options={"require": ["sub", "exp"]},
        )
    except (jwt.PyJWTError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de Neon Auth inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def create_app_token(user: AuthenticatedUser) -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + TOKEN_TTL
    payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "permissions": sorted(user.permissions),
        "iat": datetime.now(timezone.utc),
        "exp": expires_at,
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=ALGORITHM), expires_at


def verify_app_token(token: str) -> AuthenticatedUser:
    try:
        payload = jwt.decode(
            token,
            _jwt_secret(),
            algorithms=[ALGORITHM],
            options={"require": ["sub", "email", "role", "permissions", "exp"]},
        )
        role = str(payload["role"])
        permissions = frozenset(str(item) for item in payload["permissions"])
        if role not in ROLE_PERMISSIONS or not permissions <= ROLE_PERMISSIONS[role]:
            raise ValueError("Permisos inválidos.")
        return AuthenticatedUser(
            id=str(payload["sub"]),
            email=str(payload["email"]),
            role=role,
            permissions=permissions,
        )
    except (jwt.PyJWTError, KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de aplicación inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> AuthenticatedUser:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere un token Bearer.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_user = verify_app_token(credentials.credentials)
    try:
        app_user = neon_database.get_app_user(token_user.id)
    except ConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible consultar el estado del usuario.",
        ) from exc
    if not app_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no está registrado o está inactivo.",
        )
    return AuthenticatedUser(
        id=app_user["id"],
        email=app_user["email"],
        role=app_user["role"],
        permissions=ROLE_PERMISSIONS[app_user["role"]],
    )


def require_permission(permission: str) -> Callable:
    def dependency(
        user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if permission not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario no tiene permisos suficientes.",
            )
        return user

    return dependency
