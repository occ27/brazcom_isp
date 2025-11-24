from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.radius import RadiusServer, RadiusUser, RadiusSession
from app.schemas.radius import (
    RadiusServerCreate, RadiusServerUpdate,
    RadiusUserCreate, RadiusUserUpdate,
    RadiusSessionCreate, RadiusSessionUpdate
)
from app.core.security import encrypt_password

# RadiusServer CRUD
def get_radius_server(db: Session, server_id: int, empresa_id: int) -> Optional[RadiusServer]:
    """Busca um servidor RADIUS específico de uma empresa."""
    return db.query(RadiusServer).filter(
        RadiusServer.id == server_id,
        RadiusServer.empresa_id == empresa_id
    ).first()

def get_radius_servers_by_empresa(db: Session, empresa_id: int, skip: int = 0, limit: int = 100) -> List[RadiusServer]:
    """Busca todos os servidores RADIUS de uma empresa."""
    return db.query(RadiusServer).filter(RadiusServer.empresa_id == empresa_id).offset(skip).limit(limit).all()

def create_radius_server(db: Session, server: RadiusServerCreate, empresa_id: int) -> RadiusServer:
    """Cria um novo servidor RADIUS para uma empresa."""
    db_server = RadiusServer(
        name=server.name,
        ip_address=str(server.ip_address),
        port=server.port,
        secret=encrypt_password(server.secret),  # Criptografa o secret
        is_active=server.is_active,
        empresa_id=empresa_id
    )
    db.add(db_server)
    db.commit()
    db.refresh(db_server)
    return db_server

def update_radius_server(db: Session, db_server: RadiusServer, server_in: RadiusServerUpdate) -> RadiusServer:
    """Atualiza as informações de um servidor RADIUS."""
    update_data = server_in.dict(exclude_unset=True)

    if "secret" in update_data and update_data["secret"]:
        update_data["secret"] = encrypt_password(update_data["secret"])

    if "ip_address" in update_data:
        update_data["ip_address"] = str(update_data["ip_address"])

    for field, value in update_data.items():
        setattr(db_server, field, value)

    db.add(db_server)
    db.commit()
    db.refresh(db_server)
    return db_server

def remove_radius_server(db: Session, db_server: RadiusServer):
    """Remove um servidor RADIUS."""
    db.delete(db_server)
    db.commit()
    return db_server

# RadiusUser CRUD
def get_radius_user(db: Session, user_id: int, empresa_id: int) -> Optional[RadiusUser]:
    """Busca um usuário RADIUS específico de uma empresa."""
    return db.query(RadiusUser).filter(
        RadiusUser.id == user_id,
        RadiusUser.empresa_id == empresa_id
    ).first()

def get_radius_user_by_username(db: Session, username: str, empresa_id: int) -> Optional[RadiusUser]:
    """Busca um usuário RADIUS por username e empresa."""
    return db.query(RadiusUser).filter(
        RadiusUser.username == username,
        RadiusUser.empresa_id == empresa_id
    ).first()

def get_radius_users_by_empresa(db: Session, empresa_id: int, skip: int = 0, limit: int = 100) -> List[RadiusUser]:
    """Busca todos os usuários RADIUS de uma empresa."""
    return db.query(RadiusUser).filter(RadiusUser.empresa_id == empresa_id).offset(skip).limit(limit).all()

def create_radius_user(db: Session, user: RadiusUserCreate, empresa_id: int) -> RadiusUser:
    """Cria um novo usuário RADIUS para uma empresa."""
    db_user = RadiusUser(
        username=user.username,
        password=encrypt_password(user.password),  # Criptografa a senha
        ip_address=str(user.ip_address) if user.ip_address else None,
        mac_address=user.mac_address,
        service_type=user.service_type,
        is_active=user.is_active,
        empresa_id=empresa_id,
        cliente_id=user.cliente_id,
        session_timeout=user.session_timeout,
        idle_timeout=user.idle_timeout,
        rate_limit_up=user.rate_limit_up,
        rate_limit_down=user.rate_limit_down
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_radius_user(db: Session, db_user: RadiusUser, user_in: RadiusUserUpdate) -> RadiusUser:
    """Atualiza as informações de um usuário RADIUS."""
    update_data = user_in.dict(exclude_unset=True)

    if "password" in update_data and update_data["password"]:
        update_data["password"] = encrypt_password(update_data["password"])

    if "ip_address" in update_data and update_data["ip_address"]:
        update_data["ip_address"] = str(update_data["ip_address"])

    for field, value in update_data.items():
        setattr(db_user, field, value)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def remove_radius_user(db: Session, db_user: RadiusUser):
    """Remove um usuário RADIUS."""
    db.delete(db_user)
    db.commit()
    return db_user

# RadiusSession CRUD
def get_radius_session(db: Session, session_id: str, empresa_id: int) -> Optional[RadiusSession]:
    """Busca uma sessão RADIUS específica de uma empresa."""
    return db.query(RadiusSession).filter(
        RadiusSession.session_id == session_id,
        RadiusSession.empresa_id == empresa_id
    ).first()

def get_active_sessions_by_empresa(db: Session, empresa_id: int) -> List[RadiusSession]:
    """Busca todas as sessões ativas de uma empresa."""
    return db.query(RadiusSession).filter(
        RadiusSession.empresa_id == empresa_id,
        RadiusSession.end_time.is_(None)
    ).all()

def create_radius_session(db: Session, session: RadiusSessionCreate, empresa_id: int) -> RadiusSession:
    """Cria uma nova sessão RADIUS."""
    db_session = RadiusSession(
        session_id=session.session_id,
        username=session.username,
        ip_address=str(session.ip_address) if session.ip_address else None,
        mac_address=session.mac_address,
        nas_ip=str(session.nas_ip) if session.nas_ip else None,
        nas_port=session.nas_port,
        service_type=session.service_type,
        empresa_id=empresa_id,
        radius_user_id=session.radius_user_id,
        bytes_up=0,
        bytes_down=0
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def update_radius_session(db: Session, db_session: RadiusSession, session_in: RadiusSessionUpdate) -> RadiusSession:
    """Atualiza as informações de uma sessão RADIUS."""
    update_data = session_in.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_session, field, value)

    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def remove_radius_session(db: Session, db_session: RadiusSession):
    """Remove uma sessão RADIUS."""
    db.delete(db_session)
    db.commit()
    return db_session