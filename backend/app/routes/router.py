from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import crud, models
from app.core.database import get_db
from app.core.radius_db import get_radius_db
from app.routes.auth import get_current_active_user
from app.api.deps import permission_checker
from app.schemas.router import RouterCreate, RouterUpdate, RouterResponse

router_api = APIRouter(prefix="/routers", tags=["Routers"])

@router_api.post("/", response_model=RouterResponse)
def create_router(
    *,
    db: Session = Depends(get_db),
    radius_db: Session = Depends(get_radius_db),
    router_in: RouterCreate,
    current_user: models.Usuario = Depends(get_current_active_user),
    _: bool = Depends(permission_checker("router_manage"))
):
    """
    Criar um novo roteador para a empresa do usuário atual.
    """
    empresa_id = current_user.active_empresa_id or 2  # Usar 2 como fallback
    return crud.crud_router.create_router(
        db=db, 
        router=router_in, 
        empresa_id=empresa_id,
        radius_db=radius_db
    )

@router_api.get("/", response_model=List[RouterResponse])
def read_routers(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.Usuario = Depends(get_current_active_user),
    _: bool = Depends(permission_checker("router_view"))
):
    """
    Buscar todos os roteadores da empresa do usuário atual.
    """
    empresa_id = current_user.active_empresa_id or 2  # Usar 2 como fallback
    routers = crud.crud_router.get_routers_by_provider(
        db=db, empresa_id=empresa_id, skip=skip, limit=limit
    )
    return routers

@router_api.get("/{router_id}", response_model=RouterResponse)
def read_router(
    *,
    db: Session = Depends(get_db),
    router_id: int,
    current_user: models.Usuario = Depends(get_current_active_user),
    _: bool = Depends(permission_checker("router_view"))
):
    """
    Buscar um roteador específico da empresa do usuário atual.
    """
    router = crud.crud_router.get_router(db=db, router_id=router_id, empresa_id=current_user.active_empresa_id)
    if not router:
        raise HTTPException(status_code=404, detail="Roteador não encontrado")
    return router

@router_api.put("/{router_id}", response_model=RouterResponse)
def update_router(
    *,
    db: Session = Depends(get_db),
    radius_db: Session = Depends(get_radius_db),
    router_id: int,
    router_in: RouterUpdate,
    current_user: models.Usuario = Depends(get_current_active_user),
    _: bool = Depends(permission_checker("router_manage"))
):
    """
    Atualizar um roteador da empresa do usuário atual.
    """
    router = crud.crud_router.get_router(db=db, router_id=router_id, empresa_id=current_user.active_empresa_id)
    if not router:
        raise HTTPException(status_code=404, detail="Roteador não encontrado")
    router = crud.crud_router.update_router(
        db=db, 
        db_router=router, 
        router_in=router_in,
        radius_db=radius_db
    )
    return router

@router_api.delete("/{router_id}", response_model=RouterResponse)
def delete_router(
    *,
    db: Session = Depends(get_db),
    radius_db: Session = Depends(get_radius_db),
    router_id: int,
    current_user: models.Usuario = Depends(get_current_active_user),
    _: bool = Depends(permission_checker("router_manage"))
):
    """
    Deletar um roteador da empresa do usuário atual.
    """
    router = crud.crud_router.get_router(db=db, router_id=router_id, empresa_id=current_user.active_empresa_id)
    if not router:
        raise HTTPException(status_code=404, detail="Roteador não encontrado")
    router = crud.crud_router.remove_router(
        db=db, 
        db_router=router,
        radius_db=radius_db
    )
    return router

@router_api.post("/{router_id}/setup-suspension/")
def setup_router_suspension(
    *,
    db: Session = Depends(get_db),
    router_id: int,
    current_user: models.Usuario = Depends(get_current_active_user),
    _: bool = Depends(permission_checker("router_manage"))
):
    """
    Configura automaticamente as regras de suspensão (Proxy, NAT, Firewall) no roteador.
    """
    # Buscar roteador e empresa
    router_db = crud.crud_router.get_router(db=db, router_id=router_id, empresa_id=current_user.active_empresa_id)
    if not router_db:
        raise HTTPException(status_code=404, detail="Roteador não encontrado")
    
    empresa = db.query(models.Empresa).filter(models.Empresa.id == current_user.active_empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # URL de aviso (usa padrão se não houver personalizada)
    # Importante: A RB precisa conseguir chegar nessa URL.
    suspension_url = empresa.suspension_url or f"http://brazcom.com.br/aviso/{empresa.id}"

    from app.mikrotik.controller import MikrotikController
    from app.core.security import decrypt_password
    
    try:
        try:
            password = decrypt_password(router_db.senha)
        except Exception:
            password = router_db.senha

        mk = MikrotikController(
            host=router_db.ip,
            username=router_db.usuario,
            password=password,
            port=router_db.porta or 8728
        )
        
        results = mk.setup_full_suspension_system(suspension_url)
        return {"success": True, "details": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao configurar roteador: {str(e)}")