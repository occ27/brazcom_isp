from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class LicensePricingPlanBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    duration_months: int = 12
    is_active: bool = True
    is_highlighted: bool = False

class LicensePricingPlanCreate(LicensePricingPlanBase):
    pass

class LicensePricingPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    duration_months: Optional[int] = None
    is_active: Optional[bool] = None
    is_highlighted: Optional[bool] = None

class LicensePricingPlanResponse(LicensePricingPlanBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
