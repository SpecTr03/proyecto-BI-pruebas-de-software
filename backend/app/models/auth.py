"""Esquemas de autenticación de la API."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AuthUserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    permissions: list[str]


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_at: datetime
    user: AuthUserResponse
