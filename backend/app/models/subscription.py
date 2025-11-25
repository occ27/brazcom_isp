from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class SubscriptionStatus(str, enum.Enum):
    pending = 'pending'
    active = 'active'
    failed = 'failed'
    cancelled = 'cancelled'


class AuthMethod(str, enum.Enum):
    ip_mac = 'ip_mac'
    pppoe = 'pppoe'
    hotspot = 'hotspot'
    radius = 'radius'


class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=False)
    cliente_id = Column(Integer, ForeignKey('clientes.id'), nullable=False)
    servico_id = Column(Integer, ForeignKey('servicos.id'), nullable=True)
    router_id = Column(Integer, ForeignKey('routers.id'), nullable=False)

    ip = Column(String(45), nullable=False)
    mac = Column(String(50), nullable=False)
    interface = Column(String(100), nullable=True)

    auth_method = Column(SAEnum(AuthMethod), nullable=False, server_default=AuthMethod.ip_mac.value)
    status = Column(SAEnum(SubscriptionStatus), nullable=False, server_default=SubscriptionStatus.pending.value)

    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=True)
    contract_length_months = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)
    billing_cycle = Column(String(50), nullable=True)

    notes = Column(String(1000), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship('Empresa')
    cliente = relationship('Cliente')
    servico = relationship('Servico')
    router = relationship('Router')
