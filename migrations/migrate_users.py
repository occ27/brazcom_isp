"""
Safe Python migration script: copy users from nf21 -> nfcom preserving IDs when possible.
Creates a CSV report for conflicts.

Usage:
  python migrations/migrate_users.py --host localhost --user occ --password Altavista740

Options:
  --host
  --port
  --user
  --password
  --dry-run    : do not perform inserts, only report
  --overwrite  : overwrite destination rows when ID collision occurs

Notes:
- Requires PyMySQL: pip install pymysql
- This script preserves IDs when inserting. If an ID collision exists, default behavior is to skip and log conflict.
- Review conflicts CSV and decide manual resolution or re-run with --overwrite.
"""
import argparse
import csv
import sys
import os
from datetime import datetime

import pymysql

FIELDS = [
    'id', 'cpf', 'password', 'email', 'nome', 'data_nascimento', 'celular', 'image_file',
    'data_ultimo_login', 'data_cadastro', 'verify_account', 'id_ultima_novidade'
]


def connect(host, port, user, password, db):
    return pymysql.connect(host=host, port=port, user=user, password=password, db=db, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


def fetch_source_users(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT " + ",".join(FIELDS) + " FROM users ORDER BY id")
        return cur.fetchall()


def id_exists(conn, id_):
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE id=%s", (id_,))
        return cur.fetchone() is not None


def cpf_exists(conn, cpf):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE cpf=%s", (cpf,))
        return cur.fetchone()


def insert_user(conn, user):
    cols = ",".join(FIELDS)
    placeholders = ",".join(["%s"] * len(FIELDS))
    sql = f"INSERT INTO users ({cols}) VALUES ({placeholders})"
    values = [user.get(f) for f in FIELDS]
    with conn.cursor() as cur:
        cur.execute(sql, values)


def update_user(conn, user):
    set_clause = ", ".join([f"{f}=%s" for f in FIELDS if f != 'id'])
    sql = f"UPDATE users SET {set_clause} WHERE id=%s"
    values = [user.get(f) for f in FIELDS if f != 'id'] + [user.get('id')]
    with conn.cursor() as cur:
        cur.execute(sql, values)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=3306)
    parser.add_argument('--user', default='occ')
    parser.add_argument('--password', default='Altavista740')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite destination rows on ID collision')
    parser.add_argument('--no-report', action='store_true', help='Do not write conflicts CSV report (keep in-memory only)')
    args = parser.parse_args()

    print('Connecting to source (nf21) and destination (nfcom)')
    src_conn = connect(args.host, args.port, args.user, args.password, 'nf21')
    dst_conn = connect(args.host, args.port, args.user, args.password, 'nfcom')

    conflicts = []
    skipped = 0
    inserted = 0
    updated = 0
    planned_inserted = 0
    planned_updated = 0

    try:
        src_users = fetch_source_users(src_conn)
        print(f'Found {len(src_users)} users in source')

        # Begin transaction on destination
        if not args.dry_run:
            dst_conn.begin()
            # disable foreign key checks temporarily
            with dst_conn.cursor() as cur:
                cur.execute('SET FOREIGN_KEY_CHECKS=0')

        for u in src_users:
            uid = u.get('id')
            if id_exists(dst_conn, uid):
                # collision on primary key
                dst_row = None
                with dst_conn.cursor() as cur:
                    cur.execute('SELECT * FROM users WHERE id=%s', (uid,))
                    dst_row = cur.fetchone()

                # If same CPF or same content, we can skip
                if dst_row and dst_row.get('cpf') == u.get('cpf'):
                    # same user id and cpf -> consider updating missing fields if overwrite
                    if args.overwrite and not args.dry_run:
                        update_user(dst_conn, u)
                        updated += 1
                    else:
                        skipped += 1
                    conflicts.append({'id': uid, 'reason': 'id_exists_same_cpf', 'src_email': u.get('email'), 'dst_email': dst_row.get('email')})
                else:
                    # True conflict: same id but different cpf -> log
                    conflicts.append({'id': uid, 'reason': 'id_conflict_diff_cpf', 'src_cpf': u.get('cpf'), 'dst_cpf': dst_row.get('cpf') if dst_row else None, 'src_email': u.get('email'), 'dst_email': dst_row.get('email') if dst_row else None})
                    skipped += 1
            else:
                # OK to insert preserving ID
                planned_inserted += 1
                try:
                    if not args.dry_run:
                        insert_user(dst_conn, u)
                        inserted += 1
                except Exception as e:
                    conflicts.append({'id': uid, 'reason': 'insert_error', 'error': str(e)})
                    skipped += 1

        # reset auto_increment
        if not args.dry_run:
            with dst_conn.cursor() as cur:
                cur.execute('SELECT COALESCE(MAX(id), 0) as m FROM users')
                m = cur.fetchone().get('m')
                nextv = m + 1
                cur.execute(f'ALTER TABLE users AUTO_INCREMENT = {nextv}')
                cur.execute('SET FOREIGN_KEY_CHECKS=1')
            dst_conn.commit()

        # optionally write conflicts report (place file next to this script)
        if not args.no_report:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_name = f'migrate_users_conflicts_{ts}.csv'
            report_dir = os.path.dirname(os.path.abspath(__file__))
            report = os.path.join(report_dir, report_name)
            if conflicts:
                # ensure directory exists (should, but be defensive)
                os.makedirs(report_dir, exist_ok=True)
                with open(report, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=list({k for d in conflicts for k in d}))
                    writer.writeheader()
                    for r in conflicts:
                        writer.writerow(r)
                print(f'Conflicts logged to {report}')
            else:
                print('No conflicts detected')
        else:
            # If not writing a report, still summarize conflicts in the console
            if conflicts:
                print(f"Conflicts detected: {len(conflicts)} (report suppressed by --no-report).")
            else:
                print('No conflicts detected')

        print(f'Planned inserts: {planned_inserted}, Performed inserts: {inserted}, Performed updates: {updated}, Skipped: {skipped}')

    finally:
        src_conn.close()
        dst_conn.close()


if __name__ == '__main__':
    main()
