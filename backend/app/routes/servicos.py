from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routes.auth import get_current_active_user
from app.api import deps
from app.models.models import Usuario
from app.crud import crud_servico, crud_empresa
from app.schemas.servico import ServicoCreate, ServicoResponse, ServicoUpdate

router = APIRouter(prefix="/servicos", tags=["Servicos"])


@router.get("/empresa/{empresa_id}", response_model=List[ServicoResponse])
def list_servicos(empresa_id: int, q: str = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user), response: Response = None):
    # Check permission
    db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    user_empresas_ids = [e.empresa_id for e in current_user.empresas]
    if empresa_id not in user_empresas_ids and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Usuário não tem permissão")
    # compute total for UX and set header
    total = crud_servico.count_servicos_by_empresa(db, empresa_id=empresa_id, qstr=q)
    if response is not None:
        response.headers['X-Total-Count'] = str(total)
    servicos = crud_servico.get_servicos_by_empresa(db, empresa_id=empresa_id, qstr=q, skip=skip, limit=limit)
    return servicos


@router.post("/", response_model=ServicoResponse, status_code=status.HTTP_201_CREATED)
def create_servico(servico: ServicoCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    # If empresa_id provided on body, validate permission
    if servico.empresa_id:
        user_empresas_ids = [e.empresa_id for e in current_user.empresas]
        if servico.empresa_id not in user_empresas_ids and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Usuário não tem permissão para criar serviço para esta empresa")

    # Backend permission: require services_manage to create services
    deps.permission_checker('services_manage')(db=db, current_user=current_user)

    # Pass the Pydantic object to the CRUD layer; if servico.empresa_id is provided,
    # create_servico will persist it (permission already checked above).
    s = crud_servico.create_servico(db, servico_in=servico, empresa_id=getattr(servico, 'empresa_id', None))
    return s


@router.get("/{servico_id}", response_model=ServicoResponse)
def get_servico(servico_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    s = crud_servico.get_servico(db, servico_id=servico_id)
    if not s:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    # If service belongs to an empresa, check permission
    if s.empresa_id:
        user_empresas_ids = [e.empresa_id for e in current_user.empresas]
        if s.empresa_id not in user_empresas_ids and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Usuário não tem permissão")
    return s


@router.put("/{servico_id}", response_model=ServicoResponse)
def update_servico(servico_id: int, servico_in: ServicoUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    s = crud_servico.get_servico(db, servico_id=servico_id)
    if not s:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    if s.empresa_id:
        user_empresas_ids = [e.empresa_id for e in current_user.empresas]
        if s.empresa_id not in user_empresas_ids and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Usuário não tem permissão")
    # Backend permission: require services_manage to update services
    deps.permission_checker('services_manage')(db=db, current_user=current_user)
    updated = crud_servico.update_servico(db, db_obj=s, obj_in=servico_in)
    return updated


@router.delete("/{servico_id}")
def delete_servico(servico_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    s = crud_servico.get_servico(db, servico_id=servico_id)
    if not s:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    if s.empresa_id:
        user_empresas_ids = [e.empresa_id for e in current_user.empresas]
        if s.empresa_id not in user_empresas_ids and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Usuário não tem permissão")
    # Backend permission: require services_manage to delete services
    deps.permission_checker('services_manage')(db=db, current_user=current_user)
    crud_servico.delete_servico(db, db_obj=s)
    return {"detail": "Serviço removido"}
