import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.models.models import Receivable, BankAccount
from app.services.sicoob_gateway import sicoob_gateway
from app.services.sicredi_gateway import create_sicredi_gateway
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

            # Verificar tipo de banco e processar adequadamente
            if bank_account.bank == "SICOB":
                return await BillingService._register_sicoob(db, receivable, bank_account)
            elif bank_account.bank == "SICREDI":
                return await BillingService._register_sicredi(db, receivable, bank_account)
            else:
                logger.info(f"Conta bancária {bank_account.id} não suporta registro automático: {bank_account.bank}")
                return False

        except Exception as e:
            logger.error(f"Erro ao registrar boleto no banco: {str(e)}")
            receivable.status = "REGISTRATION_FAILED"
            receivable.registro_result = str(e)
            db.commit()
            return False

    @staticmethod
    async def _register_sicoob(db: Session, receivable: Receivable, bank_account: BankAccount) -> bool:
        """Registra boleto via API SICOOB."""
        try:
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
            logger.error(f"Erro ao registrar boleto via SICOOB: {str(e)}")
            receivable.status = "REGISTRATION_FAILED"
            receivable.registro_result = str(e)
            db.commit()
            return False

    @staticmethod
    async def _register_sicredi(db: Session, receivable: Receivable, bank_account: BankAccount) -> bool:
        """
        Registra boleto via SICREDI (gera entrada no arquivo de remessa).
        
        SICREDI usa arquivo de remessa CNAB 240, não API online.
        Este método marca o boleto como pendente de remessa.
        """
        try:
            # Buscar dados do cliente para o boleto
            from app.models.models import Cliente, EmpresaCliente, EmpresaClienteEndereco
            
            cliente = db.query(Cliente).filter(Cliente.id == receivable.cliente_id).first()
            if not cliente:
                logger.error(f"Cliente {receivable.cliente_id} não encontrado")
                return False
            
            # Buscar endereço principal do cliente
            empresa_cliente = db.query(EmpresaCliente).filter(
                EmpresaCliente.cliente_id == receivable.cliente_id,
                EmpresaCliente.empresa_id == receivable.empresa_id
            ).first()
            
            endereco = None
            if empresa_cliente:
                endereco = db.query(EmpresaClienteEndereco).filter(
                    EmpresaClienteEndereco.empresa_cliente_id == empresa_cliente.id,
                    EmpresaClienteEndereco.is_principal == True
                ).first()
            
            # Gerar nosso número se não existir
            if not receivable.nosso_numero:
                # Incrementar sequência e gerar nosso número
                bank_account.nosso_numero_sequence = (bank_account.nosso_numero_sequence or 0) + 1
                receivable.nosso_numero = str(bank_account.nosso_numero_sequence).zfill(10)
                db.commit()
            
            # Copiar dados da conta bancária para o receivable (snapshot)
            receivable.agencia = bank_account.agencia
            receivable.conta = bank_account.conta
            receivable.carteira = bank_account.carteira or "1"  # Carteira simples por padrão
            
            # Criar snapshot dos dados da conta
            bank_snapshot = {
                "bank": bank_account.bank,
                "agencia": bank_account.agencia,
                "conta": bank_account.conta,
                "carteira": bank_account.carteira,
                "convenio": bank_account.convenio,
                "sicredi_codigo_beneficiario": bank_account.sicredi_codigo_beneficiario,
                "sicredi_posto": bank_account.sicredi_posto,
                "sicredi_byte_id": bank_account.sicredi_byte_id
            }
            receivable.bank_account_snapshot = json.dumps(bank_snapshot)
            
            # Marcar como pendente de remessa
            receivable.status = "PENDING_REMITTANCE"
            receivable.registro_result = "Aguardando geração de arquivo de remessa CNAB 240"
            
            db.commit()
            logger.info(f"Boleto SICREDI {receivable.nosso_numero} marcado como pendente de remessa")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao preparar boleto SICREDI: {str(e)}")
            receivable.status = "REGISTRATION_FAILED"
            receivable.registro_result = str(e)
            db.commit()
            return False

    @staticmethod
    def generate_sicredi_remittance_file(
        db: Session, 
        empresa_id: int, 
        bank_account_id: int,
        receivable_ids: Optional[List[int]] = None
    ) -> Optional[str]:
        """
        Gera arquivo de remessa CNAB 240 para SICREDI.
        
        Args:
            db: Sessão do banco de dados
            empresa_id: ID da empresa
            bank_account_id: ID da conta bancária SICREDI
            receivable_ids: IDs específicos de receivables (opcional)
            
        Returns:
            str: Caminho do arquivo gerado ou None em caso de erro
        """
        try:
            from app.models.models import Cliente, EmpresaCliente, EmpresaClienteEndereco
            
            # Buscar conta bancária
            bank_account = db.query(BankAccount).filter(
                BankAccount.id == bank_account_id,
                BankAccount.empresa_id == empresa_id,
                BankAccount.bank == "SICREDI"
            ).first()
            
            if not bank_account:
                logger.error(f"Conta bancária SICREDI {bank_account_id} não encontrada")
                return None
            
            # Buscar receivables pendentes de remessa
            query = db.query(Receivable).filter(
                Receivable.empresa_id == empresa_id,
                Receivable.bank_account_id == bank_account_id,
                Receivable.status == "PENDING_REMITTANCE"
            )
            
            if receivable_ids:
                query = query.filter(Receivable.id.in_(receivable_ids))
            
            receivables = query.all()
            
            if not receivables:
                logger.warning(f"Nenhum receivable pendente de remessa encontrado")
                return None
            
            # Preparar dados da conta bancária
            bank_account_data = {
                "agencia": bank_account.agencia,
                "agencia_dv": bank_account.agencia_dv,
                "conta": bank_account.conta,
                "conta_dv": bank_account.conta_dv,
                "convenio": bank_account.convenio,
                "sicredi_codigo_beneficiario": bank_account.sicredi_codigo_beneficiario,
                "sicredi_posto": bank_account.sicredi_posto or "01",
                "sicredi_byte_id": bank_account.sicredi_byte_id or "2",
                "titular": bank_account.titular,
                "cpf_cnpj_titular": bank_account.cpf_cnpj_titular
            }
            
            # Criar gateway
            gateway = create_sicredi_gateway(bank_account_data)
            
            # Preparar dados dos receivables
            receivables_data = []
            for recv in receivables:
                # Buscar dados do cliente
                cliente = db.query(Cliente).filter(Cliente.id == recv.cliente_id).first()
                if not cliente:
                    continue
                
                # Buscar endereço
                empresa_cliente = db.query(EmpresaCliente).filter(
                    EmpresaCliente.cliente_id == recv.cliente_id,
                    EmpresaCliente.empresa_id == empresa_id
                ).first()
                
                endereco = None
                if empresa_cliente:
                    endereco = db.query(EmpresaClienteEndereco).filter(
                        EmpresaClienteEndereco.empresa_cliente_id == empresa_cliente.id,
                        EmpresaClienteEndereco.is_principal == True
                    ).first()
                
                receivable_data = {
                    "id": recv.id,
                    "nosso_numero": recv.nosso_numero,
                    "issue_date": recv.issue_date,
                    "due_date": recv.due_date,
                    "amount": recv.amount,
                    "discount": recv.discount or 0,
                    "interest_percent": recv.interest_percent or 0,
                    "fine_percent": recv.fine_percent or 0,
                    "cpf_cnpj_pagador": cliente.cpf_cnpj,
                    "nome_pagador": cliente.nome_razao_social,
                    "endereco_pagador": endereco.endereco if endereco else "",
                    "bairro_pagador": endereco.bairro if endereco else "",
                    "cidade_pagador": endereco.municipio if endereco else "",
                    "cep_pagador": endereco.cep if endereco else "",
                    "uf_pagador": endereco.uf if endereco else "",
                    "instrucoes": json.loads(bank_account.instructions) if bank_account.instructions else [
                        "Não aceitar pagamento após vencimento"
                    ]
                }
                
                receivables_data.append(receivable_data)
            
            # Gerar arquivo de remessa
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sicredi_remessa_{empresa_id}_{timestamp}.txt"
            filepath = os.path.join("uploads", "remessas", filename)
            
            # Criar diretório se não existir
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Salvar arquivo
            gateway.salvar_arquivo_remessa(receivables_data, filepath)
            
            # Atualizar status dos receivables
            for recv in receivables:
                recv.status = "REMITTED"
                recv.sent_at = datetime.utcnow()
                recv.registro_result = f"Incluído em arquivo de remessa: {filename}"
            
            db.commit()
            
            logger.info(f"Arquivo de remessa SICREDI gerado: {filepath} ({len(receivables)} boletos)")
            return filepath
            
        except Exception as e:
            logger.error(f"Erro ao gerar arquivo de remessa SICREDI: {str(e)}")
            return None

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