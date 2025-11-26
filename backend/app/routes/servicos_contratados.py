from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routes.auth import get_current_active_user
from app.models.models import Usuario
from app.schemas import servico_contratado as sc_schema
from app.crud import crud_servico_contratado, crud_empresa
from app.mikrotik.controller import MikrotikController

router = APIRouter(prefix="/servicos-contratados", tags=["ServicosContratados"])


@router.get("/", response_model=List[sc_schema.ServicoContratadoResponse])
def list_servicos_contratados(empresa_id: int = None, q: str = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user), response: Response = None):
    # If empresa_id provided, check permission
    if empresa_id is not None:
        db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
        if not db_empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        user_empresas_ids = [e.empresa_id for e in current_user.empresas]
        if empresa_id not in user_empresas_ids and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Usuário não tem permissão")
    # compute total for UX and set header
    total = crud_servico_contratado.count_servicos_contratados_by_empresa(db, empresa_id=empresa_id, qstr=q)
    if response is not None:
        response.headers['X-Total-Count'] = str(total)
    items = crud_servico_contratado.get_servicos_contratados_by_empresa(db, empresa_id=empresa_id, qstr=q, skip=skip, limit=limit)
    return items


@router.get("/{contrato_id}", response_model=sc_schema.ServicoContratadoResponse)
def get_contrato(contrato_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    c = crud_servico_contratado.get_servico_contratado(db, contrato_id=contrato_id)
    if not c:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    # If contrato belongs to an empresa, check permission
    if c.empresa_id:
        user_empresas_ids = [e.empresa_id for e in current_user.empresas]
        if c.empresa_id not in user_empresas_ids and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Usuário não tem permissão")
    return c


@router.put("/{contrato_id}", response_model=sc_schema.ServicoContratadoResponse)
def update_contrato(contrato_id: int, contrato_in: sc_schema.ServicoContratadoUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    c = crud_servico_contratado.get_servico_contratado(db, contrato_id=contrato_id)
    if not c:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    if c.empresa_id:
        user_empresas_ids = [e.empresa_id for e in current_user.empresas]
        if c.empresa_id not in user_empresas_ids and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Usuário não tem permissão")
    updated = crud_servico_contratado.update_servico_contratado(db, db_obj=c, obj_in=contrato_in)
    return updated


@router.get("/cliente/{cliente_id}", response_model=List[sc_schema.ServicoContratadoResponse])
def list_contratos_cliente(cliente_id: int, empresa_id: int = None, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    """Lista os contratos de um cliente específico, opcionalmente filtrados por empresa."""
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"Endpoint /cliente/{cliente_id} chamado com empresa_id={empresa_id}")
    logger.info(f"Usuário: {current_user.email}, is_superuser: {current_user.is_superuser}")

    # If empresa_id provided, check permission
    if empresa_id is not None:
        logger.info(f"Verificando empresa_id={empresa_id}")
        db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
        if not db_empresa:
            logger.error(f"Empresa {empresa_id} não encontrada")
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        logger.info(f"Empresa {empresa_id} encontrada: {db_empresa.razao_social}")

        user_empresas_ids = [e.empresa_id for e in current_user.empresas]
        logger.info(f"Empresas do usuário: {user_empresas_ids}")

        if empresa_id not in user_empresas_ids and not current_user.is_superuser:
            logger.error(f"Usuário não tem permissão para empresa {empresa_id}")
            raise HTTPException(status_code=403, detail="Usuário não tem permissão")

        logger.info("Permissão para empresa verificada com sucesso")

    # Get contratos for the cliente, optionally filtered by empresa
    logger.info(f"Executando query para cliente_id={cliente_id}, empresa_id={empresa_id}")
    try:
        contratos = crud_servico_contratado.get_servicos_contratados_by_cliente(db, cliente_id=cliente_id, empresa_id=empresa_id)
        logger.info(f"Query executada com sucesso, retornou {len(contratos)} contratos")
    except Exception as e:
        logger.error(f"Erro na execução da query: {e}", exc_info=True)
        raise

    # Additional permission check: ensure user has access to the empresas of these contratos
    if not current_user.is_superuser:
        logger.info("Verificando permissões para cada contrato (usuário não é superuser)")
        user_empresas_ids = [e.empresa_id for e in current_user.empresas]
        logger.info(f"Empresas do usuário: {user_empresas_ids}")

        for i, contrato in enumerate(contratos):
            logger.info(f"Verificando contrato {i+1}: empresa_id={contrato.get('empresa_id')}")
            if contrato.get('empresa_id') not in user_empresas_ids:
                logger.error(f"Usuário não tem permissão para contrato da empresa {contrato.get('empresa_id')}")
                raise HTTPException(status_code=403, detail="Usuário não tem permissão para acessar contratos desta empresa")
        logger.info("Todas as permissões verificadas com sucesso")
    else:
        logger.info("Usuário é superuser, pulando verificação de permissões")

    logger.info(f"Retornando {len(contratos)} contratos")
    return contratos


# Company-scoped endpoints (also available under /empresas/{empresa_id}/servicos-contratados)
@router.post("/empresa/{empresa_id}", response_model=sc_schema.ServicoContratadoResponse, status_code=status.HTTP_201_CREATED)
def create_contrato_for_empresa(empresa_id: int, contrato: sc_schema.ServicoContratadoCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    # check permission
    db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    user_empresas_ids = [e.empresa_id for e in current_user.empresas]
    if not current_user.is_superuser and empresa_id not in user_empresas_ids:
        raise HTTPException(status_code=403, detail="Usuário não tem permissão")
    c = crud_servico_contratado.create_servico_contratado(db, contrato_in=contrato, empresa_id=empresa_id, created_by_user_id=current_user.id)
    return c


@router.get("/empresa/{empresa_id}", response_model=List[sc_schema.ServicoContratadoResponse])
def list_contratos_empresa(empresa_id: int, q: str = None, skip: int = 0, limit: int = 100, dia_vencimento_min: int = None, dia_vencimento_max: int = None, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user), response: Response = None):
    db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    user_empresas_ids = [e.empresa_id for e in current_user.empresas]
    if not current_user.is_superuser and empresa_id not in user_empresas_ids:
        raise HTTPException(status_code=403, detail="Usuário não tem permissão")
    total = crud_servico_contratado.count_servicos_contratados_by_empresa(db, empresa_id=empresa_id, qstr=q, dia_vencimento_min=dia_vencimento_min, dia_vencimento_max=dia_vencimento_max)
    if response is not None:
        response.headers['X-Total-Count'] = str(total)
    return crud_servico_contratado.get_servicos_contratados_by_empresa(db, empresa_id=empresa_id, qstr=q, skip=skip, limit=limit, dia_vencimento_min=dia_vencimento_min, dia_vencimento_max=dia_vencimento_max)


@router.put("/empresa/{empresa_id}/{contrato_id}", response_model=sc_schema.ServicoContratadoResponse)
def update_contrato_for_empresa(empresa_id: int, contrato_id: int, contrato_in: sc_schema.ServicoContratadoUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    user_empresas_ids = [e.empresa_id for e in current_user.empresas]
    if not current_user.is_superuser and empresa_id not in user_empresas_ids:
        raise HTTPException(status_code=403, detail="Usuário não tem permissão")
    db_obj = crud_servico_contratado.get_servico_contratado(db, contrato_id=contrato_id, empresa_id=empresa_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    updated = crud_servico_contratado.update_servico_contratado(db, db_obj=db_obj, obj_in=contrato_in)
    return updated


@router.delete("/empresa/{empresa_id}/{contrato_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contrato_for_empresa(empresa_id: int, contrato_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    """Exclui um contrato de serviço para uma empresa específica."""
    import logging
    logger = logging.getLogger(__name__)

    # Verificar se a empresa existe e permissões
    db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    user_empresas_ids = [e.empresa_id for e in current_user.empresas]
    if not current_user.is_superuser and empresa_id not in user_empresas_ids:
        raise HTTPException(status_code=403, detail="Usuário não tem permissão")

    # Buscar o contrato
    db_contrato = crud_servico_contratado.get_servico_contratado(db, contrato_id=contrato_id, empresa_id=empresa_id)
    if not db_contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    # Se o contrato estiver ativo, remover as configurações do router antes de excluir
    if db_contrato.status == sc_schema.StatusContrato.ATIVO:
        logger.info(f"Contrato {contrato_id} está ativo, removendo configurações do router antes da exclusão")

        # Buscar informações do router
        from app.crud import crud_router
        router_db = crud_router.get_router(db, router_id=db_contrato.router_id, empresa_id=empresa_id)
        if router_db:
            try:
                # Descriptografar senha do router (com fallback para senha em texto plano)
                from app.core.security import decrypt_password
                try:
                    password = decrypt_password(router_db.senha) if router_db.senha else ""
                except Exception:
                    password = router_db.senha if router_db.senha else ""

                mk = MikrotikController(
                    host=router_db.ip,
                    username=router_db.usuario,
                    password=password,
                    port=router_db.porta or 8728
                )

                # Remover configurações baseado no método de autenticação
                try:
                    if db_contrato.metodo_autenticacao == 'IP_MAC' and db_contrato.assigned_ip:
                        # Remover entrada ARP
                        mk.remove_arp_entry(db_contrato.assigned_ip)
                        logger.info(f"Entrada ARP removida para IP {db_contrato.assigned_ip}")

                    elif db_contrato.metodo_autenticacao == 'PPPOE':
                        # Remover secret PPPoE
                        username = f"contrato_{db_contrato.id}"
                        mk.remove_pppoe_user(username)
                        logger.info(f"Secret PPPoE removido para usuário {username}")

                    elif db_contrato.metodo_autenticacao == 'HOTSPOT':
                        # Remover usuário Hotspot
                        username = f"contrato_{db_contrato.id}"
                        # Para hotspot, não temos método remove específico, mas podemos tentar remover via API
                        try:
                            mk.connect()
                            user_resource = mk._api.get_resource('ip/hotspot/user')
                            users = user_resource.get(name=username)
                            if users:
                                user_resource.remove(id=users[0]['.id'])
                                logger.info(f"Usuário Hotspot removido: {username}")
                        except Exception as e:
                            logger.warning(f"Erro ao remover usuário Hotspot {username}: {e}")

                    # Remover queue QoS se existir
                    queue_name = f"contrato-{db_contrato.id}"
                    try:
                        logger.info(f"Tentando remover queue QoS: {queue_name}")
                        if mk._api is None:
                            logger.warning("Mikrotik API não conectada, conectando...")
                            mk.connect()
                        queue_resource = mk._api.get_resource('queue/simple')
                        logger.info(f"Resource queue/simple obtido")
                        queues = queue_resource.get(name=queue_name)
                        logger.info(f"Busca por name={queue_name} retornou: {len(queues) if queues else 0} queues")
                        if queues:
                            for queue in queues:
                                queue_id = queue.get('.id') or queue.get('id')
                                if queue_id:
                                    logger.info(f"Removendo queue id={queue_id}, name={queue.get('name', 'N/A')}")
                                    queue_resource.remove(id=queue_id)
                                    logger.info(f"Queue QoS removida: {queue_name} (id: {queue_id})")
                                else:
                                    logger.warning(f"Queue sem ID válido: {queue}")
                        else:
                            logger.warning(f"Queue QoS {queue_name} não encontrada, listando todas as queues...")
                            try:
                                all_queues = queue_resource.get()
                                logger.info(f"Total de queues encontradas: {len(all_queues)}")
                                for q in all_queues[:10]:  # Mostra apenas as primeiras 10
                                    q_id = q.get('.id') or q.get('id')
                                    q_name = q.get('name', 'N/A')
                                    logger.info(f"  Queue: name={q_name}, id={q_id}")
                            except Exception as list_e:
                                logger.error(f"Erro ao listar queues: {list_e}")
                    except Exception as e:
                        logger.error(f"Erro ao remover queue QoS {queue_name}: {e}", exc_info=True)

                except Exception as router_exc:
                    logger.error(f"Erro ao remover configurações do router: {str(router_exc)}")
                    # Não falhar a exclusão por causa de erro no router
                finally:
                    if 'mk' in locals():
                        try:
                            mk.close()
                        except:
                            pass

            except Exception as conn_exc:
                logger.error(f"Erro ao conectar ao router para limpeza: {str(conn_exc)}")
                # Não falhar a exclusão por causa de erro de conexão

    # Excluir o contrato do banco de dados
    try:
        crud_servico_contratado.delete_servico_contratado(db, db_obj=db_contrato)
        logger.info(f"Contrato {contrato_id} excluído com sucesso da empresa {empresa_id}")
    except Exception as db_exc:
        logger.error(f"Erro ao excluir contrato do banco: {str(db_exc)}")
        raise HTTPException(status_code=500, detail="Erro interno ao excluir contrato")


@router.put("/{contrato_id}/ativar", response_model=sc_schema.ServicoContratadoResponse)
def ativar_servico(contrato_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    """Ativa um serviço contratado, mudando o status para ATIVO e enviando regras para o router."""
    import logging
    logger = logging.getLogger(__name__)

    c = crud_servico_contratado.get_servico_contratado(db, contrato_id=contrato_id)
    if not c:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    # Verificar permissões
    if c.empresa_id:
        user_empresas_ids = [e.empresa_id for e in current_user.empresas]
        if c.empresa_id not in user_empresas_ids and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Usuário não tem permissão")

    # Buscar informações do cliente para incluir no comentário das regras
    cliente_nome = "Cliente não encontrado"
    if c.cliente_id:
        from app.crud import crud_cliente
        cliente_db = crud_cliente.get_cliente(db, cliente_id=c.cliente_id)
        if cliente_db:
            cliente_nome = cliente_db.nome_razao_social

    # Verificar se o contrato pode ser ativado
    if c.status != sc_schema.StatusContrato.PENDENTE_INSTALACAO:
        raise HTTPException(status_code=400, detail=f"Contrato não pode ser ativado. Status atual: {c.status}")

    # Verificar se o contrato tem todas as informações necessárias
    if not c.router_id or not c.interface_id:
        raise HTTPException(status_code=400, detail="Contrato deve ter router e interface configurados")

    # Buscar informações do router
    from app.crud import crud_router
    router_db = crud_router.get_router(db, router_id=c.router_id, empresa_id=c.empresa_id)
    if not router_db:
        raise HTTPException(status_code=404, detail="Router não encontrado")

    # Buscar informações da interface
    from app.models.network import RouterInterface
    interface_db = db.query(RouterInterface).filter(RouterInterface.id == c.interface_id).first()
    if not interface_db:
        raise HTTPException(status_code=404, detail="Interface não encontrada")

    # Buscar informações do serviço para QoS
    servico = None
    if c.servico_id:
        from app.crud import crud_servico
        servico = crud_servico.get_servico(db, servico_id=c.servico_id, empresa_id=c.empresa_id)

    # Atualizar status para ATIVO
    from app.schemas.servico_contratado import ServicoContratadoUpdate
    update_data = ServicoContratadoUpdate(status=sc_schema.StatusContrato.ATIVO)
    updated_contract = crud_servico_contratado.update_servico_contratado(db, db_obj=c, obj_in=update_data)

    # Configurar router
    mk = None
    try:
        # Verificar se a biblioteca routeros_api está disponível
        try:
            import routeros_api
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="Biblioteca 'routeros-api' não está instalada. Instale com: pip install routeros-api"
            )

        # Descriptografar senha do router (com fallback para senha em texto plano)
        from app.core.security import decrypt_password
        try:
            password = decrypt_password(router_db.senha) if router_db.senha else ""
            logger.info("Senha descriptografada com sucesso")
        except Exception as decrypt_exc:
            logger.warning(f"Falha ao descriptografar senha, tentando usar como texto plano: {str(decrypt_exc)}")
            password = router_db.senha if router_db.senha else ""
            logger.info("Usando senha como texto plano")

        logger.info(f"Conectando ao router {router_db.ip}:{router_db.porta or 8728} com usuário {router_db.usuario}")
        mk = MikrotikController(
            host=router_db.ip,
            username=router_db.usuario,
            password=password,
            port=router_db.porta or 8728
        )

        # Testar conexão
        logger.info("Testando conexão com o router...")
        # Vamos tentar fazer uma operação simples para testar a conexão
        try:
            interfaces = mk.get_interfaces()
            logger.info(f"Conexão estabelecida. Encontradas {len(interfaces)} interfaces.")
        except Exception as conn_exc:
            logger.error(f"Falha na conexão com router: {str(conn_exc)}")
            raise Exception(f"Falha na conexão com router {router_db.ip}: {str(conn_exc)}")

        # Configurar baseado no método de autenticação
        if c.metodo_autenticacao == 'IP_MAC':
            if not c.assigned_ip or not c.mac_address:
                raise Exception("IP e MAC são obrigatórios para método IP_MAC")

            comment = f"Contrato {c.id} - {cliente_nome}"
            logger.info(f"Configurando ARP entry: IP={c.assigned_ip}, MAC={c.mac_address}, Interface={interface_db.nome}, Comment={comment}")
            try:
                mk.set_arp_entry(
                    ip=c.assigned_ip,
                    mac=c.mac_address,
                    interface=interface_db.nome,
                    comment=comment
                )
                logger.info("ARP entry configurado com sucesso")
            except Exception as arp_exc:
                logger.error(f"Erro ao configurar ARP entry: {str(arp_exc)}")
                raise Exception(f"Erro ao configurar ARP entry: {str(arp_exc)}")

        elif c.metodo_autenticacao == 'PPPOE':
            # Para PPPoE, criar usuário no servidor PPPoE
            username = f"contrato_{c.id}"
            password_pppoe = f"pppoe_{c.id}"
            comment = f"Contrato {c.id} - {cliente_nome}"

            logger.info(f"Configurando usuário PPPoE: {username}, Comment={comment}")
            try:
                mk.add_pppoe_user(
                    username=username,
                    password=password_pppoe,
                    service='pppoe',
                    comment=comment
                )
                logger.info("Usuário PPPoE criado com sucesso")
            except Exception as pppoe_exc:
                logger.error(f"Erro ao criar usuário PPPoE: {str(pppoe_exc)}")
                raise Exception(f"Erro ao criar usuário PPPoE: {str(pppoe_exc)}")

        elif c.metodo_autenticacao == 'HOTSPOT':
            # Para Hotspot, criar usuário no servidor Hotspot
            username = f"contrato_{c.id}"
            password_hotspot = f"hotspot_{c.id}"
            comment = f"Contrato {c.id} - {cliente_nome}"

            logger.info(f"Configurando usuário Hotspot: {username}, Comment={comment}")
            try:
                mk.add_hotspot_user(
                    username=username,
                    password=password_hotspot,
                    comment=comment
                )
                logger.info("Usuário Hotspot criado com sucesso")
            except Exception as hotspot_exc:
                logger.error(f"Erro ao criar usuário Hotspot: {str(hotspot_exc)}")
                raise Exception(f"Erro ao criar usuário Hotspot: {str(hotspot_exc)}")

        elif c.metodo_autenticacao == 'RADIUS':
            # Para RADIUS, a configuração geralmente é feita no servidor RADIUS
            logger.info("Método RADIUS selecionado - configuração no servidor RADIUS necessária")
            pass

        # Configurar QoS (limite de banda) se o serviço tiver limite definido
        if servico and hasattr(servico, 'max_limit') and servico.max_limit:
            queue_name = f"contrato-{c.id}"
            target_ip = c.assigned_ip if c.metodo_autenticacao == 'IP_MAC' else f"contrato_{c.id}"
            comment = f"Contrato {c.id} - {cliente_nome} - {servico.max_limit}"

            logger.info(f"Configurando QoS: {queue_name}, target={target_ip}, limit={servico.max_limit}, Comment={comment}")
            try:
                mk.set_queue_simple(
                    name=queue_name,
                    target=f"{target_ip}/32" if c.metodo_autenticacao == 'IP_MAC' else target_ip,
                    max_limit=servico.max_limit,
                    comment=comment
                )
                logger.info("QoS configurado com sucesso")
            except Exception as qos_exc:
                logger.error(f"Erro ao configurar QoS: {str(qos_exc)}")
                raise Exception(f"Erro ao configurar QoS: {str(qos_exc)}")

        logger.info(f"Contrato {contrato_id} ativado com sucesso no router {router_db.ip}")

    except Exception as exc:
        error_msg = str(exc) if str(exc) else f"Erro desconhecido (tipo: {type(exc).__name__})"
        logger.error(f"Erro ao configurar router para contrato {contrato_id}: {error_msg}")
        logger.error(f"Detalhes do erro: {repr(exc)}")

        # Reverter status em caso de erro
        try:
            update_data = sc_schema.ServicoContratadoUpdate(status=sc_schema.StatusContrato.PENDENTE_INSTALACAO)
            crud_servico_contratado.update_servico_contratado(db, db_obj=updated_contract, obj_in=update_data)
            logger.info(f"Status do contrato {contrato_id} revertido para PENDENTE_INSTALACAO")
        except Exception as rollback_exc:
            logger.error(f"Erro ao reverter status do contrato: {str(rollback_exc)}")

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao configurar router: {error_msg}. Contrato mantido como pendente."
        )
    finally:
        if mk:
            try:
                mk.close()
                logger.info("Conexão com router fechada")
            except Exception as close_exc:
                logger.error(f"Erro ao fechar conexão com router: {str(close_exc)}")

    return updated_contract


@router.put("/{contrato_id}/reset-connection", response_model=dict)
def reset_client_connection(contrato_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    """Reseta a conexão do cliente no router, forçando uma reconexão."""
    import logging
    logger = logging.getLogger(__name__)

    c = crud_servico_contratado.get_servico_contratado(db, contrato_id=contrato_id)
    if not c:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    # Verificar permissões
    if c.empresa_id:
        user_empresas_ids = [e.empresa_id for e in current_user.empresas]
        if c.empresa_id not in user_empresas_ids and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Usuário não tem permissão")

    # Verificar se o contrato está ativo
    if c.status != sc_schema.StatusContrato.ATIVO:
        raise HTTPException(status_code=400, detail=f"Contrato não está ativo. Status atual: {c.status}")

    # Verificar se o contrato tem router configurado
    if not c.router_id:
        raise HTTPException(status_code=400, detail="Contrato deve ter router configurado")

    # Buscar informações do router
    from app.crud import crud_router
    router_db = crud_router.get_router(db, router_id=c.router_id, empresa_id=c.empresa_id)
    if not router_db:
        raise HTTPException(status_code=404, detail="Router não encontrado")

    # Buscar informações do cliente para logging
    cliente_nome = "Cliente não encontrado"
    if c.cliente_id:
        from app.crud import crud_cliente
        cliente_db = crud_cliente.get_cliente(db, cliente_id=c.cliente_id)
        if cliente_db:
            cliente_nome = cliente_db.nome_razao_social

    # Configurar router
    mk = None
    try:
        # Verificar se a biblioteca routeros_api está disponível
        try:
            import routeros_api
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="Biblioteca 'routeros-api' não está instalada. Instale com: pip install routeros-api"
            )

        # Descriptografar senha do router (com fallback para senha em texto plano)
        from app.core.security import decrypt_password
        try:
            password = decrypt_password(router_db.senha) if router_db.senha else ""
            logger.info("Senha descriptografada com sucesso")
        except Exception as decrypt_exc:
            logger.warning(f"Falha ao descriptografar senha, tentando usar como texto plano: {str(decrypt_exc)}")
            password = router_db.senha if router_db.senha else ""
            logger.info("Usando senha como texto plano")

        logger.info(f"Conectando ao router {router_db.ip}:{router_db.porta or 8728} para reset de conexão")
        mk = MikrotikController(
            host=router_db.ip,
            username=router_db.usuario,
            password=password,
            port=router_db.porta or 8728
        )

        # Testar conexão
        logger.info("Testando conexão com o router...")
        try:
            interfaces = mk.get_interfaces()
            logger.info(f"Conexão estabelecida. Encontradas {len(interfaces)} interfaces.")
        except Exception as conn_exc:
            logger.error(f"Falha na conexão com router: {str(conn_exc)}")
            raise Exception(f"Falha na conexão com router {router_db.ip}: {str(conn_exc)}")

        # Resetar conexão baseado no método de autenticação
        logger.info(f"Resetando conexão para contrato {contrato_id} - {cliente_nome} (método: {c.metodo_autenticacao})")
        try:
            result = mk.reset_client_connection(
                contrato_id=c.id,
                metodo_autenticacao=c.metodo_autenticacao,
                assigned_ip=c.assigned_ip,
                mac_address=c.mac_address
            )
            logger.info(f"Conexão resetada com sucesso: {result}")
        except Exception as reset_exc:
            logger.error(f"Erro ao resetar conexão: {str(reset_exc)}")
            raise Exception(f"Erro ao resetar conexão: {str(reset_exc)}")

        logger.info(f"Conexão do contrato {contrato_id} resetada com sucesso no router {router_db.ip}")

        return {
            "success": True,
            "message": f"Conexão do contrato {contrato_id} resetada com sucesso",
            "contrato_id": contrato_id,
            "cliente": cliente_nome,
            "metodo_autenticacao": c.metodo_autenticacao
        }

    except Exception as exc:
        error_msg = str(exc) if str(exc) else f"Erro desconhecido (tipo: {type(exc).__name__})"
        logger.error(f"Erro ao resetar conexão para contrato {contrato_id}: {error_msg}")
        logger.error(f"Detalhes do erro: {repr(exc)}")

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao resetar conexão: {error_msg}"
        )
    finally:
        if mk:
            try:
                mk.close()
                logger.info("Conexão com router fechada")
            except Exception as close_exc:
                logger.error(f"Erro ao fechar conexão com router: {str(close_exc)}")
