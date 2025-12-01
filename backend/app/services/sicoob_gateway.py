import httpx
import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime, date
from app.core.config import settings

logger = logging.getLogger(__name__)

class SicoobGateway:
    """Gateway de integração com APIs do Sicoob para cobrança bancária."""

    def __init__(self, client_id: str = None, access_token: str = None):
        # Credenciais podem ser passadas dinamicamente ou usar valores padrão do sandbox
        self.client_id = client_id or "9b5e603e428cc477a2841e2683c92d21"
        self.access_token = access_token or "1301865f-c6bc-38f3-9f49-666dbcfc59c3"

        # URL base única conforme especificado
        self.base_url = "https://sandbox.sicoob.com.br/sicoob/sandbox/cobranca-bancaria/v3"

        # Headers padrão
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'client_id': self.client_id
        }

    async def _make_request(self, method: str, url: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Faz uma requisição HTTP para a API do Sicoob."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == 'GET':
                    response = await client.get(url, headers=self.headers)
                elif method.upper() == 'POST':
                    response = await client.post(url, headers=self.headers, json=data)
                elif method.upper() == 'PUT':
                    response = await client.put(url, headers=self.headers, json=data)
                elif method.upper() == 'DELETE':
                    response = await client.delete(url, headers=self.headers)
                else:
                    raise ValueError(f"Método HTTP não suportado: {method}")

                logger.info(f"Sicoob API {method} {url} - Status: {response.status_code}")

                if response.status_code >= 200 and response.status_code < 300:
                    return response.json() if response.content else {}
                else:
                    error_msg = f"Sicoob API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

        except httpx.RequestError as e:
            error_msg = f"Erro de conexão com Sicoob API: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def registrar_boleto(self, dados_boleto: Dict[str, Any]) -> Dict[str, Any]:
        """
        Registra um boleto bancário no Sicoob.

        Args:
            dados_boleto: Dicionário com os dados do boleto

        Returns:
            Dict com os dados de resposta da API
        """
        url = f"{self.base_url}/boletos"

        # Estrutura esperada pela API do Sicoob
        payload = {
            "numeroContrato": dados_boleto.get("numeroContrato"),
            "modalidade": dados_boleto.get("modalidade", 1),  # 1 = Simples
            "numeroContaCorrente": dados_boleto.get("numeroContaCorrente"),
            "especieDocumento": dados_boleto.get("especieDocumento", "DM"),  # DM = Duplicata Mercantil
            "dataEmissao": dados_boleto.get("dataEmissao"),
            "dataVencimento": dados_boleto.get("dataVencimento"),
            "valor": dados_boleto.get("valor"),
            "pagador": dados_boleto.get("pagador", {}),
            "beneficiario": dados_boleto.get("beneficiario", {}),
            "instrucoes": dados_boleto.get("instrucoes", []),
            "multa": dados_boleto.get("multa", 0),
            "juros": dados_boleto.get("juros", 0),
            "desconto": dados_boleto.get("desconto", 0)
        }

        logger.info(f"Registrando boleto no Sicoob: {payload}")
        return await self._make_request('POST', url, payload)

    async def consultar_boleto(self, numero_boleto: str) -> Dict[str, Any]:
        """
        Consulta um boleto registrado no Sicoob.

        Args:
            numero_boleto: Número do boleto a consultar

        Returns:
            Dict com os dados do boleto
        """
        url = f"{self.base_url}/boletos/{numero_boleto}"
        return await self._make_request('GET', url)

    async def baixar_boleto(self, numero_boleto: str) -> Dict[str, Any]:
        """
        Baixa um boleto no Sicoob.

        Args:
            numero_boleto: Número do boleto a baixar

        Returns:
            Dict com confirmação da baixa
        """
        url = f"{self.base_url}/boletos/{numero_boleto}/baixar"
        return await self._make_request('POST', url)

    async def consultar_conta_corrente(self, numero_conta: str) -> Dict[str, Any]:
        """
        Consulta informações da conta corrente.

        Args:
            numero_conta: Número da conta corrente

        Returns:
            Dict com informações da conta
        """
        # Nota: Este endpoint pode não estar disponível na API de cobrança bancária
        # Mantido para compatibilidade futura
        url = f"{self.base_url}/contas/{numero_conta}"
        return await self._make_request('GET', url)

    def preparar_dados_boleto(self, receivable_data: Dict[str, Any], bank_account_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepara os dados do boleto no formato esperado pela API do Sicoob.

        Args:
            receivable_data: Dados do receivable
            bank_account_data: Dados da conta bancária

        Returns:
            Dict formatado para a API
        """
        # Garantir que as datas sejam objetos datetime
        issue_date = receivable_data.get("issue_date")
        due_date = receivable_data.get("due_date")

        if isinstance(issue_date, str):
            from datetime import datetime
            issue_date = datetime.fromisoformat(issue_date.replace('Z', '+00:00'))
        elif not isinstance(issue_date, datetime):
            issue_date = datetime.now()

        if isinstance(due_date, str):
            due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
        elif not isinstance(due_date, datetime):
            due_date = datetime.now()

        return {
            "numeroContrato": bank_account_data.get("convenio"),
            "numeroContaCorrente": f"{bank_account_data.get('agencia', '')}{bank_account_data.get('conta', '')}",
            "dataEmissao": issue_date.strftime("%Y-%m-%d"),
            "dataVencimento": due_date.strftime("%Y-%m-%d"),
            "valor": receivable_data.get("amount", 0),
            "pagador": {
                "numeroCpfCnpj": receivable_data.get("cpf_cnpj_pagador"),
                "nome": receivable_data.get("nome_pagador"),
                "endereco": receivable_data.get("endereco_pagador"),
                "bairro": receivable_data.get("bairro_pagador"),
                "cidade": receivable_data.get("cidade_pagador"),
                "cep": receivable_data.get("cep_pagador"),
                "uf": receivable_data.get("uf_pagador")
            },
            "beneficiario": {
                "numeroCpfCnpj": bank_account_data.get("cpf_cnpj_titular"),
                "nome": bank_account_data.get("titular")
            },
            "instrucoes": receivable_data.get("instrucoes", [
                "Não aceitar pagamento após vencimento",
                "Multa de mora: conforme contrato",
                "Juros de mora: conforme contrato"
            ]),
            "multa": receivable_data.get("fine_percent", 0),
            "juros": receivable_data.get("interest_percent", 0),
            "desconto": receivable_data.get("discount", 0)
        }


# Instância global do gateway
sicoob_gateway = SicoobGateway()