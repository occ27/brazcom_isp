from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.models import Usuario
from app.routes.auth import get_current_active_user
from app.schemas import caixa as schema_caixa
from app.crud import crud_caixa
from app.api.deps import permission_checker

router = APIRouter()

# --- Locais de Pagamento ---

@router.get("/locais/{empresa_id}", response_model=List[schema_caixa.LocalPagamentoResponse])
def list_locais(empresa_id: int, include_inactive: bool = False, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    return crud_caixa.get_locais_pagamento(db, empresa_id, include_inactive)

@router.post("/locais/{empresa_id}", response_model=schema_caixa.LocalPagamentoResponse, status_code=status.HTTP_201_CREATED)
def create_local(empresa_id: int, payload: schema_caixa.LocalPagamentoCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    deps = permission_checker('company_manage')
    deps(db=db, current_user=current_user)
    return crud_caixa.create_local_pagamento(db, empresa_id, payload)

@router.put("/locais/{local_id}", response_model=schema_caixa.LocalPagamentoResponse)
def update_local(local_id: int, payload: schema_caixa.LocalPagamentoUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    deps = permission_checker('company_manage')
    deps(db=db, current_user=current_user)
    local = crud_caixa.update_local_pagamento(db, local_id, payload)
    if not local:
        raise HTTPException(status_code=404, detail="Local de pagamento não encontrado")
    return local

@router.delete("/locais/{local_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_local(local_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    deps = permission_checker('company_manage')
    deps(db=db, current_user=current_user)
    success = crud_caixa.delete_local_pagamento(db, local_id)
    if not success:
        raise HTTPException(status_code=404, detail="Local de pagamento não encontrado")
    return None

# --- Formas de Pagamento ---

@router.get("/formas/{empresa_id}", response_model=List[schema_caixa.FormaPagamentoResponse])
def list_formas(empresa_id: int, include_inactive: bool = False, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    return crud_caixa.get_formas_pagamento(db, empresa_id, include_inactive)

@router.post("/formas/{empresa_id}", response_model=schema_caixa.FormaPagamentoResponse, status_code=status.HTTP_201_CREATED)
def create_forma(empresa_id: int, payload: schema_caixa.FormaPagamentoCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    deps = permission_checker('company_manage')
    deps(db=db, current_user=current_user)
    return crud_caixa.create_forma_pagamento(db, empresa_id, payload)

@router.put("/formas/{forma_id}", response_model=schema_caixa.FormaPagamentoResponse)
def update_forma(forma_id: int, payload: schema_caixa.FormaPagamentoUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    deps = permission_checker('company_manage')
    deps(db=db, current_user=current_user)
    forma = crud_caixa.update_forma_pagamento(db, forma_id, payload)
    if not forma:
        raise HTTPException(status_code=404, detail="Forma de pagamento não encontrada")
    return forma

@router.delete("/formas/{forma_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_forma(forma_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    deps = permission_checker('company_manage')
    deps(db=db, current_user=current_user)
    success = crud_caixa.delete_forma_pagamento(db, forma_id)
    if not success:
        raise HTTPException(status_code=404, detail="Forma de pagamento não encontrada")
    return None

# --- Operações de Sessão ---

@router.get("/sessao/atual/{empresa_id}", response_model=schema_caixa.CaixaSessaoResponse)
def get_sessao_atual(empresa_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    sessao = crud_caixa.get_sessao_atual(db, empresa_id, current_user.id)
    if not sessao:
        raise HTTPException(status_code=404, detail="Nenhum caixa aberto para o usuário atual")
    # Attach names for UI
    from app.crud.crud_usuario import get_usuario
    sessao.usuario_nome = current_user.full_name
    sessao.local_pagamento_nome = sessao.local_pagamento.nome if sessao.local_pagamento else None
    return sessao

@router.post("/sessao/abrir/{empresa_id}", response_model=schema_caixa.CaixaSessaoResponse)
def abrir_sessao(empresa_id: int, payload: schema_caixa.CaixaSessaoAbrir, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    # Verifica se já não tem um caixa aberto
    sessao_existente = crud_caixa.get_sessao_atual(db, empresa_id, current_user.id)
    if sessao_existente:
        raise HTTPException(status_code=400, detail="Você já possui um caixa aberto.")
        
    # Verifica se outra pessoa já abriu o mesmo caixa físico
    sessoes_neste_local = crud_caixa.get_sessoes_abertas_local(db, empresa_id, payload.local_pagamento_id)
    if sessoes_neste_local:
        raise HTTPException(status_code=400, detail="Este local de pagamento já está aberto por outro usuário.")
        
    sessao = crud_caixa.abrir_sessao(db, empresa_id, current_user.id, payload)
    sessao.usuario_nome = current_user.full_name
    sessao.local_pagamento_nome = sessao.local_pagamento.nome if sessao.local_pagamento else None
    return sessao

@router.post("/sessao/fechar/{sessao_id}", response_model=schema_caixa.CaixaSessaoResponse)
def fechar_sessao(sessao_id: int, payload: schema_caixa.CaixaSessaoFechar, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    sessao = crud_caixa.get_sessao_by_id(db, sessao_id)
    if not sessao or sessao.status != "ABERTO":
        raise HTTPException(status_code=400, detail="Caixa inválido ou já fechado")
        
    if sessao.usuario_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Apenas o próprio operador pode fechar seu caixa")
        
    return crud_caixa.fechar_sessao(db, sessao, payload)

@router.get("/sessao/{sessao_id}/extrato", response_model=List[schema_caixa.CaixaMovimentacaoResponse])
def get_extrato(sessao_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    sessao = crud_caixa.get_sessao_by_id(db, sessao_id)
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    if sessao.usuario_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Acesso negado")
        
    movs = crud_caixa.get_extrato(db, sessao_id)
    for mov in movs:
        mov.forma_pagamento_nome = mov.forma_pagamento.nome if mov.forma_pagamento else None
    return movs

@router.post("/sessao/{sessao_id}/movimentacao", response_model=schema_caixa.CaixaMovimentacaoResponse)
def lancar_movimentacao(sessao_id: int, payload: schema_caixa.CaixaMovimentacaoCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    sessao = crud_caixa.get_sessao_by_id(db, sessao_id)
    if not sessao or sessao.status != "ABERTO":
        raise HTTPException(status_code=400, detail="Caixa inválido ou já fechado")
    
    if sessao.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="Apenas o próprio operador pode lançar movimentações")
        
    if payload.tipo not in ["SANGRIA", "SUPRIMENTO"]:
        raise HTTPException(status_code=400, detail="Lançamento manual apenas para Sangria e Suprimento")
        
    mov = crud_caixa.lancar_movimentacao(db, sessao_id, current_user.id, payload)
    mov.forma_pagamento_nome = mov.forma_pagamento.nome if mov.forma_pagamento else None
    return mov

@router.get("/historico/{empresa_id}")
def historico_caixas(
    empresa_id: int,
    page: int = 1,
    per_page: int = 25,
    status: str = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    deps = permission_checker('caixa_manage')
    deps(db=db, current_user=current_user)
    
    from app.models.models import CaixaSessao, Usuario, LocalPagamento
    
    query = db.query(CaixaSessao).filter(CaixaSessao.empresa_id == empresa_id)
    if status:
        query = query.filter(CaixaSessao.status == status)
        
    total = query.count()
    items = query.order_by(CaixaSessao.id.desc())\
        .offset((page - 1) * per_page)\
        .limit(per_page)\
        .all()
        
    result = []
    for s in items:
        # Preenche os nomes
        s.usuario_nome = s.usuario.full_name if s.usuario else 'Desconhecido'
        s.local_pagamento_nome = s.local_pagamento.nome if s.local_pagamento else 'Desconhecido'
        result.append(schema_caixa.CaixaSessaoResponse.model_validate(s))
        
    return {"data": result, "total": total}

@router.get("/sessao/{sessao_id}/pdf")
def get_caixa_pdf(
    sessao_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    deps = permission_checker('caixa_manage')
    deps(db=db, current_user=current_user)
    
    sessao = crud_caixa.get_sessao_by_id(db, sessao_id)
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
        
    from app.models.models import Empresa
    empresa = db.query(Empresa).filter(Empresa.id == sessao.empresa_id).first()
    
    movs = crud_caixa.get_extrato(db, sessao_id)
    usuario_nome = sessao.usuario.full_name if sessao.usuario else 'Desconhecido'
    
    from app.services.report_service import ReportService
    from fastapi.responses import StreamingResponse
    
    buffer = ReportService.generate_caixa_session_report(
        empresa=empresa,
        sessao=sessao,
        usuario_nome=usuario_nome,
        extrato=movs
    )
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=caixa_{sessao_id}.pdf"}
    )