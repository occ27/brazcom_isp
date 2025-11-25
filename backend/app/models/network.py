from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Text, Float
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

    # Relacionamentos com interfaces
    interfaces = relationship("RouterInterface", back_populates="router", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class RouterInterface(Base):
    __tablename__ = "router_interfaces"

    id = Column(Integer, primary_key=True, index=True)
    router_id = Column(Integer, ForeignKey("routers.id"), nullable=False)
    nome = Column(String(100), nullable=False)  # Nome da interface (ether1, wlan1, etc.)
    tipo = Column(String(50), nullable=False)  # Tipo da interface (ethernet, wireless, etc.)
    mac_address = Column(String(17), nullable=True)  # Endereço MAC
    comentario = Column(Text, nullable=True)  # Comentário da interface
    is_active = Column(Boolean, default=True)

    # Relacionamento com router
    router = relationship("Router", back_populates="interfaces")

    # Relacionamento com endereços IP
    enderecos_ip = relationship("InterfaceIPAddress", back_populates="interface", cascade="all, delete-orphan")

    # Relacionamento many-to-many com classes IP
    ip_classes = relationship("IPClass", secondary="interface_ip_class_assignments", back_populates="interfaces")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class InterfaceIPAddress(Base):
    __tablename__ = "interface_ip_addresses"

    id = Column(Integer, primary_key=True, index=True)
    interface_id = Column(Integer, ForeignKey("router_interfaces.id"), nullable=False)
    endereco_ip = Column(String(18), nullable=False)  # Endereço IP com máscara (192.168.1.1/24)
    comentario = Column(Text, nullable=True)  # Comentário do endereço IP
    is_primary = Column(Boolean, default=False)  # Se é o endereço IP primário da interface

    # Relacionamento com interface
    interface = relationship("RouterInterface", back_populates="enderecos_ip")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class IPClass(Base):
    __tablename__ = "ip_classes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)  # Nome da classe (Classe A, Classe B, etc.)
    rede = Column(String(18), nullable=False)  # Rede (192.168.1.0/24)
    gateway = Column(String(15), nullable=True)  # Gateway da rede
    dns1 = Column(String(15), nullable=True)  # DNS primário
    dns2 = Column(String(15), nullable=True)  # DNS secundário
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)

    # Relacionamento com empresa
    empresa = relationship("Empresa", back_populates="ip_classes")

    # Relacionamento com interfaces que usam esta classe
    interfaces = relationship("RouterInterface", secondary="interface_ip_class_assignments", back_populates="ip_classes")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Tabela de associação many-to-many entre interfaces e classes IP
class InterfaceIPClassAssignment(Base):
    __tablename__ = "interface_ip_class_assignments"

    id = Column(Integer, primary_key=True, index=True)
    interface_id = Column(Integer, ForeignKey("router_interfaces.id"), nullable=False)
    ip_class_id = Column(Integer, ForeignKey("ip_classes.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())