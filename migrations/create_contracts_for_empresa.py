"""
Create monthly contracts for all clients of a given company (empresa).

Behavior:
 - Queries all active clients linked to the given empresa_id (from empresa_clientes)
 - For each client, generates a contract with:
     * servico_id (default 315)
     * random start date in June 2025
     * 12-month duration (d_contrato_fim = start + 1 year - 1 day)
     * periodicidade = 'MENSAL'
     * dia_emissao randomly chosen from [5,10,15,20,25]
     * quantidade = 1
     * valor_unitario = 99.90
     * valor_total = quantidade * valor_unitario
     * auto_emit = 1, is_active = 1
     * numero_contrato set to the DB-generated id after insert

Usage:
  python migrations/create_contracts_for_empresa.py --empresa 34 [--servico-id 315] [--dry-run] [--host ...]

This script writes a CSV report in the migrations folder describing the actions taken (or would take in dry-run).
"""

import argparse
import csv
import os
import random
from datetime import datetime, date, timedelta
from decimal import Decimal
import pymysql


def connect(host, port, user, password, db):
    return pymysql.connect(host=host, port=port, user=user, password=password, db=db, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


def make_start_date_in_june_2025():
    day = random.randint(1, 30)  # June has 30 days
    return date(2025, 6, day)


def end_date_for_12_months(start_date: date):
    # end = start + 1 year - 1 day
    try:
        end = start_date.replace(year=start_date.year + 1) - timedelta(days=1)
    except ValueError:
        # Feb 29 corner (not relevant for June) but keep safe
        end = start_date + timedelta(days=365) - timedelta(days=1)
    return end


def cliente_ids_for_empresa(conn, empresa_id):
    with conn.cursor() as cur:
        cur.execute('SELECT DISTINCT cliente_id FROM empresa_clientes WHERE empresa_id=%s AND is_active=1', (empresa_id,))
        rows = cur.fetchall()
        return [r['cliente_id'] for r in rows]


def servico_exists(conn, servico_id):
    with conn.cursor() as cur:
        cur.execute('SELECT id FROM servicos WHERE id=%s', (servico_id,))
        return cur.fetchone() is not None


def cliente_has_contract(conn, empresa_id, cliente_id, servico_id):
    with conn.cursor() as cur:
        cur.execute('SELECT id FROM servicos_contratados WHERE empresa_id=%s AND cliente_id=%s AND servico_id=%s LIMIT 1', (empresa_id, cliente_id, servico_id))
        return cur.fetchone() is not None


def insert_contract(conn, empresa_id, cliente_id, servico_id, d_ini, d_fim, periodicidade, dia_emissao, quantidade, valor_unitario, auto_emit, is_active, created_by):
    sql = ('INSERT INTO servicos_contratados (empresa_id, cliente_id, servico_id, numero_contrato, d_contrato_ini, d_contrato_fim, periodicidade, dia_emissao, quantidade, valor_unitario, valor_total, auto_emit, is_active, created_by_user_id, created_at) '
           'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)')
    valor_total = (Decimal(valor_unitario) * Decimal(quantidade)).quantize(Decimal('0.01'))
    now = datetime.now()
    with conn.cursor() as cur:
        # leave numero_contrato null initially; we'll update it to the inserted id
        cur.execute(sql, (empresa_id, cliente_id, servico_id, None, d_ini, d_fim, periodicidade, dia_emissao, quantidade, float(valor_unitario), float(valor_total), int(auto_emit), int(is_active), created_by, now))
        return cur.lastrowid


def update_numero_contrato(conn, inserted_id, numero):
    with conn.cursor() as cur:
        cur.execute('UPDATE servicos_contratados SET numero_contrato=%s WHERE id=%s', (str(numero), inserted_id))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=3306)
    parser.add_argument('--user', default='occ')
    parser.add_argument('--password', default='Altavista740')
    parser.add_argument('--empresa', type=int, required=True, help='empresa_id to create contracts for')
    parser.add_argument('--servico-id', type=int, default=315, help='servico_id to assign to contracts')
    parser.add_argument('--created-by', type=int, default=None, help='created_by_user_id to set on contracts')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--skip-existing', action='store_true', help='skip clientes that already have a contract for this servico_id')
    args = parser.parse_args()

    dst = connect(args.host, args.port, args.user, args.password, 'nfcom')

    report = []

    try:
        if not servico_exists(dst, args.servico_id):
            print(f'Servico id {args.servico_id} not found in servicos table. Aborting.')
            return

        clientes = cliente_ids_for_empresa(dst, args.empresa)
        print(f'Found {len(clientes)} clientes associated to empresa {args.empresa} (active only).')

        for cliente_id in clientes:
            # skip if exist
            if args.skip_existing and cliente_has_contract(dst, args.empresa, cliente_id, args.servico_id):
                report.append({'cliente_id': cliente_id, 'action': 'skipped_existing_contract'})
                continue

            d_ini = make_start_date_in_june_2025()
            d_fim = end_date_for_12_months(d_ini)
            periodicidade = 'MENSAL'
            dia_emissao = random.choice([5, 10, 15, 20, 25])
            quantidade = 1
            valor_unitario = Decimal('99.90')
            auto_emit = 1
            is_active = 1

            if args.dry_run:
                report.append({'cliente_id': cliente_id, 'action': 'would_create_contract', 'servico_id': args.servico_id, 'd_contrato_ini': d_ini.isoformat(), 'd_contrato_fim': d_fim.isoformat(), 'dia_emissao': dia_emissao, 'quantidade': quantidade, 'valor_unitario': str(valor_unitario)})
            else:
                try:
                    inserted_id = insert_contract(dst, args.empresa, cliente_id, args.servico_id, d_ini, d_fim, periodicidade, dia_emissao, quantidade, valor_unitario, auto_emit, is_active, args.created_by)
                    # set numero_contrato equal to DB id
                    update_numero_contrato(dst, inserted_id, inserted_id)
                    dst.commit()
                    report.append({'cliente_id': cliente_id, 'action': 'created_contract', 'servico_contratado_id': inserted_id, 'numero_contrato': str(inserted_id)})
                except Exception as e:
                    dst.rollback()
                    report.append({'cliente_id': cliente_id, 'action': 'error', 'error': str(e)})

        # write report CSV
        report_dir = os.path.dirname(os.path.abspath(__file__))
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        rf = os.path.join(report_dir, f'create_contracts_for_empresa_{args.empresa}_{ts}.csv')
        if report:
            with open(rf, 'w', newline='', encoding='utf-8') as f:
                keys = sorted({k for d in report for k in d})
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for r in report:
                    writer.writerow(r)
            print('Report written to', rf)

    finally:
        dst.close()


if __name__ == '__main__':
    main()
