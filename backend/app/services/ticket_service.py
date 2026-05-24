from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, and_, or_, case
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import HTTPException

from app.models.models import Ticket, TicketComment, StatusTicket, Usuario, Cliente, EmpresaCliente, ServicoContratado
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketCommentCreate, TicketCommentUpdate, TicketStats


class TicketService:

    @staticmethod
    def create_ticket(db: Session, ticket_data: TicketCreate, empresa_id: int, criado_por_id: int) -> Dict[str, Any]:
        """Cria um novo ticket de suporte."""
        cliente_id_to_save = ticket_data.cliente_id

        # Validar contrato_id se for informado
        if ticket_data.contrato_id is not None:
            contrato = db.query(ServicoContratado).filter(
                ServicoContratado.id == ticket_data.contrato_id,
                ServicoContratado.empresa_id == empresa_id,
                ServicoContratado.is_active == True
            ).first()
            if not contrato:
                raise HTTPException(status_code=404, detail="Contrato não encontrado ou inativo")
            
            if ticket_data.cliente_id is not None and ticket_data.cliente_id != contrato.cliente_id:
                raise HTTPException(status_code=400, detail="O contrato informado não pertence ao cliente selecionado")
            
            cliente_id_to_save = contrato.cliente_id

        if cliente_id_to_save is not None:
            # Verifica se o cliente existe e pertence a esta empresa (via EmpresaCliente ou legacy empresa_id)
            client_exists = db.query(Cliente).filter(
                Cliente.id == cliente_id_to_save,
                Cliente.is_active == True
            ).first()
            if not client_exists:
                raise HTTPException(status_code=404, detail="Cliente não encontrado")
                
            has_assoc = db.query(EmpresaCliente).filter(
                EmpresaCliente.cliente_id == cliente_id_to_save,
                EmpresaCliente.empresa_id == empresa_id
            ).first() is not None or client_exists.empresa_id == empresa_id
            
            if not has_assoc:
                raise HTTPException(
                    status_code=400,
                    detail="O cliente selecionado não pertence à empresa/provedor ativo"
                )

        ticket_dict = ticket_data.model_dump()
        ticket_dict['cliente_id'] = cliente_id_to_save

        db_ticket = Ticket(
            **ticket_dict,
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
            func.count(TicketComment.id).label('comentarios_count'),
            ServicoContratado.numero_contrato.label('contrato_numero'),
            ServicoContratado.endereco_instalacao.label('contrato_endereco')
        ).outerjoin(
            Cliente, Ticket.cliente_id == Cliente.id
        ).outerjoin(
            ServicoContratado, Ticket.contrato_id == ServicoContratado.id
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
            Ticket.id, 
            Cliente.nome_razao_social, 
            criado_por_alias.full_name, 
            ServicoContratado.numero_contrato, 
            ServicoContratado.endereco_instalacao
        ).first()

        if ticket_with_relations:
            return {
                'id': ticket_with_relations[0].id,
                'empresa_id': ticket_with_relations[0].empresa_id,
                'cliente_id': ticket_with_relations[0].cliente_id,
                'contrato_id': ticket_with_relations[0].contrato_id,
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
                'comentarios_count': ticket_with_relations[5] or 0,
                'contrato_numero': ticket_with_relations[6],
                'contrato_endereco': ticket_with_relations[7],
                'foto_onu_serial': ticket_with_relations[0].foto_onu_serial,
                'foto_equipamentos': ticket_with_relations[0].foto_equipamentos,
                'foto_velocidade': ticket_with_relations[0].foto_velocidade,
                'foto_cto': ticket_with_relations[0].foto_cto,
                'splitter_cto': ticket_with_relations[0].splitter_cto,
                'material_utilizado': ticket_with_relations[0].material_utilizado,
                'problema_encontrado': ticket_with_relations[0].problema_encontrado
            }
        return None

    @staticmethod
    def get_tickets(
        db: Session,
        empresa_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        prioridade: Optional[str] = None,
        categoria: Optional[str] = None,
        cliente_id: Optional[int] = None,
        atribuido_para_id: Optional[int] = None,
        search: Optional[str] = None,
        current_user_id: Optional[int] = None
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
            func.count(TicketComment.id).label('comentarios_count'),
            ServicoContratado.numero_contrato.label('contrato_numero'),
            ServicoContratado.endereco_instalacao.label('contrato_endereco')
        ).outerjoin(
            Cliente, Ticket.cliente_id == Cliente.id
        ).outerjoin(
            ServicoContratado, Ticket.contrato_id == ServicoContratado.id
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
            Ticket.id, 
            Cliente.nome_razao_social, 
            criado_por_alias.full_name,
            ServicoContratado.numero_contrato,
            ServicoContratado.endereco_instalacao
        )

        # Filtragem por role "technical"
        if current_user_id:
            # 1. Verificar se o usuário é superuser ou administrador da empresa
            is_admin_or_superuser = False
            user = db.query(Usuario).filter(Usuario.id == current_user_id).first()
            if user:
                if user.is_superuser:
                    is_admin_or_superuser = True
                else:
                    from app.models.models import UsuarioEmpresa
                    assoc = db.query(UsuarioEmpresa).filter(
                        UsuarioEmpresa.usuario_id == current_user_id,
                        UsuarioEmpresa.empresa_id == empresa_id
                    ).first()
                    if assoc and assoc.is_admin:
                        is_admin_or_superuser = True

            # 2. Se não for admin nem superuser, verificar se tem a role "technical"
            if not is_admin_or_superuser:
                from app.models.access_control import Role, user_role_association
                is_technical = db.query(Role).join(
                    user_role_association,
                    Role.id == user_role_association.c.role_id
                ).filter(
                    user_role_association.c.user_id == current_user_id,
                    Role.name.ilike("technical"),
                    or_(
                        user_role_association.c.empresa_id == empresa_id,
                        user_role_association.c.empresa_id == None
                    )
                ).first() is not None

                # 3. Se for técnico, aplicar restrição: apenas tickets atribuídos ao próprio técnico ou não atribuídos (None)
                if is_technical:
                    query = query.filter(
                        or_(
                            Ticket.atribuido_para_id == None,
                            Ticket.atribuido_para_id == current_user_id
                        )
                    )

        if status:
            status_list = [s.strip() for s in status.split(',')]
            if len(status_list) == 1:
                query = query.filter(Ticket.status == status_list[0])
            else:
                query = query.filter(Ticket.status.in_(status_list))
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
                'contrato_id': row[0].contrato_id,
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
                'comentarios_count': row[5] or 0,
                'contrato_numero': row[6],
                'contrato_endereco': row[7],
                'foto_onu_serial': row[0].foto_onu_serial,
                'foto_equipamentos': row[0].foto_equipamentos,
                'foto_velocidade': row[0].foto_velocidade,
                'foto_cto': row[0].foto_cto,
                'splitter_cto': row[0].splitter_cto,
                'material_utilizado': row[0].material_utilizado,
                'problema_encontrado': row[0].problema_encontrado
            }
            tickets.append(ticket_dict)

        return tickets

    @staticmethod
    def count_tickets(
        db: Session,
        empresa_id: int,
        status: Optional[str] = None,
        prioridade: Optional[str] = None,
        categoria: Optional[str] = None,
        cliente_id: Optional[int] = None,
        atribuido_para_id: Optional[int] = None,
        search: Optional[str] = None,
        current_user_id: Optional[int] = None
    ) -> int:
        """Conta o total de tickets com filtros opcionais."""
        query = db.query(func.count(Ticket.id)).filter(
            Ticket.empresa_id == empresa_id,
            Ticket.is_active == True
        )

        # Filtragem por role "technical"
        if current_user_id:
            # 1. Verificar se o usuário é superuser ou administrador da empresa
            is_admin_or_superuser = False
            user = db.query(Usuario).filter(Usuario.id == current_user_id).first()
            if user:
                if user.is_superuser:
                    is_admin_or_superuser = True
                else:
                    from app.models.models import UsuarioEmpresa
                    assoc = db.query(UsuarioEmpresa).filter(
                        UsuarioEmpresa.usuario_id == current_user_id,
                        UsuarioEmpresa.empresa_id == empresa_id
                    ).first()
                    if assoc and assoc.is_admin:
                        is_admin_or_superuser = True

            # 2. Se não for admin nem superuser, verificar se tem a role "technical"
            if not is_admin_or_superuser:
                from app.models.access_control import Role, user_role_association
                is_technical = db.query(Role).join(
                    user_role_association,
                    Role.id == user_role_association.c.role_id
                ).filter(
                    user_role_association.c.user_id == current_user_id,
                    Role.name.ilike("technical"),
                    or_(
                        user_role_association.c.empresa_id == empresa_id,
                        user_role_association.c.empresa_id == None
                    )
                ).first() is not None

                # 3. Se for técnico, aplicar restrição: apenas tickets atribuídos ao próprio técnico ou não atribuídos (None)
                if is_technical:
                    query = query.filter(
                        or_(
                            Ticket.atribuido_para_id == None,
                            Ticket.atribuido_para_id == current_user_id
                        )
                    )

        if status:
            status_list = [s.strip() for s in status.split(',')]
            if len(status_list) == 1:
                query = query.filter(Ticket.status == status_list[0])
            else:
                query = query.filter(Ticket.status.in_(status_list))
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

        return query.scalar() or 0

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
            func.count(TicketComment.id).label('comentarios_count'),
            ServicoContratado.numero_contrato.label('contrato_numero'),
            ServicoContratado.endereco_instalacao.label('contrato_endereco')
        ).outerjoin(
            Cliente, Ticket.cliente_id == Cliente.id
        ).outerjoin(
            ServicoContratado, Ticket.contrato_id == ServicoContratado.id
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
            Ticket.id, 
            Cliente.nome_razao_social, 
            criado_por_alias.full_name,
            ServicoContratado.numero_contrato,
            ServicoContratado.endereco_instalacao
        ).first()

        if ticket:
            return {
                'id': ticket[0].id,
                'empresa_id': ticket[0].empresa_id,
                'cliente_id': ticket[0].cliente_id,
                'contrato_id': ticket[0].contrato_id,
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
                'comentarios_count': ticket[5] or 0,
                'contrato_numero': ticket[6],
                'contrato_endereco': ticket[7],
                'foto_onu_serial': ticket[0].foto_onu_serial,
                'foto_equipamentos': ticket[0].foto_equipamentos,
                'foto_velocidade': ticket[0].foto_velocidade,
                'foto_cto': ticket[0].foto_cto,
                'splitter_cto': ticket[0].splitter_cto,
                'material_utilizado': ticket[0].material_utilizado,
                'problema_encontrado': ticket[0].problema_encontrado
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

        val_contrato_id = getattr(ticket_data, 'contrato_id', None)
        # Se contrato_id for atualizado
        if val_contrato_id is not None:
            contrato = db.query(ServicoContratado).filter(
                ServicoContratado.id == val_contrato_id,
                ServicoContratado.empresa_id == empresa_id,
                ServicoContratado.is_active == True
            ).first()
            if not contrato:
                raise HTTPException(status_code=404, detail="Contrato não encontrado ou inativo")
            
            # Atualiza também o cliente_id correspondente
            setattr(ticket_data, 'cliente_id', contrato.cliente_id)

        val_cliente_id = getattr(ticket_data, 'cliente_id', None)
        if val_cliente_id is not None:
            # Verifica se o cliente existe e pertence a esta empresa (via EmpresaCliente ou legacy empresa_id)
            client_exists = db.query(Cliente).filter(
                Cliente.id == val_cliente_id,
                Cliente.is_active == True
            ).first()
            if not client_exists:
                raise HTTPException(status_code=404, detail="Cliente não encontrado")
                
            has_assoc = db.query(EmpresaCliente).filter(
                EmpresaCliente.cliente_id == val_cliente_id,
                EmpresaCliente.empresa_id == empresa_id
            ).first() is not None or client_exists.empresa_id == empresa_id
            
            if not has_assoc:
                raise HTTPException(
                    status_code=400,
                    detail="O cliente selecionado não pertence à empresa/provedor ativo"
                )

        update_data = ticket_data.model_dump(exclude_unset=True)

        # Se está mudando para resolvido ou fechado, valida se todos os campos de encerramento estão preenchidos
        if 'status' in update_data and update_data['status'] in [StatusTicket.RESOLVIDO, StatusTicket.FECHADO]:
            # Valida todos os campos de encerramento obrigatórios
            # Pegamos o valor final de cada campo (seja do update_data ou do ticket atual)
            val_onu = update_data.get('foto_onu_serial', ticket.foto_onu_serial)
            val_equip = update_data.get('foto_equipamentos', ticket.foto_equipamentos)
            val_vel = update_data.get('foto_velocidade', ticket.foto_velocidade)
            val_cto = update_data.get('foto_cto', ticket.foto_cto)
            val_splitter = update_data.get('splitter_cto', ticket.splitter_cto)
            val_material = update_data.get('material_utilizado', ticket.material_utilizado)
            val_problema = update_data.get('problema_encontrado', ticket.problema_encontrado)
            val_resolucao = update_data.get('resolucao', ticket.resolucao)

            missing_fields = []
            if not val_onu or not str(val_onu).strip():
                missing_fields.append("Foto do Serial ONU/Roteador")
            if not val_equip or not str(val_equip).strip():
                missing_fields.append("Foto de Equipamentos Instalados")
            if not val_vel or not str(val_vel).strip():
                missing_fields.append("Foto do Teste de Velocidade")
            if not val_cto or not str(val_cto).strip():
                missing_fields.append("Foto da CTO utilizada")
            if not val_splitter or not str(val_splitter).strip():
                missing_fields.append("Splitter utilizado")
            if not val_material or not str(val_material).strip():
                missing_fields.append("Material utilizado")
            if not val_problema or not str(val_problema).strip():
                missing_fields.append("Problema encontrado")
            if not val_resolucao or not str(val_resolucao).strip():
                missing_fields.append("Como foi solucionado (Resolução)")

            if missing_fields:
                raise HTTPException(
                    status_code=400,
                    detail=f"Para fechar/resolver o chamado, todos os campos de encerramento são obrigatórios. Faltando: {', '.join(missing_fields)}"
                )

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
            func.count(TicketComment.id).label('comentarios_count'),
            ServicoContratado.numero_contrato.label('contrato_numero'),
            ServicoContratado.endereco_instalacao.label('contrato_endereco')
        ).outerjoin(
            Cliente, Ticket.cliente_id == Cliente.id
        ).outerjoin(
            ServicoContratado, Ticket.contrato_id == ServicoContratado.id
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
            Ticket.id, 
            Cliente.nome_razao_social, 
            criado_por_alias.full_name,
            ServicoContratado.numero_contrato,
            ServicoContratado.endereco_instalacao
        ).first()

        if ticket_with_relations:
            return {
                'id': ticket_with_relations[0].id,
                'empresa_id': ticket_with_relations[0].empresa_id,
                'cliente_id': ticket_with_relations[0].cliente_id,
                'contrato_id': ticket_with_relations[0].contrato_id,
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
                'comentarios_count': ticket_with_relations[5] or 0,
                'contrato_numero': ticket_with_relations[6],
                'contrato_endereco': ticket_with_relations[7],
                'foto_onu_serial': ticket_with_relations[0].foto_onu_serial,
                'foto_equipamentos': ticket_with_relations[0].foto_equipamentos,
                'foto_velocidade': ticket_with_relations[0].foto_velocidade,
                'foto_cto': ticket_with_relations[0].foto_cto,
                'splitter_cto': ticket_with_relations[0].splitter_cto,
                'material_utilizado': ticket_with_relations[0].material_utilizado,
                'problema_encontrado': ticket_with_relations[0].problema_encontrado
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