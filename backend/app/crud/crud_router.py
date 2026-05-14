from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.network import Router, MetodoAutenticacaoRouter
from app.schemas.router import RouterCreate, RouterUpdate
from app.core.security import encrypt_password
from app.services.radius_sync_service import RadiusSyncService

def get_router(db: Session, router_id: int, empresa_id: int) -> Optional[Router]:
    """Busca um roteador específico de uma empresa."""
    return db.query(Router).filter(Router.id == router_id, Router.empresa_id == empresa_id).first()

def get_routers_by_provider(db: Session, empresa_id: int, skip: int = 0, limit: int = 100) -> List[Router]:
    """Busca todos os roteadores de uma empresa."""
    return db.query(Router).filter(Router.empresa_id == empresa_id).offset(skip).limit(limit).all()

def create_router(db: Session, router: RouterCreate, empresa_id: int, radius_db: Optional[Session] = None) -> Router:
    """Cria um novo roteador para uma empresa e sincroniza com RADIUS se necessário."""
    encrypted_pass = encrypt_password(router.senha)
    db_router = Router(
        nome=router.nome,
        ip=router.ip,
        usuario=router.usuario,
        senha=encrypted_pass,
        tipo=router.tipo,
        porta=router.porta,
        is_active=router.is_active,
        metodo_autenticacao_padrao=router.metodo_autenticacao_padrao,
        radius_secret=router.radius_secret,
        empresa_id=empresa_id
    )
    db.add(db_router)
    db.commit()
    db.refresh(db_router)

    # Sincronização com RADIUS (Tabela NAS)
    if radius_db and db_router.metodo_autenticacao_padrao == MetodoAutenticacaoRouter.RADIUS and db_router.radius_secret:
        radius_service = RadiusSyncService(radius_db)
        radius_service.create_nas_client(
            nasname=db_router.ip,
            secret=db_router.radius_secret,
            shortname=db_router.nome,
            description=f"Router ID {db_router.id} - {db_router.nome}"
        )

    return db_router

def update_router(db: Session, db_router: Router, router_in: RouterUpdate, radius_db: Optional[Session] = None) -> Router:
    """Atualiza as informações de um roteador e sincroniza com RADIUS."""
    old_ip = db_router.ip
    update_data = router_in.dict(exclude_unset=True)

    # Remover senha do update_data se ela for vazia ou None
    if "senha" in update_data:
        if not update_data["senha"] or update_data["senha"].strip() == "":
            del update_data["senha"]
        else:
            update_data["senha"] = encrypt_password(update_data["senha"])

    for field, value in update_data.items():
        setattr(db_router, field, value)

    db.add(db_router)
    db.commit()
    db.refresh(db_router)

    # Sincronização com RADIUS
    if radius_db and db_router.metodo_autenticacao_padrao == MetodoAutenticacaoRouter.RADIUS:
        radius_service = RadiusSyncService(radius_db)
        nas = radius_service.get_nas_client_by_ip(old_ip)
        if nas:
            radius_service.update_nas_client(
                nas_id=nas["id"],
                nasname=db_router.ip,
                secret=db_router.radius_secret,
                shortname=db_router.nome
            )
        else:
            radius_service.create_nas_client(
                nasname=db_router.ip,
                secret=db_router.radius_secret,
                shortname=db_router.nome
            )

    return db_router

def remove_router(db: Session, db_router: Router, radius_db: Optional[Session] = None):
    """Remove um roteador e limpa do RADIUS."""
    ip_to_remove = db_router.ip
    db.delete(db_router)
    db.commit()

    if radius_db:
        radius_service = RadiusSyncService(radius_db)
        nas = radius_service.get_nas_client_by_ip(ip_to_remove)
        if nas:
            radius_service.delete_nas_client(nas["id"])
            
    return db_router