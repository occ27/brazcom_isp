"""
Import customers from a CSV into nfcom database for a given company (empresa_id).

The script will:
 - read the CSV (headers inferred, case-insensitive)
 - for each row: find or create a Cliente (by cpf_cnpj or idOutros)
 - ensure an EmpresaCliente association exists for the given empresa_id
 - insert one EmpresaClienteEndereco for the row's address fields

Usage:
  python migrations/import_csv_to_empresa_clients.py /path/to/file.csv --empresa 34 --host localhost --user occ --password secret [--dry-run]

CSV headers supported (case-insensitive, common names):
  nome, nome_razao_social, cpf_cnpj, idOutros, tipo_pessoa, email, telefone,
  descricao, endereco, numero, complemento, bairro, municipio, cidade, uf, cep, codigo_ibge

If a cliente with the same cpf_cnpj exists it will be reused. If cpf_cnpj is empty, idOutros will be used.
"""

import argparse
import csv
import os
from datetime import datetime
import pymysql
import re


def connect(host, port, user, password, db):
    return pymysql.connect(host=host, port=port, user=user, password=password, db=db, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


def norm_digits(v):
    if v is None:
        return None
    s = ''.join([c for c in str(v) if c.isdigit()])
    return s if s else None


def detect_tipo_pessoa(cpf_cnpj):
    if not cpf_cnpj:
        return 'J'  # default to juridica when unknown
    d = norm_digits(cpf_cnpj)
    if not d:
        return 'J'
    if len(d) == 11:
        return 'F'
    return 'J'


def format_cpf_cnpj_from_digits(digits):
    """Format a digits-only CPF/CNPJ string into the common stored formats.

    Examples:
      11122233344 -> 111.222.333-44
      11222333000181 -> 11.222.333/0001-81
    """
    if not digits:
        return None
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    if len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    return None


def find_cliente_by_cpf(dst_conn, cpf_cnpj):
    if not cpf_cnpj:
        return None
    with dst_conn.cursor() as cur:
        cur.execute('SELECT * FROM clientes WHERE cpf_cnpj=%s', (cpf_cnpj,))
        return cur.fetchone()


def find_cliente_by_idOutros(dst_conn, idOutros):
    if not idOutros:
        return None
    with dst_conn.cursor() as cur:
        cur.execute('SELECT * FROM clientes WHERE idOutros=%s', (idOutros,))
        return cur.fetchone()


def find_cliente_by_digits(dst_conn, digits):
    """Find a cliente by comparing only digits of cpf_cnpj (strips punctuation)."""
    if not digits:
        return None
    with dst_conn.cursor() as cur:
        cur.execute("SELECT * FROM clientes WHERE REPLACE(REPLACE(REPLACE(REPLACE(cpf_cnpj,'.',''),'-',''),'/',''),' ','')=%s", (digits,))
        return cur.fetchone()


def create_cliente(dst_conn, empresa_id, row):
    # Build cliente insert with available fields
    nome = row.get('nome') or row.get('nome_razao_social') or row.get('nome_razao') or ''
    cpf_cnpj = row.get('cpf_cnpj') or None
    if cpf_cnpj:
        cpf_cnpj = norm_digits(cpf_cnpj)
        # keep formatted length up to 14
        if len(cpf_cnpj) == 11:
            cpf_cnpj = f"{cpf_cnpj[:3]}.{cpf_cnpj[3:6]}.{cpf_cnpj[6:9]}-{cpf_cnpj[9:]}"
        elif len(cpf_cnpj) == 14:
            cpf_cnpj = f"{cpf_cnpj[:2]}.{cpf_cnpj[2:5]}.{cpf_cnpj[5:8]}/{cpf_cnpj[8:12]}-{cpf_cnpj[12:]}"
    idOutros = row.get('idoutros') or row.get('idOutros') or None
    # Normalize tipo_pessoa: ENUM values are 'FISICA' or 'JURIDICA'
    tp_raw = (row.get('tipo_pessoa') or row.get('pessoa') or '').strip().lower()
    if 'f' in tp_raw or 'fis' in tp_raw:
        tipo_pessoa = 'FISICA'
    elif 'j' in tp_raw or 'jur' in tp_raw:
        tipo_pessoa = 'JURIDICA'
    else:
        # detect from CPF/CNPJ length
        d = norm_digits(cpf_cnpj) if cpf_cnpj else None
        if d and len(d) == 11:
            tipo_pessoa = 'FISICA'
        else:
            tipo_pessoa = 'JURIDICA'
    # Map ind_ie_dest: ENUM('CONTRIBUINTE_ICMS','CONTRIBUINTE_ISENTO','NAO_CONTRIBUINTE')
    ind_raw = row.get('ind_ie_dest') or row.get('indIEDest') or '9'
    if ind_raw == '1':
        ind_ie_dest = 'CONTRIBUINTE_ICMS'
    elif ind_raw == '2':
        ind_ie_dest = 'CONTRIBUINTE_ISENTO'
    else:  # '9' or other
        ind_ie_dest = 'NAO_CONTRIBUINTE'
    inscricao_estadual = row.get('inscricao_estadual') or row.get('ie') or None
    email = row.get('email') or None
    telefone = row.get('telefone') or None

    sql = ('INSERT INTO clientes (empresa_id, nome_razao_social, cpf_cnpj, idOutros, tipo_pessoa, ind_ie_dest, inscricao_estadual, email, telefone, created_at) '
           'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)')
    now = datetime.now()
    with dst_conn.cursor() as cur:
        cur.execute(sql, (empresa_id, nome, cpf_cnpj, idOutros, tipo_pessoa, ind_ie_dest, inscricao_estadual, email, telefone, now))
        return cur.lastrowid


def find_empresa_cliente(dst_conn, empresa_id, cliente_id):
    with dst_conn.cursor() as cur:
        cur.execute('SELECT id FROM empresa_clientes WHERE empresa_id=%s AND cliente_id=%s', (empresa_id, cliente_id))
        r = cur.fetchone()
        return r.get('id') if r else None


def create_empresa_cliente(dst_conn, empresa_id, cliente_id, created_by_user_id=None):
    sql = ('INSERT INTO empresa_clientes (empresa_id, cliente_id, created_by_user_id, is_active, created_at) VALUES (%s,%s,%s,%s,%s)')
    now = datetime.now()
    with dst_conn.cursor() as cur:
        cur.execute(sql, (empresa_id, cliente_id, created_by_user_id, 1, now))
        return cur.lastrowid


def insert_endereco(dst_conn, empresa_cliente_id, row):
    sql = ('INSERT INTO empresa_cliente_enderecos (empresa_cliente_id, descricao, endereco, numero, complemento, bairro, municipio, uf, cep, codigo_ibge, is_principal, created_at) '
           'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)')
    descricao = row.get('descricao') or None
    endereco = row.get('endereco') or row.get('logradouro') or ''
    numero = row.get('numero') or row.get('n') or 'SN'
    complemento = row.get('complemento') or None
    bairro = row.get('bairro') or ''
    municipio = row.get('municipio') or row.get('cidade') or ''
    uf = (row.get('uf') or '').upper() if row.get('uf') else ''
    cep = norm_digits(row.get('cep')) or ''
    codigo_ibge = norm_digits(row.get('codigo_ibge')) if row.get('codigo_ibge') else None
    is_principal = 1
    now = datetime.now()
    with dst_conn.cursor() as cur:
        cur.execute(sql, (empresa_cliente_id, descricao, endereco, numero, complemento, bairro, municipio, uf, cep, codigo_ibge, is_principal, now))
        return cur.lastrowid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csvfile', nargs='?', default=None, help='path to csv file (optional). If omitted, script will pick the most recent .csv in the migrations folder')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=3306)
    parser.add_argument('--user', default='occ')
    parser.add_argument('--password', default='Altavista740')
    parser.add_argument('--empresa', type=int, required=True, help='empresa_id to attach clients to')
    parser.add_argument('--created-by', type=int, default=None, help='created_by_user_id to set on empresa_clientes')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    # If csvfile not provided, try to auto-detect a CSV file in the same folder as this script
    if not args.csvfile:
        migrations_dir = os.path.dirname(os.path.abspath(__file__))
        # Prefer an explicit john.csv if present (user requested)
        john_path = os.path.join(migrations_dir, 'john.csv')
        if os.path.exists(john_path):
            args.csvfile = john_path
            print('Auto-detected CSV file (preferred john.csv):', args.csvfile)
        else:
            csv_files = [f for f in os.listdir(migrations_dir) if f.lower().endswith('.csv')]
            # exclude report files generated by this script to avoid picking them by accident
            csv_files = [f for f in csv_files if not f.startswith('import_csv_to_empresa_clients_report')]
            if not csv_files:
                print('No CSV file provided and no suitable .csv files found in', migrations_dir)
                return
            # pick the most recently modified CSV among remaining files
            csv_files_full = [os.path.join(migrations_dir, f) for f in csv_files]
            csv_files_full.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            args.csvfile = csv_files_full[0]
            print('Auto-detected CSV file:', args.csvfile)

    if not os.path.exists(args.csvfile):
        print('CSV file not found:', args.csvfile)
        return

    dst = connect(args.host, args.port, args.user, args.password, 'nfcom')

    report = []
    inserted_clients = 0
    created_assocs = 0
    inserted_enderecos = 0
    skipped = 0

    try:
        with open(args.csvfile, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        print(f'Found {len(rows)} rows in CSV')
        if not rows:
            return

        if not args.dry_run:
            with dst.cursor() as cur:
                cur.execute('SET FOREIGN_KEY_CHECKS=0')
            dst.begin()

        for i, r in enumerate(rows, start=1):
            # normalize keys to lowercase and remove BOM
            row = {k.strip().lower().lstrip('\ufeff'): (v.strip() if v is not None else v) for k, v in r.items()}

            cpf = row.get('cpf_cnpj') or row.get('cpf') or row.get('cnpj')
            cpf_norm = None
            if cpf:
                cpf_norm = norm_digits(cpf)
            idoutros = row.get('idoutros') or row.get('id_outros')

            # try to find existing cliente:
            # 1) try exact match using formatted CPF/CNPJ as stored in DB
            # 2) fallback to digits-only comparison (strip punctuation)
            # 3) fallback to idOutros
            db_cliente = None
            if cpf_norm:
                cpf_formatted = format_cpf_cnpj_from_digits(cpf_norm)
                if cpf_formatted:
                    db_cliente = find_cliente_by_cpf(dst, cpf_formatted)
                if not db_cliente:
                    db_cliente = find_cliente_by_digits(dst, cpf_norm)
            if not db_cliente and idoutros:
                db_cliente = find_cliente_by_idOutros(dst, idoutros)

            cliente_id = None
            if db_cliente:
                cliente_id = db_cliente.get('id')
            else:
                if args.dry_run:
                    report.append({'row': i, 'action': 'would_create_cliente', 'cpf': cpf_norm, 'idOutros': idoutros})
                else:
                    try:
                        cliente_id = create_cliente(dst, args.empresa, row)
                        inserted_clients += 1
                        report.append({'row': i, 'action': 'created_cliente', 'cliente_id': cliente_id})
                    except Exception as e:
                        skipped += 1
                        report.append({'row': i, 'reason': 'create_cliente_error', 'error': str(e)})
                        continue

            # ensure empresa_cliente association
            emp_cli_id = find_empresa_cliente(dst, args.empresa, cliente_id)
            if not emp_cli_id:
                if args.dry_run:
                    report.append({'row': i, 'action': 'would_create_empresa_cliente', 'empresa': args.empresa, 'cliente_id': cliente_id})
                else:
                    try:
                        emp_cli_id = create_empresa_cliente(dst, args.empresa, cliente_id, args.created_by)
                        created_assocs += 1
                        report.append({'row': i, 'action': 'created_empresa_cliente', 'empresa_cliente_id': emp_cli_id})
                    except Exception as e:
                        skipped += 1
                        report.append({'row': i, 'reason': 'create_empresa_cliente_error', 'error': str(e)})
                        continue

            # insert endereco
            if args.dry_run:
                report.append({'row': i, 'action': 'would_insert_endereco', 'empresa_cliente_id': emp_cli_id})
            else:
                try:
                    end_id = insert_endereco(dst, emp_cli_id, row)
                    inserted_enderecos += 1
                    report.append({'row': i, 'action': 'inserted_endereco', 'empresa_cliente_endereco_id': end_id, 'empresa_cliente_id': emp_cli_id})
                except Exception as e:
                    skipped += 1
                    report.append({'row': i, 'reason': 'insert_endereco_error', 'error': str(e)})

        if not args.dry_run:
            with dst.cursor() as cur:
                cur.execute('SET FOREIGN_KEY_CHECKS=1')
            dst.commit()

        print(f'Inserted clients: {inserted_clients}, created associations: {created_assocs}, inserted enderecos: {inserted_enderecos}, skipped: {skipped}')

        # write report CSV
        report_dir = os.path.dirname(os.path.abspath(__file__))
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        rf = os.path.join(report_dir, f'import_csv_to_empresa_clients_report_{ts}.csv')
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
