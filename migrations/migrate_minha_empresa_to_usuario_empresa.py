"""
Migrate nf21.minha_empresa -> nfcom.usuario_empresa
- Maps id_user -> usuario_id
- Maps id_empresa -> empresa_id
- Sets is_admin = 0 (no explicit mapping in source)
- Skips rows where user or empresa missing in destination
- Skips rows where pair (usuario_id, empresa_id) already exists
- Writes a CSV report with skipped rows and reason

Usage:
    python migrations/migrate_minha_empresa_to_usuario_empresa.py --host localhost --user occ --password Altavista740
"""
import argparse
import pymysql
import csv
import os
from datetime import datetime


def connect(host, port, user, password, db):
    return pymysql.connect(host=host, port=port, user=user, password=password, db=db, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


def fetch_src(conn):
    cols = ['id','id_user','id_empresa','responsavel','cargo','ativo','validade','email_server','email_username','email_password','email_port','email_tls']
    sql = 'SELECT ' + ','.join(cols) + ' FROM minha_empresa ORDER BY id'
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def user_exists(conn, uid):
    with conn.cursor() as cur:
        cur.execute('SELECT 1 FROM users WHERE id=%s', (uid,))
        return cur.fetchone() is not None


def empresa_exists(conn, eid):
    with conn.cursor() as cur:
        cur.execute('SELECT 1 FROM empresas WHERE id=%s', (eid,))
        return cur.fetchone() is not None


def pair_exists(conn, uid, eid):
    with conn.cursor() as cur:
        cur.execute('SELECT 1 FROM usuario_empresa WHERE usuario_id=%s AND empresa_id=%s', (uid, eid))
        return cur.fetchone() is not None


def insert_dst(conn, uid, eid):
    sql = 'INSERT INTO usuario_empresa (usuario_id, empresa_id, is_admin) VALUES (%s,%s,%s)'
    with conn.cursor() as cur:
        cur.execute(sql, (uid, eid, 0))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=3306)
    parser.add_argument('--user', default='occ')
    parser.add_argument('--password', default='Altavista740')
    args = parser.parse_args()

    src = connect(args.host, args.port, args.user, args.password, 'nf21')
    dst = connect(args.host, args.port, args.user, args.password, 'nfcom')

    report = []
    try:
        rows = fetch_src(src)
        print(f'Found {len(rows)} rows in nf21.minha_empresa')
        if not rows:
            return

        dst.begin()
        with dst.cursor() as cur:
            cur.execute('SET FOREIGN_KEY_CHECKS=0')

        inserted = 0
        skipped = 0
        for r in rows:
            uid = r.get('id_user')
            eid = r.get('id_empresa')
            rid = r.get('id')
            if not user_exists(dst, uid):
                skipped += 1
                report.append({'source_id': rid, 'reason': 'user_missing', 'id_user': uid, 'id_empresa': eid})
                continue
            if not empresa_exists(dst, eid):
                skipped += 1
                report.append({'source_id': rid, 'reason': 'empresa_missing', 'id_user': uid, 'id_empresa': eid})
                continue
            if pair_exists(dst, uid, eid):
                skipped += 1
                report.append({'source_id': rid, 'reason': 'pair_exists', 'id_user': uid, 'id_empresa': eid})
                continue
            try:
                insert_dst(dst, uid, eid)
                inserted += 1
            except Exception as e:
                skipped += 1
                report.append({'source_id': rid, 'reason': 'insert_error', 'error': str(e), 'id_user': uid, 'id_empresa': eid})

        with dst.cursor() as cur:
            cur.execute('SET FOREIGN_KEY_CHECKS=1')
        dst.commit()

        print(f'Inserted: {inserted}, Skipped: {skipped}, Report items: {len(report)}')

        if report:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_dir = os.path.dirname(os.path.abspath(__file__))
            rep_file = os.path.join(report_dir, f'migrate_minha_empresa_report_{ts}.csv')
            with open(rep_file, 'w', newline='', encoding='utf-8') as f:
                keys = sorted({k for d in report for k in d})
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for r in report:
                    writer.writerow(r)
            print('Report written to', rep_file)

    finally:
        src.close()
        dst.close()

if __name__ == '__main__':
    main()
