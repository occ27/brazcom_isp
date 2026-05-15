import logging
from sqlalchemy.orm import Session
from app.models.models import ServicoContratado, Router, StatusContrato, MetodoAutenticacao
from app.mikrotik.controller import MikrotikController
from app.core.security import decrypt_password
from app.core.radius_db import RadiusSessionLocal
from app.services.radius_sync_service import RadiusSyncService

logger = logging.getLogger(__name__)

def process_unblock_if_needed(db: Session, contrato_id: int):
    """
    Verifica se o contrato está suspenso e realiza o desbloqueio no router.
    Muda o status para ATIVO.
    """
    contrato = db.query(ServicoContratado).filter(ServicoContratado.id == contrato_id).first()
    if not contrato:
        logger.warning(f"Contrato {contrato_id} não encontrado para desbloqueio")
        return False
    
    # Se o contrato estiver suspenso ou pendente, vamos garantir que ele seja ativado
    if contrato.status not in [StatusContrato.SUSPENSO, StatusContrato.PENDENTE_INSTALACAO]:
        return False
    
    old_status = contrato.status
    contrato.status = StatusContrato.ATIVO
    db.add(contrato)

    # 1. Desbloqueio no RADIUS (se aplicável)
    if contrato.metodo_autenticacao == MetodoAutenticacao.RADIUS:
        if contrato.cliente and contrato.cliente.radius_user:
            radius_user = contrato.cliente.radius_user
            try:
                if RadiusSessionLocal:
                    with RadiusSessionLocal() as radius_db:
                        sync = RadiusSyncService(radius_db)
                        sync.enable_user(radius_user.username)
                        logger.info(f"Usuário Radius '{radius_user.username}' reativado no FreeRadius.")
                
                radius_user.is_active = True
                db.add(radius_user)
            except Exception as e:
                logger.error(f"Erro ao reativar usuário Radius '{radius_user.username}': {e}")
    
    # Se tiver router configurado, realiza o desbloqueio técnico
    if contrato.router_id:
        router_db = db.query(Router).filter(Router.id == contrato.router_id).first()
        if router_db:
            try:
                # Tentar descriptografar a senha
                try:
                    password = decrypt_password(router_db.senha) if router_db.senha else ""
                except Exception:
                    password = router_db.senha
                
                mk = MikrotikController(
                    host=router_db.ip,
                    username=router_db.usuario,
                    password=password,
                    port=router_db.porta or 8728
                )
                
                # Buscar nome da interface para IP_MAC
                interface_name = ""
                if contrato.interface_id:
                    from app.models.network import RouterInterface
                    ifce = db.query(RouterInterface).filter(RouterInterface.id == contrato.interface_id).first()
                    if ifce:
                        interface_name = ifce.nome
                
                # Buscar nome do cliente para o comentário
                cliente_nome = "Cliente"
                if contrato.cliente:
                    cliente_nome = contrato.cliente.nome_razao_social

                # Desbloquear primário (remover da pg_corte e regras estritas)
                # Se for RADIUS, o username no Mikrotik é o username do Radius
                mk_username = f"contrato_{contrato.id}"
                if contrato.metodo_autenticacao == MetodoAutenticacao.RADIUS and contrato.cliente.radius_user:
                    mk_username = contrato.cliente.radius_user.username

                success = mk.unsuspend_client_connection(
                    contrato_id=contrato.id,
                    metodo_autenticacao=contrato.metodo_autenticacao,
                    assigned_ip=contrato.assigned_ip,
                    mac_address=contrato.mac_address,
                    interface=interface_name,
                    comment=cliente_nome
                )
                
                # Se for RADIUS ou PPPOE, tenta derrubar a sessão ativa para forçar re-conexão com status novo
                if contrato.metodo_autenticacao in [MetodoAutenticacao.PPPOE, MetodoAutenticacao.RADIUS]:
                    mk.disconnect_pppoe_active(mk_username)

                # Restaurar a banda original (Simple Queue e DHCP) com base no serviço
                if success and contrato.servico_id:
                    profile_name = None
                    max_limit = None
                    from app.crud import crud_servico
                    servico = crud_servico.get_servico(db, servico_id=contrato.servico_id, empresa_id=contrato.empresa_id)
                    if servico:
                        max_limit = getattr(servico, 'max_limit', None)
                        if getattr(servico, 'ppp_profile_id', None):
                            from app.models.network import PPPProfile
                            ppp_profile = db.query(PPPProfile).filter(PPPProfile.id == servico.ppp_profile_id).first()
                            if ppp_profile:
                                profile_name = ppp_profile.nome
                    
                    # Força a atualização da velocidade
                    if max_limit or contrato.metodo_autenticacao == 'IP_MAC':
                        mk.sync_client_connection(
                            contrato_id=contrato.id,
                            metodo_autenticacao=contrato.metodo_autenticacao,
                            assigned_ip=contrato.assigned_ip,
                            mac_address=contrato.mac_address,
                            interface=interface_name,
                            comment=cliente_nome,
                            profile=profile_name,
                            max_limit=max_limit
                        )
                
                mk.close()
                if success:
                    logger.info(f"Contrato {contrato_id} desbloqueado com sucesso no router {router_db.ip}")
                else:
                    logger.warning(f"Comando de desbloqueio enviado mas o router retornou falha para o contrato {contrato_id}")
            except Exception as e:
                logger.error(f"Erro ao desbloquear contrato {contrato_id} no router: {e}")
                # Não falhamos a transação do banco por erro no router, 
                # mas o log registrará que o desbloqueio manual pode ser necessário.
    
    return True

def process_block_if_needed(db: Session, contrato_id: int):
    """
    Bloqueia o contrato no router e muda status para SUSPENSO.
    """
    contrato = db.query(ServicoContratado).filter(ServicoContratado.id == contrato_id).first()
    if not contrato:
        return False
    
    if contrato.status == StatusContrato.SUSPENSO:
        return False
    
    contrato.status = StatusContrato.SUSPENSO
    db.add(contrato)

    # 1. Bloqueio no RADIUS (se aplicável)
    if contrato.metodo_autenticacao == MetodoAutenticacao.RADIUS:
        if contrato.cliente and contrato.cliente.radius_user:
            radius_user = contrato.cliente.radius_user
            try:
                if RadiusSessionLocal:
                    with RadiusSessionLocal() as radius_db:
                        sync = RadiusSyncService(radius_db)
                        sync.disable_user(radius_user.username)
                        logger.info(f"Usuário Radius '{radius_user.username}' suspenso no FreeRadius.")
                
                radius_user.is_active = False
                db.add(radius_user)
            except Exception as e:
                logger.error(f"Erro ao suspender usuário Radius '{radius_user.username}': {e}")
    
    if contrato.router_id:
        router_db = db.query(Router).filter(Router.id == contrato.router_id).first()
        if router_db:
            try:
                try:
                    password = decrypt_password(router_db.senha) if router_db.senha else ""
                except Exception:
                    password = router_db.senha
                
                mk = MikrotikController(
                    host=router_db.ip,
                    username=router_db.usuario,
                    password=password,
                    port=router_db.porta or 8728
                )
                
                # Configurar regra de redirecionamento se necessário
                # O IP de aviso deve ser o IP do servidor onde o frontend está rodando
                import os
                # Buscar a URL de suspensão da empresa ou usar padrão
                notice_url = contrato.empresa.suspension_url if contrato.empresa and contrato.empresa.suspension_url else os.getenv("NOTICE_PAGE_URL", f"http://isp.brazcom.com.br/aviso/{contrato.empresa_id}")
                
                if notice_url:
                    mk.setup_suspension_nat_rule(notice_url)
                    mk.setup_suspension_firewall_rules()
                
                cliente_nome = contrato.cliente.nome_razao_social if contrato.cliente else "Cliente"
                
                # Determinar username para desconexão
                mk_username = f"contrato_{contrato.id}"
                if contrato.metodo_autenticacao == MetodoAutenticacao.RADIUS and contrato.cliente and contrato.cliente.radius_user:
                    mk_username = contrato.cliente.radius_user.username

                mk.suspend_client_connection(
                    contrato_id=contrato.id,
                    metodo_autenticacao=contrato.metodo_autenticacao,
                    assigned_ip=contrato.assigned_ip,
                    comment=cliente_nome
                )

                # Se for RADIUS ou PPPOE, derruba a conexão imediatamente para o bloqueio valer
                if contrato.metodo_autenticacao in [MetodoAutenticacao.PPPOE, MetodoAutenticacao.RADIUS]:
                    mk.disconnect_pppoe_active(mk_username)

                mk.close()
                logger.info(f"Contrato {contrato_id} bloqueado no router {router_db.ip}")
            except Exception as e:
                logger.error(f"Erro ao bloquear contrato {contrato_id} no router: {e}")
                
    return True
