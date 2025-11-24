from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.network import Router
from app.schemas.router import RouterCreate, RouterUpdate
from app.core.security import encrypt_password

def get_router(db: Session, router_id: int, empresa_id: int) -> Optional[Router]:
    """Busca um roteador específico de uma empresa."""
    return db.query(Router).filter(Router.id == router_id, Router.empresa_id == empresa_id).first()

def get_routers_by_provider(db: Session, empresa_id: int, skip: int = 0, limit: int = 100) -> List[Router]:
    """Busca todos os roteadores de uma empresa."""
    return db.query(Router).filter(Router.empresa_id == empresa_id).offset(skip).limit(limit).all()

def create_router(db: Session, router: RouterCreate, empresa_id: int) -> Router:
    """Cria um novo roteador para uma empresa."""
    encrypted_pass = encrypt_password(router.password)
    db_router = Router(
        name=router.name,
        ip_address=str(router.ip_address),
        username=router.username,
        encrypted_password=encrypted_pass,
        port=router.port,
        is_active=router.is_active,
        empresa_id=empresa_id
    )
    db.add(db_router)
    db.commit()
    db.refresh(db_router)
    return db_router

def update_router(db: Session, db_router: Router, router_in: RouterUpdate) -> Router:
    """Atualiza as informações de um roteador."""
    update_data = router_in.dict(exclude_unset=True)

    if "password" in update_data and update_data["password"]:
        update_data["encrypted_password"] = encrypt_password(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(db_router, field, value)

    db.add(db_router)
    db.commit()
    db.refresh(db_router)
    return db_router

def remove_router(db: Session, db_router: Router):
    """Remove um roteador."""
    db.delete(db_router)
    db.commit()
    return db_router