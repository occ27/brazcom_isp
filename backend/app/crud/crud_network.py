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

def sync_ip_pools(db: Session, router_id: int, empresa_id: int) -> dict:
    """
    Sincroniza pools de IP do router MikroTik com o banco de dados.
    
    Estratégia:
    - Pools existentes no MikroTik: atualiza ou cria no sistema
    - Pools removidos do MikroTik: marca como inativos (não remove)
    - Pools criados manualmente: preserva intactos
    """
    from app.mikrotik.controller import MikrotikController
    from app.core.security import decrypt_password
    from app import crud
    
    # Buscar router
    router = crud.crud_router.get_router(db=db, router_id=router_id, empresa_id=empresa_id)
    if not router:
        raise ValueError("Router não encontrado")
    
    # Conectar ao MikroTik
    try:
        password = decrypt_password(router.senha)
    except Exception:
        password = router.senha
    
    mk = MikrotikController(
        host=router.ip,
        username=router.usuario,
        password=password,
        port=router.porta or 8728
    )
    
    # Buscar pools do MikroTik
    mikrotik_pools = mk.get_dhcp_pools()
    
    # Obter pools atuais do banco para este router
    current_pools = db.query(IPPool).filter(
        IPPool.router_id == router_id,
        IPPool.empresa_id == empresa_id
    ).all()
    
    # Criar dicionário de pools atuais por nome
    current_pools_dict = {pool.nome: pool for pool in current_pools}
    
    created = 0
    updated = 0
    deactivated = 0
    
    # Processar pools do MikroTik
    for mk_pool in mikrotik_pools:
        pool_name = mk_pool.get('name', '').strip()
        pool_ranges = mk_pool.get('ranges', '').strip()
        
        if not pool_name or not pool_ranges:
            continue  # Pular pools inválidos
        
        if pool_name in current_pools_dict:
            # Atualizar pool existente
            db_pool = current_pools_dict[pool_name]
            if db_pool.ranges != pool_ranges:
                db_pool.ranges = pool_ranges
                db_pool.is_active = True  # Reativar se estava inativo
                updated += 1
            elif not db_pool.is_active:
                db_pool.is_active = True
                updated += 1
        else:
            # Criar novo pool
            new_pool = IPPool(
                nome=pool_name,
                ranges=pool_ranges,
                router_id=router_id,
                empresa_id=empresa_id,
                is_active=True
            )
            db.add(new_pool)
            created += 1
    
    # Marcar pools removidos como inativos (exceto pools criados manualmente)
    mikrotik_pool_names = {pool.get('name', '').strip() for pool in mikrotik_pools}
    for db_pool in current_pools:
        if db_pool.nome not in mikrotik_pool_names and db_pool.is_active:
            # Verificar se foi criado manualmente (não sincronizado)
            # Por enquanto, vamos desativar todos que não existem mais no MikroTik
            db_pool.is_active = False
            deactivated += 1
    
    db.commit()
    
    return {
        "created": created,
        "updated": updated,
        "deactivated": deactivated,
        "total_mikrotik": len(mikrotik_pools),
        "total_db": len(current_pools)
    }

def sync_ppp_profiles(db: Session, router_id: int, empresa_id: int) -> dict:
    """
    Sincroniza profiles PPP do router MikroTik com o banco de dados.
    
    Estratégia:
    - Profiles existentes no MikroTik: atualiza ou cria no sistema
    - Profiles removidos do MikroTik: marca como inativos (não remove)
    - Profiles criados manualmente: preserva intactos
    """
    from app.mikrotik.controller import MikrotikController
    from app.core.security import decrypt_password
    from app import crud
    
    # Buscar router
    router = crud.crud_router.get_router(db=db, router_id=router_id, empresa_id=empresa_id)
    if not router:
        raise ValueError("Router não encontrado")
    
    # Conectar ao MikroTik
    try:
        password = decrypt_password(router.senha)
    except Exception:
        password = router.senha
    
    mk = MikrotikController(
        host=router.ip,
        username=router.usuario,
        password=password,
        port=router.porta or 8728
    )
    
    # Buscar profiles do MikroTik
    mikrotik_profiles = mk.get_ppp_profiles()
    
    # Obter profiles atuais do banco para este router
    current_profiles = db.query(PPPProfile).filter(
        PPPProfile.router_id == router_id,
        PPPProfile.empresa_id == empresa_id
    ).all()
    
    # Criar dicionário de profiles atuais por nome
    current_profiles_dict = {profile.nome: profile for profile in current_profiles}
    
    created = 0
    updated = 0
    deactivated = 0
    
    # Processar profiles do MikroTik
    for mk_profile in mikrotik_profiles:
        profile_name = mk_profile.get('name', '').strip()
        local_address = mk_profile.get('local-address', '').strip()
        remote_address = mk_profile.get('remote-address', '').strip()
        rate_limit = mk_profile.get('rate-limit', '').strip()
        comment = mk_profile.get('comment', '').strip()
        
        if not profile_name or not local_address:
            continue  # Pular profiles inválidos
        
        if profile_name in current_profiles_dict:
            # Atualizar profile existente
            db_profile = current_profiles_dict[profile_name]
            needs_update = False
            
            if db_profile.local_address != local_address:
                db_profile.local_address = local_address
                needs_update = True
            
            # Tentar resolver remote_address como referência a pool de IP
            remote_pool_id = None
            if remote_address:
                # Verificar se remote_address é uma referência a pool existente
                remote_pool = db.query(IPPool).filter(
                    IPPool.nome == remote_address,
                    IPPool.empresa_id == empresa_id
                ).first()
                if remote_pool:
                    remote_pool_id = remote_pool.id
            
            if db_profile.remote_address_pool_id != remote_pool_id:
                db_profile.remote_address_pool_id = remote_pool_id
                needs_update = True
            
            if db_profile.rate_limit != rate_limit:
                db_profile.rate_limit = rate_limit
                needs_update = True
                
            if db_profile.comentario != comment:
                db_profile.comentario = comment
                needs_update = True
            
            if needs_update:
                updated += 1
            elif not db_profile.is_active:
                db_profile.is_active = True
                updated += 1
        else:
            # Criar novo profile
            # Tentar resolver remote_address como referência a pool de IP
            remote_pool_id = None
            if remote_address:
                # Verificar se remote_address é uma referência a pool existente
                remote_pool = db.query(IPPool).filter(
                    IPPool.nome == remote_address,
                    IPPool.empresa_id == empresa_id
                ).first()
                if remote_pool:
                    remote_pool_id = remote_pool.id
            
            new_profile = PPPProfile(
                nome=profile_name,
                local_address=local_address,
                remote_address_pool_id=remote_pool_id,
                rate_limit=rate_limit,
                comentario=comment,
                router_id=router_id,
                empresa_id=empresa_id,
                is_active=True
            )
            db.add(new_profile)
            created += 1
    
    # Marcar profiles removidos como inativos (exceto profiles criados manualmente)
    mikrotik_profile_names = {profile.get('name', '').strip() for profile in mikrotik_profiles}
    for db_profile in current_profiles:
        if db_profile.nome not in mikrotik_profile_names and db_profile.is_active:
            # Verificar se foi criado manualmente (não sincronizado)
            # Por enquanto, vamos desativar todos que não existem mais no MikroTik
            db_profile.is_active = False
            deactivated += 1
    
    db.commit()
    
    return {
        "created": created,
        "updated": updated,
        "deactivated": deactivated,
        "total_mikrotik": len(mikrotik_profiles),
        "total_db": len(current_profiles)
    }

def sync_pppoe_servers(db: Session, router_id: int, empresa_id: int) -> dict:
    """
    Sincroniza servidores PPPoE do router MikroTik com o banco de dados.
    
    Estratégia:
    - Servidores existentes no MikroTik: atualiza ou cria no sistema
    - Servidores removidos do MikroTik: marca como inativos (não remove)
    - Servidores criados manualmente: preserva intactos
    """
    from app.mikrotik.controller import MikrotikController
    from app.core.security import decrypt_password
    from app import crud
    
    # Buscar router
    router = crud.crud_router.get_router(db=db, router_id=router_id, empresa_id=empresa_id)
    if not router:
        raise ValueError("Router não encontrado")
    
    # Conectar ao MikroTik
    try:
        password = decrypt_password(router.senha)
    except Exception:
        password = router.senha
    
    mk = MikrotikController(
        host=router.ip,
        username=router.usuario,
        password=password,
        port=router.porta or 8728
    )
    
    # Buscar servidores do MikroTik
    mikrotik_servers = mk.get_pppoe_servers()
    
    # DEBUG: Log dos servidores retornados pelo MikroTik
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[DEBUG] Servidores PPPoE retornados pelo MikroTik: {mikrotik_servers}")
    for i, server in enumerate(mikrotik_servers):
        logger.info(f"[DEBUG] Servidor {i+1}: {server}")
    
    # Obter servidores atuais do banco para este router
    current_servers = db.query(PPPoEServer).filter(
        PPPoEServer.router_id == router_id,
        PPPoEServer.empresa_id == empresa_id
    ).all()
    
    # Criar dicionário de servidores atuais por service_name
    current_servers_dict = {server.service_name: server for server in current_servers}
    
    created = 0
    updated = 0
    deactivated = 0
    
    # Processar servidores do MikroTik
    for mk_server in mikrotik_servers:
        service_name = mk_server.get('service-name', '').strip()  # Campo correto
        interface_name = mk_server.get('interface', '').strip()
        default_profile_name = mk_server.get('default-profile', '').strip()
        
        # Processar max_sessions (pode ser string 'unlimited' ou número)
        max_sessions_raw = mk_server.get('max-sessions', 'unlimited')
        if isinstance(max_sessions_raw, str):
            max_sessions = None if max_sessions_raw == 'unlimited' else int(max_sessions_raw) if max_sessions_raw.isdigit() else None
        else:
            max_sessions = max_sessions_raw if max_sessions_raw != 'unlimited' else None
        
        # Processar max_sessions_per_host (pode ser booleano ou string)
        one_session_raw = mk_server.get('one-session-per-host')
        if isinstance(one_session_raw, bool):
            max_sessions_per_host = 1 if one_session_raw else None
        elif isinstance(one_session_raw, str):
            max_sessions_per_host = 1 if one_session_raw.lower() == 'true' else None
        else:
            max_sessions_per_host = None
            
        authentication = mk_server.get('authentication', 'pap,chap,mschap1,mschap2')
        
        # Processar keepalive_timeout (pode ser int ou string)
        keepalive_raw = mk_server.get('keepalive-timeout')
        if isinstance(keepalive_raw, int):
            keepalive_timeout = keepalive_raw
        elif isinstance(keepalive_raw, str) and keepalive_raw.isdigit():
            keepalive_timeout = int(keepalive_raw)
        else:
            keepalive_timeout = None
            
        # Processar disabled (pode ser booleano ou string)
        disabled_raw = mk_server.get('disabled', False)
        if isinstance(disabled_raw, bool):
            disabled = disabled_raw
        elif isinstance(disabled_raw, str):
            disabled = disabled_raw.lower() == 'true'
        else:
            disabled = False
        
        logger.info(f"[DEBUG] Processando servidor: service_name='{service_name}', interface='{interface_name}', disabled={disabled}")
        
        # Pular servidores desabilitados
        if disabled:
            logger.info(f"[DEBUG] Pulando servidor desabilitado: {service_name}")
            continue
        
        if not service_name or not interface_name:
            logger.warning(f"[DEBUG] Servidor inválido - service_name ou interface vazios: {mk_server}")
            continue  # Pular servidores inválidos
        
        # Buscar interface no banco de dados
        interface_obj = db.query(RouterInterface).filter(
            RouterInterface.router_id == router_id,
            RouterInterface.nome == interface_name
        ).first()
        
        if not interface_obj:
            continue  # Interface não encontrada, pular servidor
        
        # Buscar perfil padrão no banco de dados
        profile_obj = None
        if default_profile_name:
            profile_obj = db.query(PPPProfile).filter(
                PPPProfile.router_id == router_id,
                PPPProfile.empresa_id == empresa_id,
                PPPProfile.nome == default_profile_name
            ).first()
        
        if service_name in current_servers_dict:
            # Atualizar servidor existente
            db_server = current_servers_dict[service_name]
            needs_update = False
            
            if db_server.interface_id != interface_obj.id:
                db_server.interface_id = interface_obj.id
                needs_update = True
            
            if profile_obj and db_server.default_profile_id != profile_obj.id:
                db_server.default_profile_id = profile_obj.id
                needs_update = True
            
            if db_server.max_sessions != max_sessions:
                db_server.max_sessions = max_sessions
                needs_update = True
                
            if db_server.max_sessions_per_host != max_sessions_per_host:
                db_server.max_sessions_per_host = max_sessions_per_host
                needs_update = True
                
            if db_server.authentication != authentication:
                db_server.authentication = authentication
                needs_update = True
                
            if db_server.keepalive_timeout != keepalive_timeout:
                db_server.keepalive_timeout = keepalive_timeout
                needs_update = True
                
            if db_server.comentario != comment:
                db_server.comentario = comment
                needs_update = True
            
            if needs_update:
                updated += 1
                logger.info(f"[DEBUG] Servidor atualizado: {service_name}")
            elif not db_server.is_active:
                db_server.is_active = True
                updated += 1
                logger.info(f"[DEBUG] Servidor reativado: {service_name}")
            else:
                logger.info(f"[DEBUG] Servidor já existe e está atualizado: {service_name}")
        else:
            # Criar novo servidor
            new_server = PPPoEServer(
                service_name=service_name,
                interface_id=interface_obj.id,
                default_profile_id=profile_obj.id if profile_obj else None,
                max_sessions=max_sessions,
                max_sessions_per_host=max_sessions_per_host,
                authentication=authentication,
                keepalive_timeout=keepalive_timeout,
                comentario=f"Servidor PPPoE sincronizado automaticamente",
                router_id=router_id,
                empresa_id=empresa_id,
                is_active=True
            )
            db.add(new_server)
            created += 1
            logger.info(f"[DEBUG] Novo servidor criado: {service_name}")
    
    # Marcar servidores removidos como inativos (exceto servidores criados manualmente)
    mikrotik_service_names = {server.get('service-name', '').strip() for server in mikrotik_servers}
    for db_server in current_servers:
        if db_server.service_name not in mikrotik_service_names and db_server.is_active:
            # Verificar se foi criado manualmente (não sincronizado)
            # Por enquanto, vamos desativar todos que não existem mais no MikroTik
            db_server.is_active = False
            deactivated += 1
    
    db.commit()
    
    return {
        "created": created,
        "updated": updated,
        "deactivated": deactivated,
        "total_mikrotik": len(mikrotik_servers),
        "total_db": len(current_servers)
    }

# CRUD para PPPProfile
def get_ppp_profile(db: Session, profile_id: int) -> Optional[PPPProfile]:
    """Busca um perfil PPP específico."""
    return db.query(PPPProfile).options(
        joinedload(PPPProfile.remote_address_pool),
        joinedload(PPPProfile.router),
        joinedload(PPPProfile.empresa)
    ).filter(PPPProfile.id == profile_id).first()

def get_ppp_profiles_by_empresa(db: Session, empresa_id: int) -> List[PPPProfile]:
    """Busca todos os perfis PPP de uma empresa."""
    return db.query(PPPProfile).options(
        joinedload(PPPProfile.remote_address_pool),
        joinedload(PPPProfile.router),
        joinedload(PPPProfile.empresa)
    ).filter(PPPProfile.empresa_id == empresa_id).all()

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
    return db.query(PPPoEServer).options(
        joinedload(PPPoEServer.interface),
        joinedload(PPPoEServer.default_profile),
        joinedload(PPPoEServer.router),
        joinedload(PPPoEServer.empresa)
    ).filter(PPPoEServer.id == server_id).first()

def get_pppoe_servers_by_empresa(db: Session, empresa_id: int) -> List[PPPoEServer]:
    """Busca todos os servidores PPPoE de uma empresa."""
    return db.query(PPPoEServer).options(
        joinedload(PPPoEServer.interface),
        joinedload(PPPoEServer.default_profile),
        joinedload(PPPoEServer.router),
        joinedload(PPPoEServer.empresa)
    ).filter(PPPoEServer.empresa_id == empresa_id).all()

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