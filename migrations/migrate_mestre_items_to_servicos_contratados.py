"""
Migrate nf21-mestre-agenda + nf21-item-agenda -> nfcom.servicos_contratados
- Preserves id using item.id (nf21-item-agenda.id)
- Validates empresa_id, cliente_id, servico_id exist in destination
- Calculates valor_total = quantidade * valor_unitario
- Writes a CSV report with skipped rows and reasons

Usage:
    python migrations/migrate_mestre_items_to_servicos_contratados.py --host localhost --user occ --password Altavista740
"""
import argparse
import pymysql
import csv
import os
from datetime import datetime


def connect(host, port, user, password, db):
    return pymysql.connect(host=host, port=port, user=user, password=password, db=db, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


def fetch_joined(conn):
    sql = ("SELECT m.id as mestre_id, m.id_empresa, m.modelo, m.serie, m.id_cliente, m.dia as dia_emissao, m.data_proxima_emissao, m.observacao, "
           "i.id as item_id, i.id_mestre, i.id_servico, i.valor, i.bc_icms, i.isentos, i.outros, i.aliquota_icms, i.quantidade_faturada "
           "FROM `nf21-mestre-agenda` m JOIN `nf21-item-agenda` i ON m.id = i.id_mestre ORDER BY i.id")
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def empresa_exists(conn, empresa_id):
    with conn.cursor() as cur:
        cur.execute('SELECT 1 FROM empresas WHERE id=%s', (empresa_id,))
        return cur.fetchone() is not None


def cliente_exists(conn, cliente_id):
    with conn.cursor() as cur:
        cur.execute('SELECT 1 FROM clientes WHERE id=%s', (cliente_id,))
        return cur.fetchone() is not None


def servico_exists(conn, servico_id):
    with conn.cursor() as cur:
        cur.execute('SELECT 1 FROM servicos WHERE id=%s', (servico_id,))
        return cur.fetchone() is not None


def id_exists(conn, id_):
    with conn.cursor() as cur:
        cur.execute('SELECT 1 FROM servicos_contratados WHERE id=%s', (id_,))
        return cur.fetchone() is not None


def insert_dst(conn, row):
    cols = ['id','empresa_id','cliente_id','servico_id','numero_contrato','d_contrato_ini','d_contrato_fim','periodicidade','dia_emissao','quantidade','valor_unitario','valor_total','auto_emit','is_active','created_by_user_id','created_at','vencimento']
    placeholders = ','.join(['%s'] * len(cols))
    sql = f"INSERT INTO servicos_contratados ({','.join(cols)}) VALUES ({placeholders})"
    values = [
        row['item_id'],
        row['id_empresa'],
        row['id_cliente'],
        row['id_servico'],
        (f"{row['modelo']}-{row['serie']}" if row.get('modelo') and row.get('serie') else None),
        None,
        None,
        'MENSAL',
        row.get('dia_emissao') or None,
        row.get('quantidade_faturada') or 1,
        row.get('valor') or 0.0,
        (row.get('quantidade_faturada') or 1) * (row.get('valor') or 0.0),
        1,
        1,
        None,
        datetime.now(),
        None,
    ]
    with conn.cursor() as cur:
        cur.execute(sql, values)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=3306)
    parser.add_argument('--user', default='occ')
    parser.add_argument('--password', default='Altavista740')
    parser.add_argument('--no-report', action='store_true')
    args = parser.parse_args()

    src = connect(args.host, args.port, args.user, args.password, 'nf21')
    dst = connect(args.host, args.port, args.user, args.password, 'nfcom')

    report = []
    try:
        rows = fetch_joined(src)
        print(f'Found {len(rows)} agenda items to migrate')
        if not rows:
            return

        dst.begin()
        with dst.cursor() as cur:
            cur.execute('SET FOREIGN_KEY_CHECKS=0')

        inserted = 0
        skipped = 0
        for r in rows:
            rid = r.get('item_id')
            eid = r.get('id_empresa')
            cid = r.get('id_cliente')
            sid = r.get('id_servico')

            if not empresa_exists(dst, eid):
                skipped += 1
                report.append({'item_id': rid, 'reason': 'empresa_missing', 'id_empresa': eid})
                continue
            if not cliente_exists(dst, cid):
                skipped += 1
                report.append({'item_id': rid, 'reason': 'cliente_missing', 'id_cliente': cid})
                continue
            if not servico_exists(dst, sid):
                skipped += 1
                report.append({'item_id': rid, 'reason': 'servico_missing', 'id_servico': sid})
                continue
            if id_exists(dst, rid):
                skipped += 1
                report.append({'item_id': rid, 'reason': 'id_exists'})
                continue
            try:
                insert_dst(dst, r)
                inserted += 1
            except Exception as e:
                skipped += 1
                report.append({'item_id': rid, 'reason': 'insert_error', 'error': str(e)})

        with dst.cursor() as cur:
            cur.execute('SELECT COALESCE(MAX(id),0) as m FROM servicos_contratados')
            m = cur.fetchone().get('m')
            nextv = m + 1
            cur.execute(f'ALTER TABLE servicos_contratados AUTO_INCREMENT = {nextv}')
            cur.execute('SET FOREIGN_KEY_CHECKS=1')
        dst.commit()

        print(f'Inserted: {inserted}, Skipped: {skipped}, Report items: {len(report)}')

        if not args.no_report:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_dir = os.path.dirname(os.path.abspath(__file__))
            report_file = os.path.join(report_dir, f'migrate_mestre_items_report_{ts}.csv')
            with open(report_file, 'w', newline='', encoding='utf-8') as f:
                keys = sorted({k for d in report for k in d}) if report else ['item_id','reason']
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for rr in report:
                    writer.writerow(rr)
            print('Report written to', report_file)

    finally:
        src.close()
        dst.close()

if __name__ == '__main__':
    main()
