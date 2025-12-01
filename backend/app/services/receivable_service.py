from datetime import date, datetime, timedelta
import calendar
from typing import Optional
from sqlalchemy.orm import Session
import json
import logging

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


def generate_monthly_receivables_for_company(db: Session, empresa_id: int, target_date: date):
    """Gera receivables para todos os contratos ativos de uma empresa para `target_date`.

    - Retorna a lista de objetos Receivable persistidos (sem commit automático)
    """
    contratos = db.query(ServicoContratado).filter(ServicoContratado.empresa_id == empresa_id, ServicoContratado.is_active == True).all()
    created = []
    for c in contratos:
        # pular contratos que ainda não começaram (d_contrato_ini no futuro)
        if c.d_contrato_ini and c.d_contrato_ini > target_date:
            continue
        # gerar
        recv = generate_receivable_from_contract(db, c, target_date)
        create_and_persist_receivable(db, recv)
        created.append(recv)
    return created
