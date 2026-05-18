from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

# Valores possíveis para o método de autenticação do roteador
MetodoAutenticacaoRouterEnum = Literal["RADIUS", "PPPOE", "HOTSPOT", "IP_MAC"]


class RouterBase(BaseModel):
    nome: str
    ip: str
    usuario: str
    senha: str
    tipo: str
    porta: Optional[int] = 8728
    is_active: Optional[bool] = True
    # Método de autenticação padrão para clientes deste roteador
    metodo_autenticacao_padrao: Optional[MetodoAutenticacaoRouterEnum] = None
    # Endereço e segredo do servidor RADIUS associado a este roteador
    radius_server_address: Optional[str] = None
    radius_secret: Optional[str] = None
    api_encoding: Optional[str] = "utf-8"


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
    metodo_autenticacao_padrao: Optional[MetodoAutenticacaoRouterEnum] = None
    radius_server_address: Optional[str] = None
    radius_secret: Optional[str] = None
    api_encoding: Optional[str] = None


class RouterResponse(BaseModel):
    id: int
    empresa_id: int
    nome: str
    ip: str
    usuario: str
    tipo: str
    porta: Optional[int] = 8728
    is_active: Optional[bool] = True
    metodo_autenticacao_padrao: Optional[str] = None
    radius_server_address: Optional[str] = None
    # Não expõe radius_secret na listagem por segurança
    api_encoding: Optional[str] = "utf-8"
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Alias para manter compatibilidade
Router = RouterResponse