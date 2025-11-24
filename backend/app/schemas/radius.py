from pydantic import BaseModel, IPvAnyAddress
from typing import Optional
from datetime import datetime

# RadiusServer Schemas
class RadiusServerBase(BaseModel):
    name: str
    ip_address: IPvAnyAddress
    port: Optional[int] = 1812
    secret: str
    is_active: Optional[bool] = True

class RadiusServerCreate(RadiusServerBase):
    pass

class RadiusServerUpdate(BaseModel):
    name: Optional[str] = None
    ip_address: Optional[IPvAnyAddress] = None
    port: Optional[int] = None
    secret: Optional[str] = None
    is_active: Optional[bool] = None

class RadiusServer(RadiusServerBase):
    id: int
    empresa_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# RadiusUser Schemas
class RadiusUserBase(BaseModel):
    username: str
    password: str
    ip_address: Optional[IPvAnyAddress] = None
    mac_address: Optional[str] = None
    service_type: Optional[str] = "Framed-User"
    is_active: Optional[bool] = True
    cliente_id: Optional[int] = None
    session_timeout: Optional[int] = None
    idle_timeout: Optional[int] = None
    rate_limit_up: Optional[str] = None
    rate_limit_down: Optional[str] = None

class RadiusUserCreate(RadiusUserBase):
    pass

class RadiusUserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    ip_address: Optional[IPvAnyAddress] = None
    mac_address: Optional[str] = None
    service_type: Optional[str] = None
    is_active: Optional[bool] = None
    cliente_id: Optional[int] = None
    session_timeout: Optional[int] = None
    idle_timeout: Optional[int] = None
    rate_limit_up: Optional[str] = None
    rate_limit_down: Optional[str] = None

class RadiusUser(RadiusUserBase):
    id: int
    empresa_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# RadiusSession Schemas
class RadiusSessionBase(BaseModel):
    session_id: str
    username: str
    ip_address: Optional[IPvAnyAddress] = None
    mac_address: Optional[str] = None
    nas_ip: Optional[IPvAnyAddress] = None
    nas_port: Optional[str] = None
    service_type: Optional[str] = None
    radius_user_id: Optional[int] = None

class RadiusSessionCreate(RadiusSessionBase):
    pass

class RadiusSessionUpdate(BaseModel):
    end_time: Optional[datetime] = None
    bytes_up: Optional[int] = None
    bytes_down: Optional[int] = None

class RadiusSession(RadiusSessionBase):
    id: int
    empresa_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    bytes_up: int
    bytes_down: int

    class Config:
        from_attributes = True