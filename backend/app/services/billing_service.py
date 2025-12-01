import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import Receivable, BankAccount
from app.services.sicoob_gateway import sicoob_gateway
from app.core.security import decrypt_sensitive_data

logger = logging.getLogger(__name__)

class BillingService:
    """Serviço de cobrança integrado com gateways bancários."""

    @staticmethod
    async def register_receivable_with_bank(db: Session, receivable: Receivable) -> bool:
        """
        Registra um receivable no banco correspondente.

        Args:
            db: Sessão do banco de dados
            receivable: Objeto Receivable a ser registrado

        Returns:
            bool: True se registrado com sucesso, False caso contrário
        """
        try:
            # Verificar se há conta bancária associada
            if not receivable.bank_account_id:
                logger.warning(f"Receivable {receivable.id} não tem conta bancária associada")
                return False

            # Buscar dados da conta bancária
            bank_account = db.query(BankAccount).filter(BankAccount.id == receivable.bank_account_id).first()
            if not bank_account:
                logger.error(f"Conta bancária {receivable.bank_account_id} não encontrada")
                return False

            # Verificar se é SICOB
            if bank_account.bank != "SICOB":
                logger.info(f"Conta bancária {bank_account.id} não é SICOB, pulando registro automático")
                return False

            # Criar gateway com credenciais específicas da conta bancária
            from app.services.sicoob_gateway import SicoobGateway
            gateway = SicoobGateway(
                client_id=bank_account.sicoob_client_id,
                access_token=bank_account.sicoob_access_token
            )

            # Preparar dados para o gateway
            bank_account_data = {
                "convenio": bank_account.convenio,
                "agencia": bank_account.agencia,
                "conta": bank_account.conta,
                "cpf_cnpj_titular": bank_account.cpf_cnpj_titular,
                "titular": bank_account.titular
            }

            # Buscar dados do pagador (cliente)
            # Aqui precisaríamos buscar os dados do cliente associado ao receivable
            receivable_data = {
                "issue_date": receivable.issue_date,
                "due_date": receivable.due_date,
                "amount": receivable.amount,
                "fine_percent": receivable.fine_percent,
                "interest_percent": receivable.interest_percent,
                "discount": receivable.discount,
                # Dados do pagador - precisariam ser buscados do cliente
                "cpf_cnpj_pagador": "12345678901",  # Placeholder
                "nome_pagador": "Cliente Exemplo",  # Placeholder
                "endereco_pagador": "Rua Exemplo, 123",  # Placeholder
                "bairro_pagador": "Centro",  # Placeholder
                "cidade_pagador": "São Paulo",  # Placeholder
                "cep_pagador": "01234567",  # Placeholder
                "uf_pagador": "SP"  # Placeholder
            }

            # Preparar payload para o Sicoob
            boleto_data = gateway.preparar_dados_boleto(receivable_data, bank_account_data)

            # Registrar boleto no Sicoob
            response = await gateway.registrar_boleto(boleto_data)

            # Atualizar receivable com dados de resposta
            if response:
                receivable.nosso_numero = response.get("nossoNumero")
                receivable.bank_registration_id = response.get("numeroBoleto")
                receivable.codigo_barras = response.get("codigoBarras")
                receivable.linha_digitavel = response.get("linhaDigitavel")
                receivable.status = "REGISTERED"
                receivable.registered_at = datetime.utcnow()

                # Salvar payload da resposta
                receivable.bank_payload = json.dumps(response, default=str)

                db.commit()
                logger.info(f"Boleto registrado com sucesso no Sicoob: {receivable.nosso_numero}")
                return True

        except Exception as e:
            logger.error(f"Erro ao registrar boleto no banco: {str(e)}")
            # Marcar como erro de registro
            receivable.status = "REGISTRATION_FAILED"
            receivable.registro_result = str(e)
            db.commit()
            return False

        return False

    @staticmethod
    async def cancel_receivable_registration(db: Session, receivable: Receivable) -> bool:
        """
        Cancela o registro de um receivable no banco.

        Args:
            db: Sessão do banco de dados
            receivable: Objeto Receivable a ser cancelado

        Returns:
            bool: True se cancelado com sucesso, False caso contrário
        """
        try:
            if not receivable.nosso_numero:
                logger.warning(f"Receivable {receivable.id} não tem nosso_numero para cancelar")
                return False

            # Para SICOB, fazer baixa do boleto
            response = await sicoob_gateway.baixar_boleto(receivable.nosso_numero)

            if response:
                receivable.status = "CANCELLED"
                db.commit()
                logger.info(f"Boleto {receivable.nosso_numero} cancelado com sucesso")
                return True

        except Exception as e:
            logger.error(f"Erro ao cancelar boleto: {str(e)}")
            return False

        return False

    @staticmethod
    async def check_receivable_status(db: Session, receivable: Receivable) -> Optional[str]:
        """
        Verifica o status de um receivable no banco.

        Args:
            db: Sessão do banco de dados
            receivable: Objeto Receivable a verificar

        Returns:
            str or None: Novo status se encontrado, None caso contrário
        """
        try:
            if not receivable.nosso_numero:
                return None

            # Consultar boleto no SICOB
            response = await sicoob_gateway.consultar_boleto(receivable.nosso_numero)

            if response:
                status_banco = response.get("situacao", {}).get("codigo", "")
                # Mapear status do Sicoob para nosso sistema
                status_mapping = {
                    "01": "REGISTERED",  # Registrado
                    "02": "PAID",       # Pago
                    "03": "CANCELLED",  # Cancelado
                    "04": "EXPIRED"     # Vencido
                }

                new_status = status_mapping.get(status_banco)
                if new_status and new_status != receivable.status:
                    logger.info(f"Status do boleto {receivable.nosso_numero} alterado: {receivable.status} -> {new_status}")
                    return new_status

        except Exception as e:
            logger.error(f"Erro ao consultar status do boleto: {str(e)}")

        return None