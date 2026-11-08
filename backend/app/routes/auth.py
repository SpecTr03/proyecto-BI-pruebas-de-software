"""Endpoints de inicio de sesión y autorización de la aplicación."""

from __future__ import annotations

import os
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import (
    AuthenticatedUser,
    ROLE_PERMISSIONS,
    create_app_token,
    get_current_user,
    verify_neon_token,
)
from ..models.auth import AuthUserResponse, LoginRequest, LoginResponse
from ..neon_database import neon_database

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _auth_base_url() -> str:
    value = os.getenv("NEON_AUTH_BASE_URL")
    if not value:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neon Auth no está configurado.",
        )
    return value.rstrip("/")


def _auth_origin() -> str:
    origins = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173")
    return origins.split(",", 1)[0].strip()


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"description": "Credenciales inválidas"},
        403: {"description": "Usuario sin rol o inactivo"},
        503: {"description": "Servicio de autenticación no disponible"},
    },
)
async def login(payload: LoginRequest) -> LoginResponse:
    """Valida credenciales con Neon Auth y emite un JWT de aplicación de 8 horas."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{_auth_base_url()}/sign-in/email",
                headers={"Origin": _auth_origin()},
                json={"email": str(payload.email), "password": payload.password},
            )
            if response.is_success:
                token_response = await client.get(
                    f"{_auth_base_url()}/token",
                    headers={"Origin": _auth_origin()},
                )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible contactar a Neon Auth.",
        ) from exc

    if response.status_code in {401, 403}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El correo o la contraseña no son correctos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if response.is_error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neon Auth rechazó la solicitud de inicio de sesión.",
        )

    if token_response.is_error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neon Auth no devolvió un JWT verificable.",
        )

    data = response.json()
    neon_token = token_response.json().get("token")
    if not isinstance(neon_token, str):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neon Auth no devolvió un token válido.",
        )

    claims = verify_neon_token(neon_token)
    neon_user_id = claims.get("sub")
    if not isinstance(neon_user_id, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token de Neon Auth no tiene un usuario válido.",
        )

    try:
        app_user = neon_database.get_app_user(neon_user_id)
    except ConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible consultar los permisos del usuario.",
        ) from exc

    if not app_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no está registrado o está inactivo en la aplicación.",
        )

    role = app_user["role"]
    user = AuthenticatedUser(
        id=app_user["id"],
        email=app_user["email"],
        role=role,
        permissions=ROLE_PERMISSIONS[role],
    )
    access_token, expires_at = create_app_token(user)
    return LoginResponse(
        access_token=access_token,
        expires_at=expires_at,
        user=AuthUserResponse(
            id=user.id,
            name=app_user["name"],
            email=user.email,
            role=user.role,
            permissions=sorted(user.permissions),
        ),
    )


@router.get("/me", response_model=AuthUserResponse)
def current_user(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthUserResponse:
    """Devuelve el usuario contenido en el JWT de aplicación."""
    app_user = neon_database.get_app_user(user.id)
    if not app_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no está registrado o está inactivo.",
        )
    return AuthUserResponse(
        id=user.id,
        name=app_user["name"],
        email=user.email,
        role=user.role,
        permissions=sorted(user.permissions),
    )


@router.get("/permissions", response_model=list[str])
def permissions(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> list[str]:
    """Devuelve los permisos efectivos del usuario autenticado."""
    return sorted(user.permissions)
