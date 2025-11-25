from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Schemas para RouterInterface
class RouterInterfaceBase(BaseModel):
    nome: str
    tipo: str
    mac_address: Optional[str] = None
    comentario: Optional[str] = None
    is_active: Optional[bool] = True

class RouterInterfaceCreate(RouterInterfaceBase):
    pass

class RouterInterfaceUpdate(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[str] = None
    mac_address: Optional[str] = None
    comentario: Optional[str] = None
    is_active: Optional[bool] = None

class RouterInterfaceResponse(RouterInterfaceBase):
    id: int
    router_id: int
    enderecos_ip: List["InterfaceIPAddressResponse"] = []
    ip_classes: List["IPClassResponse"] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Schemas para InterfaceIPAddress
class InterfaceIPAddressBase(BaseModel):
    endereco_ip: str
    comentario: Optional[str] = None
    is_primary: Optional[bool] = False

class InterfaceIPAddressCreate(InterfaceIPAddressBase):
    pass

class InterfaceIPAddressUpdate(BaseModel):
    endereco_ip: Optional[str] = None
    comentario: Optional[str] = None
    is_primary: Optional[bool] = None

class InterfaceIPAddressResponse(InterfaceIPAddressBase):
    id: int
    interface_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Schemas para IPClass
class IPClassBase(BaseModel):
    nome: str
    rede: str
    gateway: Optional[str] = None
    dns1: Optional[str] = None
    dns2: Optional[str] = None

class IPClassCreate(IPClassBase):
    pass

class IPClassUpdate(BaseModel):
    nome: Optional[str] = None
    rede: Optional[str] = None
    gateway: Optional[str] = None
    dns1: Optional[str] = None
    dns2: Optional[str] = None

class IPClassResponse(IPClassBase):
    id: int
    empresa_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Schemas para atribuição de classes IP
class InterfaceIPClassAssignmentBase(BaseModel):
    interface_id: int
    ip_class_id: int

class InterfaceIPClassAssignmentCreate(InterfaceIPClassAssignmentBase):
    pass

class InterfaceIPClassAssignmentResponse(InterfaceIPClassAssignmentBase):
    id: int
    assigned_at: datetime
    applied_configs: Optional[List[str]] = None
    application_status: Optional[str] = None

    class Config:
        from_attributes = True

# Atualizar RouterResponse para incluir interfaces
from app.schemas.router import RouterResponse

# Criar uma nova versão do RouterResponse que inclui interfaces
class RouterWithInterfacesResponse(RouterResponse):
    interfaces: List[RouterInterfaceResponse] = []

    class Config:
        from_attributes = True