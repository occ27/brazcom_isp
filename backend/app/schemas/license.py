from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.models.license import LicenseStatus, LicensePlan

class LicenseBase(BaseModel):
    plan: LicensePlan
    price: float

class LicenseCreate(BaseModel):
    empresa_id: int
    plan_id: Optional[int] = None
    # Mantendo campos antigos para compatibilidade temporária
    plan: Optional[LicensePlan] = None
    price: Optional[float] = None

class LicenseAdminCreate(LicenseBase):
    empresa_id: int
    user_id: Optional[int] = None
    status: LicenseStatus = LicenseStatus.ACTIVE
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class LicenseUpdate(BaseModel):
    plan: Optional[LicensePlan] = None
    status: Optional[LicenseStatus] = None
    price: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None

class LicenseResponse(LicenseBase):
    id: int
    empresa_id: int
    user_id: int
    status: LicenseStatus
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    payment_date: Optional[datetime] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    approved_by_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
