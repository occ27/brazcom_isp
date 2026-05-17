import logging
import os
import re
import requests
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
    def send_message(empresa: Empresa, to_phone: str, message: str) -> bool:
        """
        Envia uma mensagem de WhatsApp real via Evolution API com fallback de simulação em log local.
        """
        try:
            cleaned_phone = WhatsAppService._clean_phone(to_phone)
            if not cleaned_phone:
                logger.error("Número de telefone inválido para envio de WhatsApp")
                return False

            instance_name = getattr(empresa, 'whatsapp_api_instance', 'mega-net-telecom') or 'mega-net-telecom'
            system_name = getattr(empresa, 'whatsapp_api_system', 'MK Auth') or 'MK Auth'
            
            # 1. Tenta envio via Evolution API (Real)
            api_url = getattr(empresa, 'whatsapp_api_server', None) or os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
            api_key = getattr(empresa, 'whatsapp_api_password', None) or os.getenv("EVOLUTION_API_TOKEN", "brazcom_secure_token_12345")
            
            if api_url:
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
                    logger.info(f"Tentando envio real de WhatsApp via Evolution API para {cleaned_phone}")
                    response = requests.post(endpoint, json=payload, headers=headers, timeout=5)
                    if response.status_code in [200, 201]:
                        logger.info(f"Mensagem enviada com sucesso via Evolution API para {cleaned_phone}!")
                        return True
                    else:
                        logger.warning(f"Evolution API retornou status {response.status_code}: {response.text}. Ativando fallback de simulação.")
                except Exception as api_err:
                    logger.warning(f"Falha de conexão com a Evolution API ({api_err}). Ativando fallback de simulação local.")
            
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
                f.write(f"[{empresa.razao_social}] Para: {cleaned_phone} | Msg: {message.replace('\n', ' ')}\n")

            return True
        except Exception as e:
            logger.error(f"Erro ao disparar mensagem de WhatsApp: {e}", exc_info=True)
            return False

    @staticmethod
    def send_receivable_message(
        empresa: Empresa,
        cliente_nome: str,
        cliente_phone: str,
        receivable_data: Dict[str, Any]
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
        else:
            message += "O PDF do seu boleto foi encaminhado para o seu e-mail cadastrado.\n\n"

        message += f"Agradecemos a sua parceria!\n*Atenciosamente, {company_name}*"

        return WhatsAppService.send_message(empresa, cliente_phone, message)

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
            api_url = getattr(empresa, 'whatsapp_api_server', None) or os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
            api_key = getattr(empresa, 'whatsapp_api_password', None) or os.getenv("EVOLUTION_API_TOKEN", "brazcom_secure_token_12345")
            instance_name = getattr(empresa, 'whatsapp_api_instance', 'mega-net-telecom') or 'mega-net-telecom'

            if not api_url:
                return {"connected": False, "state": "offline", "message": "API URL não configurada"}

            if api_url.endswith("/"):
                api_url = api_url[:-1]

            endpoint = f"{api_url}/instance/connectionState/{instance_name}"
            headers = {"apikey": api_key}

            response = requests.get(endpoint, headers=headers, timeout=5)
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
            api_url = getattr(empresa, 'whatsapp_api_server', None) or os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
            api_key = getattr(empresa, 'whatsapp_api_password', None) or os.getenv("EVOLUTION_API_TOKEN", "brazcom_secure_token_12345")
            instance_name = getattr(empresa, 'whatsapp_api_instance', 'mega-net-telecom') or 'mega-net-telecom'

            if not api_url:
                return {"success": False, "message": "API URL não configurada"}

            if api_url.endswith("/"):
                api_url = api_url[:-1]

            # 1. Garante que a instância esteja criada (Evolution API cria automaticamente no /connect se v1,
            # mas na v2 convém fazer a chamada de criação antes se der erro)
            create_endpoint = f"{api_url}/instance/create"
            headers = {"Content-Type": "application/json", "apikey": api_key}
            create_payload = {
                "instanceName": instance_name,
                "token": api_key,
                "qrcode": True
            }
            try:
                requests.post(create_endpoint, json=create_payload, headers=headers, timeout=5)
            except Exception:
                pass # Se já existir, a API retornará erro ou ignoramos

            # 2. Solicita o QR Code
            connect_endpoint = f"{api_url}/instance/connect/{instance_name}"
            response = requests.get(connect_endpoint, headers={"apikey": api_key}, timeout=8)
            if response.status_code == 200:
                data = response.json()
                base64_qr = data.get("base64")
                return {"success": True, "base64": base64_qr}
            return {"success": False, "message": f"Erro da API: {response.text}"}
        except Exception as e:
            logger.error(f"Erro ao gerar QR Code do WhatsApp: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    @staticmethod
    def disconnect_instance(empresa: Empresa) -> bool:
        """
        Desconecta e faz logout da instância do WhatsApp na Evolution API.
        """
        try:
            api_url = getattr(empresa, 'whatsapp_api_server', None) or os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
            api_key = getattr(empresa, 'whatsapp_api_password', None) or os.getenv("EVOLUTION_API_TOKEN", "brazcom_secure_token_12345")
            instance_name = getattr(empresa, 'whatsapp_api_instance', 'mega-net-telecom') or 'mega-net-telecom'

            if not api_url:
                return False

            if api_url.endswith("/"):
                api_url = api_url[:-1]

            endpoint = f"{api_url}/instance/logout/{instance_name}"
            response = requests.delete(endpoint, headers={"apikey": api_key}, timeout=5)
            return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Erro ao desconectar instância do WhatsApp: {e}", exc_info=True)
            return False
