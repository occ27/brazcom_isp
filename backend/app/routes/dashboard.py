from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.models import NFCom, Empresa, Usuario, Cliente, ServicoContratado, Receivable
from app.routes.auth import get_current_active_user
from typing import Dict, Any
from datetime import datetime, timedelta, date

router = APIRouter()

@router.get("/dashboard/stats", response_model=Dict[str, Any])
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Obtém estatísticas para o dashboard"""
    
    # Verificar se o usuário tem empresa ativa
    if not current_user.active_empresa_id:
        raise HTTPException(status_code=400, detail="Usuário deve ter empresa ativa")
    
    empresa_id = current_user.active_empresa_id
    
    # Estatísticas gerais
    total_nfcom = db.query(NFCom).filter(NFCom.empresa_id == empresa_id).count()
    
    total_autorizadas = db.query(NFCom).filter(
        NFCom.empresa_id == empresa_id,
        NFCom.protocolo_autorizacao.isnot(None)
    ).count()
    
    total_pendentes = db.query(NFCom).filter(
        NFCom.empresa_id == empresa_id,
        NFCom.protocolo_autorizacao.is_(None)
    ).count()
    
    total_canceladas = db.query(NFCom).filter(
        NFCom.empresa_id == empresa_id,
        NFCom.informacoes_adicionais.like('%cStat=134%') |
        NFCom.informacoes_adicionais.like('%cStat=135%') |
        NFCom.informacoes_adicionais.like('%cStat=136%')
    ).count()
    
    valor_total = db.query(func.sum(NFCom.valor_total)).filter(NFCom.empresa_id == empresa_id).scalar() or 0.0
    
    # --- Estatísticas de Clientes ---
    total_clientes = db.query(Cliente).filter(Cliente.empresa_id == empresa_id).count()
    
    # --- Estatísticas de Contratos ---
    total_contratos_ativos = db.query(ServicoContratado).filter(
        ServicoContratado.empresa_id == empresa_id,
        ServicoContratado.status == 'ATIVO'
    ).count()
    total_contratos_bloqueados = db.query(ServicoContratado).filter(
        ServicoContratado.empresa_id == empresa_id,
        ServicoContratado.status == 'BLOQUEADO'
    ).count()
    
    # --- Estatísticas Financeiras (Receivables) ---
    today = date.today()
    first_day_of_month = today.replace(day=1)
    
    # Recebido no Mês
    recebido_mes = db.query(func.sum(Receivable.amount)).filter(
        Receivable.empresa_id == empresa_id,
        Receivable.status == 'PAID',
        func.date(Receivable.paid_at) >= first_day_of_month
    ).scalar() or 0.0

    # Pendente a receber no Mês (vencimento no mês atual, não pago)
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
        
    pendente_mes = db.query(func.sum(Receivable.amount)).filter(
        Receivable.empresa_id == empresa_id,
        Receivable.status.in_(['PENDING', 'REGISTERED', 'PRINTED', 'SENT']),
        func.date(Receivable.due_date) >= first_day_of_month,
        func.date(Receivable.due_date) < next_month
    ).scalar() or 0.0

    # Vencido (Inadimplência total)
    vencido_total = db.query(func.sum(Receivable.amount)).filter(
        Receivable.empresa_id == empresa_id,
        Receivable.status.in_(['PENDING', 'REGISTERED', 'PRINTED', 'SENT']),
        func.date(Receivable.due_date) < today
    ).scalar() or 0.0

    # Dados para gráfico de status (NFComs mantido como exemplo, ou pode ser contratos)
    status_data = [
        {"name": "Ativos", "value": total_contratos_ativos, "color": "#10b981"}, # emerald-500
        {"name": "Bloqueados", "value": total_contratos_bloqueados, "color": "#f43f5e"}, # rose-500
    ]
    
    # Dados mensais de Faturamento (Receivables) dos últimos 6 meses
    monthly_data = []
    for i in range(5, -1, -1):
        month_start = (datetime.now().replace(day=1) - timedelta(days=i*30)).replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
        
        month_value = db.query(func.sum(Receivable.amount)).filter(
            Receivable.empresa_id == empresa_id,
            Receivable.status == 'PAID',
            func.date(Receivable.paid_at) >= month_start.date(),
            func.date(Receivable.paid_at) <= month_end.date()
        ).scalar() or 0.0
        
        monthly_data.append({
            "month": month_start.strftime("%b"),
            "valor": float(month_value)
        })
    
    return {
        "stats": {
            "clientes_total": total_clientes,
            "contratos_ativos": total_contratos_ativos,
            "contratos_bloqueados": total_contratos_bloqueados,
            "nfcom_emitidas": total_nfcom,
            "valor_total_nfcom": float(valor_total),
            "recebido_mes": float(recebido_mes),
            "pendente_mes": float(pendente_mes),
            "vencido_total": float(vencido_total),
        },
        "charts": {
            "status": status_data,
            "monthly": monthly_data
        }
    }
