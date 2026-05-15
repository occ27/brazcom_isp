from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from datetime import date, datetime

from app.core.database import get_db
from app.routes.auth import get_current_active_user
from app.models.models import Usuario, Empresa, ServicoContratado, Receivable, Cliente, Servico
from app.services.report_service import ReportService
from app.api import deps

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/contracts/pdf")
def get_contracts_report_pdf(
    empresa_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[str] = None,
    servico_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Gera um relatório de contratos em PDF."""
    # Verificar permissão (pode usar 'contracts_view' ou similar)
    deps.permission_checker('contracts_view')(db=db, current_user=current_user)
    
    # Verificar se a empresa pertence ao usuário
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
    # Query de contratos
    query = db.query(ServicoContratado).filter(ServicoContratado.empresa_id == empresa_id)
    
    if start_date:
        query = query.filter(func.date(ServicoContratado.created_at) >= start_date)
    if end_date:
        query = query.filter(func.date(ServicoContratado.created_at) <= end_date)
    if status:
        query = query.filter(ServicoContratado.status == status)
    if servico_id:
        query = query.filter(ServicoContratado.servico_id == servico_id)
        
    contracts_db = query.all()
    
    # Preparar dados para o serviço
    contracts_data = []
    status_map = {
        "ATIVO": "Ativo",
        "SUSPENSO": "Suspenso",
        "CANCELADO": "Cancelado",
        "PENDENTE_INSTALACAO": "Pendente Instalação",
        "AGUARDANDO_ASSINATURA": "Aguardando Assinatura"
    }
    
    for c in contracts_db:
        contracts_data.append({
            "id": c.id,
            "cliente_nome": c.cliente.nome_razao_social if c.cliente else "N/A",
            "servico_descricao": c.servico.descricao if c.servico else "N/A",
            "created_at": c.created_at.strftime('%d/%m/%Y') if c.created_at else "",
            "valor_unitario": c.valor_unitario,
            "status": status_map.get(c.status, c.status)
        })
        
    filters = {
        "start_date": start_date.strftime('%d/%m/%Y') if start_date else "",
        "end_date": end_date.strftime('%d/%m/%Y') if end_date else "",
        "status": status
    }
    
    pdf_buffer = ReportService.generate_contracts_report(empresa, contracts_data, filters)
    
    filename = f"relatorio_contratos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/financial/pdf")
def get_financial_report_pdf(
    empresa_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[str] = None,
    date_type: str = Query("due_date", enum=["due_date", "paid_at"]),
    servico_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Gera um relatório financeiro em PDF."""
    deps.permission_checker('receivables_view')(db=db, current_user=current_user)
    
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
    query = db.query(Receivable).filter(Receivable.empresa_id == empresa_id)
    
    # Determinar coluna de data
    date_col = Receivable.due_date if date_type == "due_date" else Receivable.paid_at
    
    if start_date:
        query = query.filter(date_col >= start_date)
    if end_date:
        query = query.filter(date_col <= end_date)
    if status:
        query = query.filter(Receivable.status == status)
    if servico_id:
        query = query.filter(Receivable.servico_contratado.has(ServicoContratado.servico_id == servico_id))
        
    receivables_db = query.all()
    
    receivables_data = []
    status_map_fin = {
        "PAID": "Pago",
        "OPEN": "Aberto",
        "CANCELLED": "Cancelado",
        "PENDING": "Pendente",
        "REJECTED": "Rejeitado"
    }

    for r in receivables_db:
        servico_nome = "N/A"
        if r.servico_contratado and r.servico_contratado.servico:
            servico_nome = r.servico_contratado.servico.descricao

        receivables_data.append({
            "id": r.id,
            "cliente_nome": r.cliente.nome_razao_social if r.cliente else "N/A",
            "tipo": r.tipo,
            "due_date": r.due_date.strftime('%d/%m/%Y') if r.due_date else "",
            "amount": r.amount,
            "paid_amount": r.paid_amount,
            "status": status_map_fin.get(r.status, r.status),
            "paid_at": r.paid_at.strftime('%d/%m/%Y') if r.paid_at else None,
            "servico_nome": servico_nome
        })
        
    filters = {
        "start_date": start_date.strftime('%d/%m/%Y') if start_date else "",
        "end_date": end_date.strftime('%d/%m/%Y') if end_date else "",
        "status": status
    }
    
    pdf_buffer = ReportService.generate_financial_report(empresa, receivables_data, filters)
    
    filename = f"relatorio_financeiro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/clients/pdf")
def get_clients_report_pdf(
    empresa_id: int,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Gera um relatório de clientes em PDF."""
    deps.permission_checker('clients_view')(db=db, current_user=current_user)
    
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
    # Buscar todos os endereços vinculados a clientes desta empresa
    from app.models.models import EmpresaCliente, EmpresaClienteEndereco, Cliente
    from sqlalchemy import and_
    
    query = db.query(
        Cliente.id,
        Cliente.nome_razao_social,
        Cliente.cpf_cnpj,
        Cliente.email,
        Cliente.telefone,
        Cliente.is_active,
        EmpresaClienteEndereco.endereco,
        EmpresaClienteEndereco.numero,
        EmpresaClienteEndereco.bairro,
        EmpresaClienteEndereco.municipio,
        EmpresaClienteEndereco.uf,
        EmpresaClienteEndereco.complemento
    ).join(
        EmpresaCliente, Cliente.id == EmpresaCliente.cliente_id
    ).join(
        EmpresaClienteEndereco, EmpresaCliente.id == EmpresaClienteEndereco.empresa_cliente_id
    ).filter(
        EmpresaCliente.empresa_id == empresa_id
    )
    
    if q:
        pattern = f"%{q}%"
        from sqlalchemy import or_
        query = query.filter(or_(
            Cliente.nome_razao_social.ilike(pattern),
            Cliente.cpf_cnpj.ilike(pattern),
            EmpresaClienteEndereco.bairro.ilike(pattern),
            EmpresaClienteEndereco.municipio.ilike(pattern)
        ))
    
    # Ordenar por Bairro e depois por Nome
    results = query.order_by(EmpresaClienteEndereco.bairro, Cliente.nome_razao_social).all()
    
    clients_data = []
    for r in results:
        clients_data.append({
            "id": r.id,
            "nome_razao_social": r.nome_razao_social,
            "cpf_cnpj": r.cpf_cnpj,
            "email": r.email,
            "telefone": r.telefone,
            "is_active": r.is_active,
            "endereco": r.endereco,
            "numero": r.numero,
            "bairro": r.bairro or "SEM BAIRRO",
            "municipio": r.municipio,
            "uf": r.uf,
            "complemento": r.complemento
        })
        
    filters = {"q": q}
    pdf_buffer = ReportService.generate_clients_report(empresa, clients_data, filters)
    
    filename = f"relatorio_clientes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
