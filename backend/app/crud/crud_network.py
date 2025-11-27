from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app.models.network import (
    RouterInterface, InterfaceIPAddress, IPClass, InterfaceIPClassAssignment,
    IPPool, PPPProfile, PPPoEServer, DHCPServer, DHCPNetwork
)
from app.schemas.network import (
    RouterInterfaceCreate, RouterInterfaceUpdate,
    InterfaceIPAddressCreate, InterfaceIPAddressUpdate,
    IPClassCreate, IPClassUpdate,
    InterfaceIPClassAssignmentCreate,
    IPPoolCreate, IPPoolUpdate,
    PPPProfileCreate, PPPProfileUpdate,
    PPPoEServerCreate, PPPoEServerUpdate,
    DHCPServerCreate, DHCPServerUpdate,
    DHCPNetworkCreate, DHCPNetworkUpdate
)

# CRUD para RouterInterface
def get_router_interface(db: Session, interface_id: int) -> Optional[RouterInterface]:
    """Busca uma interface específica."""
    return db.query(RouterInterface).filter(RouterInterface.id == interface_id).first()

def get_router_interfaces_by_router(db: Session, router_id: int) -> List[RouterInterface]:
    """Busca todas as interfaces de um router com suas classes de IP."""
    return db.query(RouterInterface)\
        .options(joinedload(RouterInterface.ip_classes))\
        .filter(RouterInterface.router_id == router_id)\
        .all()

def create_router_interface(db: Session, interface: RouterInterfaceCreate, router_id: int) -> RouterInterface:
    """Cria uma nova interface para um router."""
    db_interface = RouterInterface(
        router_id=router_id,
        nome=interface.nome,
        tipo=interface.tipo,
        mac_address=interface.mac_address,
        comentario=interface.comentario,
        is_active=interface.is_active
    )
    db.add(db_interface)
    db.commit()
    db.refresh(db_interface)
    return db_interface

def update_router_interface(db: Session, db_interface: RouterInterface, interface_in: RouterInterfaceUpdate) -> RouterInterface:
    """Atualiza uma interface."""
    update_data = interface_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_interface, field, value)

    db.add(db_interface)
    db.commit()
    db.refresh(db_interface)
    return db_interface

def remove_router_interface(db: Session, db_interface: RouterInterface):
    """Remove uma interface."""
    db.delete(db_interface)
    db.commit()
    return db_interface

# CRUD para InterfaceIPAddress
def get_interface_ip_address(db: Session, ip_id: int) -> Optional[InterfaceIPAddress]:
    """Busca um endereço IP específico."""
    return db.query(InterfaceIPAddress).filter(InterfaceIPAddress.id == ip_id).first()

def get_ip_addresses_by_interface(db: Session, interface_id: int) -> List[InterfaceIPAddress]:
    """Busca todos os endereços IP de uma interface."""
    return db.query(InterfaceIPAddress).filter(InterfaceIPAddress.interface_id == interface_id).all()

def create_interface_ip_address(db: Session, ip_address: InterfaceIPAddressCreate, interface_id: int) -> InterfaceIPAddress:
    """Cria um novo endereço IP para uma interface."""
    db_ip = InterfaceIPAddress(
        interface_id=interface_id,
        endereco_ip=ip_address.endereco_ip,
        comentario=ip_address.comentario,
        is_primary=ip_address.is_primary
    )
    db.add(db_ip)
    db.commit()
    db.refresh(db_ip)
    return db_ip

def update_interface_ip_address(db: Session, db_ip: InterfaceIPAddress, ip_in: InterfaceIPAddressUpdate) -> InterfaceIPAddress:
    """Atualiza um endereço IP."""
    update_data = ip_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_ip, field, value)

    db.add(db_ip)
    db.commit()
    db.refresh(db_ip)
    return db_ip

def remove_interface_ip_address(db: Session, db_ip: InterfaceIPAddress):
    """Remove um endereço IP."""
    db.delete(db_ip)
    db.commit()
    return db_ip

# CRUD para IPClass
def get_ip_class(db: Session, class_id: int) -> Optional[IPClass]:
    """Busca uma classe IP específica."""
    return db.query(IPClass).filter(IPClass.id == class_id).first()

def get_ip_classes_by_empresa(db: Session, empresa_id: int) -> List[IPClass]:
    """Busca todas as classes IP de uma empresa."""
    return db.query(IPClass).filter(IPClass.empresa_id == empresa_id).all()

def create_ip_class(db: Session, ip_class: IPClassCreate, empresa_id: int) -> IPClass:
    """Cria uma nova classe IP para uma empresa."""
    db_class = IPClass(
        empresa_id=empresa_id,
        nome=ip_class.nome,
        rede=ip_class.rede,
        gateway=ip_class.gateway,
        dns1=ip_class.dns1,
        dns2=ip_class.dns2
    )
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class

def update_ip_class(db: Session, db_class: IPClass, class_in: IPClassUpdate) -> IPClass:
    """Atualiza uma classe IP."""
    update_data = class_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_class, field, value)

    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class

def remove_ip_class(db: Session, db_class: IPClass):
    """Remove uma classe IP."""
    db.delete(db_class)
    db.commit()
    return db_class

# CRUD para InterfaceIPClassAssignment
def assign_ip_class_to_interface(db: Session, assignment: InterfaceIPClassAssignmentCreate) -> InterfaceIPClassAssignment:
    """Atribui uma classe IP a uma interface."""
    db_assignment = InterfaceIPClassAssignment(
        interface_id=assignment.interface_id,
        ip_class_id=assignment.ip_class_id
    )
    db.add(db_assignment)
    db.commit()
    db.refresh(db_assignment)
    return db_assignment

def remove_ip_class_from_interface(db: Session, interface_id: int, ip_class_id: int):
    """Remove a atribuição de uma classe IP de uma interface."""
    assignment = db.query(InterfaceIPClassAssignment).filter(
        InterfaceIPClassAssignment.interface_id == interface_id,
        InterfaceIPClassAssignment.ip_class_id == ip_class_id
    ).first()
    if assignment:
        db.delete(assignment)
        db.commit()
    return assignment

def get_ip_classes_by_interface(db: Session, interface_id: int) -> List[IPClass]:
    """Busca todas as classes IP atribuídas a uma interface."""
    interface = db.query(RouterInterface).filter(RouterInterface.id == interface_id).first()
    if interface:
        return interface.ip_classes
    return []

def get_interfaces_by_ip_class(db: Session, class_id: int) -> List[RouterInterface]:
    """Busca todas as interfaces que têm uma classe IP específica atribuída."""
    ip_class = db.query(IPClass).filter(IPClass.id == class_id).first()
    if ip_class:
        return ip_class.interfaces
    return []

def get_used_ips_by_ip_class(db: Session, ip_class_id: int) -> List[str]:
    """Busca todos os IPs já atribuídos em contratos para uma classe IP específica."""
    from app.models.models import ServicoContratado

    # Busca contratos que têm IP atribuído nesta classe IP
    used_ips = db.query(ServicoContratado.assigned_ip)\
        .filter(
            ServicoContratado.ip_class_id == ip_class_id,
            ServicoContratado.assigned_ip.isnot(None),
            ServicoContratado.assigned_ip != ''
        )\
        .all()

    # Retorna lista de IPs (desempacota tuplas)
    return [ip[0] for ip in used_ips]

# CRUD para IPPool
def get_ip_pool(db: Session, pool_id: int) -> Optional[IPPool]:
    """Busca um pool de IP específico."""
    return db.query(IPPool).filter(IPPool.id == pool_id).first()

def get_ip_pools_by_empresa(db: Session, empresa_id: int) -> List[IPPool]:
    """Busca todos os pools de IP de uma empresa."""
    return db.query(IPPool).filter(IPPool.empresa_id == empresa_id).all()

def create_ip_pool(db: Session, pool: IPPoolCreate, empresa_id: int) -> IPPool:
    """Cria um novo pool de IP."""
    db_pool = IPPool(
        empresa_id=empresa_id,
        router_id=pool.router_id,
        nome=pool.nome,
        ranges=pool.ranges,
        comentario=pool.comentario
    )
    db.add(db_pool)
    db.commit()
    db.refresh(db_pool)
    return db_pool

def update_ip_pool(db: Session, db_pool: IPPool, pool_in: IPPoolUpdate) -> IPPool:
    """Atualiza um pool de IP."""
    update_data = pool_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_pool, field, value)

    db.add(db_pool)
    db.commit()
    db.refresh(db_pool)
    return db_pool

def delete_ip_pool(db: Session, pool_id: int) -> bool:
    """Remove um pool de IP."""
    pool = db.query(IPPool).filter(IPPool.id == pool_id).first()
    if pool:
        db.delete(pool)
        db.commit()
        return True
    return False

# CRUD para PPPProfile
def get_ppp_profile(db: Session, profile_id: int) -> Optional[PPPProfile]:
    """Busca um perfil PPP específico."""
    return db.query(PPPProfile).filter(PPPProfile.id == profile_id).first()

def get_ppp_profiles_by_empresa(db: Session, empresa_id: int) -> List[PPPProfile]:
    """Busca todos os perfis PPP de uma empresa."""
    return db.query(PPPProfile).filter(PPPProfile.empresa_id == empresa_id).all()

def create_ppp_profile(db: Session, profile: PPPProfileCreate, empresa_id: int) -> PPPProfile:
    """Cria um novo perfil PPP."""
    db_profile = PPPProfile(
        empresa_id=empresa_id,
        router_id=profile.router_id,
        nome=profile.nome,
        local_address=profile.local_address,
        remote_address_pool_id=profile.remote_address_pool_id,
        rate_limit=profile.rate_limit,
        session_timeout=profile.session_timeout,
        idle_timeout=profile.idle_timeout,
        only_one_session=profile.only_one_session,
        comentario=profile.comentario
    )
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile

def update_ppp_profile(db: Session, db_profile: PPPProfile, profile_in: PPPProfileUpdate) -> PPPProfile:
    """Atualiza um perfil PPP."""
    update_data = profile_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_profile, field, value)

    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile

def delete_ppp_profile(db: Session, profile_id: int) -> bool:
    """Remove um perfil PPP."""
    profile = db.query(PPPProfile).filter(PPPProfile.id == profile_id).first()
    if profile:
        db.delete(profile)
        db.commit()
        return True
    return False

# CRUD para PPPoEServer
def get_pppoe_server(db: Session, server_id: int) -> Optional[PPPoEServer]:
    """Busca um servidor PPPoE específico."""
    return db.query(PPPoEServer).filter(PPPoEServer.id == server_id).first()

def get_pppoe_servers_by_empresa(db: Session, empresa_id: int) -> List[PPPoEServer]:
    """Busca todos os servidores PPPoE de uma empresa."""
    return db.query(PPPoEServer).filter(PPPoEServer.empresa_id == empresa_id).all()

def create_pppoe_server(db: Session, server: PPPoEServerCreate, empresa_id: int) -> PPPoEServer:
    """Cria um novo servidor PPPoE."""
    db_server = PPPoEServer(
        empresa_id=empresa_id,
        router_id=server.router_id,
        service_name=server.service_name,
        interface_id=server.interface_id,
        default_profile_id=server.default_profile_id,
        max_sessions=server.max_sessions,
        max_sessions_per_host=server.max_sessions_per_host,
        authentication=server.authentication,
        keepalive_timeout=server.keepalive_timeout,
        comentario=server.comentario
    )
    db.add(db_server)
    db.commit()
    db.refresh(db_server)
    return db_server

def update_pppoe_server(db: Session, db_server: PPPoEServer, server_in: PPPoEServerUpdate) -> PPPoEServer:
    """Atualiza um servidor PPPoE."""
    update_data = server_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_server, field, value)

    db.add(db_server)
    db.commit()
    db.refresh(db_server)
    return db_server

def delete_pppoe_server(db: Session, server_id: int) -> bool:
    """Remove um servidor PPPoE."""
    server = db.query(PPPoEServer).filter(PPPoEServer.id == server_id).first()
    if server:
        db.delete(server)
        db.commit()
        return True
    return False

# CRUD para DHCPServer
def get_dhcp_server(db: Session, server_id: int) -> Optional[DHCPServer]:
    """Busca um servidor DHCP específico."""
    return db.query(DHCPServer).filter(DHCPServer.id == server_id).first()

def get_dhcp_servers_by_empresa(db: Session, empresa_id: int) -> List[DHCPServer]:
    """Busca todos os servidores DHCP de uma empresa."""
    return db.query(DHCPServer).filter(DHCPServer.empresa_id == empresa_id).all()

def create_dhcp_server(db: Session, server: DHCPServerCreate, empresa_id: int) -> DHCPServer:
    """Cria um novo servidor DHCP."""
    db_server = DHCPServer(
        empresa_id=empresa_id,
        router_id=server.router_id,
        nome=server.nome,
        interface_id=server.interface_id,
        address_pool_id=server.address_pool_id,
        lease_time=server.lease_time,
        bootp_support=server.bootp_support,
        comentario=server.comentario
    )
    db.add(db_server)
    db.commit()
    db.refresh(db_server)
    return db_server

def update_dhcp_server(db: Session, db_server: DHCPServer, server_in: DHCPServerUpdate) -> DHCPServer:
    """Atualiza um servidor DHCP."""
    update_data = server_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_server, field, value)

    db.add(db_server)
    db.commit()
    db.refresh(db_server)
    return db_server

def delete_dhcp_server(db: Session, server_id: int) -> bool:
    """Remove um servidor DHCP."""
    server = db.query(DHCPServer).filter(DHCPServer.id == server_id).first()
    if server:
        db.delete(server)
        db.commit()
        return True
    return False

# CRUD para DHCPNetwork
def get_dhcp_network(db: Session, network_id: int) -> Optional[DHCPNetwork]:
    """Busca uma rede DHCP específica."""
    return db.query(DHCPNetwork).filter(DHCPNetwork.id == network_id).first()

def get_dhcp_networks_by_empresa(db: Session, empresa_id: int) -> List[DHCPNetwork]:
    """Busca todas as redes DHCP de uma empresa."""
    return db.query(DHCPNetwork).filter(DHCPNetwork.empresa_id == empresa_id).all()

def create_dhcp_network(db: Session, network: DHCPNetworkCreate, empresa_id: int) -> DHCPNetwork:
    """Cria uma nova rede DHCP."""
    db_network = DHCPNetwork(
        empresa_id=empresa_id,
        router_id=network.router_id,
        dhcp_server_id=network.dhcp_server_id,
        address=network.address,
        gateway=network.gateway,
        dns_servers=network.dns_servers,
        domain=network.domain,
        wins_servers=network.wins_servers,
        ntp_servers=network.ntp_servers,
        caps_manager=network.caps_manager,
        comentario=network.comentario
    )
    db.add(db_network)
    db.commit()
    db.refresh(db_network)
    return db_network

def update_dhcp_network(db: Session, db_network: DHCPNetwork, network_in: DHCPNetworkUpdate) -> DHCPNetwork:
    """Atualiza uma rede DHCP."""
    update_data = network_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_network, field, value)

    db.add(db_network)
    db.commit()
    db.refresh(db_network)
    return db_network

def delete_dhcp_network(db: Session, network_id: int) -> bool:
    """Remove uma rede DHCP."""
    network = db.query(DHCPNetwork).filter(DHCPNetwork.id == network_id).first()
    if network:
        db.delete(network)
        db.commit()
        return True
    return False