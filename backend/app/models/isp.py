from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class IspClient(Base):
    __tablename__ = "isp_clients"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    servico_id = Column(Integer, ForeignKey("servicos.id"), nullable=True)
    router_id = Column(Integer, ForeignKey("routers.id"), nullable=False)

    ip = Column(String(45), nullable=False)
    mac = Column(String(50), nullable=False)
    interface = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa")
    cliente = relationship("Cliente")
    servico = relationship("Servico")
    router = relationship("Router")
