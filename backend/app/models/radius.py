from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

class RadiusServer(Base):
    """Servidor RADIUS para autenticação."""
    __tablename__ = "radius_servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    ip_address = Column(String(45), nullable=False)  # IPv4/IPv6
    port = Column(Integer, default=1812, nullable=False)
    secret = Column(String(255), nullable=False)  # Secret compartilhado
    is_active = Column(Boolean, default=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    empresa = relationship("Empresa", back_populates="radius_servers")

class RadiusUser(Base):
    """Usuário RADIUS para autenticação PPPoE/Hotspot."""
    __tablename__ = "radius_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False)
    password = Column(String(255), nullable=False)  # Senha criptografada
    ip_address = Column(String(45))  # IP fixo opcional
    mac_address = Column(String(17))  # MAC address opcional
    service_type = Column(String(50), default="Framed-User")  # PPPoE, Hotspot, etc.
    is_active = Column(Boolean, default=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))  # Vinculado a cliente

    # Atributos RADIUS adicionais
    session_timeout = Column(Integer)  # em segundos
    idle_timeout = Column(Integer)  # em segundos
    rate_limit_up = Column(String(50))  # Ex: "10M/10M"
    rate_limit_down = Column(String(50))  # Ex: "10M/10M"

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    empresa = relationship("Empresa", back_populates="radius_users")
    cliente = relationship("Cliente", back_populates="radius_user")

class RadiusSession(Base):
    """Sessões ativas RADIUS."""
    __tablename__ = "radius_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False)
    username = Column(String(100), nullable=False)
    ip_address = Column(String(45))
    mac_address = Column(String(17))
    nas_ip = Column(String(45))  # Network Access Server IP
    nas_port = Column(String(50))  # Porta física
    service_type = Column(String(50))
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    bytes_up = Column(Integer, default=0)
    bytes_down = Column(Integer, default=0)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    radius_user_id = Column(Integer, ForeignKey("radius_users.id"))

    # Relationships
    empresa = relationship("Empresa")
    radius_user = relationship("RadiusUser")