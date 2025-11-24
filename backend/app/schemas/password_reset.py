from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetVerify(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=20)


class PasswordResetConfirm(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=20)
    new_password: str = Field(..., min_length=6, max_length=72)
