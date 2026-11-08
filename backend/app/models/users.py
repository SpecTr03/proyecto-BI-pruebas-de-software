"""Modelos de la administración de usuarios."""

from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    administrador = "Administrador"
    analista = "Analista"
    investigador = "Investigador"


class CreateUserRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole


class UpdateUserRequest(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: UserRole
    is_active: bool
