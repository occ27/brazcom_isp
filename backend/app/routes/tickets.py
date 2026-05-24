from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.api import deps
from app.models.models import Usuario, StatusTicket, Empresa, UsuarioEmpresa
from app.schemas.ticket import (
    Ticket, TicketCreate, TicketUpdate, TicketDetail,
    TicketComment, TicketCommentCreate, TicketCommentUpdate,
    TicketStats
)
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("/", response_model=Ticket)
def create_ticket(
    ticket: TicketCreate,
    _: bool = Depends(deps.permission_checker("tickets_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Cria um novo ticket de suporte."""
    empresa_id = active_empresa.id
    return TicketService.create_ticket(db, ticket, empresa_id, current_user.id)


@router.get("/")
def get_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    prioridade: Optional[str] = None,
    categoria: Optional[str] = None,
    cliente_id: Optional[int] = None,
    atribuido_para_id: Optional[int] = None,
    search: Optional[str] = None,
    _: bool = Depends(deps.permission_checker("tickets_view")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Lista tickets com filtros opcionais."""
    empresa_id = active_empresa.id
    
    # Calcular total para paginação
    total = TicketService.count_tickets(
        db, empresa_id, status, prioridade,
        categoria, cliente_id, atribuido_para_id, search,
        current_user_id=current_user.id
    )
        
    tickets = TicketService.get_tickets(
        db, empresa_id, skip, limit, status, prioridade,
        categoria, cliente_id, atribuido_para_id, search,
        current_user_id=current_user.id
    )

    return {"data": tickets, "total": total}


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(
    ticket_id: int,
    _: bool = Depends(deps.permission_checker("tickets_view")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Busca um ticket específico por ID."""
    empresa_id = active_empresa.id
    ticket = TicketService.get_ticket_by_id(db, ticket_id, empresa_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    return ticket


@router.put("/{ticket_id}", response_model=Ticket)
def update_ticket(
    ticket_id: int,
    ticket_update: TicketUpdate,
    _: bool = Depends(deps.permission_checker("tickets_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Atualiza um ticket existente."""
    empresa_id = active_empresa.id
    
    # Buscar o ticket no banco para validar o status atual
    existing_ticket = db.query(Usuario).filter(Usuario.id == current_user.id).first() # Just checking db access
    from app.models.models import Ticket as TicketModel
    db_ticket = db.query(TicketModel).filter(
        TicketModel.id == ticket_id,
        TicketModel.empresa_id == empresa_id,
        TicketModel.is_active == True
    ).first()
    
    if not db_ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
        
    if db_ticket.status in [StatusTicket.RESOLVIDO, StatusTicket.FECHADO, StatusTicket.CANCELADO]:
        # Verificar se o usuário é admin/superuser
        is_admin = False
        if not current_user.is_superuser:
            assoc_user = db.query(UsuarioEmpresa).filter(
                UsuarioEmpresa.usuario_id == current_user.id,
                UsuarioEmpresa.empresa_id == empresa_id,
                UsuarioEmpresa.is_admin == True
            ).first()
            if assoc_user:
                is_admin = True
                
        if not current_user.is_superuser and not is_admin:
            raise HTTPException(
                status_code=403, 
                detail="Tickets finalizados (resolvidos, fechados ou cancelados) só podem ser alterados por administradores"
            )

    ticket = TicketService.update_ticket(db, ticket_id, empresa_id, ticket_update, current_user.id)
    return ticket


@router.delete("/{ticket_id}")
def delete_ticket(
    ticket_id: int,
    _: bool = Depends(deps.permission_checker("tickets_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Remove um ticket (soft delete). Apenas para superusers ou administradores da empresa."""
    empresa_id = active_empresa.id
    
    # Verificar se o usuário é superuser ou admin da empresa
    is_admin = False
    if not current_user.is_superuser:
        assoc_user = db.query(UsuarioEmpresa).filter(
            UsuarioEmpresa.usuario_id == current_user.id,
            UsuarioEmpresa.empresa_id == empresa_id,
            UsuarioEmpresa.is_admin == True
        ).first()
        if assoc_user:
            is_admin = True

    if not current_user.is_superuser and not is_admin:
        raise HTTPException(
            status_code=403, 
            detail="Apenas administradores da empresa ou superusuários podem excluir tickets"
        )
    
    success = TicketService.delete_ticket(db, ticket_id, empresa_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    return {"message": "Ticket removido com sucesso"}


@router.post("/{ticket_id}/comments", response_model=TicketComment)
def add_comment(
    ticket_id: int,
    comment: TicketCommentCreate,
    _: bool = Depends(deps.permission_checker("tickets_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Adiciona um comentário a um ticket."""
    empresa_id = active_empresa.id
    new_comment = TicketService.add_comment(db, ticket_id, empresa_id, comment, current_user.id)
    if not new_comment:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    return new_comment


@router.get("/{ticket_id}/comments", response_model=List[TicketComment])
def get_ticket_comments(
    ticket_id: int,
    _: bool = Depends(deps.permission_checker("tickets_view")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Busca todos os comentários de um ticket."""
    empresa_id = active_empresa.id
    # Verifica se o ticket existe
    ticket = TicketService.get_ticket_by_id(db, ticket_id, empresa_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    return TicketService.get_ticket_comments(db, ticket_id, empresa_id)


@router.get("/stats/summary", response_model=TicketStats)
def get_ticket_stats(
    _: bool = Depends(deps.permission_checker("tickets_view")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Retorna estatísticas dos tickets da empresa."""
    empresa_id = active_empresa.id
    return TicketService.get_ticket_stats(db, empresa_id)