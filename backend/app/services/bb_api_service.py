# -*- coding: utf-8 -*-
import logging
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional, List, Dict, Any

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

SANDBOX_PAGADOR_CPF = '12345678909'
SANDBOX_PAGADOR_NOME = 'CLIENTE TESTE BB HOMOLOGACAO'

def _make_http_client(sandbox: bool, company=None) -> httpx.Client:
    # Por enquanto, simplificado sem mTLS (certificado digital)
    # TODO: Implementar mTLS para produção se necessário
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
    cached = _token_cache.get(bank_account_id)
    if cached:
        token, expires_at = cached
        if now < expires_at - 60:
            return token

    url = _OAUTH_URL[sandbox]
    try:
        with _make_http_client(sandbox, company) as client:
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Developer-Application-Key': app_key
            }
            resp = client.post(
                url,
                data={'grant_type': 'client_credentials'},
                auth=(client_id, client_secret),
                headers=headers,
            )
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        error_body = exc.response.text
        logger.error(f'BB OAuth erro HTTP {exc.response.status_code}: {error_body}')
        raise ValueError(f'Falha na autenticação BB ({exc.response.status_code}): {error_body}')
    except Exception as exc:
        logger.error(f'BB OAuth erro: {str(exc)}')
        raise ValueError(f'Falha na autenticação BB: {str(exc)}')

    data = resp.json()
    token = data.get('access_token', '')
    expires_in = int(data.get('expires_in', 600))
    _token_cache[bank_account_id] = (token, now + expires_in)
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
    app_key = ba.bb_app_key

    if not client_id or not client_secret or not app_key:
        raise ValueError('Credenciais da API BB não configuradas nesta conta bancária.')

    # Em brazcom_isp, o bb_client_secret pode estar criptografado
    from app.core.security import decrypt_sensitive_data
    try:
        client_secret_dec = decrypt_sensitive_data(client_secret)
    except:
        client_secret_dec = client_secret

    token = get_access_token(ba.id, client_id, client_secret_dec, app_key, sandbox)

    # Dados do cliente
    cliente = db.query(Cliente).filter(Cliente.id == receivable.cliente_id).first()
    if not cliente:
        raise ValueError('Cliente não encontrado para este receivable.')

    # Em brazcom_isp, o endereço do cliente está no próprio modelo Cliente ou EmpresaClienteEndereco
    # Vamos tentar pegar os campos básicos do modelo Cliente
    client_name = cliente.nome_razao_social
    client_doc = cliente.cpf_cnpj
    
    # Endereço (tentar buscar EmpresaClienteEndereco se existir)
    from app.models.models import EmpresaCliente, EmpresaClienteEndereco
    empresa_cliente = db.query(EmpresaCliente).filter(
        EmpresaCliente.cliente_id == receivable.cliente_id,
        EmpresaCliente.empresa_id == receivable.empresa_id
    ).first()
    
    client_addr = {}
    if empresa_cliente:
        addr = db.query(EmpresaClienteEndereco).filter(
            EmpresaClienteEndereco.empresa_cliente_id == empresa_cliente.id,
            EmpresaClienteEndereco.is_principal == True
        ).first()
        if addr:
            client_addr = {
                'logradouro': addr.endereco,
                'numero': '', # Brazcom ISP parece não ter campo separado de número
                'bairro': addr.bairro,
                'cep': addr.cep,
                'cidade': addr.municipio,
                'uf': addr.uf
            }

    convenio = (ba.convenio or '').strip()
    carteira = int(ba.carteira or 17)
    carteira_variacao = int(ba.carteira_variacao or 35)

    if sandbox:
        convenio_int = SANDBOX_CEDENTE['numeroConvenio']
        carteira = SANDBOX_CEDENTE['numeroCarteira']
        carteira_variacao = SANDBOX_CEDENTE['numeroVariacaoCarteira']
        agencia_cedente = SANDBOX_CEDENTE['numeroAgenciaCliente']
        conta_cedente = SANDBOX_CEDENTE['numeroContaCliente']
        dv_conta_cedente = SANDBOX_CEDENTE['digitoVerificadorConta']
        client_doc_use = SANDBOX_PAGADOR_CPF
        client_name_use = SANDBOX_PAGADOR_NOME
        
        seq_ts = str(int(time.time()))[-10:].zfill(10)
        conv7 = str(SANDBOX_CEDENTE['numeroConvenio']).zfill(7)
        numero_titulo_cliente = '000' + conv7 + seq_ts
    else:
        if not convenio:
            raise ValueError('Convênio BB não configurado.')
        convenio_int = int(convenio)
        agencia_cedente = int(''.join(filter(str.isdigit, ba.agencia or '')) or 0)
        conta_cedente = int(''.join(filter(str.isdigit, ba.conta or '')) or 0)
        dv_conta_cedente = (ba.conta_dv or '').strip()
        client_doc_use = client_doc
        client_name_use = client_name
        numero_titulo_cliente = _nosso_numero_seq(str(receivable.nosso_numero or receivable.id), str(convenio_int))

    digits_doc = _strip_doc(client_doc_use)
    tipo_inscricao = 2 if len(digits_doc) > 11 else 1

    cep = _strip_doc(client_addr.get('cep', ''))[:8].zfill(8)
    
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
        'codigoTipoTitulo': 2, # DM
        'indicadorPermissaoRecebimentoParcial': 'N',
        'numeroTituloEmitente': str(receivable.id)[:15],
        'numeroTituloCliente': numero_titulo_cliente,
        'indicadorPix': 'S' if usar_pix else 'N',
        'pagador': {
            'tipoInscricao': tipo_inscricao,
            'numeroInscricao': int(digits_doc) if digits_doc.isdigit() else 0,
            'nome': (client_name_use or 'CLIENTE')[:60].upper(),
            'endereco': str(client_addr.get('logradouro', ''))[:60],
            'cep': cep,
            'cidade': str(client_addr.get('cidade', ''))[:20],
            'bairro': str(client_addr.get('bairro', ''))[:20],
            'uf': str(client_addr.get('uf', ''))[:2].upper(),
        },
    }

    # Juros/Multa
    if ba.multa_atraso_percentual:
        payload['multa'] = {
            'tipo': 2,
            'porcentagem': float(ba.multa_atraso_percentual),
            'data': _fmt_date(receivable.due_date)
        }
    
    if ba.juros_atraso_percentual:
        payload['jurosMora'] = {
            'tipo': 2, # Taxa mensal
            'porcentagem': float(ba.juros_atraso_percentual)
        }

    base_url = _API_BASE[sandbox]
    url = f'{base_url}/cobrancas/v2/boletos'

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'x-developer-application-key': app_key,
    }
    
    with _make_http_client(sandbox) as client:
        resp = client.post(url, json=payload, headers=headers)
        
    if resp.status_code != 201:
        logger.error(f'BB registrar_boleto erro: {resp.text}')
        raise ValueError(f'Erro BB {resp.status_code}: {resp.text}')

    return resp.json()

def solicitar_baixa(
    bank_account: BankAccount,
    bb_numero: str
) -> bool:
    ba = bank_account
    sandbox = bool(ba.bb_sandbox)
    client_id = ba.bb_client_id
    client_secret = ba.bb_client_secret
    app_key = ba.bb_app_key

    from app.core.security import decrypt_sensitive_data
    try:
        client_secret_dec = decrypt_sensitive_data(client_secret)
    except:
        client_secret_dec = client_secret

    token = get_access_token(ba.id, client_id, client_secret_dec, app_key, sandbox)
    
    convenio = (ba.convenio or '').strip()
    if sandbox:
        convenio_int = SANDBOX_CEDENTE['numeroConvenio']
    else:
        convenio_int = int(convenio)

    base_url = _API_BASE[sandbox]
    url = f'{base_url}/cobrancas/v2/boletos/{bb_numero}/baixar'
    payload = {'numeroConvenio': convenio_int}

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'x-developer-application-key': app_key,
    }
    
    with _make_http_client(sandbox) as client:
        resp = client.post(url, json=payload, headers=headers)
        
    return resp.status_code in [200, 204]
