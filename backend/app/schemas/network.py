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
from app.schemas.empresa import EmpresaResponse

# Criar uma nova versão do RouterResponse que inclui interfaces
class RouterWithInterfacesResponse(RouterResponse):
    interfaces: List[RouterInterfaceResponse] = []

    class Config:
        from_attributes = True


# Schemas para configuração PPPoE
class PPPoESetupRequest(BaseModel):
    interface: str
    ip_pool_name: Optional[str] = "pppoe-pool"
    local_address: Optional[str] = "192.168.1.1"
    first_ip: Optional[str] = "192.168.1.2"
    last_ip: Optional[str] = "192.168.1.254"
    default_profile: Optional[str] = "pppoe-default"

class PPPoESetupResponse(BaseModel):
    message: str
    details: dict

class PPPoEStatusResponse(BaseModel):
    profiles: List[dict] = []
    servers: List[dict] = []
    interfaces: List[dict] = []
    pools: List[dict] = []
    error: Optional[str] = None

# Schemas para IPPool
class IPPoolBase(BaseModel):
    nome: str
    ranges: str
    comentario: Optional[str] = None
    is_active: bool = True

class IPPoolCreate(IPPoolBase):
    router_id: Optional[int] = None

class IPPoolUpdate(BaseModel):
    router_id: Optional[int] = None
    nome: Optional[str] = None
    ranges: Optional[str] = None
    comentario: Optional[str] = None
    is_active: Optional[bool] = None

class IPPoolResponse(IPPoolBase):
    id: int
    empresa_id: int
    router_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Schemas para PPPProfile
class PPPProfileBase(BaseModel):
    nome: str
    local_address: str
    remote_address_pool_id: Optional[int] = None
    rate_limit: Optional[str] = None
    session_timeout: Optional[str] = None
    idle_timeout: Optional[str] = None
    only_one_session: Optional[bool] = False
    comentario: Optional[str] = None
    is_active: bool = True

class PPPProfileCreate(PPPProfileBase):
    router_id: Optional[int] = None

class PPPProfileUpdate(BaseModel):
    router_id: Optional[int] = None
    nome: Optional[str] = None
    local_address: Optional[str] = None
    remote_address_pool_id: Optional[int] = None
    rate_limit: Optional[str] = None
    session_timeout: Optional[str] = None
    idle_timeout: Optional[str] = None
    only_one_session: Optional[bool] = None
    comentario: Optional[str] = None
    is_active: Optional[bool] = None

class PPPProfileResponse(PPPProfileBase):
    id: int
    empresa_id: int
    router_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    remote_address_pool: Optional["IPPoolResponse"] = None

    class Config:
        from_attributes = True

# Schemas para PPPoEServer
class PPPoEServerBase(BaseModel):
    service_name: str
    interface_id: int
    default_profile_id: int
    max_sessions: Optional[int] = None
    max_sessions_per_host: Optional[int] = 1
    authentication: Optional[str] = "pap,chap,mschap1,mschap2"
    keepalive_timeout: Optional[str] = None
    comentario: Optional[str] = None
    is_active: Optional[bool] = True

class PPPoEServerCreate(PPPoEServerBase):
    router_id: Optional[int] = None

class PPPoEServerUpdate(BaseModel):
    router_id: Optional[int] = None
    service_name: Optional[str] = None
    interface_id: Optional[int] = None
    default_profile_id: Optional[int] = None
    max_sessions: Optional[int] = None
    max_sessions_per_host: Optional[int] = None
    authentication: Optional[str] = None
    keepalive_timeout: Optional[str] = None
    comentario: Optional[str] = None
    is_active: Optional[bool] = None

class PPPoEServerResponse(PPPoEServerBase):
    id: int
    empresa_id: int
    router_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    interface: Optional[RouterInterfaceResponse] = None
    default_profile: Optional[PPPProfileResponse] = None
    router: Optional[RouterResponse] = None
    empresa: Optional[EmpresaResponse] = None

    class Config:
        from_attributes = True

# Schemas para DHCPServer
class DHCPServerBase(BaseModel):
    nome: str
    interface_id: int
    address_pool_id: int
    lease_time: Optional[str] = "1d 00:00:00"
    bootp_support: Optional[str] = "static"
    comentario: Optional[str] = None

class DHCPServerCreate(DHCPServerBase):
    router_id: Optional[int] = None

class DHCPServerUpdate(BaseModel):
    router_id: Optional[int] = None
    nome: Optional[str] = None
    interface_id: Optional[int] = None
    address_pool_id: Optional[int] = None
    lease_time: Optional[str] = None
    bootp_support: Optional[str] = None
    comentario: Optional[str] = None

class DHCPServerResponse(DHCPServerBase):
    id: int
    empresa_id: int
    router_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Schemas para DHCPNetwork
class DHCPNetworkBase(BaseModel):
    address: str
    gateway: Optional[str] = None
    dns_servers: Optional[str] = None
    domain: Optional[str] = None
    wins_servers: Optional[str] = None
    ntp_servers: Optional[str] = None
    caps_manager: Optional[str] = None
    comentario: Optional[str] = None

class DHCPNetworkCreate(DHCPNetworkBase):
    dhcp_server_id: int
    router_id: Optional[int] = None

class DHCPNetworkUpdate(BaseModel):
    dhcp_server_id: Optional[int] = None
    router_id: Optional[int] = None
    address: Optional[str] = None
    gateway: Optional[str] = None
    dns_servers: Optional[str] = None
    domain: Optional[str] = None
    wins_servers: Optional[str] = None
    ntp_servers: Optional[str] = None
    caps_manager: Optional[str] = None
    comentario: Optional[str] = None

class DHCPNetworkResponse(DHCPNetworkBase):
    id: int
    empresa_id: int
    dhcp_server_id: int
    router_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True