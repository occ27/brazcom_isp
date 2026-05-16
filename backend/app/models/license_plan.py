from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class LicensePricingPlan(Base):
    """Tabela para definir os planos de licenciamento dinamicamente."""
    __tablename__ = "license_pricing_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # Ex: "Anual", "Bianual", "Trimestral"
    description = Column(String(255))
    price = Column(Float, nullable=False)
    duration_months = Column(Integer, nullable=False, default=12)
    is_active = Column(Boolean, default=True)
    is_highlighted = Column(Boolean, default=False) # Para destacar no frontend
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
