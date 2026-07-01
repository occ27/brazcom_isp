import logging
import os
import re
import requests
import time
from typing import Dict, Any, Optional
from app.models.models import Empresa

logger = logging.getLogger(__name__)

class WhatsAppService:
    """Serviço para envio de mensagens via WhatsApp (Integração real com Evolution API & Simulação Local)"""

    @staticmethod
    def _clean_phone(phone: str) -> str:
        """Limpa e formata o número do celular para o padrão internacional (DDI + DDD + Número)"""
        if not phone:
            return ""
        # Remove todos os caracteres não numéricos
        cleaned = re.sub(r"\D", "", phone)
        
        # Se começar com 0, remove
        if cleaned.startswith("0"):
            cleaned = cleaned[1:]
            
        # Garante que tenha o código do país (55 para Brasil)
        if len(cleaned) <= 11:
            cleaned = "55" + cleaned
            
        return cleaned

    @staticmethod
    def _get_api_url(empresa: Empresa) -> str:
        """Retorna a URL da Evolution API resolvida da empresa ou do fallback local (.env)"""
        url = getattr(empresa, 'whatsapp_api_server', None)
        if not url or ":3000" in url or "/api/whatsapp/send" in url or "brazcom.com.br" in url:
            url = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
        return url

    @staticmethod
    def send_message(empresa: Empresa, to_phone: str, message: str) -> bool:
        """
        Coloca a mensagem na fila assíncrona do WhatsApp para evitar bloqueio por anti-spam.
        Retorna True imediatamente.
        """
        from app.services.whatsapp_queue import wa_queue
        
        cleaned_phone = WhatsAppService._clean_phone(to_phone)
        if not cleaned_phone:
            logger.error("Número de telefone inválido para envio de WhatsApp")
            return False
            
        empresa_data = {
            "id": getattr(empresa, "id", None),
            "razao_social": getattr(empresa, "razao_social", "Desconhecida"),
            "whatsapp_api_server": getattr(empresa, "whatsapp_api_server", None),
            "whatsapp_api_instance": getattr(empresa, "whatsapp_api_instance", None),
            "whatsapp_api_system": getattr(empresa, "whatsapp_api_system", None),
        }
        
        wa_queue.put({
            "empresa": empresa_data,
            "to_phone": to_phone,
            "message": message,
            "is_media": False
        })
        
        return True

    @staticmethod
    def _send_message_sync_real(empresa: Empresa, to_phone: str, message: str) -> bool:
        """
        Envia uma mensagem de WhatsApp real via Evolution API com fallback de simulação em log local.
        (Chamado pelo worker da fila)
        """
        try:
            cleaned_phone = WhatsAppService._clean_phone(to_phone)
            if not cleaned_phone:
                logger.error("Número de telefone inválido para envio de WhatsApp")
                return False

            instance_name = getattr(empresa, 'whatsapp_api_instance', 'mega-net-telecom') or 'mega-net-telecom'
            system_name = getattr(empresa, 'whatsapp_api_system', 'MK Auth') or 'MK Auth'
            
            # 1. Tenta envio via Evolution API (Real)
            api_url = WhatsAppService._get_api_url(empresa)
            api_key = os.getenv("EVOLUTION_API_TOKEN", "brazcom_secure_token_12345")
            
            if api_url:
                # 1.1 Verificar se a instância está conectada antes de tentar o envio real para evitar timeouts longos
                conn = WhatsAppService.get_connection_state(empresa)
                if not conn.get("connected", False):
                    logger.warning(f"Instância WhatsApp '{instance_name}' não está ativa/conectada (Status: {conn.get('state', 'desconhecido')}). Ativando fallback de simulação local.")
                else:
                    if api_url.endswith("/"):
                        api_url = api_url[:-1]
                    
                    endpoint = f"{api_url}/message/sendText/{instance_name}"
                    headers = {
                        "Content-Type": "application/json",
                        "apikey": api_key
                    }
                    payload = {
                        "number": cleaned_phone,
                        "text": message
                    }
                    
                    try:
                        logger.info(f"Tentando envio real de WhatsApp via Brazcom API para {cleaned_phone}")
                        response = requests.post(endpoint, json=payload, headers=headers, timeout=5)
                        if response.status_code in [200, 201]:
                            logger.info(f"Mensagem enviada com sucesso via Brazcom API para {cleaned_phone}!")
                            return True
                        else:
                            logger.warning(f"Brazcom API retornou status {response.status_code}: {response.text}. Ativando fallback de simulação.")
                    except Exception as api_err:
                        logger.warning(f"Falha de conexão com a Brazcom API ({api_err}). Ativando fallback de simulação local.")
            
            # 2. Fallback de Simulação em arquivo local de logs (Garante que nunca quebra o fluxo local)
            logger.info("=========================================")
            logger.info("  DISPARO DE WHATSAPP (SIMULADO / FALLBACK)")
            logger.info(f"  Empresa: {empresa.razao_social} (ID: {empresa.id})")
            logger.info(f"  Instância: {instance_name}")
            logger.info(f"  Integração: {system_name}")
            logger.info(f"  Destinatário: {cleaned_phone} (Original: {to_phone})")
            logger.info(f"  Mensagem: {message}")
            logger.info("=========================================")
            
            log_dir = "/Users/orlando/python/FastAPI/brazcom_isp/backend/logs"
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "whatsapp_sent.log")
            with open(log_path, "a", encoding="utf-8") as f:
                clean_msg = message.replace('\n', ' ')
                f.write(f"[{empresa.razao_social}] Para: {cleaned_phone} | Msg: {clean_msg}\n")

            return True
        except Exception as e:
            logger.error(f"Erro ao disparar mensagem de WhatsApp: {e}", exc_info=True)
            return False

    @staticmethod
    def send_document(
        empresa: Empresa,
        to_phone: str,
        caption: str,
        file_path: str
    ) -> bool:
        """
        Coloca o documento na fila assíncrona do WhatsApp.
        Retorna True imediatamente.
        """
        from app.services.whatsapp_queue import wa_queue
        
        cleaned_phone = WhatsAppService._clean_phone(to_phone)
        if not cleaned_phone:
            logger.error("Número de telefone inválido para envio de documento WhatsApp")
            return False
            
        empresa_data = {
            "id": getattr(empresa, "id", None),
            "razao_social": getattr(empresa, "razao_social", "Desconhecida"),
            "whatsapp_api_server": getattr(empresa, "whatsapp_api_server", None),
            "whatsapp_api_instance": getattr(empresa, "whatsapp_api_instance", None),
            "whatsapp_api_system": getattr(empresa, "whatsapp_api_system", None),
        }
        
        wa_queue.put({
            "empresa": empresa_data,
            "to_phone": to_phone,
            "message": caption,
            "is_media": True,
            "file_path": file_path
        })
        
        return True

    @staticmethod
    def _send_document_sync_real(
        empresa: Empresa,
        to_phone: str,
        caption: str,
        file_path: str
    ) -> bool:
        """
        Envia um documento via WhatsApp API usando message/sendMedia
        (Chamado pelo worker da fila)
        """
        if not to_phone:
            return False

        cleaned_phone = WhatsAppService._clean_phone(to_phone)
        if not cleaned_phone:
            return False

        system_name = os.getenv("WHATSAPP_SYSTEM", "evolution_api").lower()
        
        try:
            if system_name == "evolution_api":
                api_url = WhatsAppService._get_api_url(empresa)
                api_key = os.getenv("EVOLUTION_API_TOKEN", "brazcom_secure_token_12345")
                instance_name = getattr(empresa, 'whatsapp_api_instance', 'mega-net-telecom') or 'mega-net-telecom'

                conn = WhatsAppService.get_connection_state(empresa)
                if not conn.get("connected", False):
                    logger.warning(f"Instância WhatsApp '{instance_name}' não está ativa/conectada. Ativando fallback local para arquivo.")
                else:
                    if api_url.endswith("/"):
                        api_url = api_url[:-1]
                    
                    endpoint = f"{api_url}/message/sendMedia/{instance_name}"
                    headers = {
                        "Content-Type": "application/json",
                        "apikey": api_key
                    }
                    
                    import base64
                    with open(file_path, "rb") as f:
                        file_data = base64.b64encode(f.read()).decode('utf-8')
                    
                    file_name = os.path.basename(file_path)
                    
                    payload = {
                        "number": cleaned_phone,
                        "options": {
                            "delay": 1200,
                            "presence": "composing"
                        },
                        "mediaMessage": {
                            "mediatype": "document",
                            "caption": caption,
                            "media": file_data,
                            "fileName": file_name
                        }
                    }
                    
                    # Evolution API v2 fallback if v1 payload doesn't work
                    payload_v2 = {
                        "number": cleaned_phone,
                        "mediatype": "document",
                        "mimetype": "application/pdf",
                        "caption": caption,
                        "media": file_data,
                        "fileName": file_name
                    }
                    
                    try:
                        logger.info(f"Tentando envio de documento via WhatsApp API para {cleaned_phone}")
                        # Tentamos com payload padrão v1
                        response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
                        if response.status_code not in [200, 201]:
                            logger.info(f"Falha com v1, tentando v2...")
                            response = requests.post(endpoint, json=payload_v2, headers=headers, timeout=10)
                            
                        if response.status_code in [200, 201]:
                            logger.info(f"Documento enviado com sucesso para {cleaned_phone}!")
                            return True
                        else:
                            logger.warning(f"Brazcom API retornou status {response.status_code}: {response.text}.")
                    except Exception as api_err:
                        logger.warning(f"Falha de conexão com a API ({api_err}). Fallback de simulação local.")
            
            # Fallback
            logger.info("=========================================")
            logger.info("  DISPARO DE WHATSAPP COM ARQUIVO (SIMULADO)")
            logger.info(f"  Destinatário: {cleaned_phone}")
            logger.info(f"  Arquivo: {file_path}")
            logger.info(f"  Legenda: {caption}")
            logger.info("=========================================")
            
            log_dir = "/Users/orlando/python/FastAPI/brazcom_isp/backend/logs"
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "whatsapp_sent.log")
            with open(log_path, "a", encoding="utf-8") as f:
                clean_msg = caption.replace('\n', ' ')
                f.write(f"[{empresa.razao_social}] Para: {cleaned_phone} | Arquivo: {os.path.basename(file_path)} | Msg: {clean_msg}\n")

            return True
        except Exception as e:
            logger.error(f"Erro ao disparar documento WhatsApp: {e}", exc_info=True)
            return False

    @staticmethod
    def send_receivable_message(
        empresa: Empresa,
        cliente_nome: str,
        cliente_phone: str,
        receivable_data: Dict[str, Any],
        pdf_path: Optional[str] = None
    ) -> bool:
        """
        Formata e envia uma cobrança (Receivable) por WhatsApp para o cliente.
        """
        amount = receivable_data.get('amount', 0.0)
        due_date = receivable_data.get('due_date')
        payment_url = receivable_data.get('payment_url')

        if hasattr(due_date, 'strftime'):
            due_date_str = due_date.strftime('%d/%m/%Y')
        else:
            due_date_str = str(due_date)

        company_name = empresa.nome_fantasia or empresa.razao_social

        message = f"Olá, *{cliente_nome}*!\n\n"
        message += f"Sua fatura de *{company_name}* no valor de *R$ {amount:,.2f}* com vencimento em *{due_date_str}* já está disponível.\n\n"
        
        if payment_url:
            message += f"Para realizar o pagamento de forma rápida via Pix, Boleto ou Cartão de Crédito, clique no link abaixo:\n"
            message += f"{payment_url}\n\n"
        elif not pdf_path:
            message += "O PDF do seu boleto foi encaminhado para o seu e-mail cadastrado.\n\n"

        message += f"Agradecemos a sua parceria!\n*Atenciosamente, {company_name}*"

        if pdf_path and os.path.exists(pdf_path):
            return WhatsAppService.send_document(empresa, cliente_phone, message, pdf_path)
        else:
            return WhatsAppService.send_message(empresa, cliente_phone, message)

    @staticmethod
    def send_carnet_message(
        empresa: Empresa,
        cliente_nome: str,
        cliente_phone: str,
        amount_total: float,
        boletos_count: int,
        pdf_path: str
    ) -> bool:
        """
        Formata e envia um Carnê (vários boletos agrupados em PDF) por WhatsApp.
        """
        company_name = empresa.nome_fantasia or empresa.razao_social

        message = f"Olá, *{cliente_nome}*!\n\n"
        message += f"Segue em anexo o Carnê contendo os *{boletos_count}* boletos "
        message += f"da *{company_name}*, totalizando *R$ {amount_total:,.2f}*.\n\n"
        message += f"Você pode utilizar o PDF anexo para realizar os pagamentos nas datas de vencimento.\n\n"
        message += f"Agradecemos a sua parceria!\n*Atenciosamente, {company_name}*"

        if pdf_path and os.path.exists(pdf_path):
            return WhatsAppService.send_document(empresa, cliente_phone, message, pdf_path)
        else:
            return False

    @staticmethod
    def send_contract_message(
        empresa: Empresa,
        cliente_nome: str,
        cliente_phone: str,
        signing_url: str
    ) -> bool:
        """
        Formata e envia o link de assinatura de contrato por WhatsApp para o cliente.
        """
        company_name = empresa.nome_fantasia or empresa.razao_social

        message = f"Olá, *{cliente_nome}*!\n\n"
        message += f"Falta muito pouco para você aproveitar o melhor da internet ultraveloz da *{company_name}*! 🚀\n\n"
        message += "Para finalizarmos a ativação do seu serviço, precisamos que você revise e assine digitalmente o seu *Termo de Adesão*.\n\n"
        message += "Acesse o link seguro abaixo para assinar agora mesmo:\n"
        message += f"{signing_url}\n\n"
        message += "Caso precise de suporte, estamos à disposição!\n\n"
        message += f"*Atenciosamente, equipe {company_name}*"

        return WhatsAppService.send_message(empresa, cliente_phone, message)

    @staticmethod
    def get_connection_state(empresa: Empresa) -> Dict[str, Any]:
        """
        Consulta o status de conexão da instância do WhatsApp na Evolution API.
        Retorna {"connected": True/False, "state": "open"/"close"/etc.}
        """
        try:
            api_url = WhatsAppService._get_api_url(empresa)
            api_key = os.getenv("EVOLUTION_API_TOKEN", "brazcom_secure_token_12345")
            instance_name = getattr(empresa, 'whatsapp_api_instance', 'mega-net-telecom') or 'mega-net-telecom'

            if not api_url:
                return {"connected": False, "state": "offline", "message": "API URL não configurada"}

            if api_url.endswith("/"):
                api_url = api_url[:-1]

            endpoint = f"{api_url}/instance/connectionState/{instance_name}"
            headers = {"apikey": api_key}

            response = requests.get(endpoint, headers=headers, timeout=3)
            if response.status_code == 200:
                data = response.json()
                # O state retornado pela Evolution API v2 costuma ser "open" quando conectado
                state = data.get("instance", {}).get("state", "close")
                connected = (state == "open")
                return {"connected": connected, "state": state}
            return {"connected": False, "state": "close", "detail": f"Status HTTP: {response.status_code}"}
        except Exception as e:
            logger.warning(f"Erro ao verificar conexão da instância ({e})")
            return {"connected": False, "state": "offline", "error": str(e)}

    @staticmethod
    def get_qr_code(empresa: Empresa) -> Dict[str, Any]:
        """
        Cria/conecta a instância na Evolution API e retorna o QR Code em base64.
        """
        try:
            api_url = WhatsAppService._get_api_url(empresa)
            api_key = os.getenv("EVOLUTION_API_TOKEN", "brazcom_secure_token_12345")
            instance_name = getattr(empresa, 'whatsapp_api_instance', 'mega-net-telecom') or 'mega-net-telecom'

            if not api_url:
                return {"success": False, "message": "API URL não configurada"}

            if api_url.endswith("/"):
                api_url = api_url[:-1]

            # 1. Garante que a instância esteja criada (Evolution API v2 exige a integração WHATSAPP-BAILEYS)
            create_endpoint = f"{api_url}/instance/create"
            headers = {"Content-Type": "application/json", "apikey": api_key}
            create_payload = {
                "instanceName": instance_name,
                "token": api_key,
                "qrcode": True,
                "integration": "WHATSAPP-BAILEYS"
            }
            try:
                res = requests.post(create_endpoint, json=create_payload, headers=headers, timeout=20)
                print(f"\n[DEBUG WHATSAPP] ENVIADO PARA: {create_endpoint}")
                print(f"[DEBUG WHATSAPP] PAYLOAD: {create_payload}")
                print(f"[DEBUG WHATSAPP] HEADERS: {headers}")
                print(f"[DEBUG WHATSAPP] RESPOSTA CRIACAO: {res.status_code} - {res.text}\n")
            except Exception as e:
                print(f"\n[DEBUG WHATSAPP] ERRO EXCECAO CRIACAO: {e}\n")

            # 2. Solicita o QR Code (com retentativa caso a inicialização do Baileys ainda esteja ocorrendo)
            connect_endpoint = f"{api_url}/instance/connect/{instance_name}"
            
            base64_qr = None
            for attempt in range(1, 6):  # Tenta até 5 vezes
                print(f"\n[DEBUG WHATSAPP] SOLICITANDO QR CODE EM: {connect_endpoint} (Tentativa {attempt}/5)")
                response = requests.get(connect_endpoint, headers={"apikey": api_key}, timeout=20)
                print(f"[DEBUG WHATSAPP] RESPOSTA QR CODE: {response.status_code} - {response.text}\n")
                
                if response.status_code == 200:
                    data = response.json()
                    # A Evolution API pode retornar o base64 direto ou dentro de um objeto 'qrcode'
                    base64_qr = data.get("base64") or (data.get("qrcode", {}) if isinstance(data.get("qrcode"), dict) else {}).get("base64")
                    
                    if base64_qr:
                        return {"success": True, "base64": base64_qr}
                
                # Se não obtivemos o base64, aguardamos 2 segundos antes de tentar novamente
                print(f"[DEBUG WHATSAPP] QR Code ainda não está pronto, aguardando 2 segundos para tentar novamente...")
                time.sleep(2)
            
            return {"success": False, "message": f"Erro da API: QR Code não foi gerado a tempo pela Brazcom API."}
        except Exception as e:
            logger.error(f"Erro ao gerar QR Code do WhatsApp: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    @staticmethod
    def disconnect_instance(empresa: Empresa) -> bool:
        """
        Desconecta, faz logout e exclui a instância do WhatsApp na Evolution API.
        """
        try:
            api_url = WhatsAppService._get_api_url(empresa)
            api_key = os.getenv("EVOLUTION_API_TOKEN", "brazcom_secure_token_12345")
            instance_name = getattr(empresa, 'whatsapp_api_instance', 'mega-net-telecom') or 'mega-net-telecom'

            if not api_url:
                return False

            if api_url.endswith("/"):
                api_url = api_url[:-1]

            # 1. Tenta fazer logout (desconecta a sessão do WhatsApp)
            logout_endpoint = f"{api_url}/instance/logout/{instance_name}"
            try:
                requests.delete(logout_endpoint, headers={"apikey": api_key}, timeout=5)
            except Exception as e:
                logger.warning(f"Erro ao solicitar logout da instância: {e}")

            # 2. Exclui por completo a instância do gateway
            delete_endpoint = f"{api_url}/instance/delete/{instance_name}"
            response = requests.delete(delete_endpoint, headers={"apikey": api_key}, timeout=5)
            return response.status_code in [200, 201, 404]  # 404 significa que ela já não existia, o que também é sucesso para nós
        except Exception as e:
            logger.error(f"Erro ao desconectar/excluir instância do WhatsApp: {e}", exc_info=True)
            return False

    @staticmethod
    def send_carne_message(
        empresa: Empresa,
        cliente_nome: str,
        cliente_phone: str,
        carne_data: Dict[str, Any],
        pdf_path: str = None
    ) -> bool:
        """
        Formata e envia uma notificação de carnê por WhatsApp para o cliente.
        """
        count = carne_data.get('count', 0)
        company_name = empresa.nome_fantasia or empresa.razao_social

        message = f"Olá, *{cliente_nome}*!\n\n"
        message += f"O seu carnê contendo as próximas {count} faturas da *{company_name}* já foi gerado.\n\n"
        
        if pdf_path and os.path.exists(pdf_path):
            message += "Segue o PDF do seu carnê com todos os boletos anexado nesta mensagem.\n\n"
            message += f"Agradecemos a sua parceria!\n*Atenciosamente, {company_name}*"
            return WhatsAppService.send_document(empresa, cliente_phone, message, pdf_path)
        else:
            message += "O PDF do seu carnê com todos os boletos foi encaminhado para o seu e-mail cadastrado.\n\n"
            message += f"Agradecemos a sua parceria!\n*Atenciosamente, {company_name}*"
            return WhatsAppService.send_message(empresa, cliente_phone, message)
