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

@router.get("/contracts/filters")
def get_contracts_filters(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Retorna listas de roteadores, interfaces e classes de IP de uma empresa para popular filtros."""
    deps.permission_checker('contracts_view')(db=db, current_user=current_user)
    
    from app.models.network import Router, RouterInterface, IPClass
    
    routers = db.query(Router.id, Router.nome).filter(Router.empresa_id == empresa_id).order_by(Router.nome).all()
    ip_classes = db.query(IPClass.id, IPClass.nome).filter(IPClass.empresa_id == empresa_id).order_by(IPClass.nome).all()
    
    interfaces = db.query(RouterInterface.id, RouterInterface.nome, RouterInterface.router_id)\
        .join(Router, Router.id == RouterInterface.router_id)\
        .filter(Router.empresa_id == empresa_id)\
        .order_by(RouterInterface.nome).all()
        
    return {
        "routers": [{"id": r[0], "nome": r[1]} for r in routers],
        "ip_classes": [{"id": ipc[0], "name": ipc[1]} for ipc in ip_classes],
        "interfaces": [{"id": i[0], "name": i[1], "router_id": i[2]} for i in interfaces]
    }

@router.get("/contracts/pdf")
def get_contracts_report_pdf(
    empresa_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[str] = None,
    servico_id: Optional[int] = None,
    municipio: Optional[str] = None,
    bairro: Optional[List[str]] = Query(None),
    router_id: Optional[int] = None,
    interface_id: Optional[int] = None,
    ip_class_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Gera um relatório de contratos em PDF com filtros avançados de provedor."""
    deps.permission_checker('contracts_view')(db=db, current_user=current_user)
    
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
    # Query de contratos com join de endereço para filtros de cidade/bairro
    from app.models.models import EmpresaClienteEndereco
    
    query = db.query(ServicoContratado, EmpresaClienteEndereco).join(
        EmpresaClienteEndereco, ServicoContratado.endereco_id == EmpresaClienteEndereco.id, isouter=True
    ).filter(ServicoContratado.empresa_id == empresa_id)
    
    if start_date:
        query = query.filter(func.date(ServicoContratado.created_at) >= start_date)
    if end_date:
        query = query.filter(func.date(ServicoContratado.created_at) <= end_date)
    if status:
        query = query.filter(ServicoContratado.status == status)
    if servico_id:
        query = query.filter(ServicoContratado.servico_id == servico_id)
    if router_id:
        query = query.filter(ServicoContratado.router_id == router_id)
    if interface_id:
        query = query.filter(ServicoContratado.interface_id == interface_id)
    if ip_class_id:
        query = query.filter(ServicoContratado.ip_class_id == ip_class_id)
        
    if municipio:
        query = query.filter(EmpresaClienteEndereco.municipio == municipio)
        
    if bairro:
        from sqlalchemy import or_
        conditions = []
        has_sem_bairro = "SEM BAIRRO" in bairro
        other_bairros = [b for b in bairro if b != "SEM BAIRRO"]
        
        if other_bairros:
            conditions.append(EmpresaClienteEndereco.bairro.in_(other_bairros))
        if has_sem_bairro:
            conditions.append(EmpresaClienteEndereco.bairro == None)
            conditions.append(EmpresaClienteEndereco.bairro == '')
            conditions.append(ServicoContratado.endereco_id == None)
            
        if conditions:
            query = query.filter(or_(*conditions))
            
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
    
    for c, end_inst in contracts_db:
        contracts_data.append({
            "id": c.id,
            "cliente_nome": c.cliente.nome_razao_social if c.cliente else "N/A",
            "servico_descricao": c.servico.descricao if c.servico else "N/A",
            "created_at": c.created_at.strftime('%d/%m/%Y') if c.created_at else "",
            "valor_unitario": c.valor_unitario,
            "status": status_map.get(c.status, c.status),
            # Informações adicionais para agrupamento e detalhamento
            "bairro": end_inst.bairro if end_inst else "Sem Bairro",
            "municipio": end_inst.municipio if end_inst else "",
            "endereco_completo": f"{end_inst.endereco or ''}, {end_inst.numero or ''}" if end_inst else "",
            "router_nome": c.router.nome if c.router else "",
            "interface_nome": c.interface.nome if c.interface else "",
            "ip_class_nome": c.ip_class.nome if c.ip_class else "",
            "ip_address": c.assigned_ip or ""
        })
        
    router_name = None
    if router_id:
        from app.models.network import Router
        r_obj = db.query(Router.nome).filter(Router.id == router_id).first()
        if r_obj:
            router_name = r_obj[0]
            
    interface_name = None
    if interface_id:
        from app.models.network import RouterInterface
        i_obj = db.query(RouterInterface.nome).filter(RouterInterface.id == interface_id).first()
        if i_obj:
            interface_name = i_obj[0]
            
    ip_class_name = None
    if ip_class_id:
        from app.models.network import IPClass
        ipc_obj = db.query(IPClass.nome).filter(IPClass.id == ip_class_id).first()
        if ipc_obj:
            ip_class_name = ipc_obj[0]
        
    filters = {
        "start_date": start_date.strftime('%d/%m/%Y') if start_date else "",
        "end_date": end_date.strftime('%d/%m/%Y') if end_date else "",
        "status": status,
        "municipio": municipio,
        "bairro": bairro,
        "router": router_name,
        "interface": interface_name,
        "ip_class": ip_class_name
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
    municipio: Optional[str] = None,
    bairro: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Gera um relatório financeiro em PDF com filtros avançados."""
    deps.permission_checker('receivables_view')(db=db, current_user=current_user)
    
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
    # Query de faturamento com join do endereço do cliente para filtros de cidade/bairro
    # Query de faturamento com join do endereço do cliente para filtros de cidade/bairro
    from app.models.models import Cliente, EmpresaCliente, EmpresaClienteEndereco
    from sqlalchemy.orm import aliased
    from sqlalchemy import func
    
    ClientAddress = aliased(EmpresaClienteEndereco, name="client_address")
    ContractAddress = aliased(EmpresaClienteEndereco, name="contract_address")
    
    query = db.query(Receivable, ClientAddress, ContractAddress).join(
        Cliente, Receivable.cliente_id == Cliente.id
    ).join(
        EmpresaCliente, (Cliente.id == EmpresaCliente.cliente_id) & (EmpresaCliente.empresa_id == empresa_id)
    ).join(
        ClientAddress, (EmpresaCliente.id == ClientAddress.empresa_cliente_id) & (ClientAddress.is_principal == True), isouter=True
    ).join(
        ServicoContratado, Receivable.servico_contratado_id == ServicoContratado.id, isouter=True
    ).join(
        ContractAddress, ServicoContratado.endereco_id == ContractAddress.id, isouter=True
    ).filter(
        Receivable.empresa_id == empresa_id
    )
    
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
        
    effective_municipio = func.coalesce(ContractAddress.municipio, ClientAddress.municipio)
    effective_bairro = func.coalesce(ContractAddress.bairro, ClientAddress.bairro)

    if municipio:
        query = query.filter(effective_municipio == municipio)
        
    if bairro:
        from sqlalchemy import or_
        conditions = []
        has_sem_bairro = "SEM BAIRRO" in bairro
        other_bairros = [b for b in bairro if b != "SEM BAIRRO"]
        
        if other_bairros:
            conditions.append(effective_bairro.in_(other_bairros))
        if has_sem_bairro:
            conditions.append(effective_bairro == None)
            conditions.append(effective_bairro == '')
            
        if conditions:
            query = query.filter(or_(*conditions))
        
    receivables_db = query.all()
    
    seen_receivable_ids = set()
    receivables_data = []
    status_map_fin = {
        "PAID": "Pago",
        "OPEN": "Aberto",
        "CANCELLED": "Cancelado",
        "PENDING": "Pendente",
        "REJECTED": "Rejeitado"
    }

    for r, client_addr, contract_addr in receivables_db:
        if r.id in seen_receivable_ids:
            continue
        seen_receivable_ids.add(r.id)

        # Escolhe o endereço do contrato se houver, caso contrário o principal do cliente
        end_principal = contract_addr if contract_addr else client_addr

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
            "servico_nome": servico_nome,
            # Informações adicionais de endereço
            "bairro": end_principal.bairro if end_principal else "Sem Bairro",
            "municipio": end_principal.municipio if end_principal else "",
            "endereco_completo": f"{end_principal.endereco or ''}, {end_principal.numero or ''}" if end_principal else ""
        })
        
    filters = {
        "start_date": start_date.strftime('%d/%m/%Y') if start_date else "",
        "end_date": end_date.strftime('%d/%m/%Y') if end_date else "",
        "status": status,
        "municipio": municipio,
        "bairro": bairro
    }
    
    pdf_buffer = ReportService.generate_financial_report(empresa, receivables_data, filters)
    
    filename = f"relatorio_financeiro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/clients/locations")
def get_clients_locations(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Retorna um mapeamento de cidades para seus respectivos bairros únicos dos clientes de uma empresa."""
    deps.permission_checker('clients_view')(db=db, current_user=current_user)
    
    from app.models.models import EmpresaCliente, EmpresaClienteEndereco
    from collections import defaultdict
    
    results = db.query(EmpresaClienteEndereco.municipio, EmpresaClienteEndereco.bairro)\
        .join(EmpresaCliente, EmpresaCliente.id == EmpresaClienteEndereco.empresa_cliente_id)\
        .filter(EmpresaCliente.empresa_id == empresa_id)\
        .distinct().all()
        
    locations = defaultdict(set)
    for m, b in results:
        city = m.strip() if m else ""
        neighborhood = b.strip() if b else ""
        if city:
            locations[city].add(neighborhood or "SEM BAIRRO")
            
    return {city: sorted(list(neighs)) for city, neighs in locations.items() if city}

@router.get("/clients/pdf")
def get_clients_report_pdf(
    empresa_id: int,
    q: Optional[str] = None,
    municipio: Optional[str] = None,
    bairro: Optional[List[str]] = Query(None),
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
        
    if municipio:
        query = query.filter(EmpresaClienteEndereco.municipio == municipio)
        
    if bairro:
        from sqlalchemy import or_
        conditions = []
        has_sem_bairro = "SEM BAIRRO" in bairro
        other_bairros = [b for b in bairro if b != "SEM BAIRRO"]
        
        if other_bairros:
            conditions.append(EmpresaClienteEndereco.bairro.in_(other_bairros))
        if has_sem_bairro:
            conditions.append(EmpresaClienteEndereco.bairro == None)
            conditions.append(EmpresaClienteEndereco.bairro == '')
            
        if conditions:
            query = query.filter(or_(*conditions))
    
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
        
    filters = {"q": q, "municipio": municipio, "bairro": bairro}
    pdf_buffer = ReportService.generate_clients_report(empresa, clients_data, filters)
    
    filename = f"relatorio_clientes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
