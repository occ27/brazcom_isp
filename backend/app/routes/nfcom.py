from fastapi import APIRouter, Depends, HTTPException, status, Response, Body, Query, Request
from fastapi.responses import JSONResponse, FileResponse
from starlette.background import BackgroundTask
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.crud import crud_empresa, crud_usuario, crud_nfcom, crud_servico
from app.schemas.empresa import EmpresaCreate, EmpresaUpdate, EmpresaResponse, UsuarioEmpresaCreate
from app.schemas.nfcom import NFComCreate, NFComResponse, NFComListResponse, NFComUpdate, BulkEmitNFComRequest, BulkEmitNFComResponse
from app.schemas import servico as servico_schema
from app.routes.auth import get_current_active_superuser, get_current_active_user
from app.models.models import Usuario, Empresa, UsuarioEmpresa, NFCom
from app.models import models
from app.services.email_service import EmailService
from app.services.danfe_generator import generate_danfe
import os
import tempfile
import threading
from app.core.database import SessionLocal
from datetime import datetime

router = APIRouter(prefix="/empresas", tags=["Empresas"])


def _sanitize_value(v):
    """Strip and collapse multiple whitespace for a string value."""
    import re
    if v is None:
        return v
    if isinstance(v, str):
        # replace any whitespace sequence (tabs, newlines, multiple spaces) with single space
        s = re.sub(r"\s+", " ", v)
        return s.strip()
    return v


def _sanitize_obj(obj):
    """Recursively sanitize a dict/list/primitive produced from a Pydantic model.

    Returns a new structure with strings stripped and collapsed.
    """
    if obj is None:
        return obj
    if isinstance(obj, dict):
        out = {}
        for k, val in obj.items():
            out[k] = _sanitize_obj(val)
        return out
    if isinstance(obj, list):
        return [_sanitize_obj(x) for x in obj]
    # primitives
    return _sanitize_value(obj)

# Helper function for permission checking
def _check_user_permission_for_empresa(empresa_id: int, current_user: Usuario, db: Session):
    """Helper function to check if a user can access a company's resources."""
    db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    user_empresas_ids = [assoc.empresa_id for assoc in current_user.empresas]
    if not current_user.is_superuser and empresa_id not in user_empresas_ids:
        raise HTTPException(status_code=403, detail="Usuário não tem permissão para acessar recursos desta empresa")
    return db_empresa

@router.post("/", response_model=EmpresaResponse, status_code=status.HTTP_201_CREATED)
def create_empresa(
    empresa: EmpresaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_superuser)
):
    """Cria uma nova empresa. Apenas superusuários podem criar empresas."""
    db_empresa = crud_empresa.get_empresa_by_cnpj(db, cnpj=empresa.cnpj)
    if db_empresa:
        raise HTTPException(status_code=400, detail="CNPJ já registrado")
    return crud_empresa.create_empresa(db=db, empresa=empresa, user_id=current_user.id)

@router.get("/", response_model=List[EmpresaResponse])
def read_empresas(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Lista empresas. Superusuários veem todas, usuários normais veem apenas suas empresas."""
    if current_user.is_superuser:
        empresas = crud_empresa.get_empresas(db, skip=skip, limit=limit)
    else:
        empresas = crud_empresa.get_empresas_by_usuario(db, usuario_id=current_user.id, skip=skip, limit=limit)
    return empresas

@router.get("/{empresa_id}", response_model=EmpresaResponse)
def read_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Obtém uma empresa específica pelo ID."""
    return _check_user_permission_for_empresa(empresa_id, current_user, db)

@router.put("/{empresa_id}", response_model=EmpresaResponse)
def update_empresa(
    empresa_id: int,
    empresa: EmpresaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Atualiza uma empresa."""
    db_empresa = _check_user_permission_for_empresa(empresa_id, current_user, db)
    if not current_user.is_superuser and db_empresa.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado para atualização")
    return crud_empresa.update_empresa(db=db, db_obj=db_empresa, obj_in=empresa)

@router.delete("/{empresa_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_superuser)
):
    """Deleta uma empresa. Apenas superusuários."""
    db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if db_empresa is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    crud_empresa.delete_empresa(db=db, db_obj=db_empresa)
    return None

@router.post("/associar-usuario/", status_code=status.HTTP_201_CREATED)
def associar_usuario_empresa(
    associacao: UsuarioEmpresaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Associa um usuário a uma empresa."""
    is_admin_of_empresa = any(e.empresa_id == associacao.empresa_id and e.is_admin for e in current_user.empresas)
    if not current_user.is_superuser and not is_admin_of_empresa:
        raise HTTPException(status_code=403, detail="Permissão negada")
    _check_user_permission_for_empresa(associacao.empresa_id, current_user, db)
    db_usuario = crud_usuario.get_usuario(db, usuario_id=associacao.usuario_id)
    if not db_usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    crud_empresa.associar_usuario(db, associacao=associacao)
    return {"message": "Associação criada com sucesso"}

@router.post("/{empresa_id}/nfcom", response_model=NFComResponse, status_code=status.HTTP_201_CREATED)
def create_empresa_nfcom(
    empresa_id: int,
    nfcom_in: NFComCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Cria uma nova NFCom para a empresa especificada."""
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    # Sanitiza todos os campos de entrada (strip + colapso de espaços múltiplos)
    try:
        raw = nfcom_in.model_dump()
    except Exception:
        # Fallback para compatibilidade com Pydantic v1 style
        raw = dict(nfcom_in)
    sanitized = _sanitize_obj(raw)
    # Construir o objeto esperado pelo CRUD (NFComCreate)
    nfcreate = NFComCreate(**sanitized)
    return crud_nfcom.create_nfcom(db=db, nfcom_in=nfcreate, empresa_id=empresa_id)

@router.post("/{empresa_id}/nfcom/bulk-emit", response_model=BulkEmitNFComResponse)
def bulk_emit_nfcom_from_contracts(
    empresa_id: int,
    request: BulkEmitNFComRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Emite NFCom em massa para uma lista de contratos selecionados."""
    _check_user_permission_for_empresa(empresa_id, current_user, db)

    if not request.contract_ids:
        raise HTTPException(status_code=400, detail="Lista de contratos não pode estar vazia")

    # Segurança adicional: garantir que TODOS os contratos solicitados pertencem
    # à empresa informada. Fazemos uma pré-validação e removemos/registramos
    # contratos inválidos antes de chamar a função CRUD que cria as NFs.
    from app.crud import crud_servico_contratado

    valid_ids = []
    invalids = []
    for cid in request.contract_ids:
        c = crud_servico_contratado.get_servico_contratado(db, contrato_id=cid, empresa_id=empresa_id)
        if c is None:
            invalids.append({"contract_id": cid, "error": "Contrato não pertence à empresa ou não encontrado"})
        else:
            valid_ids.append(cid)

    if not valid_ids:
        # Nenhum contrato válido para processar
        return BulkEmitNFComResponse(
            successes=[],
            failures=invalids,
            total_processed=len(request.contract_ids),
            total_success=0,
            total_failed=len(invalids)
        )

    # Chamar a função CRUD de emissão em massa apenas com os contratos válidos
    results = crud_nfcom.bulk_emit_nfcom_from_contracts(
        db=db,
        contract_ids=valid_ids,
        empresa_id=empresa_id,
        execute=getattr(request, 'execute', False),
        transmit=getattr(request, 'transmit', False)
    )

    # Mesclar falhas pré-validadas com as que vieram do processamento
    results_failures = results.get('failures', [])
    results_failures.extend(invalids)

    # Preparar resposta (usar falhas mescladas)
    merged_failures = results.get('failures', [])
    # results_failures já estendeu invalids, mas garantir união segura
    if results_failures is not merged_failures:
        # Se por algum motivo não for a mesma lista, reconstruir
        merged_failures = results.get('failures', []) + invalids

    response = BulkEmitNFComResponse(
        successes=results.get("successes", []),
        failures=merged_failures,
        total_processed=len(request.contract_ids),
        total_success=len(results.get("successes", [])),
        total_failed=len(merged_failures)
    )

    return response


@router.post("/{empresa_id}/nfcom/bulk-email")
def bulk_email_nfcoms(
    empresa_id: int,
    nfcom_ids: List[int] = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Inicia envio de emails para uma lista de NFComs em background.

    Retorna imediatamente um job_id que pode ser consultado para acompanhar progresso.
    """
    _check_user_permission_for_empresa(empresa_id, current_user, db)

    if not nfcom_ids:
        raise HTTPException(status_code=400, detail="Lista de NFComs não pode estar vazia")

    # Criar job no banco
    job = None
    try:
        job = db.query(models.NFComEmailJob).filter(False).first()  # type: ignore
    except Exception:
        pass

    # Inserir registro do job
    job = models.NFComEmailJob(
        empresa_id=empresa_id,
        created_by_user_id=current_user.id,
        total=len(nfcom_ids),
        processed=0,
        successes=0,
        failures=0,
        status='pending'
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Criar entradas iniciais de status por NFCom
    for nid in nfcom_ids:
        status_row = models.NFComEmailStatus(
            job_id=job.id,
            nfcom_id=nid,
            status='pending'
        )
        db.add(status_row)
    db.commit()

    # Iniciar thread background para processar envio
    def _process_job(job_id: int, empresa_id: int, nfcom_ids: List[int], user_id: int):
        dbbg = SessionLocal()
        try:
            job_obj = dbbg.query(models.NFComEmailJob).get(job_id)
            if not job_obj:
                return
            job_obj.status = 'running'
            dbbg.commit()

            for nid in nfcom_ids:
                try:
                    status_row = dbbg.query(models.NFComEmailStatus).filter(models.NFComEmailStatus.job_id == job_id, models.NFComEmailStatus.nfcom_id == nid).first()
                    nf = crud_nfcom.get_nfcom(dbbg, nfcom_id=nid, empresa_id=empresa_id)
                    if not nf:
                        status_row.status = 'failed'
                        status_row.error_message = 'NFCom não encontrada'
                        dbbg.commit()
                        job_obj.processed += 1
                        job_obj.failures += 1
                        dbbg.commit()
                        continue

                    # obter email do cliente
                    cliente_email = getattr(nf.cliente, 'email', None)
                    if not cliente_email:
                        status_row.status = 'failed'
                        status_row.error_message = 'Email do cliente não disponível'
                        dbbg.commit()
                        job_obj.processed += 1
                        job_obj.failures += 1
                        dbbg.commit()
                        continue

                    # gerar DANFE temporário
                    try:
                        pdf_buffer = generate_danfe(nf)
                        tmpf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                        tmpf.write(pdf_buffer.getvalue())
                        tmpf.close()
                        pdf_path = tmpf.name
                    except Exception as e:
                        status_row.status = 'failed'
                        status_row.error_message = f'Erro ao gerar DANFE: {str(e)}'
                        dbbg.commit()
                        job_obj.processed += 1
                        job_obj.failures += 1
                        dbbg.commit()
                        continue

                    # enviar email
                    sent = False
                    sent_err = None
                    try:
                        sent = EmailService.send_nfcom_email(nf.empresa, cliente_email, {
                            'nfcom_id': nf.id,
                            'numero_nf': nf.numero_nf,
                            'serie': nf.serie
                        }, pdf_path=pdf_path)
                    except Exception as e:
                        sent = False
                        sent_err = str(e)

                    # remover arquivo temporário
                    try:
                        os.unlink(pdf_path)
                    except Exception:
                        pass

                    if sent:
                        status_row.status = 'sent'
                        status_row.sent_at = datetime.utcnow()
                        job_obj.successes += 1
                        # Also update NFCom record for UI convenience
                        try:
                            nf.email_status = 'sent'
                            nf.email_sent_at = datetime.utcnow()
                            nf.email_error = None
                            dbbg.add(nf)
                        except Exception:
                            pass
                    else:
                        status_row.status = 'failed'
                        status_row.error_message = sent_err or 'Falha ao enviar email'
                        job_obj.failures += 1
                        try:
                            nf.email_status = 'failed'
                            nf.email_error = sent_err or 'Falha ao enviar email'
                            dbbg.add(nf)
                        except Exception:
                            pass

                    job_obj.processed += 1
                    dbbg.commit()

                except Exception as e:
                    try:
                        status_row.status = 'failed'
                        status_row.error_message = str(e)
                        dbbg.commit()
                    except Exception:
                        pass
                    job_obj.processed += 1
                    job_obj.failures += 1
                    dbbg.commit()

            job_obj.status = 'finished'
            dbbg.commit()
        finally:
            dbbg.close()

    thread = threading.Thread(target=_process_job, args=(job.id, empresa_id, nfcom_ids, current_user.id), daemon=True)
    thread.start()

    return {"job_id": job.id, "total": job.total, "status": job.status}


@router.get("/{empresa_id}/nfcom/email-job/{job_id}")
def get_email_job_status(empresa_id: int, job_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    job = db.query(models.NFComEmailJob).filter(models.NFComEmailJob.id == job_id, models.NFComEmailJob.empresa_id == empresa_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    items = db.query(models.NFComEmailStatus).filter(models.NFComEmailStatus.job_id == job_id).all()
    # Convert to simple dicts
    items_out = []
    for it in items:
        items_out.append({
            'nfcom_id': it.nfcom_id,
            'status': it.status,
            'error_message': it.error_message,
            'sent_at': it.sent_at.isoformat() if it.sent_at else None
        })

    return {
        'job': {
            'id': job.id,
            'total': job.total,
            'processed': job.processed,
            'successes': job.successes,
            'failures': job.failures,
            'status': job.status
        },
        'items': items_out
    }



@router.get("/{empresa_id}/nfcom/email-status")
def get_nfcoms_email_status(empresa_id: int, nfcom_ids: str = Query(None, description='Comma separated list of nfcom ids or multiple params'), db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user), request: Request = None):
    """Retorna o status de envio de email para uma lista de NFCom ids.

    Parâmetro `nfcom_ids` deve ser uma lista separada por vírgula, ex: ?nfcom_ids=1,2,3
    Retorno: { nfcom_id: { status, error_message, sent_at } }
    """
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    # Support both formats:
    # - single param with CSV: ?nfcom_ids=1,2,3
    # - repeated params: ?nfcom_ids=1&nfcom_ids=2
    ids = []
    try:
        if request is not None:
            qlist = request.query_params.getlist('nfcom_ids')
        else:
            qlist = [nfcom_ids] if nfcom_ids is not None else []

        if not qlist:
            raise HTTPException(status_code=400, detail='nfcom_ids é obrigatório')

        for entry in qlist:
            if entry is None:
                continue
            parts = [p.strip() for p in entry.split(',') if p.strip()]
            for p in parts:
                ids.append(int(p))
    except ValueError:
        raise HTTPException(status_code=400, detail='nfcom_ids inválido')

    out = {}
    for nid in ids:
        # buscar o registro mais recente para este nfcom_id
        row = db.query(models.NFComEmailStatus).filter(models.NFComEmailStatus.nfcom_id == nid).order_by(models.NFComEmailStatus.id.desc()).first()
        if row:
            out[nid] = {
                'status': row.status,
                'error_message': row.error_message,
                'sent_at': row.sent_at.isoformat() if row.sent_at else None
            }
        else:
            out[nid] = {'status': 'unknown', 'error_message': None, 'sent_at': None}

    return out

@router.get("/{empresa_id}/nfcom", response_model=NFComListResponse)
def read_empresa_nfcoms(
    empresa_id: int,
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    date_from: str = None,
    date_to: str = None,
    status: str = None,
    min_value: float = None,
    max_value: float = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Lista as NFComs de uma empresa específica com filtros opcionais."""
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    return crud_nfcom.get_nfcoms_by_empresa(
        db, empresa_id=empresa_id, skip=skip, limit=limit,
        search=search, date_from=date_from, date_to=date_to,
        status=status, min_value=min_value, max_value=max_value
    )

@router.get("/{empresa_id}/nfcom/{nfcom_id}", response_model=NFComResponse)
def read_empresa_nfcom(empresa_id: int, nfcom_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    """Obtém uma NFCom específica de uma empresa pelo ID."""
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    db_nfcom = crud_nfcom.get_nfcom(db, nfcom_id=nfcom_id, empresa_id=empresa_id)
    if db_nfcom is None:
        raise HTTPException(status_code=404, detail="NFCom não encontrada nesta empresa")
    return db_nfcom

@router.get("/{empresa_id}/nfcom", response_model=NFComListResponse)
def read_empresa_nfcoms(
    empresa_id: int,
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    date_from: str = None,
    date_to: str = None,
    status: str = None,
    min_value: float = None,
    max_value: float = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Lista as NFComs de uma empresa específica com filtros opcionais."""
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    return crud_nfcom.get_nfcoms_by_empresa(
        db, empresa_id=empresa_id, skip=skip, limit=limit,
        search=search, date_from=date_from, date_to=date_to,
        status=status, min_value=min_value, max_value=max_value
    )

@router.get("/{empresa_id}/nfcom/{nfcom_id}", response_model=NFComResponse)
def read_empresa_nfcom(empresa_id: int, nfcom_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    """Obtém uma NFCom específica de uma empresa pelo ID."""
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    db_nfcom = crud_nfcom.get_nfcom(db, nfcom_id=nfcom_id, empresa_id=empresa_id)
    if db_nfcom is None:
        raise HTTPException(status_code=404, detail="NFCom não encontrada nesta empresa")
    return db_nfcom

@router.put("/{empresa_id}/nfcom/{nfcom_id}", response_model=NFComResponse)
def update_empresa_nfcom(
    empresa_id: int,
    nfcom_id: int,
    nfcom_in: NFComUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Atualiza uma NFCom de uma empresa específica."""
    # 1. Valida a permissão do usuário para a empresa
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    # 2. O CRUD de update já busca a nota e verifica se ela existe
    try:
        raw = nfcom_in.model_dump()
    except Exception:
        raw = dict(nfcom_in)
    sanitized = _sanitize_obj(raw)
    nfupdate = NFComUpdate(**sanitized)
    return crud_nfcom.update_nfcom(db=db, nfcom_id=nfcom_id, nfcom_in=nfupdate)

@router.delete("/{empresa_id}/nfcom/{nfcom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_empresa_nfcom(
    empresa_id: int,
    nfcom_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Exclui uma NFCom de uma empresa específica (apenas se não estiver autorizada)."""
    # 1. Valida a permissão do usuário para a empresa
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    # 2. Exclui a NFCom (o CRUD já verifica se pode ser excluída)
    crud_nfcom.delete_nfcom(db=db, nfcom_id=nfcom_id, empresa_id=empresa_id)
    return None

@router.get("/{empresa_id}/nfcom/{nfcom_id}/xml", response_class=Response)
def download_empresa_nfcom_xml(
    empresa_id: int,
    nfcom_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Fornece o XML de uma NFCom específica de uma empresa para download.
    """
    # 1. Valida a permissão do usuário para a empresa
    _check_user_permission_for_empresa(empresa_id, current_user, db)

    # 2. Busca a NFCom garantindo que ela pertence à empresa correta
    db_nfcom = crud_nfcom.get_nfcom(db, nfcom_id=nfcom_id, empresa_id=empresa_id)
    if not db_nfcom:
        raise HTTPException(status_code=404, detail="NFCom não encontrada nesta empresa")

    if not db_nfcom.xml_gerado:
        raise HTTPException(status_code=404, detail="XML não disponível para esta NFCom")

    return Response(
        content=db_nfcom.xml_gerado,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename=nfcom_{db_nfcom.numero_nf}_{db_nfcom.serie}.xml"}
    )

@router.get("/{empresa_id}/nfcom/{nfcom_id}/danfe", response_class=Response)
def visualizar_danfe_nfcom(
    empresa_id: int,
    nfcom_id: int,
    download: bool = Query(False, description="Se True, força o download do PDF"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Gera e retorna o DANFE-COM (PDF) de uma NFCom específica de uma empresa.
    Pode ser visualizado no navegador (download=false) ou baixado (download=true).
    """
    # 1. Valida a permissão do usuário para a empresa
    _check_user_permission_for_empresa(empresa_id, current_user, db)

    # 2. Busca a NFCom garantindo que ela pertence à empresa correta
    # IMPORTANTE: Carrega todos os relacionamentos necessários para o DANFE
    db_nfcom = db.query(NFCom).filter(
        NFCom.id == nfcom_id,
        NFCom.empresa_id == empresa_id
    ).first()
    
    if not db_nfcom:
        raise HTTPException(status_code=404, detail="NFCom não encontrada nesta empresa")

    # 3. Gera o DANFE
    try:
        pdf_buffer = generate_danfe(db_nfcom)
        pdf_content = pdf_buffer.getvalue()
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao gerar DANFE: {str(e)}"
        )

    # 4. Define o nome do arquivo
    filename = f"danfe_nfcom_{db_nfcom.numero_nf}_{db_nfcom.serie}.pdf"
    
    # 5. Define o Content-Disposition baseado no parâmetro download
    if download:
        content_disposition = f"attachment; filename={filename}"
    else:
        content_disposition = f"inline; filename={filename}"

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": content_disposition}
    )

#
# Serviços
#

@router.post("/{empresa_id}/servicos", response_model=servico_schema.ServicoResponse, status_code=status.HTTP_201_CREATED)
def create_servico_for_empresa(
    empresa_id: int,
    servico: servico_schema.ServicoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Cria um novo serviço para uma empresa."""
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    return crud_servico.create_servico(db=db, servico_in=servico, empresa_id=empresa_id)

@router.get("/{empresa_id}/servicos", response_model=List[servico_schema.ServicoResponse])
def read_servicos_from_empresa(
    empresa_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
    response: Response = None
):
    """Lista os serviços de uma empresa."""
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    total = crud_servico.count_servicos_by_empresa(db, empresa_id=empresa_id)
    if response is not None:
        response.headers['X-Total-Count'] = str(total)
    return crud_servico.get_servicos_by_empresa(db, empresa_id=empresa_id, skip=skip, limit=limit)

@router.put("/{empresa_id}/servicos/{servico_id}", response_model=servico_schema.ServicoResponse)
def update_servico_for_empresa(
    empresa_id: int,
    servico_id: int,
    servico: servico_schema.ServicoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Atualiza um serviço de uma empresa."""
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    db_servico = crud_servico.get_servico(db, servico_id=servico_id, empresa_id=empresa_id)
    if not db_servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    return crud_servico.update_servico(db=db, db_obj=db_servico, obj_in=servico)

@router.delete("/{empresa_id}/servicos/{servico_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_servico_from_empresa(
    empresa_id: int,
    servico_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Deleta um serviço de uma empresa."""
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    db_servico = crud_servico.get_servico(db, servico_id=servico_id, empresa_id=empresa_id)
    if not db_servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    crud_servico.delete_servico(db=db, db_obj=db_servico)
    return None

@router.post("/{empresa_id}/nfcom/{nfcom_id}/transmitir")
def transmitir_empresa_nfcom(
    empresa_id: int,
    nfcom_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Transmite uma NFCom para o SEFAZ."""
    # Retorna também a empresa (usada para envio de email caso necessário)
    db_empresa = _check_user_permission_for_empresa(empresa_id, current_user, db)
    db_nfcom = crud_nfcom.get_nfcom(db, nfcom_id=nfcom_id, empresa_id=empresa_id)
    if db_nfcom is None:
        raise HTTPException(status_code=404, detail="NFCom não encontrada nesta empresa")
    
    try:
        resultado = crud_nfcom.transmit_nfcom(db, nfcom_id=nfcom_id, empresa_id=empresa_id)

        # Se a SEFAZ retornou um cStat diferente de 100 (autorizada), propagar a mensagem
        cStat = resultado.get('cStat') if isinstance(resultado, dict) else None
        xMotivo = resultado.get('xMotivo') if isinstance(resultado, dict) else None

        if cStat and str(cStat) != '100':
            # Retornar 400 com a mensagem da SEFAZ para que o frontend a exiba
            detail_msg = f"Transmissão não autorizada pela SEFAZ (cStat={cStat}). Motivo: {xMotivo}"
            # Retornar um JSON estruturado onde `detail` é uma string (compatível com o frontend atual)
            content = {
                "detail": detail_msg,
                "cStat": cStat,
                "xMotivo": xMotivo,
                "resultado": resultado,
            }
            return JSONResponse(status_code=400, content=content)

        # Se a NFCom foi autorizada (cStat == 100), tentar enviar o DANFE por email
        resp = {"status": "sucesso", "resultado": resultado}
        try:
            if cStat and str(cStat) == '100':
                # Carregar cliente e checar email
                cliente = getattr(db_nfcom, 'cliente', None)
                cliente_email = None
                if cliente:
                    cliente_email = getattr(cliente, 'email', None)

                if cliente_email:
                    # Gerar DANFE (PDF) em buffer e escrever em arquivo temporário
                    try:
                        pdf_buffer = generate_danfe(db_nfcom)
                        import tempfile, os
                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                        try:
                            tmp.write(pdf_buffer.getvalue())
                            tmp.flush()
                            tmp.close()
                            # Obter objeto ORM da empresa (contém smtp_password criptografada)
                            from app.crud import crud_empresa as _crud_empresa
                            orm_empresa = _crud_empresa.get_empresa_raw(db, empresa_id=empresa_id)
                            sent = EmailService.send_nfcom_email(orm_empresa, cliente_email, {
                                'numero_nf': db_nfcom.numero_nf,
                                'serie': db_nfcom.serie,
                                'protocolo_autorizacao': getattr(db_nfcom, 'protocolo_autorizacao', None)
                            }, pdf_path=tmp.name)
                            resp['email_sent'] = bool(sent)
                            resp['email_message'] = 'Email enviado' if sent else 'Falha ao enviar email'
                            # Persistir status de envio na NFCom para frontend
                            try:
                                if sent:
                                    db_nfcom.email_status = 'sent'
                                    from datetime import datetime
                                    db_nfcom.email_sent_at = datetime.utcnow()
                                    db_nfcom.email_error = None
                                else:
                                    db_nfcom.email_status = 'failed'
                                    db_nfcom.email_error = 'Falha ao enviar email'
                                db.add(db_nfcom)
                                db.commit()
                            except Exception:
                                db.rollback()
                        finally:
                            try:
                                os.unlink(tmp.name)
                            except Exception:
                                pass
                    except Exception as e:
                        # Não falhar a transmissão por conta de erro no envio de email
                        resp['email_sent'] = False
                        resp['email_message'] = f'Erro ao gerar/enviar DANFE por email: {str(e)}'
        except Exception:
            # Protege de qualquer exceção no envio de email; não atrapalha a resposta principal
            pass

        return resp
    except HTTPException:
        # Repropagar HTTPExceptions (transmissão retornou erro esperado)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na transmissão: {str(e)}")


@router.post("/{empresa_id}/nfcom/{nfcom_id}/cancelar")
def cancelar_empresa_nfcom(
    empresa_id: int,
    nfcom_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Envia evento de cancelamento (110111) para a NFCom autorizada."""
    _check_user_permission_for_empresa(empresa_id, current_user, db)

    # Sanitiza e valida payload
    try:
        raw = payload
    except Exception:
        raw = dict(payload)
    sanitized = _sanitize_obj(raw)

    nProt = sanitized.get('nProt') or sanitized.get('nprot')
    xJust = sanitized.get('xJust') or sanitized.get('xjust') or sanitized.get('justificativa')

    if not nProt:
        raise HTTPException(status_code=400, detail="Parâmetro 'nProt' (número do protocolo de autorização) é obrigatório para cancelamento")
    if not xJust:
        raise HTTPException(status_code=400, detail="Parâmetro 'xJust' (justificativa) é obrigatório para cancelamento")
    
    # Validação conforme MOC/XSD: xJust (TJust) deve ter de 15 a 255 caracteres
    xJust_limpo = xJust.strip()
    if len(xJust_limpo) < 15:
        raise HTTPException(status_code=400, detail="Justificativa deve ter no mínimo 15 caracteres (campo xJust - TJust do XSD)")
    if len(xJust_limpo) > 255:
        raise HTTPException(status_code=400, detail="Justificativa deve ter no máximo 255 caracteres (campo xJust)")
    
    xJust = xJust_limpo
#nota fiscal cancelada em ambiente de homologação
    try:
        resultado = crud_nfcom.transmit_evento_cancelamento(db, nfcom_id=nfcom_id, empresa_id=empresa_id, nProt=nProt, justificativa=xJust)

        cStat = resultado.get('cStat') if isinstance(resultado, dict) else None
        xMotivo = resultado.get('xMotivo') if isinstance(resultado, dict) else None

        # Status de sucesso do evento depende do cStat da SEFAZ. Não forçar um código específico,
        # mas para facilitar frontend, retornamos 400 quando SEFAZ retornou rejeição (cStat não presente
        # ou não indicou sucesso).
        # cStat válidos: 
        # 135 (vinculado), 136 (vinculação prejudicada), 134 (NFCom em situação diferente)
        # 631 (duplicidade de evento - cancelamento já registrado)
        # 218 (NFCom já está cancelada - cancelamento já processado)
        codigos_sucesso = ('135', '136', '134', '128', '631', '218')
        if cStat and str(cStat).strip() not in codigos_sucesso:
            # Rejeição/erro registrado pela SEFAZ
            content = {
                "detail": f"Evento não aceito pela SEFAZ (cStat={cStat}). Motivo: {xMotivo}",
                "cStat": cStat,
                "xMotivo": xMotivo,
                "resultado": resultado,
            }
            return JSONResponse(status_code=400, content=content)

        return {"status": "sucesso", "resultado": resultado}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no envio do evento de cancelamento: {str(e)}")


@router.post("/{empresa_id}/nfcom/{nfcom_id}/download_debug")
def download_debug_file(
    empresa_id: int,
    nfcom_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Fornece arquivos temporários de debug (soap, resposta) gerados durante a transmissão.

    Segurança: apenas permite arquivos localizados no diretório temporário do sistema.
    Espera um JSON com { "path": "/tmp/soap_nfcom_...xml" } e valida que o arquivo está
    dentro de tempfile.gettempdir().
    """
    _check_user_permission_for_empresa(empresa_id, current_user, db)

    file_path = payload.get('path')
    if not file_path or not isinstance(file_path, str):
        raise HTTPException(status_code=400, detail="Parâmetro 'path' é obrigatório")

    # Permitir somente arquivos do diretório temporário para reduzir superfície de ataque
    allowed_dir = os.path.abspath(tempfile.gettempdir())
    try:
        target = os.path.abspath(file_path)
    except Exception:
        raise HTTPException(status_code=400, detail="Caminho inválido")

    # Verifica que o arquivo pedido está dentro do diretório temporário
    try:
        common = os.path.commonpath([allowed_dir, target])
    except Exception:
        raise HTTPException(status_code=400, detail="Caminho inválido")

    if common != allowed_dir:
        raise HTTPException(status_code=403, detail="Acesso negado ao arquivo solicitado")

    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(path=target, filename=os.path.basename(target), media_type='application/octet-stream')


@router.post("/{empresa_id}/nfcom/send-emails")
def send_emails_for_nfcoms(
    empresa_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Envia por email os DANFEs das NFComs listadas em payload['nfcom_ids'].

    Corpo esperado: { "nfcom_ids": [1,2,3] }
    Retorna resumo por nota com status de envio.
    """
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    nfcom_ids = payload.get('nfcom_ids')
    if not nfcom_ids or not isinstance(nfcom_ids, list):
        raise HTTPException(status_code=400, detail="Parâmetro 'nfcom_ids' obrigatório e deve ser uma lista")

    # Validação prévia: não permitir envio para notas pendentes ou canceladas
    invalid = []
    valid_nfcoms = []
    for nf_id in nfcom_ids:
        db_nfcom = crud_nfcom.get_nfcom(db, nfcom_id=nf_id, empresa_id=empresa_id)
        if not db_nfcom:
            invalid.append({"nfcom_id": nf_id, "reason": "not_found"})
            continue
        info = (getattr(db_nfcom, 'informacoes_adicionais', '') or '')
        is_cancelled = any(code in info for code in ['cStat=135', 'cStat=136', 'cStat=134'])
        is_authorized = bool(getattr(db_nfcom, 'protocolo_autorizacao', None))
        if is_cancelled:
            invalid.append({"nfcom_id": nf_id, "reason": "cancelled"})
            continue
        if not is_authorized:
            invalid.append({"nfcom_id": nf_id, "reason": "pending"})
            continue
        valid_nfcoms.append(db_nfcom)

    if invalid:
        # Retornar 400 com lista de notas inválidas para ação
        raise HTTPException(status_code=400, detail={"invalid": invalid})

    results = []
    for db_nfcom in valid_nfcoms:
        nf_id = db_nfcom.id
        try:
            cliente = getattr(db_nfcom, 'cliente', None)
            cliente_email = cliente.email if cliente else None
            if not cliente_email:
                results.append({"nfcom_id": nf_id, "sent": False, "message": "Cliente sem email cadastrado"})
                continue

            # Gerar PDF e enviar
            try:
                pdf_buffer = generate_danfe(db_nfcom)
                import tempfile, os
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                try:
                    tmp.write(pdf_buffer.getvalue())
                    tmp.flush()
                    tmp.close()
                    # Obter ORM da empresa para envio (tem smtp_password criptografada)
                    from app.crud import crud_empresa as _crud_empresa
                    orm_empresa = _crud_empresa.get_empresa_raw(db, empresa_id=empresa_id)
                    sent = EmailService.send_nfcom_email(orm_empresa, cliente_email, {
                        'numero_nf': db_nfcom.numero_nf,
                        'serie': db_nfcom.serie,
                        'protocolo_autorizacao': getattr(db_nfcom, 'protocolo_autorizacao', None)
                    }, pdf_path=tmp.name)
                    # Update NFCom record with email result
                    try:
                        if sent:
                            db_nfcom.email_status = 'sent'
                            db_nfcom.email_sent_at = datetime.utcnow()
                            db_nfcom.email_error = None
                        else:
                            db_nfcom.email_status = 'failed'
                            db_nfcom.email_error = 'Falha ao enviar email'
                        db.add(db_nfcom)
                        db.commit()
                    except Exception:
                        db.rollback()

                    results.append({"nfcom_id": nf_id, "sent": bool(sent), "message": 'Email enviado' if sent else 'Falha ao enviar email'})
                finally:
                    try:
                        os.unlink(tmp.name)
                    except Exception:
                        pass
            except Exception as e:
                # Update NFCom with error
                try:
                    db_nfcom.email_status = 'failed'
                    db_nfcom.email_error = f"Erro ao gerar/enviar: {str(e)}"
                    db.add(db_nfcom)
                    db.commit()
                except Exception:
                    db.rollback()
                results.append({"nfcom_id": nf_id, "sent": False, "message": f"Erro ao gerar/enviar: {str(e)}"})

        except Exception as e:
            results.append({"nfcom_id": nf_id, "sent": False, "message": f"Erro inesperado: {str(e)}"})

    return {"results": results}


@router.post("/{empresa_id}/nfcom/bulk-transmit")
def bulk_transmit_nfcoms(
    empresa_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Transmite em massa as NFComs listadas em `payload['nfcom_ids']`.

    O envio ocorre na ordem da lista. Ao encontrar a primeira nota que retorna
    erro (cStat diferente de 100) ou lançar exceção, a operação para e a
    resposta indica quais foram transmitidas com sucesso e qual foi a falha.
    """
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    nfcom_ids = payload.get('nfcom_ids')
    if not nfcom_ids or not isinstance(nfcom_ids, list):
        raise HTTPException(status_code=400, detail="Parâmetro 'nfcom_ids' obrigatório e deve ser uma lista")

    results_success = []
    results_failure = []

    for nf_id in nfcom_ids:
        # buscar e validar pertence/estado
        db_nfcom = crud_nfcom.get_nfcom(db, nfcom_id=nf_id, empresa_id=empresa_id)
        if not db_nfcom:
            # nota não encontrada: considera erro e para o lote
            results_failure.append({"nfcom_id": nf_id, "error": "not_found"})
            break

        info = (getattr(db_nfcom, 'informacoes_adicionais', '') or '')
        # se cancelada, trata como erro e para o lote
        if any(code in info for code in ['cStat=135', 'cStat=136', 'cStat=134']):
            results_failure.append({"nfcom_id": nf_id, "error": "cancelled"})
            break

        # se já autorizada, não transmite novamente — consideramos sucesso e continua
        if getattr(db_nfcom, 'protocolo_autorizacao', None):
            results_success.append({"nfcom_id": nf_id, "status": "already_authorized"})
            continue

        try:
            resultado = crud_nfcom.transmit_nfcom(db, nfcom_id=nf_id, empresa_id=empresa_id)
        except HTTPException as he:
            # Propaga erro com detalhe para o frontend e para no lote
            msg = getattr(he, 'detail', str(he))
            results_failure.append({"nfcom_id": nf_id, "error": "exception", "message": msg})
            break
        except Exception as e:
            results_failure.append({"nfcom_id": nf_id, "error": "exception", "message": str(e)})
            break

        # Checar retorno da transmissão
        cStat = None
        xMotivo = None
        if isinstance(resultado, dict):
            cStat = resultado.get('cStat')
            xMotivo = resultado.get('xMotivo')

        if cStat and str(cStat) == '100':
            results_success.append({"nfcom_id": nf_id, "status": "authorized", "cStat": cStat})
            # continuar para próxima nota
            continue
        else:
            # se retorno não contém cStat==100, registra falha e para lote
            detail_msg = None
            if isinstance(resultado, dict):
                detail_msg = resultado.get('xMotivo') or resultado.get('error') or str(resultado)
            results_failure.append({"nfcom_id": nf_id, "error": "transmit_failed", "cStat": cStat, "message": detail_msg, "resultado": resultado})
            break

    return {
        "successes": results_success,
        "failures": results_failure,
        "total_requested": len(nfcom_ids),
        "total_success": len(results_success),
        "total_failed": len(results_failure)
    }



@router.post("/{empresa_id}/nfcom/download-zip")
def download_nfcoms_zip(
    empresa_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Gera um ZIP contendo XMLs ou DANFEs (PDF) para as NFComs informadas.

    Payload: { "nfcom_ids": [1,2,3], "type": "xml" | "danfe" }
    """
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    nfcom_ids = payload.get('nfcom_ids')
    typ = payload.get('type')
    if not nfcom_ids or not isinstance(nfcom_ids, list):
        raise HTTPException(status_code=400, detail="Parâmetro 'nfcom_ids' obrigatório e deve ser uma lista")
    if typ not in ('xml', 'danfe'):
        raise HTTPException(status_code=400, detail="Parâmetro 'type' deve ser 'xml' ou 'danfe'")

    import zipfile, tempfile, os

    tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    tmp_zip.close()

    try:
        # Validação prévia: proibir ações em notas canceladas; proibir geração de DANFE para pendentes
        invalid = []
        for nf_id in nfcom_ids:
            db_nfcom = crud_nfcom.get_nfcom(db, nfcom_id=nf_id, empresa_id=empresa_id)
            if not db_nfcom:
                invalid.append({"nfcom_id": nf_id, "reason": "not_found"})
                continue
            info = (getattr(db_nfcom, 'informacoes_adicionais', '') or '')
            is_cancelled = any(code in info for code in ['cStat=135', 'cStat=136', 'cStat=134'])
            is_authorized = bool(getattr(db_nfcom, 'protocolo_autorizacao', None))
            if is_cancelled:
                invalid.append({"nfcom_id": nf_id, "reason": "cancelled"})
                continue
            if typ == 'danfe' and not is_authorized:
                invalid.append({"nfcom_id": nf_id, "reason": "pending"})
                continue

        if invalid:
            raise HTTPException(status_code=400, detail={"invalid": invalid})

        with zipfile.ZipFile(tmp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zf:
            for nf_id in nfcom_ids:
                db_nfcom = crud_nfcom.get_nfcom(db, nfcom_id=nf_id, empresa_id=empresa_id)
                if not db_nfcom:
                    continue

                if typ == 'xml':
                    xml_bytes = getattr(db_nfcom, 'xml_gerado', None)
                    if not xml_bytes:
                        continue
                    filename = f"nfcom_{db_nfcom.numero_nf}_{db_nfcom.serie}.xml"
                    zf.writestr(filename, xml_bytes)

                else:  # danfe
                    try:
                        pdf_buffer = generate_danfe(db_nfcom)
                        filename = f"danfe_nfcom_{db_nfcom.numero_nf}_{db_nfcom.serie}.pdf"
                        zf.writestr(filename, pdf_buffer.getvalue())
                    except Exception:
                        # pular notas cuja geração de DANFE falhar
                        continue

        # Retornar o arquivo com BackgroundTask para remover após envio
        def _cleanup(path: str):
            try:
                os.unlink(path)
            except Exception:
                pass

        bt = BackgroundTask(_cleanup, tmp_zip.name)
        return FileResponse(path=tmp_zip.name, filename=os.path.basename(tmp_zip.name), media_type='application/zip', background=bt)
    except Exception as e:
        try:
            os.unlink(tmp_zip.name)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Erro ao gerar ZIP: {str(e)}")