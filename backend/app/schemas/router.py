from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RouterBase(BaseModel):
    nome: str
    ip: str
    usuario: str
    senha: str
    tipo: str
    porta: Optional[int] = 8728
    is_active: Optional[bool] = True

class RouterCreate(RouterBase):
    pass

class RouterUpdate(BaseModel):
    nome: Optional[str] = None
    ip: Optional[str] = None
    usuario: Optional[str] = None
    senha: Optional[str] = None
    tipo: Optional[str] = None
    porta: Optional[int] = None
    is_active: Optional[bool] = None

class RouterResponse(BaseModel):
    id: int
    empresa_id: int
    nome: str
    ip: str
    usuario: str
    tipo: str
    porta: Optional[int] = 8728
    is_active: Optional[bool] = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Alias para manter compatibilidade
Router = RouterResponse