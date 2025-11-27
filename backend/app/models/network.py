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

    # Relacionamentos com configurações PPPoE e DHCP
    ip_pools = relationship("IPPool", back_populates="router", cascade="all, delete-orphan")
    ppp_profiles = relationship("PPPProfile", back_populates="router", cascade="all, delete-orphan")
    pppoe_servers = relationship("PPPoEServer", back_populates="router", cascade="all, delete-orphan")
    dhcp_servers = relationship("DHCPServer", back_populates="router", cascade="all, delete-orphan")
    dhcp_networks = relationship("DHCPNetwork", back_populates="router", cascade="all, delete-orphan")

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

    # Relacionamentos com servidores PPPoE e DHCP
    pppoe_servers = relationship("PPPoEServer", back_populates="interface", cascade="all, delete-orphan")
    dhcp_servers = relationship("DHCPServer", back_populates="interface", cascade="all, delete-orphan")

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

class IPPool(Base):
    """Pool de endereços IP para DHCP e PPPoE."""
    __tablename__ = "ip_pools"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False, unique=True)  # Nome do pool
    ranges = Column(Text, nullable=False)  # Ranges de IP (ex: "192.168.1.2-192.168.1.254")
    comentario = Column(Text, nullable=True)  # Comentário do pool
    is_active = Column(Boolean, default=True)  # Status ativo/inativo
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    router_id = Column(Integer, ForeignKey("routers.id"), nullable=True)  # Router onde foi criado

    # Relacionamentos
    empresa = relationship("Empresa", back_populates="ip_pools")
    router = relationship("Router", back_populates="ip_pools")

    # Relacionamentos com perfis e servidores que usam este pool
    ppp_profiles = relationship("PPPProfile", back_populates="remote_address_pool", cascade="all, delete-orphan")
    dhcp_servers = relationship("DHCPServer", back_populates="address_pool", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class PPPProfile(Base):
    """Perfil PPP para autenticação PPPoE."""
    __tablename__ = "ppp_profiles"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False, unique=True)  # Nome do perfil
    local_address = Column(String(15), nullable=False)  # Endereço IP local do servidor
    remote_address_pool_id = Column(Integer, ForeignKey("ip_pools.id"), nullable=True)  # Pool de IPs remotos
    rate_limit = Column(String(50), nullable=True)  # Limite de velocidade (ex: "10M/10M")
    session_timeout = Column(String(20), nullable=True)  # Timeout da sessão (ex: "1d 00:00:00")
    idle_timeout = Column(String(20), nullable=True)  # Timeout de inatividade
    only_one_session = Column(Boolean, default=False)  # Uma sessão por usuário
    comentario = Column(Text, nullable=True)  # Comentário do perfil
    is_active = Column(Boolean, default=True)  # Status ativo/inativo

    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    router_id = Column(Integer, ForeignKey("routers.id"), nullable=True)  # Router onde foi criado

    # Relacionamentos
    empresa = relationship("Empresa", back_populates="ppp_profiles")
    router = relationship("Router", back_populates="ppp_profiles")
    remote_address_pool = relationship("IPPool", back_populates="ppp_profiles")

    # Relacionamento com servidores PPPoE que usam este perfil
    pppoe_servers = relationship("PPPoEServer", back_populates="default_profile", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class PPPoEServer(Base):
    """Servidor PPPoE para autenticação."""
    __tablename__ = "pppoe_servers"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(100), nullable=False, unique=True)  # Nome do serviço
    interface_id = Column(Integer, ForeignKey("router_interfaces.id"), nullable=False)  # Interface onde roda
    default_profile_id = Column(Integer, ForeignKey("ppp_profiles.id"), nullable=False)  # Perfil padrão
    max_sessions = Column(Integer, nullable=True)  # Número máximo de sessões
    max_sessions_per_host = Column(Integer, default=1)  # Sessões por host
    authentication = Column(String(100), default="pap,chap,mschap1,mschap2")  # Métodos de autenticação
    keepalive_timeout = Column(String(20), nullable=True)  # Timeout keepalive
    comentario = Column(Text, nullable=True)  # Comentário do servidor
    is_active = Column(Boolean, default=True)  # Status ativo/inativo

    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    router_id = Column(Integer, ForeignKey("routers.id"), nullable=True)  # Router onde foi criado

    # Relacionamentos
    empresa = relationship("Empresa", back_populates="pppoe_servers")
    router = relationship("Router", back_populates="pppoe_servers")
    interface = relationship("RouterInterface", back_populates="pppoe_servers")
    default_profile = relationship("PPPProfile", back_populates="pppoe_servers")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class DHCPServer(Base):
    """Servidor DHCP."""
    __tablename__ = "dhcp_servers"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False, unique=True)  # Nome do servidor DHCP
    interface_id = Column(Integer, ForeignKey("router_interfaces.id"), nullable=False)  # Interface
    address_pool_id = Column(Integer, ForeignKey("ip_pools.id"), nullable=False)  # Pool de endereços
    lease_time = Column(String(20), default="1d 00:00:00")  # Tempo de lease
    bootp_support = Column(String(10), default="static")  # Suporte BOOTP
    comentario = Column(Text, nullable=True)  # Comentário

    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    router_id = Column(Integer, ForeignKey("routers.id"), nullable=True)  # Router onde foi criado

    # Relacionamentos
    empresa = relationship("Empresa", back_populates="dhcp_servers")
    router = relationship("Router", back_populates="dhcp_servers")
    interface = relationship("RouterInterface", back_populates="dhcp_servers")
    address_pool = relationship("IPPool", back_populates="dhcp_servers")

    # Relacionamento com redes DHCP
    dhcp_networks = relationship("DHCPNetwork", back_populates="dhcp_server", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class DHCPNetwork(Base):
    """Rede DHCP com configurações específicas."""
    __tablename__ = "dhcp_networks"

    id = Column(Integer, primary_key=True, index=True)
    dhcp_server_id = Column(Integer, ForeignKey("dhcp_servers.id"), nullable=False)
    address = Column(String(18), nullable=False)  # Rede (ex: 192.168.1.0/24)
    gateway = Column(String(15), nullable=True)  # Gateway
    dns_servers = Column(String(255), nullable=True)  # Servidores DNS (separados por vírgula)
    domain = Column(String(100), nullable=True)  # Domínio
    wins_servers = Column(String(255), nullable=True)  # Servidores WINS
    ntp_servers = Column(String(255), nullable=True)  # Servidores NTP
    caps_manager = Column(String(255), nullable=True)  # Gerenciadores CAPS
    comentario = Column(Text, nullable=True)  # Comentário

    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    router_id = Column(Integer, ForeignKey("routers.id"), nullable=True)  # Router onde foi criado

    # Relacionamentos
    empresa = relationship("Empresa", back_populates="dhcp_networks")
    router = relationship("Router", back_populates="dhcp_networks")
    dhcp_server = relationship("DHCPServer", back_populates="dhcp_networks")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())