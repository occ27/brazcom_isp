from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import crud, models
from app.api import deps
from app.schemas.router import RouterCreate, RouterUpdate, RouterResponse

router = APIRouter(prefix="/routers", tags=["Routers"])

@router.post("/", response_model=RouterResponse)
def create_router(
    *,
    db: Session = Depends(deps.get_db),
    router_in: RouterCreate,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("router_manage"))
):
    """
    Criar um novo roteador para a empresa do usuário atual.
    """
    empresa_id = current_user.active_empresa_id or 2  # Usar 2 como fallback
    return crud.crud_router.create_router(db=db, router=router_in, empresa_id=empresa_id)

@router.get("/", response_model=List[RouterResponse])
def read_routers(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("router_view"))
):
    """
    Buscar todos os roteadores da empresa do usuário atual.
    """
    empresa_id = current_user.active_empresa_id or 2  # Usar 2 como fallback
    routers = crud.crud_router.get_routers_by_provider(
        db=db, empresa_id=empresa_id, skip=skip, limit=limit
    )
    return routers

@router.get("/{router_id}", response_model=RouterResponse)
def read_router(
    *,
    db: Session = Depends(deps.get_db),
    router_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("router_view"))
):
    """
    Buscar um roteador específico da empresa do usuário atual.
    """
    router = crud.crud_router.get_router(db=db, router_id=router_id, empresa_id=current_user.active_empresa_id)
    if not router:
        raise HTTPException(status_code=404, detail="Roteador não encontrado")
    return router

@router.put("/{router_id}", response_model=RouterResponse)
def update_router(
    *,
    db: Session = Depends(deps.get_db),
    router_id: int,
    router_in: RouterUpdate,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("router_manage"))
):
    """
    Atualizar um roteador da empresa do usuário atual.
    """
    router = crud.crud_router.get_router(db=db, router_id=router_id, empresa_id=current_user.active_empresa_id)
    if not router:
        raise HTTPException(status_code=404, detail="Roteador não encontrado")
    router = crud.crud_router.update_router(db=db, db_router=router, router_in=router_in)
    return router

@router.delete("/{router_id}", response_model=RouterResponse)
def delete_router(
    *,
    db: Session = Depends(deps.get_db),
    router_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("router_manage"))
):
    """
    Deletar um roteador da empresa do usuário atual.
    """
    router = crud.crud_router.get_router(db=db, router_id=router_id, empresa_id=current_user.active_empresa_id)
    if not router:
        raise HTTPException(status_code=404, detail="Roteador não encontrado")
    router = crud.crud_router.remove_router(db=db, db_router=router)
    return router