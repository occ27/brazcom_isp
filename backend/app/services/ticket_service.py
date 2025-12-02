from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, and_, or_, case
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.models.models import Ticket, TicketComment, StatusTicket, Usuario, Cliente
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketCommentCreate, TicketCommentUpdate, TicketStats


class TicketService:

    @staticmethod
    def create_ticket(db: Session, ticket_data: TicketCreate, empresa_id: int, criado_por_id: int) -> Dict[str, Any]:
        """Cria um novo ticket de suporte."""
        db_ticket = Ticket(
            **ticket_data.model_dump(),
            empresa_id=empresa_id,
            criado_por_id=criado_por_id,
            status=StatusTicket.ABERTO
        )
        db.add(db_ticket)
        db.commit()
        db.refresh(db_ticket)

        # Busca os dados relacionados para retornar um dicionário completo
        # Usar aliases para evitar conflito de nomes na tabela users
        criado_por_alias = aliased(Usuario, name='criado_por')
        atribuido_para_alias = aliased(Usuario, name='atribuido_para')
        resolvido_por_alias = aliased(Usuario, name='resolvido_por')
        
        ticket_with_relations = db.query(
            Ticket,
            Cliente.nome_razao_social.label('cliente_nome'),
            criado_por_alias.full_name.label('criado_por_nome'),
            atribuido_para_alias.full_name.label('atribuido_para_nome'),
            resolvido_por_alias.full_name.label('resolvido_por_nome'),
            func.count(TicketComment.id).label('comentarios_count')
        ).outerjoin(
            Cliente, Ticket.cliente_id == Cliente.id
        ).join(
            criado_por_alias, Ticket.criado_por_id == criado_por_alias.id
        ).outerjoin(
            atribuido_para_alias, Ticket.atribuido_para_id == atribuido_para_alias.id
        ).outerjoin(
            resolvido_por_alias, Ticket.resolvido_por_id == resolvido_por_alias.id
        ).outerjoin(
            TicketComment, Ticket.id == TicketComment.ticket_id
        ).filter(
            Ticket.id == db_ticket.id
        ).group_by(
            Ticket.id, Cliente.nome_razao_social, criado_por_alias.full_name
        ).first()

        if ticket_with_relations:
            return {
                'id': ticket_with_relations[0].id,
                'empresa_id': ticket_with_relations[0].empresa_id,
                'cliente_id': ticket_with_relations[0].cliente_id,
                'criado_por_id': ticket_with_relations[0].criado_por_id,
                'atribuido_para_id': ticket_with_relations[0].atribuido_para_id,
                'titulo': ticket_with_relations[0].titulo,
                'descricao': ticket_with_relations[0].descricao,
                'status': ticket_with_relations[0].status,
                'prioridade': ticket_with_relations[0].prioridade,
                'categoria': ticket_with_relations[0].categoria,
                'resolucao': ticket_with_relations[0].resolucao,
                'resolvido_em': ticket_with_relations[0].resolvido_em,
                'resolvido_por_id': ticket_with_relations[0].resolvido_por_id,
                'prazo_resolucao': ticket_with_relations[0].prazo_resolucao,
                'tempo_gasto_minutos': ticket_with_relations[0].tempo_gasto_minutos,
                'is_active': ticket_with_relations[0].is_active,
                'created_at': ticket_with_relations[0].created_at,
                'updated_at': ticket_with_relations[0].updated_at,
                'cliente_nome': ticket_with_relations[1],
                'criado_por_nome': ticket_with_relations[2],
                'atribuido_para_nome': ticket_with_relations[3],
                'resolvido_por_nome': ticket_with_relations[4],
                'comentarios_count': ticket_with_relations[5] or 0
            }
        return None

    @staticmethod
    def get_tickets(
        db: Session,
        empresa_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[StatusTicket] = None,
        prioridade: Optional[str] = None,
        categoria: Optional[str] = None,
        cliente_id: Optional[int] = None,
        atribuido_para_id: Optional[int] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Busca tickets com filtros opcionais."""
        # Usar aliases para evitar conflito de nomes na tabela users
        criado_por_alias = aliased(Usuario, name='criado_por')
        atribuido_para_alias = aliased(Usuario, name='atribuido_para')
        resolvido_por_alias = aliased(Usuario, name='resolvido_por')
        
        query = db.query(
            Ticket,
            Cliente.nome_razao_social.label('cliente_nome'),
            criado_por_alias.full_name.label('criado_por_nome'),
            atribuido_para_alias.full_name.label('atribuido_para_nome'),
            resolvido_por_alias.full_name.label('resolvido_por_nome'),
            func.count(TicketComment.id).label('comentarios_count')
        ).outerjoin(
            Cliente, Ticket.cliente_id == Cliente.id
        ).join(
            criado_por_alias, Ticket.criado_por_id == criado_por_alias.id
        ).outerjoin(
            atribuido_para_alias, Ticket.atribuido_para_id == atribuido_para_alias.id
        ).outerjoin(
            resolvido_por_alias, Ticket.resolvido_por_id == resolvido_por_alias.id
        ).outerjoin(
            TicketComment, Ticket.id == TicketComment.ticket_id
        ).filter(
            Ticket.empresa_id == empresa_id,
            Ticket.is_active == True
        ).group_by(
            Ticket.id, Cliente.nome_razao_social, criado_por_alias.full_name
        )

        if status:
            query = query.filter(Ticket.status == status)
        if prioridade:
            query = query.filter(Ticket.prioridade == prioridade)
        if categoria:
            query = query.filter(Ticket.categoria == categoria)
        if cliente_id:
            query = query.filter(Ticket.cliente_id == cliente_id)
        if atribuido_para_id:
            query = query.filter(Ticket.atribuido_para_id == atribuido_para_id)
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                or_(
                    Ticket.titulo.ilike(search_filter),
                    Ticket.descricao.ilike(search_filter)
                )
            )

        query = query.order_by(Ticket.created_at.desc())
        results = query.offset(skip).limit(limit).all()

        # Converte os resultados para objetos Ticket com dados relacionados
        tickets = []
        for row in results:
            ticket_dict = {
                'id': row[0].id,
                'empresa_id': row[0].empresa_id,
                'cliente_id': row[0].cliente_id,
                'criado_por_id': row[0].criado_por_id,
                'atribuido_para_id': row[0].atribuido_para_id,
                'titulo': row[0].titulo,
                'descricao': row[0].descricao,
                'status': row[0].status,
                'prioridade': row[0].prioridade,
                'categoria': row[0].categoria,
                'resolucao': row[0].resolucao,
                'resolvido_em': row[0].resolvido_em,
                'resolvido_por_id': row[0].resolvido_por_id,
                'prazo_resolucao': row[0].prazo_resolucao,
                'tempo_gasto_minutos': row[0].tempo_gasto_minutos,
                'is_active': row[0].is_active,
                'created_at': row[0].created_at,
                'updated_at': row[0].updated_at,
                'cliente_nome': row[1],
                'criado_por_nome': row[2],
                'atribuido_para_nome': row[3],
                'resolvido_por_nome': row[4],
                'comentarios_count': row[5] or 0
            }
            tickets.append(ticket_dict)

        return tickets

    @staticmethod
    def get_ticket_by_id(db: Session, ticket_id: int, empresa_id: int) -> Optional[Dict[str, Any]]:
        """Busca um ticket específico por ID."""
        # Usar aliases para evitar conflito de nomes na tabela users
        criado_por_alias = aliased(Usuario, name='criado_por')
        atribuido_para_alias = aliased(Usuario, name='atribuido_para')
        resolvido_por_alias = aliased(Usuario, name='resolvido_por')
        
        ticket = db.query(
            Ticket,
            Cliente.nome_razao_social.label('cliente_nome'),
            criado_por_alias.full_name.label('criado_por_nome'),
            atribuido_para_alias.full_name.label('atribuido_para_nome'),
            resolvido_por_alias.full_name.label('resolvido_por_nome'),
            func.count(TicketComment.id).label('comentarios_count')
        ).outerjoin(
            Cliente, Ticket.cliente_id == Cliente.id
        ).join(
            criado_por_alias, Ticket.criado_por_id == criado_por_alias.id
        ).outerjoin(
            atribuido_para_alias, Ticket.atribuido_para_id == atribuido_para_alias.id
        ).outerjoin(
            resolvido_por_alias, Ticket.resolvido_por_id == resolvido_por_alias.id
        ).outerjoin(
            TicketComment, Ticket.id == TicketComment.ticket_id
        ).filter(
            Ticket.id == ticket_id,
            Ticket.empresa_id == empresa_id,
            Ticket.is_active == True
        ).group_by(
            Ticket.id, Cliente.nome_razao_social, criado_por_alias.full_name
        ).first()

        if ticket:
            return {
                'id': ticket[0].id,
                'empresa_id': ticket[0].empresa_id,
                'cliente_id': ticket[0].cliente_id,
                'criado_por_id': ticket[0].criado_por_id,
                'atribuido_para_id': ticket[0].atribuido_para_id,
                'titulo': ticket[0].titulo,
                'descricao': ticket[0].descricao,
                'status': ticket[0].status,
                'prioridade': ticket[0].prioridade,
                'categoria': ticket[0].categoria,
                'resolucao': ticket[0].resolucao,
                'resolvido_em': ticket[0].resolvido_em,
                'resolvido_por_id': ticket[0].resolvido_por_id,
                'prazo_resolucao': ticket[0].prazo_resolucao,
                'tempo_gasto_minutos': ticket[0].tempo_gasto_minutos,
                'is_active': ticket[0].is_active,
                'created_at': ticket[0].created_at,
                'updated_at': ticket[0].updated_at,
                'cliente_nome': ticket[1],
                'criado_por_nome': ticket[2],
                'atribuido_para_nome': ticket[3],
                'resolvido_por_nome': ticket[4],
                'comentarios_count': ticket[5] or 0
            }
        return None

    @staticmethod
    def update_ticket(db: Session, ticket_id: int, empresa_id: int, ticket_data: TicketUpdate, updated_by_id: int) -> Optional[Dict[str, Any]]:
        """Atualiza um ticket existente."""
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.empresa_id == empresa_id,
            Ticket.is_active == True
        ).first()

        if not ticket:
            return None

        update_data = ticket_data.model_dump(exclude_unset=True)

        # Se está mudando para resolvido, registra data e usuário
        if 'status' in update_data and update_data['status'] in [StatusTicket.RESOLVIDO, StatusTicket.FECHADO]:
            if ticket.status not in [StatusTicket.RESOLVIDO, StatusTicket.FECHADO]:
                update_data['resolvido_em'] = datetime.utcnow()
                update_data['resolvido_por_id'] = updated_by_id

        for field, value in update_data.items():
            setattr(ticket, field, value)

        db.commit()
        db.refresh(ticket)

        # Busca os dados relacionados para retornar um dicionário completo
        # Usar aliases para evitar conflito de nomes na tabela users
        criado_por_alias = aliased(Usuario, name='criado_por')
        atribuido_para_alias = aliased(Usuario, name='atribuido_para')
        resolvido_por_alias = aliased(Usuario, name='resolvido_por')
        
        ticket_with_relations = db.query(
            Ticket,
            Cliente.nome_razao_social.label('cliente_nome'),
            criado_por_alias.full_name.label('criado_por_nome'),
            atribuido_para_alias.full_name.label('atribuido_para_nome'),
            resolvido_por_alias.full_name.label('resolvido_por_nome'),
            func.count(TicketComment.id).label('comentarios_count')
        ).outerjoin(
            Cliente, Ticket.cliente_id == Cliente.id
        ).join(
            criado_por_alias, Ticket.criado_por_id == criado_por_alias.id
        ).outerjoin(
            atribuido_para_alias, Ticket.atribuido_para_id == atribuido_para_alias.id
        ).outerjoin(
            resolvido_por_alias, Ticket.resolvido_por_id == resolvido_por_alias.id
        ).outerjoin(
            TicketComment, Ticket.id == TicketComment.ticket_id
        ).filter(
            Ticket.id == ticket.id
        ).group_by(
            Ticket.id, Cliente.nome_razao_social, criado_por_alias.full_name
        ).first()

        if ticket_with_relations:
            return {
                'id': ticket_with_relations[0].id,
                'empresa_id': ticket_with_relations[0].empresa_id,
                'cliente_id': ticket_with_relations[0].cliente_id,
                'criado_por_id': ticket_with_relations[0].criado_por_id,
                'atribuido_para_id': ticket_with_relations[0].atribuido_para_id,
                'titulo': ticket_with_relations[0].titulo,
                'descricao': ticket_with_relations[0].descricao,
                'status': ticket_with_relations[0].status,
                'prioridade': ticket_with_relations[0].prioridade,
                'categoria': ticket_with_relations[0].categoria,
                'resolucao': ticket_with_relations[0].resolucao,
                'resolvido_em': ticket_with_relations[0].resolvido_em,
                'resolvido_por_id': ticket_with_relations[0].resolvido_por_id,
                'prazo_resolucao': ticket_with_relations[0].prazo_resolucao,
                'tempo_gasto_minutos': ticket_with_relations[0].tempo_gasto_minutos,
                'is_active': ticket_with_relations[0].is_active,
                'created_at': ticket_with_relations[0].created_at,
                'updated_at': ticket_with_relations[0].updated_at,
                'cliente_nome': ticket_with_relations[1],
                'criado_por_nome': ticket_with_relations[2],
                'atribuido_para_nome': ticket_with_relations[3],
                'resolvido_por_nome': ticket_with_relations[4],
                'comentarios_count': ticket_with_relations[5] or 0
            }
        return None

    @staticmethod
    def delete_ticket(db: Session, ticket_id: int, empresa_id: int) -> bool:
        """Remove um ticket (soft delete)."""
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.empresa_id == empresa_id
        ).first()

        if not ticket:
            return False

        ticket.is_active = False
        db.commit()
        return True

    @staticmethod
    def add_comment(db: Session, ticket_id: int, empresa_id: int, comment_data: TicketCommentCreate, usuario_id: int) -> Optional[TicketComment]:
        """Adiciona um comentário a um ticket."""
        # Verifica se o ticket existe
        ticket = db.query(Ticket).filter(
            Ticket.id == ticket_id,
            Ticket.empresa_id == empresa_id,
            Ticket.is_active == True
        ).first()

        if not ticket:
            return None

        db_comment = TicketComment(
            **comment_data.model_dump(),
            ticket_id=ticket_id,
            usuario_id=usuario_id
        )
        db.add(db_comment)
        db.commit()
        db.refresh(db_comment)
        return db_comment

    @staticmethod
    def get_ticket_comments(db: Session, ticket_id: int, empresa_id: int) -> List[TicketComment]:
        """Busca todos os comentários de um ticket."""
        return db.query(TicketComment).join(Ticket).filter(
            TicketComment.ticket_id == ticket_id,
            Ticket.empresa_id == empresa_id,
            Ticket.is_active == True
        ).order_by(TicketComment.created_at.asc()).all()

    @staticmethod
    def get_ticket_stats(db: Session, empresa_id: int) -> TicketStats:
        """Retorna estatísticas dos tickets da empresa."""
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # Query básica para contagem por status
        status_counts = db.query(
            Ticket.status,
            func.count(Ticket.id).label('count')
        ).filter(
            Ticket.empresa_id == empresa_id,
            Ticket.is_active == True
        ).group_by(Ticket.status).all()

        # Converte para dicionário
        status_dict = {status.value: count for status, count in status_counts}

        # Estatísticas temporais
        tickets_hoje = db.query(func.count(Ticket.id)).filter(
            Ticket.empresa_id == empresa_id,
            Ticket.is_active == True,
            func.date(Ticket.created_at) == func.date(now)
        ).scalar() or 0

        tickets_semana = db.query(func.count(Ticket.id)).filter(
            Ticket.empresa_id == empresa_id,
            Ticket.is_active == True,
            Ticket.created_at >= week_ago
        ).scalar() or 0

        tickets_mes = db.query(func.count(Ticket.id)).filter(
            Ticket.empresa_id == empresa_id,
            Ticket.is_active == True,
            Ticket.created_at >= month_ago
        ).scalar() or 0

        # Tempo médio de resolução (em horas)
        avg_resolution_time = db.query(
            func.avg(
                func.extract('epoch', Ticket.resolvido_em - Ticket.created_at) / 3600
            )
        ).filter(
            Ticket.empresa_id == empresa_id,
            Ticket.is_active == True,
            Ticket.resolvido_em.isnot(None)
        ).scalar()

        return TicketStats(
            total_tickets=sum(status_dict.values()),
            tickets_abertos=status_dict.get('ABERTO', 0),
            tickets_em_andamento=status_dict.get('EM_ANDAMENTO', 0),
            tickets_resolvidos=status_dict.get('RESOLVIDO', 0),
            tickets_fechados=status_dict.get('FECHADO', 0),
            tickets_hoje=tickets_hoje,
            tickets_semana=tickets_semana,
            tickets_mes=tickets_mes,
            tempo_medio_resolucao_horas=round(avg_resolution_time, 2) if avg_resolution_time else None
        )