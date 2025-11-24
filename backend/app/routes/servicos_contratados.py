from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routes.auth import get_current_active_user
from app.models.models import Usuario
from app.schemas import servico_contratado as sc_schema
from app.crud import crud_servico_contratado, crud_empresa

router = APIRouter(prefix="/servicos-contratados", tags=["ServicosContratados"])


@router.get("/", response_model=List[sc_schema.ServicoContratadoResponse])
def list_servicos_contratados(empresa_id: int = None, q: str = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user), response: Response = None):
    # If empresa_id provided, check permission
    if empresa_id is not None:
        db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
        if not db_empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        user_empresas_ids = [e.empresa_id for e in current_user.empresas]
        if empresa_id not in user_empresas_ids and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Usuário não tem permissão")
    # compute total for UX and set header
    total = crud_servico_contratado.count_servicos_contratados_by_empresa(db, empresa_id=empresa_id, qstr=q)
    if response is not None:
        response.headers['X-Total-Count'] = str(total)
    items = crud_servico_contratado.get_servicos_contratados_by_empresa(db, empresa_id=empresa_id, qstr=q, skip=skip, limit=limit)
    return items


@router.get("/{contrato_id}", response_model=sc_schema.ServicoContratadoResponse)
def get_contrato(contrato_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    c = crud_servico_contratado.get_servico_contratado(db, contrato_id=contrato_id)
    if not c:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    # If contrato belongs to an empresa, check permission
    if c.empresa_id:
        user_empresas_ids = [e.empresa_id for e in current_user.empresas]
        if c.empresa_id not in user_empresas_ids and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Usuário não tem permissão")
    return c


@router.put("/{contrato_id}", response_model=sc_schema.ServicoContratadoResponse)
def update_contrato(contrato_id: int, contrato_in: sc_schema.ServicoContratadoUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    c = crud_servico_contratado.get_servico_contratado(db, contrato_id=contrato_id)
    if not c:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    if c.empresa_id:
        user_empresas_ids = [e.empresa_id for e in current_user.empresas]
        if c.empresa_id not in user_empresas_ids and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Usuário não tem permissão")
    updated = crud_servico_contratado.update_servico_contratado(db, db_obj=c, obj_in=contrato_in)
    return updated


@router.get("/cliente/{cliente_id}", response_model=List[sc_schema.ServicoContratadoResponse])
def list_contratos_cliente(cliente_id: int, empresa_id: int = None, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    """Lista os contratos de um cliente específico, opcionalmente filtrados por empresa."""
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"Endpoint /cliente/{cliente_id} chamado com empresa_id={empresa_id}")
    logger.info(f"Usuário: {current_user.email}, is_superuser: {current_user.is_superuser}")

    # If empresa_id provided, check permission
    if empresa_id is not None:
        logger.info(f"Verificando empresa_id={empresa_id}")
        db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
        if not db_empresa:
            logger.error(f"Empresa {empresa_id} não encontrada")
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        logger.info(f"Empresa {empresa_id} encontrada: {db_empresa.razao_social}")

        user_empresas_ids = [e.empresa_id for e in current_user.empresas]
        logger.info(f"Empresas do usuário: {user_empresas_ids}")

        if empresa_id not in user_empresas_ids and not current_user.is_superuser:
            logger.error(f"Usuário não tem permissão para empresa {empresa_id}")
            raise HTTPException(status_code=403, detail="Usuário não tem permissão")

        logger.info("Permissão para empresa verificada com sucesso")

    # Get contratos for the cliente, optionally filtered by empresa
    logger.info(f"Executando query para cliente_id={cliente_id}, empresa_id={empresa_id}")
    try:
        contratos = crud_servico_contratado.get_servicos_contratados_by_cliente(db, cliente_id=cliente_id, empresa_id=empresa_id)
        logger.info(f"Query executada com sucesso, retornou {len(contratos)} contratos")
    except Exception as e:
        logger.error(f"Erro na execução da query: {e}", exc_info=True)
        raise

    # Additional permission check: ensure user has access to the empresas of these contratos
    if not current_user.is_superuser:
        logger.info("Verificando permissões para cada contrato (usuário não é superuser)")
        user_empresas_ids = [e.empresa_id for e in current_user.empresas]
        logger.info(f"Empresas do usuário: {user_empresas_ids}")

        for i, contrato in enumerate(contratos):
            logger.info(f"Verificando contrato {i+1}: empresa_id={contrato.get('empresa_id')}")
            if contrato.get('empresa_id') not in user_empresas_ids:
                logger.error(f"Usuário não tem permissão para contrato da empresa {contrato.get('empresa_id')}")
                raise HTTPException(status_code=403, detail="Usuário não tem permissão para acessar contratos desta empresa")
        logger.info("Todas as permissões verificadas com sucesso")
    else:
        logger.info("Usuário é superuser, pulando verificação de permissões")

    logger.info(f"Retornando {len(contratos)} contratos")
    return contratos


# Company-scoped endpoints (also available under /empresas/{empresa_id}/servicos-contratados)
@router.post("/empresa/{empresa_id}", response_model=sc_schema.ServicoContratadoResponse, status_code=status.HTTP_201_CREATED)
def create_contrato_for_empresa(empresa_id: int, contrato: sc_schema.ServicoContratadoCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    # check permission
    db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    user_empresas_ids = [e.empresa_id for e in current_user.empresas]
    if not current_user.is_superuser and empresa_id not in user_empresas_ids:
        raise HTTPException(status_code=403, detail="Usuário não tem permissão")
    c = crud_servico_contratado.create_servico_contratado(db, contrato_in=contrato, empresa_id=empresa_id, created_by_user_id=current_user.id)
    return c


@router.get("/empresa/{empresa_id}", response_model=List[sc_schema.ServicoContratadoResponse])
def list_contratos_empresa(empresa_id: int, q: str = None, skip: int = 0, limit: int = 100, dia_vencimento_min: int = None, dia_vencimento_max: int = None, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user), response: Response = None):
    db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    user_empresas_ids = [e.empresa_id for e in current_user.empresas]
    if not current_user.is_superuser and empresa_id not in user_empresas_ids:
        raise HTTPException(status_code=403, detail="Usuário não tem permissão")
    total = crud_servico_contratado.count_servicos_contratados_by_empresa(db, empresa_id=empresa_id, qstr=q, dia_vencimento_min=dia_vencimento_min, dia_vencimento_max=dia_vencimento_max)
    if response is not None:
        response.headers['X-Total-Count'] = str(total)
    return crud_servico_contratado.get_servicos_contratados_by_empresa(db, empresa_id=empresa_id, qstr=q, skip=skip, limit=limit, dia_vencimento_min=dia_vencimento_min, dia_vencimento_max=dia_vencimento_max)


@router.put("/empresa/{empresa_id}/{contrato_id}", response_model=sc_schema.ServicoContratadoResponse)
def update_contrato_for_empresa(empresa_id: int, contrato_id: int, contrato_in: sc_schema.ServicoContratadoUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    user_empresas_ids = [e.empresa_id for e in current_user.empresas]
    if not current_user.is_superuser and empresa_id not in user_empresas_ids:
        raise HTTPException(status_code=403, detail="Usuário não tem permissão")
    db_obj = crud_servico_contratado.get_servico_contratado(db, contrato_id=contrato_id, empresa_id=empresa_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    updated = crud_servico_contratado.update_servico_contratado(db, db_obj=db_obj, obj_in=contrato_in)
    return updated


@router.delete("/empresa/{empresa_id}/{contrato_id}")
def delete_contrato_for_empresa(empresa_id: int, contrato_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    user_empresas_ids = [e.empresa_id for e in current_user.empresas]
    if not current_user.is_superuser and empresa_id not in user_empresas_ids:
        raise HTTPException(status_code=403, detail="Usuário não tem permissão")
    db_obj = crud_servico_contratado.get_servico_contratado(db, contrato_id=contrato_id, empresa_id=empresa_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    crud_servico_contratado.delete_servico_contratado(db, db_obj=db_obj)
    return None
