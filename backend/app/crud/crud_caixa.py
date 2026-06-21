from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from app.models import models
from app.schemas import caixa as schema_caixa
from typing import List, Optional

# --- Local de Pagamento ---

def get_locais_pagamento(db: Session, empresa_id: int, include_inactive: bool = False) -> List[models.LocalPagamento]:
    query = db.query(models.LocalPagamento).filter(models.LocalPagamento.empresa_id == empresa_id)
    if not include_inactive:
        query = query.filter(models.LocalPagamento.is_active == True)
    return query.all()

def create_local_pagamento(db: Session, empresa_id: int, obj_in: schema_caixa.LocalPagamentoCreate) -> models.LocalPagamento:
    db_obj = models.LocalPagamento(**obj_in.model_dump(), empresa_id=empresa_id)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update_local_pagamento(db: Session, local_id: int, obj_in: schema_caixa.LocalPagamentoUpdate) -> Optional[models.LocalPagamento]:
    db_obj = db.query(models.LocalPagamento).filter(models.LocalPagamento.id == local_id).first()
    if not db_obj:
        return None
    
    update_data = obj_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_obj, key, value)
        
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete_local_pagamento(db: Session, local_id: int) -> bool:
    db_obj = db.query(models.LocalPagamento).filter(models.LocalPagamento.id == local_id).first()
    if not db_obj:
        return False
    db.delete(db_obj)
    db.commit()
    return True

# --- Forma de Pagamento ---

def get_formas_pagamento(db: Session, empresa_id: int, include_inactive: bool = False) -> List[models.FormaPagamento]:
    query = db.query(models.FormaPagamento).filter(models.FormaPagamento.empresa_id == empresa_id)
    if not include_inactive:
        query = query.filter(models.FormaPagamento.is_active == True)
    return query.all()

def create_forma_pagamento(db: Session, empresa_id: int, obj_in: schema_caixa.FormaPagamentoCreate) -> models.FormaPagamento:
    db_obj = models.FormaPagamento(**obj_in.model_dump(), empresa_id=empresa_id)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update_forma_pagamento(db: Session, forma_id: int, obj_in: schema_caixa.FormaPagamentoUpdate) -> Optional[models.FormaPagamento]:
    db_obj = db.query(models.FormaPagamento).filter(models.FormaPagamento.id == forma_id).first()
    if not db_obj:
        return None
    
    update_data = obj_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_obj, key, value)
        
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete_forma_pagamento(db: Session, forma_id: int) -> bool:
    db_obj = db.query(models.FormaPagamento).filter(models.FormaPagamento.id == forma_id).first()
    if not db_obj:
        return False
    db.delete(db_obj)
    db.commit()
    return True

# --- Sessão de Caixa ---

def get_sessoes_abertas_local(db: Session, empresa_id: int, local_pagamento_id: int) -> List[models.CaixaSessao]:
    return db.query(models.CaixaSessao).filter(
        models.CaixaSessao.empresa_id == empresa_id,
        models.CaixaSessao.local_pagamento_id == local_pagamento_id,
        models.CaixaSessao.status == "ABERTO"
    ).all()

def get_sessao_atual(db: Session, empresa_id: int, usuario_id: int) -> Optional[models.CaixaSessao]:
    return db.query(models.CaixaSessao).filter(
        models.CaixaSessao.empresa_id == empresa_id,
        models.CaixaSessao.usuario_id == usuario_id,
        models.CaixaSessao.status == "ABERTO"
    ).first()

def get_sessao_by_id(db: Session, sessao_id: int) -> Optional[models.CaixaSessao]:
    return db.query(models.CaixaSessao).filter(models.CaixaSessao.id == sessao_id).first()

def abrir_sessao(db: Session, empresa_id: int, usuario_id: int, obj_in: schema_caixa.CaixaSessaoAbrir) -> models.CaixaSessao:
    sessao = models.CaixaSessao(
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        local_pagamento_id=obj_in.local_pagamento_id,
        saldo_inicial=obj_in.saldo_inicial,
        status="ABERTO"
    )
    db.add(sessao)
    db.commit()
    db.refresh(sessao)
    return sessao

def fechar_sessao(db: Session, sessao: models.CaixaSessao, obj_in: schema_caixa.CaixaSessaoFechar) -> models.CaixaSessao:
    # Calcular o saldo total (inicial + suprimentos + recebimentos - sangrias)
    movimentacoes = get_extrato(db, sessao.id)
    saldo_calculado = sessao.saldo_inicial
    for mov in movimentacoes:
        if mov.tipo in ["RECEBIMENTO", "SUPRIMENTO"]:
            saldo_calculado += mov.valor
        elif mov.tipo == "SANGRIA":
            saldo_calculado -= mov.valor
            
    sessao.saldo_final_informado = obj_in.saldo_final_informado
    sessao.saldo_final_calculado = saldo_calculado
    sessao.data_fechamento = func.now()
    sessao.status = "FECHADO"
    db.commit()
    db.refresh(sessao)
    return sessao

def get_extrato(db: Session, sessao_id: int) -> List[models.CaixaMovimentacao]:
    return db.query(models.CaixaMovimentacao).filter(
        models.CaixaMovimentacao.sessao_id == sessao_id
    ).order_by(models.CaixaMovimentacao.created_at.asc()).all()

def lancar_movimentacao(
    db: Session, 
    sessao_id: int, 
    usuario_id: int, 
    obj_in: schema_caixa.CaixaMovimentacaoCreate,
    recebimento_caixa_id: Optional[int] = None
) -> models.CaixaMovimentacao:
    mov = models.CaixaMovimentacao(
        sessao_id=sessao_id,
        usuario_id=usuario_id,
        forma_pagamento_id=obj_in.forma_pagamento_id,
        recebimento_caixa_id=recebimento_caixa_id,
        tipo=obj_in.tipo.upper(),
        valor=obj_in.valor,
        descricao=obj_in.descricao
    )
    db.add(mov)
    db.commit()
    db.refresh(mov)
    return mov