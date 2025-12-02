from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.models import StatusTicket, PrioridadeTicket, CategoriaTicket


class TicketBase(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=255)
    descricao: str = Field(..., min_length=1)
    prioridade: PrioridadeTicket = PrioridadeTicket.NORMAL
    categoria: CategoriaTicket = CategoriaTicket.SUPORTE
    cliente_id: Optional[int] = None
    atribuido_para_id: Optional[int] = None
    prazo_resolucao: Optional[datetime] = None


class TicketCreate(TicketBase):
    cliente_id: int = Field(..., description="ID do cliente obrigatório")


class TicketUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=255)
    descricao: Optional[str] = None
    status: Optional[StatusTicket] = None
    prioridade: Optional[PrioridadeTicket] = None
    categoria: Optional[CategoriaTicket] = None
    atribuido_para_id: Optional[int] = None
    resolucao: Optional[str] = None
    prazo_resolucao: Optional[datetime] = None
    tempo_gasto_minutos: Optional[int] = Field(None, ge=0)


class TicketCommentBase(BaseModel):
    comentario: str = Field(..., min_length=1)
    is_internal: bool = False


class TicketCommentCreate(TicketCommentBase):
    pass


class TicketCommentUpdate(BaseModel):
    comentario: Optional[str] = Field(None, min_length=1)
    is_internal: Optional[bool] = None


class TicketComment(TicketCommentBase):
    id: int
    ticket_id: int
    usuario_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Ticket(TicketBase):
    id: int
    empresa_id: int
    criado_por_id: int
    status: StatusTicket
    resolvido_em: Optional[datetime] = None
    resolvido_por_id: Optional[int] = None
    tempo_gasto_minutos: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Dados relacionados
    cliente_nome: Optional[str] = None
    criado_por_nome: str
    atribuido_para_nome: Optional[str] = None
    resolvido_por_nome: Optional[str] = None
    comentarios_count: int = 0

    class Config:
        from_attributes = True


class TicketDetail(Ticket):
    comentarios: List[TicketComment] = []

    class Config:
        from_attributes = True


class TicketStats(BaseModel):
    total_tickets: int
    tickets_abertos: int
    tickets_em_andamento: int
    tickets_resolvidos: int
    tickets_fechados: int
    tickets_hoje: int
    tickets_semana: int
    tickets_mes: int
    tempo_medio_resolucao_horas: Optional[float] = None