"""Pydantic schemas for authentication."""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    device_type: str = Field(default="desktop", max_length=20)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    device_type: Optional[str] = None
    created_at: datetime
    last_active_at: Optional[datetime] = None
    is_active: bool

    model_config = {"from_attributes": True}
