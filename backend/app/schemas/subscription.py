from pydantic import BaseModel, IPvAnyAddress, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class AuthMethod(str, Enum):
    ip_mac = 'ip_mac'
    pppoe = 'pppoe'
    hotspot = 'hotspot'
    radius = 'radius'


class SubscriptionCreate(BaseModel):
    cliente_id: int
    servico_id: Optional[int] = None
    router_id: int
    ip: IPvAnyAddress
    mac: str = Field(..., example='AA:BB:CC:DD:EE:FF')
    interface: Optional[str] = None
    auth_method: AuthMethod = AuthMethod.ip_mac
    contract_length_months: Optional[int] = None
    price: Optional[float] = None


class SubscriptionResponse(BaseModel):
    id: int
    cliente_id: int
    servico_id: Optional[int]
    router_id: int
    ip: str
    mac: str
    interface: Optional[str]
    auth_method: AuthMethod
    status: str
    start_date: Optional[datetime]

    class Config:
        from_attributes = True
