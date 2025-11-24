"""
Check DB counts for contracts created by the bulk script.

Usage:
  python migrations/check_created_contracts_db.py --empresa 34 --servico-id 315 --host <host> --port <port> --user <user> --password <pwd>

Prints total contracts for empresa/servico and number of rows where numero_contrato = id.
"""
import argparse
from datetime import datetime
import pymysql


def connect(host, port, user, password, db):
    return pymysql.connect(host=host, port=port, user=user, password=password, db=db, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=3306)
    parser.add_argument('--user', default='occ')
    parser.add_argument('--password', default='Altavista740')
    parser.add_argument('--empresa', type=int, required=True)
    parser.add_argument('--servico-id', type=int, required=True)
    args = parser.parse_args()

    conn = connect(args.host, args.port, args.user, args.password, 'nfcom')
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) as cnt FROM servicos_contratados WHERE empresa_id=%s AND servico_id=%s', (args.empresa, args.servico_id))
            tot = cur.fetchone().get('cnt')
            cur.execute('SELECT COUNT(*) as cnt FROM servicos_contratados WHERE empresa_id=%s AND servico_id=%s AND numero_contrato IS NOT NULL AND CAST(numero_contrato AS CHAR)=CAST(id AS CHAR)', (args.empresa, args.servico_id))
            match_num = cur.fetchone().get('cnt')
            print(f'empresa {args.empresa} / servico {args.servico_id} -> total contratos: {tot}, numero_contrato==id: {match_num}')
            # show some sample rows
            cur.execute('SELECT id, numero_contrato, cliente_id, d_contrato_ini FROM servicos_contratados WHERE empresa_id=%s AND servico_id=%s ORDER BY id DESC LIMIT 5', (args.empresa, args.servico_id))
            rows = cur.fetchall()
            print('\nÚltimas 5 inserções:')
            for r in rows:
                print(' ', r)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
