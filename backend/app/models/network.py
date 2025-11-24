from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base

class Router(Base):
    __tablename__ = "routers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    ip_address = Column(String(15), nullable=False)
    username = Column(String(100), nullable=False)
    encrypted_password = Column(String(255), nullable=False)
    port = Column(Integer, default=8728)
    is_active = Column(Boolean, default=True)

    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    empresa = relationship("Empresa", back_populates="routers")