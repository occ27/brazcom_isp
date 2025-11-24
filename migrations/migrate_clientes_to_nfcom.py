"""
Migrate nf21.clientes -> nfcom.clientes and create empresa_clientes associations from meus_clientes.
- Finds the first empresa associated to a client via meus_clientes -> minha_empresa
- Preserves client id when inserting
- Writes CSV report for skipped rows

Usage:
    python migrations/migrate_clientes_to_nfcom.py --host localhost --user occ --password Altavista740
"""
import argparse
import pymysql
import csv
import os
from datetime import datetime


def connect(host, port, user, password, db):
    return pymysql.connect(host=host, port=port, user=user, password=password, db=db, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


def fetch_clients(conn):
    cols = ['id','id_user','cnpj','inscricao','nome','cep','endereco','numero','complemento','bairro','cidade','uf','telefone','data_cadastro','ativo','ibge','email','obs']
    with conn.cursor() as cur:
        cur.execute('SELECT ' + ','.join(cols) + ' FROM clientes ORDER BY id')
        return cur.fetchall()


def find_empresa_for_client(src_conn, client_id):
    # look up meus_clientes -> minha_empresa -> id_empresa
    with src_conn.cursor() as cur:
        cur.execute('SELECT m.id_empresa FROM meus_clientes mc JOIN minha_empresa m ON mc.id_minha_empresa = m.id WHERE mc.id_cliente=%s LIMIT 1', (client_id,))
        r = cur.fetchone()
        return r.get('id_empresa') if r else None


def empresa_exists(dst_conn, empresa_id):
    with dst_conn.cursor() as cur:
        cur.execute('SELECT 1 FROM empresas WHERE id=%s', (empresa_id,))
        return cur.fetchone() is not None


def client_exists(dst_conn, client_id):
    with dst_conn.cursor() as cur:
        cur.execute('SELECT 1 FROM clientes WHERE id=%s', (client_id,))
        return cur.fetchone() is not None


def insert_client(dst_conn, client, empresa_id):
    sql = ('INSERT INTO clientes (id, empresa_id, nome_razao_social, cpf_cnpj, idOutros, tipo_pessoa, ind_ie_dest, inscricao_estadual, email, telefone, is_active, created_at) '
           'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)')
    # determine tipo_pessoa: database expects 'FISICA' or 'JURIDICA'
    cpfcnpj = client.get('cnpj')
    tipo = 'JURIDICA' if cpfcnpj and len(cpfcnpj.replace('.','').replace('/','').replace('-','').strip())>11 else 'FISICA'
    ind_ie_dest = 'NAO_CONTRIBUINTE'  # default
    values = [
        client.get('id'),
        empresa_id,
        client.get('nome'),
        client.get('cnpj'),
        None,
        tipo,
        ind_ie_dest,
        client.get('inscricao'),
        client.get('email'),
        client.get('telefone'),
        1 if client.get('ativo') else 0,
        client.get('data_cadastro') or datetime.now(),
    ]
    with dst_conn.cursor() as cur:
        cur.execute(sql, values)


def insert_empresa_cliente(dst_conn, empresa_id, cliente_id, created_by_user_id=None):
    sql = ('INSERT INTO empresa_clientes (empresa_id, cliente_id, created_by_user_id, is_active, created_at) '
           'VALUES (%s,%s,%s,%s,%s)')
    with dst_conn.cursor() as cur:
        cur.execute(sql, (empresa_id, cliente_id, created_by_user_id, 1, datetime.now()))


def fetch_meus_clientes(src_conn):
    with src_conn.cursor() as cur:
        cur.execute('SELECT id, id_minha_empresa, id_cliente FROM meus_clientes ORDER BY id')
        return cur.fetchall()


def get_minha_empresa(src_conn, id_minha_empresa):
    with src_conn.cursor() as cur:
        cur.execute('SELECT id, id_empresa, id_user FROM minha_empresa WHERE id=%s', (id_minha_empresa,))
        return cur.fetchone()


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
    assoc_report = []
    try:
        clients = fetch_clients(src)
        print(f'Found {len(clients)} clients in nf21')
        if not clients:
            return

        dst.begin()
        with dst.cursor() as cur:
            cur.execute('SET FOREIGN_KEY_CHECKS=0')

        inserted = 0
        skipped = 0
        for c in clients:
            cid = c.get('id')
            if client_exists(dst, cid):
                skipped += 1
                report.append({'id': cid, 'reason': 'already_exists'})
                continue
            empresa_id = find_empresa_for_client(src, cid)
            if not empresa_id:
                skipped += 1
                report.append({'id': cid, 'reason': 'no_empresa_association'})
                continue
            if not empresa_exists(dst, empresa_id):
                skipped += 1
                report.append({'id': cid, 'reason': 'empresa_missing', 'empresa_id': empresa_id})
                continue
            try:
                # insert client
                sql = ('INSERT INTO clientes (id, empresa_id, nome_razao_social, cpf_cnpj, idOutros, tipo_pessoa, ind_ie_dest, inscricao_estadual, email, telefone, is_active, created_at) '
                       'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)')
                cpfcnpj = c.get('cnpj')
                tipo = 'JURIDICA' if cpfcnpj and len(cpfcnpj.replace('.','').replace('/','').replace('-','').strip())>11 else 'FISICA'
                ind_ie_dest = 'NAO_CONTRIBUINTE'
                values = [
                    c.get('id'),
                    empresa_id,
                    c.get('nome'),
                    c.get('cnpj'),
                    None,
                    tipo,
                    ind_ie_dest,
                    c.get('inscricao'),
                    c.get('email'),
                    c.get('telefone'),
                    1 if c.get('ativo') else 0,
                    c.get('data_cadastro') or datetime.now(),
                ]
                with dst.cursor() as cur:
                    cur.execute(sql, values)
                inserted += 1
            except Exception as e:
                skipped += 1
                report.append({'id': cid, 'reason': 'insert_error', 'error': str(e)})

        # now create empresa_clientes associations from meus_clientes
        meus = fetch_meus_clientes(src)
        assoc_inserted = 0
        assoc_skipped = 0
        for m in meus:
            mc_id = m.get('id')
            id_minha_empresa = m.get('id_minha_empresa')
            cliente_id = m.get('id_cliente')
            minha = get_minha_empresa(src, id_minha_empresa)
            if not minha:
                assoc_skipped += 1
                assoc_report.append({'meus_id': mc_id, 'reason': 'minha_empresa_missing', 'id_minha_empresa': id_minha_empresa})
                continue
            empresa_id = minha.get('id_empresa')
            created_by_user_id = minha.get('id_user')
            # validate existences
            if not empresa_exists(dst, empresa_id):
                assoc_skipped += 1
                assoc_report.append({'meus_id': mc_id, 'reason': 'empresa_missing', 'empresa_id': empresa_id})
                continue
            # ensure client exists
            with dst.cursor() as cur:
                cur.execute('SELECT 1 FROM clientes WHERE id=%s', (cliente_id,))
                if cur.fetchone() is None:
                    assoc_skipped += 1
                    assoc_report.append({'meus_id': mc_id, 'reason': 'cliente_missing', 'cliente_id': cliente_id})
                    continue
            # check duplicate
            with dst.cursor() as cur:
                cur.execute('SELECT 1 FROM empresa_clientes WHERE empresa_id=%s AND cliente_id=%s', (empresa_id, cliente_id))
                if cur.fetchone():
                    assoc_skipped += 1
                    assoc_report.append({'meus_id': mc_id, 'reason': 'assoc_exists', 'empresa_id': empresa_id, 'cliente_id': cliente_id})
                    continue
            try:
                insert_empresa_cliente(dst, empresa_id, cliente_id, created_by_user_id)
                assoc_inserted += 1
            except Exception as e:
                assoc_skipped += 1
                assoc_report.append({'meus_id': mc_id, 'reason': 'insert_error', 'error': str(e)})

        with dst.cursor() as cur:
            cur.execute('SELECT COALESCE(MAX(id),0) as m FROM clientes')
            m = cur.fetchone().get('m')
            cur.execute(f'ALTER TABLE clientes AUTO_INCREMENT = {m+1}')
            cur.execute('SET FOREIGN_KEY_CHECKS=1')
        dst.commit()

        print(f'Clients inserted: {inserted}, skipped: {skipped}')
        print(f'Associations inserted: {assoc_inserted}, skipped: {assoc_skipped}')

        # write reports
        report_dir = os.path.dirname(os.path.abspath(__file__))
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        if report:
            rf = os.path.join(report_dir, f'migrate_clientes_report_{ts}.csv')
            with open(rf, 'w', newline='', encoding='utf-8') as f:
                keys = sorted({k for d in report for k in d})
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for r in report:
                    writer.writerow(r)
            print('Client report written to', rf)
        if assoc_report:
            af = os.path.join(report_dir, f'migrate_clientes_assoc_report_{ts}.csv')
            with open(af, 'w', newline='', encoding='utf-8') as f:
                keys = sorted({k for d in assoc_report for k in d})
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for r in assoc_report:
                    writer.writerow(r)
            print('Association report written to', af)

    finally:
        src.close()
        dst.close()

if __name__ == '__main__':
    main()
