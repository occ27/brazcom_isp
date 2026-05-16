from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base

class LicenseStatus(str, enum.Enum):
    PENDING = "PENDENTE"
    ACTIVE = "ATIVA"
    EXPIRED = "EXPIRADA"
    CANCELLED = "CANCELADA"

class LicensePlan(str, enum.Enum):
    ANNUAL = "ANUAL"
    BIANNUAL = "BIANUAL"

class CompanyLicense(Base):
    __tablename__ = "company_licenses"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # Usuário que solicitou/pagou a licença
    
    plan_id = Column(Integer, ForeignKey("license_pricing_plans.id"), nullable=True)
    plan = Column(String(100), nullable=False) # Armazenamos o nome como string para histórico se o plano for deletado
    status = Column(SQLAlchemyEnum(LicenseStatus), default=LicenseStatus.PENDING)
    price = Column(Float, nullable=False)
    
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    payment_date = Column(DateTime(timezone=True), nullable=True)
    payment_method = Column(String(50), default="PIX")
    
    # Informações para aprovação manual
    notes = Column(String(500), nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="licenses")
    user = relationship("Usuario", foreign_keys=[user_id])
    approved_by = relationship("Usuario", foreign_keys=[approved_by_id])
