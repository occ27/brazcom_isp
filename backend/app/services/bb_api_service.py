# -*- coding: utf-8 -*-
"""
Serviço de integração com a API de Cobrança do Banco do Brasil (v2).
Sincronizado com Agrobraz.
"""

from __future__ import annotations
import logging
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional, Any, Dict, List

import httpx
from sqlalchemy.orm import Session
from app.models.models import Receivable, BankAccount, Cliente, Empresa

logger = logging.getLogger(__name__)

# URLs por ambiente
_OAUTH_URL = {
    True:  'https://oauth.hm.bb.com.br/oauth/token',   # sandbox
    False: 'https://oauth.bb.com.br/oauth/token',       # produção
}

_API_BASE = {
    True:  'https://api.hm.bb.com.br',   # sandbox
    False: 'https://api.bb.com.br',       # produção
}

# Cache de tokens em memória
_token_cache: Dict[int, tuple] = {}
_last_auth_failure: Dict[int, float] = {}  # Cache de falhas para evitar loops de 429

TIPO_TITULO = {
    'DM': 2,   # Duplicata Mercantil
    'DS': 4,   # Duplicata de Serviço
    'NP': 12,  # Nota Promissória
    'RC': 17,  # Recibo
    'OUT': 31, # Outros
}

SANDBOX_CEDENTE = {
    'numeroConvenio':          3128557,
    'numeroCarteira':          17,
    'numeroVariacaoCarteira':  35,
    'numeroAgenciaCliente':    452,
    'numeroContaCliente':      123873,
    'digitoVerificadorConta':  '7',
}

_SITUACAO_MAP = {
    # Códigos zero-padded (API de consulta)
    '01': 'REGISTERED',   # Normal (a vencer)
    '02': 'REGISTERED',   # Vencido
    '03': 'CANCELLED',    # Baixado (não pago)
    '04': 'CANCELLED',    # Transferido para cartório / Baixado
    '05': 'REGISTERED',   # Em cartório
    '06': 'PAID',         # Liquidado (pago)
    '07': 'CANCELLED',    # Confirmação de recebimento de instrução de baixa
    '09': 'CANCELLED',    # Baixado automaticamente
    # Códigos sem zero (payload do webhook BB)
    '1': 'REGISTERED',
    '2': 'REGISTERED',
    '3': 'CANCELLED',
    '4': 'CANCELLED',
    '5': 'REGISTERED',
    '6': 'PAID',
    '7': 'CANCELLED',
    '9': 'CANCELLED',
}

def situacao_para_status(codigo: str) -> str:
    """Converte o codigoSituacao da API BB para o status interno (REGISTERED, PAID, CANCELLED)."""
    return _SITUACAO_MAP.get(str(codigo), 'REGISTERED')

SANDBOX_PAGADOR_CPF = '12345678909'
SANDBOX_PAGADOR_NOME = 'CLIENTE TESTE BB HOMOLOGACAO'

def _make_http_client(sandbox: bool, company=None) -> httpx.Client:
    return httpx.Client(timeout=30.0)

def _fmt_date(d: Optional[date]) -> str:
    if d is None:
        return datetime.today().strftime('%d.%m.%Y')
    return d.strftime('%d.%m.%Y')

def _strip_doc(doc: str) -> str:
    return ''.join(filter(str.isdigit, doc or ''))

def _nosso_numero_seq(nosso_numero_raw: str, convenio: str) -> str:
    if '/' in nosso_numero_raw:
        seq_part = nosso_numero_raw.split('/')[-1].strip()
    else:
        seq_part = nosso_numero_raw
    only_digits = ''.join(filter(str.isdigit, seq_part))
    seq10 = only_digits[-10:].zfill(10)
    conv7 = ''.join(filter(str.isdigit, convenio or ''))[-7:].zfill(7)
    return '000' + conv7 + seq10

def get_access_token(bank_account_id: int, client_id: str, client_secret: str,
                      app_key: str, sandbox: bool = True, company=None) -> str:
    now = time.time()
    
    # Se falhou nos últimos 30 segundos, não tenta de novo para não agravar 429
    last_fail = _last_auth_failure.get(bank_account_id, 0)
    if now - last_fail < 30:
        raise ValueError('Autenticação BB temporariamente bloqueada após falha recente. Aguarde 30 segundos.')

    cached = _token_cache.get(bank_account_id)
    if cached:
        token, expires_at = cached
        if now < expires_at - 60:
            return token

    url = _OAUTH_URL[sandbox]
    client_id = client_id.strip()
    client_secret = client_secret.strip()
    app_key = app_key.strip()
    
    try:
        with _make_http_client(sandbox, company) as client:
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'gw-dev-app-key': app_key,
                'X-Developer-Application-Key': app_key
            }
            resp = client.post(
                url,
                data={
                    'grant_type': 'client_credentials',
                    'scope': 'cobrancas.boletos-info cobrancas.boletos-requisicao'
                },
                auth=(client_id, client_secret),
                headers=headers,
            )
        
        if resp.status_code == 429:
            _last_auth_failure[bank_account_id] = now
            raise ValueError('Limite de taxa (429) excedido no Banco do Brasil. Aguarde alguns minutos (Cloudflare Error 1015).')
            
        resp.raise_for_status()
        
    except httpx.HTTPStatusError as exc:
        _last_auth_failure[bank_account_id] = now
        error_text = exc.response.text
        if "Cloudflare" in error_text or "1015" in error_text:
            error_text = "Bloqueio de segurança Cloudflare (Rate Limit). Verifique se o IP do servidor não está bloqueado no BB ou se você está usando credenciais de Sandbox em Produção."
        
        logger.error(f'BB OAuth erro HTTP {exc.response.status_code}: {error_text}')
        raise ValueError(f'Falha na autenticação BB ({exc.response.status_code}): {error_text}')
    except Exception as exc:
        logger.error(f'BB OAuth erro: {str(exc)}')
        raise ValueError(f'Falha na conexão com BB: {str(exc)}')

    data = resp.json()
    token = data.get('access_token', '')
    expires_in = int(data.get('expires_in', 600))
    _token_cache[bank_account_id] = (token, now + expires_in)
    # Limpa falha anterior se teve sucesso
    _last_auth_failure.pop(bank_account_id, None)
    return token

def registrar_boleto(
    db: Session,
    bank_account: BankAccount,
    receivable: Receivable,
    usar_pix: bool = True
) -> Dict[str, Any]:
    ba = bank_account
    sandbox = bool(ba.bb_sandbox)
    client_id = ba.bb_client_id
    client_secret = ba.bb_client_secret
    app_key = (ba.bb_app_key or '').strip()

    if not client_id or not client_secret or not app_key:
        raise ValueError('Credenciais da API BB não configuradas.')

    from app.core.security import decrypt_sensitive_data
    try:
        client_secret_dec = decrypt_sensitive_data(client_secret)
    except:
        client_secret_dec = client_secret

    token = get_access_token(ba.id, client_id, client_secret_dec, app_key, sandbox)

    # Dados do cliente
    cliente = db.query(Cliente).filter(Cliente.id == receivable.cliente_id).first()
    if not cliente:
        raise ValueError('Cliente não encontrado.')

    client_name = cliente.nome_razao_social
    client_doc = cliente.cpf_cnpj

    # Buscar endereço principal do cliente para a empresa associada
    from app.models.models import EmpresaCliente, EmpresaClienteEndereco
    emp_cli = db.query(EmpresaCliente).filter(
        EmpresaCliente.cliente_id == receivable.cliente_id,
        EmpresaCliente.empresa_id == receivable.empresa_id
    ).first()
    
    endereco_obj = None
    if emp_cli:
        endereco_obj = db.query(EmpresaClienteEndereco).filter(
            EmpresaClienteEndereco.empresa_cliente_id == emp_cli.id,
            EmpresaClienteEndereco.is_principal == True
        ).first()

    # Mapeamento do cedente (Agrobraz pattern)
    convenio = ''.join(filter(str.isdigit, (ba.convenio or '').strip()))
    carteira = int(ba.carteira or 17)
    carteira_variacao = int(ba.carteira_variacao or 35)

    if sandbox:
        convenio_int      = SANDBOX_CEDENTE['numeroConvenio']
        carteira          = SANDBOX_CEDENTE['numeroCarteira']
        carteira_variacao = SANDBOX_CEDENTE['numeroVariacaoCarteira']
        agencia_cedente   = SANDBOX_CEDENTE['numeroAgenciaCliente']
        conta_cedente     = SANDBOX_CEDENTE['numeroContaCliente']
        dv_conta_cedente  = SANDBOX_CEDENTE['digitoVerificadorConta']
        client_doc_use    = SANDBOX_PAGADOR_CPF
        client_name_use   = SANDBOX_PAGADOR_NOME
        # Sandbox exige numeroTituloCliente único
        seq_ts = str(int(time.time()))[-10:].zfill(10)
        conv7  = str(SANDBOX_CEDENTE['numeroConvenio']).zfill(7)
        numero_titulo_cliente = '000' + conv7 + seq_ts
        
        endereco_str = 'ENDERECO TESTE'
        cep_int = 12345678
        cidade_str = 'CIDADE'
        bairro_str = 'BAIRRO'
        uf_str = 'DF'
    else:
        convenio_int      = int(convenio)
        agencia_cedente   = int(''.join(filter(str.isdigit, ba.agencia or '')) or 0)
        conta_cedente     = int(''.join(filter(str.isdigit, ba.conta or '')) or 0)
        dv_conta_cedente  = (ba.conta_dv or '').strip()
        client_doc_use    = _strip_doc(client_doc)
        client_name_use   = client_name
        numero_titulo_cliente = _nosso_numero_seq(receivable.nosso_numero or str(receivable.id), convenio)
        
        if endereco_obj:
            rua_num = f"{endereco_obj.endereco}, {endereco_obj.numero}"
            if endereco_obj.complemento:
                rua_num = f"{rua_num} - {endereco_obj.complemento}"
            endereco_str = rua_num[:60].strip()
            
            cep_digits = ''.join(filter(str.isdigit, endereco_obj.cep or ''))
            if not cep_digits or len(cep_digits) != 8:
                raise ValueError('O CEP do cliente deve ter exatamente 8 dígitos. Verifique o endereço no cadastro do cliente.')
            cep_int = int(cep_digits)
            
            cidade_str = (endereco_obj.municipio or '')[:30].strip()
            bairro_str = (endereco_obj.bairro or '')[:30].strip()
            uf_str = (endereco_obj.uf or '')[:2].strip().upper()
            
            if not cidade_str or not bairro_str or not uf_str:
                raise ValueError('Cadastro de endereço do cliente incompleto (Cidade, Bairro e UF são obrigatórios).')
        else:
            raise ValueError('Endereço do cliente não cadastrado. Por favor, cadastre um endereço principal antes de registrar o boleto.')

    digits_doc = _strip_doc(client_doc_use)
    tipo_inscricao = 2 if len(digits_doc) > 11 else 1

    payload = {
        'numeroConvenio': convenio_int,
        'numeroCarteira': carteira,
        'numeroVariacaoCarteira': carteira_variacao,
        'codigoModalidade': 1,
        'numeroAgenciaCliente': agencia_cedente,
        'numeroContaCliente': conta_cedente,
        'digitoVerificadorConta': dv_conta_cedente,
        'dataEmissao': _fmt_date(receivable.issue_date),
        'dataVencimento': _fmt_date(receivable.due_date),
        'valorOriginal': float(round(receivable.amount, 2)),
        'codigoTipoTitulo': 2,
        'indicadorPermissaoRecebimentoParcial': 'N',
        'numeroTituloEmitente': str(receivable.id)[:15],
        'numeroTituloCliente': numero_titulo_cliente,
        'indicadorPix': 'S' if usar_pix else 'N',
        'pagador': {
            'tipoInscricao': tipo_inscricao,
            'numeroInscricao': int(digits_doc) if digits_doc.isdigit() else 0,
            'nome': client_name_use[:60].upper(),
            'endereco': endereco_str,
            'cep': cep_int,
            'cidade': cidade_str,
            'bairro': bairro_str,
            'uf': uf_str,
        },
    }

    if ba.multa_atraso_percentual:
        from datetime import timedelta
        multa_date = receivable.due_date + timedelta(days=1)
        payload['multa'] = {'tipo': 2, 'porcentagem': float(ba.multa_atraso_percentual), 'data': _fmt_date(multa_date)}
    if ba.juros_atraso_percentual:
        payload['jurosMora'] = {'tipo': 2, 'porcentagem': float(ba.juros_atraso_percentual)}

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'x-developer-application-key': app_key,
    }

    base_url = _API_BASE[sandbox]
    url = f'{base_url}/cobrancas/v2/boletos'

    with _make_http_client(sandbox) as client:
        resp = client.post(url, json=payload, headers=headers)
        if resp.status_code == 201:
            data = resp.json()
            return {
                'numero': str(data.get('numero', '')),
                'codigoLinhaDigitavel': data.get('codigoLinhaDigitavel', ''),
                'textoUrl': data.get('textoUrl', ''),
                'qrCode': data.get('qrCode') or {},
            }
        else:
            logger.error(f'BB Registro erro {resp.status_code}: {resp.text}')
            raise ValueError(f'Erro no registro BB: {resp.text}')

def solicitar_baixa(bank_account: BankAccount, bb_numero: str) -> bool:
    ba = bank_account
    sandbox = bool(ba.bb_sandbox)
    client_id = ba.bb_client_id
    client_secret = ba.bb_client_secret
    app_key = (ba.bb_app_key or '').strip()

    from app.core.security import decrypt_sensitive_data
    try:
        client_secret_dec = decrypt_sensitive_data(client_secret)
    except:
        client_secret_dec = client_secret

    token = get_access_token(ba.id, client_id, client_secret_dec, app_key, sandbox)
    base_url = _API_BASE[sandbox]
    url = f'{base_url}/cobrancas/v2/boletos/{bb_numero}/baixar'

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'x-developer-application-key': app_key,
    }

    with _make_http_client(sandbox) as client:
        resp = client.post(url, json={'numeroConvenio': int(ba.convenio or 0)}, headers=headers)
        return resp.status_code in [200, 204]
