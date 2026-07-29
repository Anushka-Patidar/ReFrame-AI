from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: str
    city: str


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: str
    created_at: datetime


class ProfileUpdate(BaseModel):
    name: str
    phone: str
    city: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
