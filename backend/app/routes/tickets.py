from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.api import deps
from app.models.models import Usuario, StatusTicket
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
    db: Session = Depends(get_db)
):
    """Cria um novo ticket de suporte."""
    if not current_user.active_empresa_id:
        raise HTTPException(status_code=400, detail="Usuário deve ter empresa ativa")
    
    empresa_id = current_user.active_empresa_id
    return TicketService.create_ticket(db, ticket, empresa_id, current_user.id)


@router.get("/", response_model=List[Ticket])
def get_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[StatusTicket] = None,
    prioridade: Optional[str] = None,
    categoria: Optional[str] = None,
    cliente_id: Optional[int] = None,
    atribuido_para_id: Optional[int] = None,
    search: Optional[str] = None,
    _: bool = Depends(deps.permission_checker("tickets_view")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Lista tickets com filtros opcionais."""
    if not current_user.active_empresa_id:
        raise HTTPException(status_code=400, detail="Usuário deve ter empresa ativa")
    
    empresa_id = current_user.active_empresa_id
    return TicketService.get_tickets(
        db, empresa_id, skip, limit, status, prioridade,
        categoria, cliente_id, atribuido_para_id, search
    )


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(
    ticket_id: int,
    _: bool = Depends(deps.permission_checker("tickets_view")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Busca um ticket específico por ID."""
    if not current_user.active_empresa_id:
        raise HTTPException(status_code=400, detail="Usuário deve ter empresa ativa")
    
    empresa_id = current_user.active_empresa_id
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
    db: Session = Depends(get_db)
):
    """Atualiza um ticket existente."""
    if not current_user.active_empresa_id:
        raise HTTPException(status_code=400, detail="Usuário deve ter empresa ativa")
    
    empresa_id = current_user.active_empresa_id
    ticket = TicketService.update_ticket(db, ticket_id, empresa_id, ticket_update, current_user.id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    return ticket


@router.delete("/{ticket_id}")
def delete_ticket(
    ticket_id: int,
    _: bool = Depends(deps.permission_checker("tickets_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove um ticket (soft delete)."""
    if not current_user.active_empresa_id:
        raise HTTPException(status_code=400, detail="Usuário deve ter empresa ativa")
    
    empresa_id = current_user.active_empresa_id
    
    # Verificar se o usuário é superuser (pode excluir qualquer ticket)
    if current_user.is_superuser:
        success = TicketService.delete_ticket(db, ticket_id, empresa_id)
        if not success:
            raise HTTPException(status_code=404, detail="Ticket não encontrado")
        return {"message": "Ticket removido com sucesso"}
    
    # Para usuários não-superuser, verificar se é Secretary e se o ticket está ABERTO
    from app.models.access_control import Role, user_role_association
    
    # Verificar se o usuário tem role Secretary
    secretary_role = db.query(Role).filter(Role.name == "Secretary").first()
    if secretary_role:
        has_secretary_role = db.query(user_role_association).filter(
            user_role_association.c.user_id == current_user.id,
            user_role_association.c.role_id == secretary_role.id,
            (user_role_association.c.empresa_id == None) | (user_role_association.c.empresa_id == empresa_id)
        ).first() is not None
        
        if has_secretary_role:
            # Secretary só pode excluir tickets ABERTO
            ticket = TicketService.get_ticket_by_id(db, ticket_id, empresa_id)
            if not ticket:
                raise HTTPException(status_code=404, detail="Ticket não encontrado")
            
            if ticket.get('status') != 'ABERTO':
                raise HTTPException(
                    status_code=403, 
                    detail="Secretaries só podem excluir tickets no status ABERTO"
                )
            
            success = TicketService.delete_ticket(db, ticket_id, empresa_id)
            if not success:
                raise HTTPException(status_code=404, detail="Ticket não encontrado")
            return {"message": "Ticket removido com sucesso"}
    
    # Para outros usuários com permissão tickets_manage, permitir exclusão normal
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
    db: Session = Depends(get_db)
):
    """Adiciona um comentário a um ticket."""
    if not current_user.active_empresa_id:
        raise HTTPException(status_code=400, detail="Usuário deve ter empresa ativa")
    
    empresa_id = current_user.active_empresa_id
    new_comment = TicketService.add_comment(db, ticket_id, empresa_id, comment, current_user.id)
    if not new_comment:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    return new_comment


@router.get("/{ticket_id}/comments", response_model=List[TicketComment])
def get_ticket_comments(
    ticket_id: int,
    _: bool = Depends(deps.permission_checker("tickets_view")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Busca todos os comentários de um ticket."""
    if not current_user.active_empresa_id:
        raise HTTPException(status_code=400, detail="Usuário deve ter empresa ativa")
    
    empresa_id = current_user.active_empresa_id
    # Verifica se o ticket existe
    ticket = TicketService.get_ticket_by_id(db, ticket_id, empresa_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    return TicketService.get_ticket_comments(db, ticket_id, empresa_id)


@router.get("/stats/summary", response_model=TicketStats)
def get_ticket_stats(
    _: bool = Depends(deps.permission_checker("tickets_view")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retorna estatísticas dos tickets da empresa."""
    if not current_user.active_empresa_id:
        raise HTTPException(status_code=400, detail="Usuário deve ter empresa ativa")
    
    empresa_id = current_user.active_empresa_id
    return TicketService.get_ticket_stats(db, empresa_id)