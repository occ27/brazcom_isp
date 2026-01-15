"""
Gateway de integração com SICREDI para geração de arquivos de remessa CNAB 240.

Este módulo implementa a geração de arquivos de remessa no padrão CNAB 240
para o banco SICREDI (código 748), permitindo o registro de boletos bancários.

Referências:
- Layout CNAB 240 SICREDI versão 04.02.2018
- Manual de Cobrança SICREDI
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from decimal import Decimal

logger = logging.getLogger(__name__)


class SicrediCNAB240:
    """Gerador de arquivos de remessa CNAB 240 para SICREDI."""
    
    CODIGO_BANCO = "748"  # Código do SICREDI
    NOME_BANCO = "SICREDI"
    VERSAO_LAYOUT = "103"  # Versão do layout CNAB 240
    
    def __init__(self, bank_account_data: Dict[str, Any]):
        """
        Inicializa o gerador de CNAB 240.
        
        Args:
            bank_account_data: Dados da conta bancária incluindo:
                - agencia: Número da agência (4 dígitos)
                - agencia_dv: Dígito verificador da agência (1 dígito)
                - conta: Número da conta (5 dígitos)
                - conta_dv: Dígito verificador da conta (1 dígito)
                - convenio: Código do beneficiário
                - sicredi_codigo_beneficiario: Código do beneficiário no SICREDI
                - sicredi_posto: Posto de atendimento (2 dígitos)
                - sicredi_byte_id: Byte de identificação
                - titular: Nome do titular da conta
                - cpf_cnpj_titular: CPF/CNPJ do titular
        """
        self.agencia = self._format_numeric(bank_account_data.get("agencia", ""), 4)
        self.agencia_dv = bank_account_data.get("agencia_dv", "0")
        self.conta = self._format_numeric(bank_account_data.get("conta", ""), 5)
        self.conta_dv = bank_account_data.get("conta_dv", "0")
        self.codigo_beneficiario = self._format_numeric(
            bank_account_data.get("sicredi_codigo_beneficiario") or bank_account_data.get("convenio", ""),
            5
        )
        self.posto = bank_account_data.get("sicredi_posto", "01")
        self.byte_id = bank_account_data.get("sicredi_byte_id", "2")
        self.nome_empresa = self._format_text(bank_account_data.get("titular", ""), 30)
        self.cpf_cnpj = self._only_digits(bank_account_data.get("cpf_cnpj_titular", ""))
        
        # Contadores de sequência
        self.numero_sequencial_arquivo = 1
        self.numero_sequencial_lote = 1
        self.numero_sequencial_registro = 0
        self.numero_lote = 1
    
    def _only_digits(self, text: str) -> str:
        """Retorna apenas dígitos de um texto."""
        return "".join(c for c in str(text) if c.isdigit())
    
    def _format_numeric(self, value: Any, size: int, fill_char: str = "0") -> str:
        """Formata um valor numérico com zeros à esquerda."""
        digits = self._only_digits(str(value))
        return digits.zfill(size)[-size:]
    
    def _format_text(self, text: str, size: int, align: str = "left") -> str:
        """Formata texto com espaços."""
        text = str(text or "").upper()
        # Remover caracteres especiais
        text = "".join(c if c.isalnum() or c == " " else " " for c in text)
        if align == "left":
            return text.ljust(size)[:size]
        return text.rjust(size)[:size]
    
    def _format_valor(self, valor: float, size: int = 15) -> str:
        """Formata valor monetário (centavos)."""
        centavos = int(Decimal(str(valor)) * 100)
        return str(centavos).zfill(size)
    
    def _format_data(self, data: Any) -> str:
        """Formata data para DDMMAAAA."""
        if isinstance(data, str):
            # Tenta converter string ISO para datetime
            try:
                data = datetime.fromisoformat(data.replace('Z', '+00:00'))
            except:
                # Se falhar, tenta outros formatos
                try:
                    data = datetime.strptime(data, "%Y-%m-%d")
                except:
                    data = datetime.now()
        
        if isinstance(data, datetime):
            data = data.date()
        
        if isinstance(data, date):
            return data.strftime("%d%m%Y")
        
        return datetime.now().strftime("%d%m%Y")
    
    def gerar_header_arquivo(self, data_geracao: datetime = None) -> str:
        """
        Gera o registro header do arquivo (posição 0).
        
        Total: 240 caracteres
        """
        if data_geracao is None:
            data_geracao = datetime.now()
        
        # Tipo de inscrição: 1 = CPF, 2 = CNPJ
        tipo_inscricao = "2" if len(self.cpf_cnpj) == 14 else "1"
        
        linha = ""
        linha += self.CODIGO_BANCO.zfill(3)  # 001-003: Código do banco
        linha += "0000"  # 004-007: Lote de serviço (0000 para header)
        linha += "0"  # 008: Tipo de registro (0 = header arquivo)
        linha += " " * 9  # 009-017: Uso exclusivo FEBRABAN/CNAB
        linha += tipo_inscricao  # 018: Tipo de inscrição da empresa
        linha += self.cpf_cnpj.zfill(14)  # 019-032: CPF/CNPJ da empresa
        linha += " " * 20  # 033-052: Código do convênio (uso do banco)
        linha += self.agencia.zfill(5)  # 053-057: Agência
        linha += " "  # 058: DV agência (SICREDI não usa)
        linha += self.conta.zfill(12)  # 059-070: Conta corrente
        linha += self.conta_dv  # 071: DV conta
        linha += " "  # 072: DV agência/conta (não usado)
        linha += self.nome_empresa.ljust(30)  # 073-102: Nome da empresa
        linha += "SICREDI".ljust(30)  # 103-132: Nome do banco
        linha += " " * 10  # 133-142: Uso exclusivo FEBRABAN/CNAB
        linha += "1"  # 143: Código de remessa (1) / retorno (2)
        linha += data_geracao.strftime("%d%m%Y")  # 144-151: Data de geração
        linha += data_geracao.strftime("%H%M%S")  # 152-157: Hora de geração
        linha += str(self.numero_sequencial_arquivo).zfill(6)  # 158-163: Número sequencial do arquivo
        linha += self.VERSAO_LAYOUT.zfill(3)  # 164-166: Versão do layout
        linha += "0" * 5  # 167-171: Densidade de gravação (zeros)
        linha += " " * 20  # 172-191: Uso reservado do banco
        linha += " " * 20  # 192-211: Uso reservado da empresa
        linha += " " * 29  # 212-240: Uso exclusivo FEBRABAN/CNAB
        
        return linha
    
    def gerar_header_lote(self, lote: int = 1) -> str:
        """
        Gera o registro header do lote (posição 1).
        
        Total: 240 caracteres
        """
        tipo_inscricao = "2" if len(self.cpf_cnpj) == 14 else "1"
        
        linha = ""
        linha += self.CODIGO_BANCO.zfill(3)  # 001-003: Código do banco
        linha += str(lote).zfill(4)  # 004-007: Lote de serviço
        linha += "1"  # 008: Tipo de registro (1 = header lote)
        linha += "R"  # 009: Tipo de operação (R = remessa)
        linha += "01"  # 010-011: Tipo de serviço (01 = cobrança)
        linha += "00"  # 012-013: Forma de lançamento (zeros)
        linha += self.VERSAO_LAYOUT.zfill(3)  # 014-016: Versão do layout lote
        linha += " "  # 017: Uso exclusivo FEBRABAN/CNAB
        linha += tipo_inscricao  # 018: Tipo de inscrição da empresa
        linha += self.cpf_cnpj.zfill(15)  # 019-033: CPF/CNPJ da empresa
        linha += " " * 20  # 034-053: Código do convênio (uso do banco)
        linha += self.agencia.zfill(5)  # 054-058: Agência
        linha += " "  # 059: DV agência
        linha += self.conta.zfill(12)  # 060-071: Conta corrente
        linha += self.conta_dv  # 072: DV conta
        linha += " "  # 073: DV agência/conta
        linha += self.nome_empresa.ljust(30)  # 074-103: Nome da empresa
        linha += " " * 80  # 104-183: Mensagem (uso livre)
        linha += " " * 8  # 184-191: Logradouro (não usado aqui)
        linha += " " * 5  # 192-196: Número (não usado)
        linha += " " * 15  # 197-211: Complemento (não usado)
        linha += " " * 20  # 212-231: Cidade (não usado)
        linha += " " * 5  # 232-236: CEP (não usado)
        linha += " " * 2  # 237-238: UF (não usado)
        linha += " " * 2  # 239-240: Uso exclusivo
        
        return linha
    
    def gerar_segmento_p(self, boleto_data: Dict[str, Any], sequencial: int, lote: int = 1) -> str:
        """
        Gera o segmento P (dados do boleto).
        
        Total: 240 caracteres
        """
        tipo_inscricao_sacado = "2" if len(self._only_digits(boleto_data.get("cpf_cnpj_pagador", ""))) == 14 else "1"
        
        linha = ""
        linha += self.CODIGO_BANCO.zfill(3)  # 001-003: Código do banco
        linha += str(lote).zfill(4)  # 004-007: Lote de serviço
        linha += "3"  # 008: Tipo de registro (3 = detalhe)
        linha += str(sequencial).zfill(5)  # 009-013: Número sequencial
        linha += "P"  # 014: Código do segmento
        linha += " "  # 015: Uso exclusivo FEBRABAN/CNAB
        linha += "01"  # 016-017: Código de movimento (01 = entrada de título)
        linha += self.agencia.zfill(5)  # 018-022: Agência
        linha += " "  # 023: DV agência
        linha += self.conta.zfill(12)  # 024-035: Conta corrente
        linha += self.conta_dv  # 036: DV conta
        linha += " "  # 037: DV agência/conta
        
        # Nosso número (20 posições no SICREDI)
        nosso_numero = self._format_numeric(boleto_data.get("nosso_numero", ""), 20)
        linha += nosso_numero  # 038-057: Nosso número
        
        linha += "1"  # 058: Carteira (1 = simples)
        linha += "1"  # 059: Forma de cadastramento (1 = com registro)
        linha += "2"  # 060: Tipo de documento (2 = duplicata mercantil)
        linha += "1"  # 061: Identificação de emissão (1 = banco emite)
        linha += "2"  # 062: Identificação de distribuição (2 = cliente busca no banco)
        
        # Número do documento (15 posições)
        numero_documento = self._format_text(boleto_data.get("numero_documento", nosso_numero), 15)
        linha += numero_documento  # 063-077: Número do documento
        
        # Data de vencimento
        linha += self._format_data(boleto_data.get("due_date"))  # 078-085: Data de vencimento
        
        # Valor nominal
        linha += self._format_valor(boleto_data.get("amount", 0))  # 086-100: Valor nominal
        
        linha += "00000"  # 101-105: Agência cobradora (zeros = SICREDI)
        linha += " "  # 106: DV agência cobradora
        linha += "01"  # 107-108: Espécie do título (01 = duplicata mercantil)
        linha += "N"  # 109: Aceite (N = não aceite)
        
        # Data de emissão
        linha += self._format_data(boleto_data.get("issue_date"))  # 110-117: Data de emissão
        
        # Código de juros
        juros = float(boleto_data.get("interest_percent", 0))
        if juros > 0:
            linha += "1"  # 118: Código de juros (1 = valor por dia)
            linha += self._format_data(boleto_data.get("due_date"))  # 119-126: Data juros
            linha += self._format_valor(juros * float(boleto_data.get("amount", 0)) / 100)  # 127-141: Juros por dia
        else:
            linha += "0"  # 118: Sem juros
            linha += "0" * 8  # 119-126: Data juros
            linha += "0" * 15  # 127-141: Juros
        
        # Código de desconto
        desconto = float(boleto_data.get("discount", 0))
        if desconto > 0:
            linha += "1"  # 142: Código de desconto (1 = valor fixo)
            linha += self._format_data(boleto_data.get("due_date"))  # 143-150: Data desconto
            linha += self._format_valor(desconto)  # 151-165: Valor desconto
        else:
            linha += "0"  # 142: Sem desconto
            linha += "0" * 8  # 143-150: Data desconto
            linha += "0" * 15  # 151-165: Valor desconto
        
        linha += "0" * 15  # 166-180: Valor IOF
        linha += "0" * 15  # 181-195: Valor abatimento
        
        # Uso da empresa (25 posições)
        linha += self._format_text(boleto_data.get("uso_empresa", ""), 25)  # 196-220
        
        # Código de protesto e baixa
        linha += "3"  # 221: Código de protesto (3 = não protestar)
        linha += "00"  # 222-223: Prazo para protesto
        linha += "0"  # 224: Código de baixa (0 = não baixar)
        linha += "000"  # 225-227: Prazo para baixa
        linha += "09"  # 228-229: Código da moeda (09 = Real)
        linha += "0000000000"  # 230-239: Número do contrato (zeros)
        linha += " "  # 240: Uso exclusivo
        
        return linha
    
    def gerar_segmento_q(self, boleto_data: Dict[str, Any], sequencial: int, lote: int = 1) -> str:
        """
        Gera o segmento Q (dados do sacado/pagador).
        
        Total: 240 caracteres
        """
        cpf_cnpj = self._only_digits(boleto_data.get("cpf_cnpj_pagador", ""))
        tipo_inscricao = "2" if len(cpf_cnpj) == 14 else "1"
        
        linha = ""
        linha += self.CODIGO_BANCO.zfill(3)  # 001-003: Código do banco
        linha += str(lote).zfill(4)  # 004-007: Lote de serviço
        linha += "3"  # 008: Tipo de registro (3 = detalhe)
        linha += str(sequencial).zfill(5)  # 009-013: Número sequencial
        linha += "Q"  # 014: Código do segmento
        linha += " "  # 015: Uso exclusivo FEBRABAN/CNAB
        linha += "01"  # 016-017: Código de movimento
        linha += tipo_inscricao  # 018: Tipo de inscrição sacado
        linha += cpf_cnpj.zfill(15)  # 019-033: CPF/CNPJ do sacado
        linha += self._format_text(boleto_data.get("nome_pagador", ""), 40)  # 034-073: Nome do sacado
        linha += self._format_text(boleto_data.get("endereco_pagador", ""), 40)  # 074-113: Endereço
        linha += self._format_text(boleto_data.get("bairro_pagador", ""), 15)  # 114-128: Bairro
        linha += self._only_digits(boleto_data.get("cep_pagador", "")).zfill(8)  # 129-136: CEP
        linha += self._format_text(boleto_data.get("cidade_pagador", ""), 15)  # 137-151: Cidade
        linha += self._format_text(boleto_data.get("uf_pagador", ""), 2)  # 152-153: UF
        
        # Sacador/Avalista (caso exista)
        linha += "0"  # 154: Tipo de inscrição sacador (0 = não informado)
        linha += "0" * 15  # 155-169: CPF/CNPJ sacador
        linha += " " * 40  # 170-209: Nome sacador
        
        # Código de baixa e banco correspondente
        linha += "000"  # 210-212: Código banco correspondente
        linha += " " * 20  # 213-232: Nosso número banco correspondente
        linha += " " * 8  # 233-240: Uso exclusivo FEBRABAN/CNAB
        
        return linha
    
    def gerar_segmento_r(self, boleto_data: Dict[str, Any], sequencial: int, lote: int = 1) -> str:
        """
        Gera o segmento R (multa e mensagens).
        
        Total: 240 caracteres
        """
        linha = ""
        linha += self.CODIGO_BANCO.zfill(3)  # 001-003: Código do banco
        linha += str(lote).zfill(4)  # 004-007: Lote de serviço
        linha += "3"  # 008: Tipo de registro (3 = detalhe)
        linha += str(sequencial).zfill(5)  # 009-013: Número sequencial
        linha += "R"  # 014: Código do segmento
        linha += " "  # 015: Uso exclusivo FEBRABAN/CNAB
        linha += "01"  # 016-017: Código de movimento
        linha += "0"  # 018: Código de desconto 2 (0 = sem desconto)
        linha += "0" * 8  # 019-026: Data desconto 2
        linha += "0" * 15  # 027-041: Valor/Percentual desconto 2
        linha += "0"  # 042: Código de desconto 3
        linha += "0" * 8  # 043-050: Data desconto 3
        linha += "0" * 15  # 051-065: Valor/Percentual desconto 3
        
        # Código de multa
        multa = float(boleto_data.get("fine_percent", 0))
        if multa > 0:
            linha += "2"  # 066: Código de multa (2 = percentual)
            linha += self._format_data(boleto_data.get("due_date"))  # 067-074: Data multa
            linha += self._format_valor(multa, 15)  # 075-089: Valor/Percentual multa
        else:
            linha += "0"  # 066: Sem multa
            linha += "0" * 8  # 067-074: Data multa
            linha += "0" * 15  # 075-089: Valor multa
        
        # Informações ao sacado
        instrucoes = boleto_data.get("instrucoes", [])
        mensagem = " ".join(instrucoes) if isinstance(instrucoes, list) else str(instrucoes)
        
        linha += " " * 10  # 090-099: Informação ao sacado (não usado)
        linha += self._format_text(mensagem, 40)  # 100-139: Mensagem 3
        linha += " " * 40  # 140-179: Mensagem 4
        linha += " " * 20  # 180-199: Uso exclusivo FEBRABAN/CNAB
        linha += "0" * 8  # 200-207: Código ocorrência sacado (zeros)
        linha += "0" * 8  # 208-215: Código banco débito automático
        linha += "0" * 5  # 216-220: Agência débito
        linha += " "  # 221: DV agência débito
        linha += "0" * 12  # 222-233: Conta débito
        linha += " "  # 234: DV conta débito
        linha += " "  # 235: DV agência/conta débito
        linha += " "  # 236: Aviso ao débito automático
        linha += " " * 4  # 237-240: Uso exclusivo FEBRABAN/CNAB
        
        return linha
    
    def gerar_trailer_lote(self, lote: int, qtd_registros: int) -> str:
        """
        Gera o registro trailer do lote.
        
        Total: 240 caracteres
        """
        linha = ""
        linha += self.CODIGO_BANCO.zfill(3)  # 001-003: Código do banco
        linha += str(lote).zfill(4)  # 004-007: Lote de serviço
        linha += "5"  # 008: Tipo de registro (5 = trailer lote)
        linha += " " * 9  # 009-017: Uso exclusivo FEBRABAN/CNAB
        linha += str(qtd_registros + 2).zfill(6)  # 018-023: Quantidade de registros no lote
        linha += "0" * 6  # 024-029: Quantidade de títulos em cobrança simples
        linha += "0" * 17  # 030-046: Valor total dos títulos em cobrança simples
        linha += "0" * 6  # 047-052: Quantidade de títulos em cobrança vinculada
        linha += "0" * 17  # 053-069: Valor total dos títulos em cobrança vinculada
        linha += "0" * 6  # 070-075: Quantidade de títulos em cobrança caucionada
        linha += "0" * 17  # 076-092: Valor total dos títulos em cobrança caucionada
        linha += "0" * 6  # 093-098: Quantidade de títulos em cobrança descontada
        linha += "0" * 17  # 099-115: Valor total dos títulos em cobrança descontada
        linha += " " * 8  # 116-123: Número do aviso de lançamento
        linha += " " * 117  # 124-240: Uso exclusivo FEBRABAN/CNAB
        
        return linha
    
    def gerar_trailer_arquivo(self, qtd_lotes: int, qtd_registros: int) -> str:
        """
        Gera o registro trailer do arquivo.
        
        Total: 240 caracteres
        """
        linha = ""
        linha += self.CODIGO_BANCO.zfill(3)  # 001-003: Código do banco
        linha += "9999"  # 004-007: Lote de serviço (9999 para trailer)
        linha += "9"  # 008: Tipo de registro (9 = trailer arquivo)
        linha += " " * 9  # 009-017: Uso exclusivo FEBRABAN/CNAB
        linha += str(qtd_lotes).zfill(6)  # 018-023: Quantidade de lotes
        linha += str(qtd_registros).zfill(6)  # 024-029: Quantidade de registros
        linha += "0" * 6  # 030-035: Quantidade de contas conciliação
        linha += " " * 205  # 036-240: Uso exclusivo FEBRABAN/CNAB
        
        return linha
    
    def gerar_arquivo_remessa(self, boletos: List[Dict[str, Any]], data_geracao: datetime = None) -> str:
        """
        Gera um arquivo de remessa completo CNAB 240 para SICREDI.
        
        Args:
            boletos: Lista de dicionários com dados dos boletos
            data_geracao: Data de geração do arquivo
            
        Returns:
            String contendo o conteúdo do arquivo CNAB 240
        """
        if data_geracao is None:
            data_geracao = datetime.now()
        
        linhas = []
        
        # Header do arquivo
        linhas.append(self.gerar_header_arquivo(data_geracao))
        
        # Header do lote
        linhas.append(self.gerar_header_lote(self.numero_lote))
        
        # Registros de detalhe (segmentos P, Q e R para cada boleto)
        sequencial = 1
        for boleto in boletos:
            linhas.append(self.gerar_segmento_p(boleto, sequencial, self.numero_lote))
            sequencial += 1
            
            linhas.append(self.gerar_segmento_q(boleto, sequencial, self.numero_lote))
            sequencial += 1
            
            linhas.append(self.gerar_segmento_r(boleto, sequencial, self.numero_lote))
            sequencial += 1
        
        qtd_registros_lote = len(boletos) * 3  # 3 segmentos por boleto
        
        # Trailer do lote
        linhas.append(self.gerar_trailer_lote(self.numero_lote, qtd_registros_lote))
        
        # Trailer do arquivo
        qtd_registros_arquivo = len(linhas) + 1  # +1 para o próprio trailer
        linhas.append(self.gerar_trailer_arquivo(1, qtd_registros_arquivo))
        
        return "\n".join(linhas)


class SicrediGateway:
    """Gateway de integração com SICREDI para geração de cobranças."""
    
    def __init__(self, bank_account_data: Dict[str, Any]):
        """
        Inicializa o gateway SICREDI.
        
        Args:
            bank_account_data: Dados da conta bancária
        """
        self.bank_account_data = bank_account_data
        self.cnab_generator = SicrediCNAB240(bank_account_data)
    
    def preparar_dados_boleto(self, receivable_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepara os dados do receivable no formato esperado para geração CNAB.
        
        Args:
            receivable_data: Dados do receivable
            
        Returns:
            Dict formatado para geração CNAB
        """
        return {
            "nosso_numero": receivable_data.get("nosso_numero", ""),
            "numero_documento": receivable_data.get("id", ""),
            "due_date": receivable_data.get("due_date"),
            "issue_date": receivable_data.get("issue_date"),
            "amount": receivable_data.get("amount", 0),
            "discount": receivable_data.get("discount", 0),
            "interest_percent": receivable_data.get("interest_percent", 0),
            "fine_percent": receivable_data.get("fine_percent", 0),
            "cpf_cnpj_pagador": receivable_data.get("cpf_cnpj_pagador", ""),
            "nome_pagador": receivable_data.get("nome_pagador", ""),
            "endereco_pagador": receivable_data.get("endereco_pagador", ""),
            "bairro_pagador": receivable_data.get("bairro_pagador", ""),
            "cidade_pagador": receivable_data.get("cidade_pagador", ""),
            "cep_pagador": receivable_data.get("cep_pagador", ""),
            "uf_pagador": receivable_data.get("uf_pagador", ""),
            "instrucoes": receivable_data.get("instrucoes", [
                "Não aceitar pagamento após vencimento",
                "Multa e juros conforme contrato"
            ]),
            "uso_empresa": receivable_data.get("uso_empresa", "")
        }
    
    def gerar_arquivo_remessa(self, receivables: List[Dict[str, Any]]) -> str:
        """
        Gera arquivo de remessa CNAB 240 para uma lista de receivables.
        
        Args:
            receivables: Lista de receivables
            
        Returns:
            Conteúdo do arquivo CNAB 240
        """
        boletos = [self.preparar_dados_boleto(r) for r in receivables]
        return self.cnab_generator.gerar_arquivo_remessa(boletos)
    
    def salvar_arquivo_remessa(self, receivables: List[Dict[str, Any]], filepath: str) -> str:
        """
        Gera e salva arquivo de remessa em disco.
        
        Args:
            receivables: Lista de receivables
            filepath: Caminho onde salvar o arquivo
            
        Returns:
            Caminho do arquivo salvo
        """
        conteudo = self.gerar_arquivo_remessa(receivables)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        logger.info(f"Arquivo de remessa SICREDI salvo em: {filepath}")
        return filepath


# Instância global (pode ser configurada dinamicamente)
def create_sicredi_gateway(bank_account_data: Dict[str, Any]) -> SicrediGateway:
    """Factory para criar instância do gateway SICREDI."""
    return SicrediGateway(bank_account_data)
