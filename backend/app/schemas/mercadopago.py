from pydantic import BaseModel
from typing import List, Optional

class MercadoPagoPaymentRequest(BaseModel):
    transaction_amount: float
    payment_method_id: str
    payer: dict
    token: Optional[str] = None
    issuer_id: Optional[str] = None
    installments: Optional[int] = None
    receivable_ids: List[int]
    discount_amount: Optional[float] = 0

class MercadoPagoResponse(BaseModel):
    payment_id: str
    status: str
    detail: dict

class MercadoPagoPreferenceResponse(BaseModel):
    preference_id: str
    init_point: str
