import logging
from sqlalchemy.orm import Session
from app.models.models import ServicoContratado, Router, StatusContrato
from app.mikrotik.controller import MikrotikController
from app.core.security import decrypt_password

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

                success = mk.unsuspend_client_connection(
                    contrato_id=contrato.id,
                    metodo_autenticacao=contrato.metodo_autenticacao,
                    assigned_ip=contrato.assigned_ip,
                    mac_address=contrato.mac_address,
                    interface=interface_name,
                    comment=cliente_nome
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
                notice_url = contrato.empresa.suspension_url if contrato.empresa and contrato.empresa.suspension_url else os.getenv("NOTICE_PAGE_URL", f"http://brazcom.com.br/aviso/{contrato.id}")
                
                if notice_url:
                    mk.setup_suspension_nat_rule(notice_url)
                    mk.setup_suspension_firewall_rules()
                
                cliente_nome = contrato.cliente.nome_razao_social if contrato.cliente else "Cliente"
                
                mk.suspend_client_connection(
                    contrato_id=contrato.id,
                    metodo_autenticacao=contrato.metodo_autenticacao,
                    assigned_ip=contrato.assigned_ip,
                    comment=cliente_nome
                )
                mk.close()
                logger.info(f"Contrato {contrato_id} bloqueado no router {router_db.ip}")
            except Exception as e:
                logger.error(f"Erro ao bloquear contrato {contrato_id} no router: {e}")
                
    return True
