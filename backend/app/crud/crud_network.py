from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app.models.network import (
    RouterInterface, InterfaceIPAddress, IPClass, InterfaceIPClassAssignment
)
from app.schemas.network import (
    RouterInterfaceCreate, RouterInterfaceUpdate,
    InterfaceIPAddressCreate, InterfaceIPAddressUpdate,
    IPClassCreate, IPClassUpdate,
    InterfaceIPClassAssignmentCreate
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