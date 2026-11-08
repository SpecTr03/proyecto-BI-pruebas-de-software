"""Endpoints administrativos para gestionar usuarios y roles."""

from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import AuthenticatedUser, require_permission
from ..models.users import CreateUserRequest, UpdateUserRequest, UserResponse
from ..neon_database import neon_database
from .auth import _auth_base_url, _auth_origin

router = APIRouter(prefix="/users", tags=["Users"])
read_permission = Depends(require_permission("users:read"))
write_permission = Depends(require_permission("users:write"))


def _find_user(user_id: str) -> dict[str, object]:
    for user in neon_database.list_app_users():
        if str(user["id"]) == user_id:
            return user
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="El usuario no existe en la aplicación.",
    )


def _as_response(user: dict[str, object]) -> UserResponse:
    return UserResponse(
        id=str(user["id"]),
        name=str(user["name"]),
        email=str(user["email"]),
        role=str(user["role"]),
        is_active=bool(user["is_active"]),
    )


@router.get("", response_model=list[UserResponse], dependencies=[read_permission])
def list_users() -> list[UserResponse]:
    try:
        return [_as_response(user) for user in neon_database.list_app_users()]
    except ConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible consultar los usuarios.",
        ) from exc


@router.post("", response_model=UserResponse, dependencies=[write_permission])
async def create_user(payload: CreateUserRequest) -> UserResponse:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{_auth_base_url()}/sign-up/email",
                headers={"Origin": _auth_origin()},
                json={
                    "name": payload.name,
                    "email": str(payload.email),
                    "password": payload.password,
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible contactar Neon Auth.",
        ) from exc

    if response.status_code in {400, 409, 422}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese correo o los datos son inválidos.",
        )
    if response.is_error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neon Auth no pudo crear la cuenta.",
        )

    try:
        neon_user = neon_database.get_user_by_email(str(payload.email))
        if not neon_user:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="La cuenta fue creada, pero aún no pudo vincularse.",
            )
        neon_database.upsert_app_user(
            neon_user["id"],
            str(payload.email),
            payload.role.value,
            True,
        )
        return _as_response(_find_user(neon_user["id"]))
    except ConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La cuenta fue creada, pero falló la configuración de permisos.",
        ) from exc


@router.patch("/{user_id}", response_model=UserResponse, dependencies=[write_permission])
def update_user(
    user_id: str,
    payload: UpdateUserRequest,
    current_user: Annotated[
        AuthenticatedUser,
        Depends(require_permission("users:write")),
    ],
) -> UserResponse:
    try:
        current = _find_user(user_id)
        role = payload.role.value if payload.role else str(current["role"])
        is_active = (
            payload.is_active if payload.is_active is not None else bool(current["is_active"])
        )
        if user_id == current_user.id and not is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes desactivar tu propia cuenta.",
            )
        neon_database.upsert_app_user(
            user_id,
            str(current["email"]),
            role,
            is_active,
        )
        return _as_response(_find_user(user_id))
    except ConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible actualizar el usuario.",
        ) from exc
