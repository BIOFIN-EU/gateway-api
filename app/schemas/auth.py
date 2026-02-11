from pydantic import BaseModel, EmailStr
from uuid import UUID


# ---------- REQUESTS ----------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------- RESPONSES ----------

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    expires_in_hours: int


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    is_active: bool
    is_superuser: bool
