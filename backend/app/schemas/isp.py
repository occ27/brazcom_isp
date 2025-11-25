from pydantic import BaseModel, Field, IPvAnyAddress
from typing import Optional


class IspClientBase(BaseModel):
    cliente_id: int
    servico_id: Optional[int] = None
    router_id: int
    ip: IPvAnyAddress
    mac: str = Field(..., example="AA:BB:CC:DD:EE:FF")
    interface: Optional[str] = None
    is_active: Optional[bool] = True


class IspClientCreate(IspClientBase):
    pass


class IspClientUpdate(BaseModel):
    ip: Optional[IPvAnyAddress]
    mac: Optional[str]
    interface: Optional[str]
    is_active: Optional[bool]


class IspClientResponse(IspClientBase):
    id: int

    class Config:
        orm_mode = True
