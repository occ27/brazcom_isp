#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reconcile_bb_payments.py
------------------------
Script de reconciliação de pagamentos do Banco do Brasil.

Consulta diretamente a API do BB para:
  1. Boletos com status REGISTERED (registrados pelo nosso sistema mas sem baixa via webhook)
  2. Boletos com status PENDING que vieram importados do sistema Altarede
     (têm nosso_numero preenchido mas não têm bb_boleto_numero)

Funciona como rede de segurança para quando o webhook falha ou não chega.

Uso:
    python scripts/reconcile_bb_payments.py
    python scripts/reconcile_bb_payments.py --company 6
    python scripts/reconcile_bb_payments.py --days 60   # boletos vencidos há no máximo 60 dias
    python scripts/reconcile_bb_payments.py --dry-run   # apenas exibe, não salva

Cron sugerido (rodar todo dia às 10:00 e 17:00):
    0 10,17 * * * /caminho/venv/bin/python /caminho/scripts/reconcile_bb_payments.py >> /var/log/reconcile_bb.log 2>&1
"""

import sys
import os
import argparse
import logging
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def run(company_id=None, days_back=60, dry_run=False):
    from app.core.database import SessionLocal
    from app.models.models import Receivable, BankAccount, Empresa
    from app.services import bb_api_service, isp_service

    session = SessionLocal()
    total_checked = 0
    total_updated = 0
    total_errors = 0

    try:
        cutoff_date = datetime.now() - timedelta(days=days_back)

        # Grupo 1: boletos registrados pelo nosso sistema (têm bb_boleto_numero)
        q1 = session.query(Receivable).filter(
            Receivable.status == 'REGISTERED',
            Receivable.bb_boleto_numero != None,
            Receivable.bb_boleto_numero != '',
            Receivable.due_date >= cutoff_date,
        )

        # Grupo 2: boletos importados do Altarede (PENDING + nosso_numero, sem bb_boleto_numero)
        q2 = session.query(Receivable).filter(
            Receivable.status == 'PENDING',
            Receivable.nosso_numero != None,
            Receivable.nosso_numero != '',
            Receivable.bb_boleto_numero == None,
            Receivable.due_date >= cutoff_date,
        )

        if company_id:
            q1 = q1.filter(Receivable.empresa_id == company_id)
            q2 = q2.filter(Receivable.empresa_id == company_id)

        receivables = q1.all() + q2.all()

        if not receivables:
            logger.info("Nenhum boleto BB pendente de reconciliação encontrado.")
            return

        logger.info(f"Encontrados {len(receivables)} boleto(s) BB para verificar ({len(q1.all())} REGISTERED + {len(q2.all())} PENDING/Altarede).")

        by_bank_account = {}
        for r in receivables:
            key = r.bank_account_id
            if key not in by_bank_account:
                by_bank_account[key] = []
            by_bank_account[key].append(r)

        for bank_account_id, recv_list in by_bank_account.items():
            bank_account = None

            if bank_account_id is not None:
                bank_account = session.query(BankAccount).filter_by(id=bank_account_id).first()

            # Fallback para boletos Altarede que não têm bank_account_id:
            # usa a conta bancária BB padrão da empresa do primeiro boleto da lista
            if bank_account is None:
                sample = recv_list[0]
                bank_account = session.query(BankAccount).filter(
                    BankAccount.empresa_id == sample.empresa_id,
                    BankAccount.bank.in_(['BANCO DO BRASIL', 'BB', 'BANCO_DO_BRASIL']),
                    BankAccount.bb_client_id != None,
                    BankAccount.is_active == True,
                ).first()
                if bank_account is None:
                    logger.warning(f"  {len(recv_list)} boleto(s) sem conta bancária BB configurada. Pulando.")
                    continue

            if not bank_account.bb_client_id:
                logger.warning(f"  Conta {bank_account.id} sem credenciais BB. Pulando.")
                continue

            empresa = session.query(Empresa).filter_by(id=bank_account.empresa_id).first()
            logger.info(f"\n[{empresa.nome_fantasia or empresa.razao_social}] Conta BB #{bank_account_id} — {len(recv_list)} boleto(s)")

            # Monta o número completo do BB para boletos do Altarede (nosso_numero curto)
            # Formato BB: '000' + convenio(7 dígitos) + sequência(10 dígitos)
            convenio_digits = ''.join(filter(str.isdigit, bank_account.convenio or ''))

            def get_bb_numero(r):
                """Retorna o número de 20 dígitos para consultar no BB."""
                if r.bb_boleto_numero:
                    return r.bb_boleto_numero
                # Altarede: expande nosso_numero curto para o formato completo
                seq = ''.join(filter(str.isdigit, r.nosso_numero or ''))
                return '000' + convenio_digits.zfill(7) + seq.zfill(10)

            for r in recv_list:
                total_checked += 1
                bb_numero = get_bb_numero(r)
                try:
                    dados = bb_api_service.consultar_boleto(bank_account, bb_numero)
                    if dados is None:
                        logger.warning(f"  [SKIP] Boleto {bb_numero} (ID={r.id}, nosso={r.nosso_numero}) — sem resposta da API BB")
                        continue

                    codigo_sit = str(dados.get('codigoEstadoTituloCobranca', '') or '').strip()
                    new_status = bb_api_service.situacao_para_status(codigo_sit) if codigo_sit else None

                    logger.info(
                        f"  Boleto {bb_numero} (ID={r.id}, nosso={r.nosso_numero}) | "
                        f"código={codigo_sit} -> {new_status} (atual={r.status})"
                    )

                    # Para boletos Altarede recém-descobertos como PAID, salva o bb_boleto_numero
                    if not r.bb_boleto_numero and new_status == 'PAID':
                        r.bb_boleto_numero = bb_numero

                    if new_status and new_status != r.status:
                        if dry_run:
                            logger.info(f"    [DRY-RUN] Atualizaria: {r.status} -> {new_status}")
                        else:
                            r.status = new_status

                            if new_status == 'PAID':
                                if not r.paid_at:
                                    r.paid_at = datetime.now()
                                valor_pago = dados.get('valorPagoSacado') or dados.get('valorPago')
                                if valor_pago is not None:
                                    try:
                                        r.paid_amount = float(valor_pago)
                                    except (ValueError, TypeError):
                                        pass
                                if r.servico_contratado_id:
                                    try:
                                        isp_service.process_unblock_if_needed(session, r.servico_contratado_id)
                                        logger.info(f"    Contrato #{r.servico_contratado_id} desbloqueado.")
                                    except Exception as e:
                                        logger.error(f"    Erro ao desbloquear contrato: {e}")

                            session.add(r)
                            total_updated += 1
                            logger.info(f"    -> Atualizado para {new_status}")
                    else:
                        logger.info(f"    -> Sem alteração.")

                except Exception as e:
                    total_errors += 1
                    logger.error(f"  [ERRO] Boleto {bb_numero} (ID={r.id}): {e}")

        if not dry_run and total_updated > 0:
            session.commit()
            logger.info(f"\nAlterações salvas com sucesso.")

    except Exception as e:
        session.rollback()
        logger.exception(f"Erro fatal na reconciliação: {e}")
    finally:
        session.close()

    print(f"\n{'='*60}")
    print(f"  RECONCILIAÇÃO BB — RESUMO")
    print(f"{'='*60}")
    print(f"  Boletos verificados : {total_checked}")
    print(f"  Boletos atualizados : {total_updated}{' (DRY-RUN, nada salvo)' if dry_run else ''}")
    print(f"  Erros               : {total_errors}")
    print(f"{'='*60}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Reconciliação de pagamentos BB')
    parser.add_argument('--company', type=int, default=None)
    parser.add_argument('--days', type=int, default=60)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    run(company_id=args.company, days_back=args.days, dry_run=args.dry_run)
