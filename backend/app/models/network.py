from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

class Router(Base):
    __tablename__ = "routers"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), index=True, nullable=False)
    ip = Column(String(15), nullable=False)
    usuario = Column(String(100), nullable=False)
    senha = Column(String(255), nullable=False)
    tipo = Column(String(50), nullable=False)
    porta = Column(Integer, default=8728)
    is_active = Column(Boolean, default=True)

    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    empresa = relationship("Empresa", back_populates="routers")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())