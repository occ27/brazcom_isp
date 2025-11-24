from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models import NFCom, Empresa, Usuario
from app.routes.auth import get_current_active_user
from app.models import Usuario
from typing import Dict, Any

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
    
    # Dados para gráfico de status
    status_data = [
        {"name": "Autorizadas", "value": total_autorizadas, "color": "#4caf50"},
        {"name": "Pendentes", "value": total_pendentes, "color": "#ff9800"},
        {"name": "Canceladas", "value": total_canceladas, "color": "#f44336"},
    ]
    
    # Dados mensais (últimos 6 meses)
    from datetime import datetime, timedelta
    monthly_data = []
    for i in range(5, -1, -1):
        month_start = (datetime.now().replace(day=1) - timedelta(days=i*30)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        month_value = db.query(func.sum(NFCom.valor_total)).filter(
            NFCom.empresa_id == empresa_id,
            NFCom.data_emissao >= month_start,
            NFCom.data_emissao <= month_end
        ).scalar() or 0.0
        
        monthly_data.append({
            "month": month_start.strftime("%b"),
            "valor": float(month_value)
        })
    
    return {
        "stats": {
            "nfcom_emitidas": total_nfcom,
            "valor_total": float(valor_total),
            "autorizadas": total_autorizadas,
            "pendentes": total_pendentes,
            "canceladas": total_canceladas,
        },
        "charts": {
            "status": status_data,
            "monthly": monthly_data
        }
    }