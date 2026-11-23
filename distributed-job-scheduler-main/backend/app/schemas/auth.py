from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=1)
    organization_name: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    name: str
    organization_id: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    created_at: datetime
    organization_id: Optional[str] = None

    class Config:
        from_attributes = True
