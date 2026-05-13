from datetime import date, datetime, timedelta
from decimal import Decimal
import calendar
from typing import Optional
from sqlalchemy.orm import Session
import json
import logging
import secrets
import os

from app.models.models import ServicoContratado, Receivable, BankAccount, Empresa, Bank


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def prorated_amount_for_period(full_amount: float, start_date: date, billing_date: date) -> float:
    """Calcula o valor prorrateado para o mês de `billing_date` considerando `start_date`.

    Se o start_date estiver no mesmo mês de billing_date, calcula a proporção de dias ativos nesse mês.
    Caso contrário, retorna o `full_amount`.
    """
    if start_date.year == billing_date.year and start_date.month == billing_date.month:
        dim = days_in_month(billing_date.year, billing_date.month)
        # dias ativos: desde start_date até o final do mês (inclusive)
        active_days = dim - (start_date.day - 1)
        proportion = active_days / dim
        return round(full_amount * proportion, 2)
    else:
        return round(full_amount, 2)


def generate_receivable_from_contract(db: Session, contrato: ServicoContratado, target_date: date) -> Receivable:
    """Gera um objeto Receivable em memória (não comita) a partir de um contrato para `target_date`.

    - Respeita `d_contrato_ini` para prorrata quando necessário
    - Usa `valor_unitario * quantidade` como base
    - Respeita `taxa_instalacao` se for apropriado (isso pode ser ajustado posteriormente)
    """
    base = (contrato.valor_unitario or 0.0) * (contrato.quantidade or 1.0)
    # por enquanto não somamos taxa_instalacao automaticamente (configurável)
    start = contrato.d_contrato_ini
    amount = base
    if start:
        amount = prorated_amount_for_period(base, start, target_date)

    # Construir due_date: use `dia_vencimento` se presente, senão use mesmo dia do target_date
    if contrato.dia_vencimento:
        # proteger valores inválidos (>28/29/30/31) criando a data mais próxima
        day = min(contrato.dia_vencimento, days_in_month(target_date.year, target_date.month))
        due_date = datetime(target_date.year, target_date.month, day)
    else:
        # usar o último dia do mês para evitar vencimentos inexistentes
        day = min(target_date.day, days_in_month(target_date.year, target_date.month))
        due_date = datetime(target_date.year, target_date.month, day)

    recv = Receivable(
        empresa_id=contrato.empresa_id,
        cliente_id=contrato.cliente_id,
        servico_contratado_id=contrato.id,
        issue_date=datetime.utcnow(),
        due_date=due_date,
        amount=amount,
        discount=0.0,
        interest_percent=0.0,
        fine_percent=0.0,  # Will be set from bank account below
        status='PENDING'
    )

    # Definir tipo baseado na modalidade do contrato
    if contrato.payment_method == 'MERCADO_PAGO':
        recv.tipo = 'MERCADO_PAGO'
        recv.payment_token = secrets.token_urlsafe(32)
        
        # Obter URL base do ambiente (localhost ou brazcom.com.br)
        base_url = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
            
        recv.payment_url = f"{base_url}/checkout?token={recv.payment_token}"
    else:
        recv.tipo = 'BOLETO'

    # Determinar qual conta bancária usar: preferir a do contrato, senão a default da empresa
    bank_account = None
    try:
        if getattr(contrato, "bank_account_id", None):
            bank_account = db.query(BankAccount).filter(BankAccount.id == contrato.bank_account_id).first()
        if not bank_account:
            empresa = db.query(Empresa).filter(Empresa.id == contrato.empresa_id).first()
            if empresa and getattr(empresa, "default_bank_account_id", None):
                bank_account = db.query(BankAccount).filter(BankAccount.id == empresa.default_bank_account_id).first()
    except Exception:
        logging.exception("Erro ao buscar conta bancária para geração de cobrança")

    if bank_account:
        # Aplicar configurações de cobrança da conta bancária
        recv.fine_percent = bank_account.multa_atraso_percentual or 0.0
        recv.interest_percent = bank_account.juros_atraso_percentual or 0.0
        
        # Popular referência à conta e snapshot (sem credenciais)
        recv.bank_account_id = bank_account.id
        try:
            # Se possível, atribuir enum Bank a coluna receivable.bank
            recv.bank = Bank(bank_account.bank)
        except Exception:
            # fallback: atribuir string (SQLAlchemy pode converter)
            recv.bank = bank_account.bank

        snapshot = {
            "id": bank_account.id,
            "bank": bank_account.bank,
            "codigo_banco": bank_account.codigo_banco,
            "agencia": bank_account.agencia,
            "agencia_dv": bank_account.agencia_dv,
            "conta": bank_account.conta,
            "conta_dv": bank_account.conta_dv,
            "titular": bank_account.titular,
            "cpf_cnpj_titular": bank_account.cpf_cnpj_titular,
            "carteira": bank_account.carteira,
            "convenio": bank_account.convenio,
            "is_default": bool(bank_account.is_default),
            "multa_atraso_percentual": bank_account.multa_atraso_percentual,
            "juros_atraso_percentual": bank_account.juros_atraso_percentual,
        }
        recv.bank_account_snapshot = json.dumps(snapshot, default=str)
    else:
        # Fallback: usar configurações do contrato se não houver conta bancária
        recv.fine_percent = contrato.multa_atraso_percentual or 0.0

    return recv


def create_and_persist_receivable(db: Session, recv: Receivable) -> Receivable:
    db.add(recv)
    db.flush()
    return recv


def should_generate_for_contract(contrato: ServicoContratado, target_date: date) -> bool:
    """Verifica se deve gerar cobrança para o contrato na data alvo, baseado na periodicidade e dia_emissao."""
    if not contrato.dia_emissao or not contrato.d_contrato_ini:
        return False

    # Verificar se o contrato já foi emitido recentemente (evitar duplicatas)
    if contrato.last_emission:
        # Para mensal, verificar se já foi emitido neste mês
        if contrato.periodicidade == 'MENSAL':
            if contrato.last_emission.year == target_date.year and contrato.last_emission.month == target_date.month:
                return False
        # Para outras periodicidades, verificar se já foi emitido no período atual
        # Simplificar: não gerar se last_emission for no mesmo mês
        if contrato.last_emission.year == target_date.year and contrato.last_emission.month == target_date.month:
            return False

    # Verificar dia de emissão
    if target_date.day != contrato.dia_emissao:
        return False

    # Verificar periodicidade baseada na data de início
    months_diff = (target_date.year - contrato.d_contrato_ini.year) * 12 + (target_date.month - contrato.d_contrato_ini.month)

    if contrato.periodicidade == 'MENSAL':
        return True  # Já verificou dia
    elif contrato.periodicidade == 'BIMESTRAL':
        return months_diff % 2 == 0
    elif contrato.periodicidade == 'TRIMESTRAL':
        return months_diff % 3 == 0
    elif contrato.periodicidade == 'SEMESTRAL':
        return months_diff % 6 == 0
    elif contrato.periodicidade == 'ANUAL':
        return months_diff % 12 == 0
    else:
        # Default: mensal
        return True


def generate_receivables_for_company(db: Session, empresa_id: int, target_date: date):
    """Gera receivables para contratos elegíveis de uma empresa para `target_date`.

    - Considera periodicidade e dia_emissao para determinar se deve gerar
    - Retorna a lista de objetos Receivable persistidos (sem commit automático)
    """
    contratos = db.query(ServicoContratado).filter(ServicoContratado.empresa_id == empresa_id, ServicoContratado.is_active == True).all()
    created = []
    for c in contratos:
        # pular contratos que ainda não começaram (d_contrato_ini no futuro)
        if c.d_contrato_ini and c.d_contrato_ini > target_date:
            continue
        # pular contratos que já terminaram
        if c.d_contrato_fim and c.d_contrato_fim < target_date:
            continue
        # verificar se deve gerar baseado na periodicidade
        if not should_generate_for_contract(c, target_date):
            continue
        # gerar
        recv = generate_receivable_from_contract(db, c, target_date)
        create_and_persist_receivable(db, recv)
        # atualizar last_emission
        c.last_emission = datetime.utcnow()
        created.append(recv)
    return created
def build_boleto_context(db: Session, recv: Receivable) -> dict:
    """Prepara o dicionário de contexto para o gerador de PDF."""
    from app.models.models import Cliente, Empresa, BankAccount
    cliente = db.query(Cliente).filter(Cliente.id == recv.cliente_id).first()
    empresa = db.query(Empresa).filter(Empresa.id == recv.empresa_id).first()
    
    # Pegar dados da conta bancária (preferir snapshot se existir)
    ba_data = {}
    if recv.bank_account_snapshot:
        try:
            ba_data = json.loads(recv.bank_account_snapshot)
        except:
            pass
    
    if not ba_data and recv.bank_account_id:
        ba = db.query(BankAccount).filter(BankAccount.id == recv.bank_account_id).first()
        if ba:
            ba_data = {
                "bank": ba.bank,
                "codigo_banco": ba.codigo_banco,
                "agencia": ba.agencia,
                "agencia_dv": ba.agencia_dv,
                "conta": ba.conta,
                "conta_dv": ba.conta_dv,
                "carteira": ba.carteira,
                "convenio": ba.convenio,
            }

    # Endereço do cliente
    from app.models.models import EmpresaCliente, EmpresaClienteEndereco
    emp_cli = db.query(EmpresaCliente).filter(
        EmpresaCliente.cliente_id == recv.cliente_id,
        EmpresaCliente.empresa_id == recv.empresa_id
    ).first()
    addr_str = ""
    mun_uf = ""
    cep = ""
    if emp_cli:
        addr = db.query(EmpresaClienteEndereco).filter(
            EmpresaClienteEndereco.empresa_cliente_id == emp_cli.id,
            EmpresaClienteEndereco.is_principal == True
        ).first()
        if addr:
            addr_str = f"{addr.endereco}, {addr.bairro}"
            mun_uf = f"{addr.municipio}/{addr.uf}"
            cep = addr.cep

    # Instruções formatadas estilo Agrobraz
    if recv.bank in ['BANCO DO BRASIL', 'BANCO_DO_BRASIL', '001']:
        banco_cod = '001-9'
        juros_dia = (recv.amount * (recv.interest_percent / 100)) / 30
        multa_val = recv.amount * (recv.fine_percent / 100)
        instrucoes = f"APÓS VENCIMENTO COBRAR JUROS DE R$ {juros_dia:,.2f} AO DIA.\n" \
                     f"COBRAR MULTA DE R$ {multa_val:,.2f}.\n" \
                     f"NÃO RECEBER APÓS 30 DIAS DO VENCIMENTO."
    elif recv.bank in ['SICREDI', '748']:
        banco_cod = '748-X'
        instrucoes = f"Após o vencimento cobrar multa de {recv.fine_percent}% e juros de {recv.interest_percent}% ao mês."
    else:
        banco_cod = ba_data.get('codigo_banco', '000-0')
        instrucoes = f"Após o vencimento cobrar multa de {recv.fine_percent}% e juros de {recv.interest_percent}% ao mês."

    # Se for BB, usar dados específicos se disponíveis e formatar como Agrobraz
    nosso_numero = recv.nosso_numero or recv.bb_boleto_numero or str(recv.id)
    convenio = ba_data.get('convenio', '')
    
    if (recv.bank == 'BANCO DO BRASIL' or recv.bank == 'BANCO_DO_BRASIL' or recv.bank == '001') and '/' not in nosso_numero:
        if convenio:
            nosso_numero = f"{convenio}/{nosso_numero.zfill(10)}"

    linha_digitavel = recv.linha_digitavel or ""
    barcode = recv.codigo_barras or ""
    
    # Se não tiver linha digitável mas for BB, podemos tentar calcular se tivermos os dados
    if not linha_digitavel and (recv.bank in ['BANCO DO BRASIL', 'BANCO_DO_BRASIL', '001']):
        from app.services.boleto_service import compute_fator_vencimento, compute_valor_str, compute_campo_livre, compute_barcode44, compute_linha_digitavel
        try:
            fator = compute_fator_vencimento(recv.due_date.date())
            valor = compute_valor_str(Decimal(str(recv.amount)))
            # No BB em homologação, o nosso número seq costuma ser o final do nosso_numero
            seq = nosso_numero.split('/')[-1] if '/' in nosso_numero else nosso_numero
            campo = compute_campo_livre('001', ba_data.get('agencia',''), ba_data.get('conta',''), convenio, ba_data.get('carteira','17'), seq)
            barcode = compute_barcode44('001', '9', fator, valor, campo)
            linha_digitavel = compute_linha_digitavel(barcode)
        except Exception as e:
            logging.error(f"Erro ao calcular linha digitável BB: {e}")

    agencia = f"{ba_data.get('agencia','')}-{ba_data.get('agencia_dv','')}" if ba_data.get('agencia_dv') else ba_data.get('agencia','')
    conta = f"{ba_data.get('conta','')}-{ba_data.get('conta_dv','')}" if ba_data.get('conta_dv') else ba_data.get('conta','')

    return {
        "id": recv.id,
        "pix_qrcode": recv.bb_pix_qrcode,
        "pix_txid": recv.bb_pix_txid,
        "numero_documento": str(recv.id),
        "banco_codigo": banco_cod,
        "cedente_nome": empresa.razao_social if empresa else "EMPRESA",
        "cedente_cnpj": empresa.cnpj if empresa else "",
        "agencia_conta": f"{agencia} / {conta}",
        "nosso_numero": nosso_numero,
        "data_vencimento": recv.due_date.strftime('%d/%m/%Y'),
        "data_emissao": recv.issue_date.strftime('%d/%m/%Y'),
        "valor": f"{recv.amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        "sacado_nome": cliente.nome_razao_social if cliente else "CLIENTE",
        "sacado_documento": cliente.cpf_cnpj if cliente else "",
        "sacado_endereco": addr_str,
        "sacado_municipio": mun_uf.split('/')[0] if '/' in mun_uf else mun_uf,
        "sacado_cep": cep,
        "sacado_uf": mun_uf.split('/')[-1] if '/' in mun_uf else "",
        "carteira": ba_data.get('carteira', '17'),
        "local_pagamento": "Pagável em qualquer banco até o vencimento",
        "instrucoes": instrucoes,
        "linha_digitavel": linha_digitavel,
        "barcode44": barcode
    }
