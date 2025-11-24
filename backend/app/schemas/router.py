from pydantic import BaseModel
from typing import Optional
from ipaddress import IPv4Address

class RouterBase(BaseModel):
    name: str
    ip_address: IPv4Address
    username: str
    password: str
    port: Optional[int] = 8728
    is_active: Optional[bool] = True

class RouterCreate(RouterBase):
    pass

class RouterUpdate(BaseModel):
    name: Optional[str] = None
    ip_address: Optional[IPv4Address] = None
    username: Optional[str] = None
    password: Optional[str] = None
    port: Optional[int] = None
    is_active: Optional[bool] = None

class Router(RouterBase):
    id: int
    empresa_id: int

    class Config:
        from_attributes = True