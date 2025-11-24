"""
Migrate nf21.meus_clientes -> nfcom.empresa_cliente_enderecos

Maps address fields from meus_clientes to empresa_cliente_enderecos. For each meus_clientes row:
 - resolve minha_empresa -> id_empresa
 - find or create empresa_clientes (empresa_id, cliente_id)
 - insert endereco record linked to empresa_clientes.id

Usage:
    python migrations/migrate_meus_clientes_to_empresa_cliente_enderecos.py --host localhost --user occ --password Altavista740 [--dry-run]
"""
import argparse
import pymysql
import csv
import os
from datetime import datetime


def connect(host, port, user, password, db):
    return pymysql.connect(host=host, port=port, user=user, password=password, db=db, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


def fetch_meus_clientes(src_conn):
    cols = ['id','id_minha_empresa','id_cliente','tipo_cliente','status','cep','endereco','numero','complemento','bairro','cidade','uf','ibge']
    with src_conn.cursor() as cur:
        cur.execute('SELECT ' + ','.join(cols) + ' FROM meus_clientes ORDER BY id')
        return cur.fetchall()


def get_minha_empresa(src_conn, id_minha_empresa):
    with src_conn.cursor() as cur:
        cur.execute('SELECT id, id_empresa, id_user FROM minha_empresa WHERE id=%s', (id_minha_empresa,))
        return cur.fetchone()


def find_empresa_cliente(dst_conn, empresa_id, cliente_id):
    with dst_conn.cursor() as cur:
        cur.execute('SELECT id FROM empresa_clientes WHERE empresa_id=%s AND cliente_id=%s', (empresa_id, cliente_id))
        r = cur.fetchone()
        return r.get('id') if r else None


def create_empresa_cliente(dst_conn, empresa_id, cliente_id, created_by_user_id=None):
    sql = ('INSERT INTO empresa_clientes (empresa_id, cliente_id, created_by_user_id, is_active, created_at) VALUES (%s,%s,%s,%s,%s)')
    with dst_conn.cursor() as cur:
        cur.execute(sql, (empresa_id, cliente_id, created_by_user_id, 1, datetime.now()))
        return cur.lastrowid


def insert_endereco(dst_conn, empresa_cliente_id, row):
    sql = ('INSERT INTO empresa_cliente_enderecos (empresa_cliente_id, descricao, endereco, numero, complemento, bairro, municipio, uf, cep, codigo_ibge, is_principal, created_at) '
           'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)')
    descricao = None
    endereco = row.get('endereco') or ''
    numero = row.get('numero') or 'SN'
    complemento = row.get('complemento')
    bairro = row.get('bairro') or ''
    municipio = row.get('cidade') or ''
    uf = row.get('uf') or ''
    cep = row.get('cep') or ''
    codigo_ibge = row.get('ibge') or '0000000'
    is_principal = 1
    values = [empresa_cliente_id, descricao, endereco, numero, complemento, bairro, municipio, uf, cep, codigo_ibge, is_principal, datetime.now()]
    with dst_conn.cursor() as cur:
        cur.execute(sql, values)
        return cur.lastrowid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=3306)
    parser.add_argument('--user', default='occ')
    parser.add_argument('--password', default='Altavista740')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    src = connect(args.host, args.port, args.user, args.password, 'nf21')
    dst = connect(args.host, args.port, args.user, args.password, 'nfcom')

    report = []
    inserted = 0
    skipped = 0

    try:
        meus = fetch_meus_clientes(src)
        print(f'Found {len(meus)} meus_clientes rows in nf21')
        if not meus:
            return

        if not args.dry_run:
            dst.begin()
            with dst.cursor() as cur:
                cur.execute('SET FOREIGN_KEY_CHECKS=0')

        for m in meus:
            mc_id = m.get('id')
            id_minha_empresa = m.get('id_minha_empresa')
            cliente_id = m.get('id_cliente')

            minha = get_minha_empresa(src, id_minha_empresa)
            if not minha:
                skipped += 1
                report.append({'meus_id': mc_id, 'reason': 'minha_empresa_missing', 'id_minha_empresa': id_minha_empresa})
                continue
            empresa_id = minha.get('id_empresa')
            created_by_user_id = minha.get('id_user')

            # ensure empresa exists in dst
            with dst.cursor() as cur:
                cur.execute('SELECT 1 FROM empresas WHERE id=%s', (empresa_id,))
                if cur.fetchone() is None:
                    skipped += 1
                    report.append({'meus_id': mc_id, 'reason': 'empresa_missing', 'empresa_id': empresa_id})
                    continue

            # ensure cliente exists in dst
            with dst.cursor() as cur:
                cur.execute('SELECT 1 FROM clientes WHERE id=%s', (cliente_id,))
                if cur.fetchone() is None:
                    skipped += 1
                    report.append({'meus_id': mc_id, 'reason': 'cliente_missing', 'cliente_id': cliente_id})
                    continue

            # find or create empresa_cliente
            empresa_cliente_id = find_empresa_cliente(dst, empresa_id, cliente_id)
            if not empresa_cliente_id:
                if args.dry_run:
                    # report what would be created
                    report.append({'meus_id': mc_id, 'action': 'would_create_empresa_cliente', 'empresa_id': empresa_id, 'cliente_id': cliente_id})
                    empresa_cliente_id = None
                else:
                    try:
                        empresa_cliente_id = create_empresa_cliente(dst, empresa_id, cliente_id, created_by_user_id)
                    except Exception as e:
                        skipped += 1
                        report.append({'meus_id': mc_id, 'reason': 'create_empresa_cliente_error', 'error': str(e)})
                        continue

            # insert endereco
            try:
                if args.dry_run:
                    report.append({'meus_id': mc_id, 'action': 'would_insert_endereco', 'empresa_cliente_id': empresa_cliente_id or 'will_create'})
                else:
                    inserted_id = insert_endereco(dst, empresa_cliente_id, m)
                    report.append({'meus_id': mc_id, 'action': 'inserted_endereco', 'empresa_cliente_endereco_id': inserted_id, 'empresa_cliente_id': empresa_cliente_id})
                    inserted += 1
            except Exception as e:
                skipped += 1
                report.append({'meus_id': mc_id, 'reason': 'insert_endereco_error', 'error': str(e)})

        if not args.dry_run:
            with dst.cursor() as cur:
                cur.execute('SET FOREIGN_KEY_CHECKS=1')
            dst.commit()

        print(f'Enderecos inserted: {inserted}, skipped: {skipped}')

        # write report CSV
        report_dir = os.path.dirname(os.path.abspath(__file__))
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        rf = os.path.join(report_dir, f'migrate_meus_clientes_enderecos_report_{ts}.csv')
        if report:
            with open(rf, 'w', newline='', encoding='utf-8') as f:
                keys = sorted({k for d in report for k in d})
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for r in report:
                    writer.writerow(r)
            print('Report written to', rf)

    finally:
        src.close()
        dst.close()


if __name__ == '__main__':
    main()
