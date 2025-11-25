from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime

# Schemas para Usuário

class UsuarioBase(BaseModel):
    # Permite popular o modelo tanto por nome do campo (`full_name`) quanto
    # pelo alias em português (`nome`). Para compatibilidade com frontends
    # que enviam `nome`, usamos `alias="nome"` e `populate_by_name=True`.
    model_config = ConfigDict(populate_by_name=True)

    full_name: str = Field(..., min_length=3, max_length=255, alias="nome")
    email: EmailStr

class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=6, max_length=72)
    is_superuser: Optional[bool] = False

class UsuarioRegister(UsuarioBase):
    password: str = Field(..., min_length=6, max_length=72)

class UsuarioUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=3, max_length=255)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6, max_length=72)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None

class UsuarioResponse(UsuarioBase):
    id: int
    is_active: bool
    is_superuser: bool
    active_empresa_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Schemas para Token

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[int] = None
