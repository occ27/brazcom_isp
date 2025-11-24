"""
Migrate services from nf21.`nf21-servicos` -> nfcom.servicos
- Preserves id
- Maps source columns to destination per mapping in conversation
- Skips rows where empresa_id not found in destination
- Produces a CSV report with any errors and unmapped fields

Usage:
    python migrations/migrate_servicos_to_nfcom.py --host localhost --user occ --password Altavista740
"""
import argparse
import pymysql
import csv
import os
from datetime import datetime


def connect(host, port, user, password, db):
    return pymysql.connect(host=host, port=port, user=user, password=password, db=db, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


def fetch_src(conn):
    # source table name contains a hyphen
    cols = ['id','id_empresa','codigo','descricao','cfop','codigo_classificacao','unidade','numero_contrato','tipo_isencao','indicador_desconto_judicial','valor','bc_icms','aliquota_icms','isentas','quantidade_faturada','aliquota_pis','pis_pasep','aliquota_cofins','cofins','outras','anatel_tipo_atendimento','anatel_tipo_meio','anatel_tipo_produto','anatel_tipo_tecnologia']
    sql = 'SELECT ' + ','.join(cols) + ' FROM `nf21-servicos` ORDER BY id'
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def id_exists(conn, id_):
    with conn.cursor() as cur:
        cur.execute('SELECT 1 FROM servicos WHERE id=%s', (id_,))
        return cur.fetchone() is not None


def empresa_exists(conn, empresa_id):
    with conn.cursor() as cur:
        cur.execute('SELECT 1 FROM empresas WHERE id=%s', (empresa_id,))
        return cur.fetchone() is not None


def insert_dst(conn, s):
    cols = ['id','empresa_id','codigo','descricao','cClass','unidade_medida','valor_unitario','is_active','cfop','ncm','base_calculo_icms_default','aliquota_icms_default','valor_desconto_default','valor_outros_default']
    placeholders = ','.join(['%s'] * len(cols))
    sql = f"INSERT INTO servicos ({','.join(cols)}) VALUES ({placeholders})"
    values = [
        s.get('id'),
        s.get('id_empresa'),
        s.get('codigo'),
        s.get('descricao'),
        s.get('codigo_classificacao'),
        s.get('unidade'),
        s.get('valor'),
        1,  # is_active default
        s.get('cfop'),
        None,  # ncm not present in source
        s.get('bc_icms'),
        s.get('aliquota_icms'),
        None,  # valor_desconto_default: not clearly mappable
        s.get('outras'),
    ]
    with conn.cursor() as cur:
        cur.execute(sql, values)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=3306)
    parser.add_argument('--user', default='occ')
    parser.add_argument('--password', default='Altavista740')
    parser.add_argument('--no-report', action='store_true', help='Do not write CSV report')
    args = parser.parse_args()

    src = connect(args.host, args.port, args.user, args.password, 'nf21')
    dst = connect(args.host, args.port, args.user, args.password, 'nfcom')

    report = []
    unmapped_report = []
    try:
        rows = fetch_src(src)
        print(f'Found {len(rows)} services in nf21.`nf21-servicos`')
        if not rows:
            print('No rows to migrate')
            return

        dst.begin()
        with dst.cursor() as cur:
            cur.execute('SET FOREIGN_KEY_CHECKS=0')

        inserted = 0
        skipped = 0
        for r in rows:
            rid = r.get('id')
            eid = r.get('id_empresa')
            if not empresa_exists(dst, eid):
                skipped += 1
                report.append({'id': rid, 'reason': 'empresa_missing', 'id_empresa': eid})
                continue
            if id_exists(dst, rid):
                skipped += 1
                report.append({'id': rid, 'reason': 'id_exists'})
                continue
            try:
                insert_dst(dst, r)
                inserted += 1
                # collect unmapped important fields for auditing
                unmapped = {k: r.get(k) for k in ('aliquota_pis','pis_pasep','aliquota_cofins','cofins','quantidade_faturada','numero_contrato','tipo_isencao','indicador_desconto_judicial')}
                unmapped_report.append({'id': rid, **unmapped})
            except Exception as e:
                skipped += 1
                report.append({'id': rid, 'reason': 'insert_error', 'error': str(e)})

        # reset auto_increment
        with dst.cursor() as cur:
            cur.execute('SELECT COALESCE(MAX(id), 0) as m FROM servicos')
            m = cur.fetchone().get('m')
            nextv = m + 1
            cur.execute(f'ALTER TABLE servicos AUTO_INCREMENT = {nextv}')
            cur.execute('SET FOREIGN_KEY_CHECKS=1')
        dst.commit()

        print(f'Inserted: {inserted}, Skipped: {skipped}, Errors: {len([r for r in report if r.get("reason")])}')

        if not args.no_report:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_dir = os.path.dirname(os.path.abspath(__file__))
            rep_file = os.path.join(report_dir, f'migrate_servicos_report_{ts}.csv')
            unmapped_file = os.path.join(report_dir, f'migrate_servicos_unmapped_{ts}.csv')
            # write report
            with open(rep_file, 'w', newline='', encoding='utf-8') as f:
                keys = set(k for d in report for k in d) if report else {'id','reason'}
                writer = csv.DictWriter(f, fieldnames=sorted(keys))
                writer.writeheader()
                for r in report:
                    writer.writerow(r)
            # write unmapped
            with open(unmapped_file, 'w', newline='', encoding='utf-8') as f:
                keys2 = ['id','aliquota_pis','pis_pasep','aliquota_cofins','cofins','quantidade_faturada','numero_contrato','tipo_isencao','indicador_desconto_judicial']
                writer = csv.DictWriter(f, fieldnames=keys2)
                writer.writeheader()
                for r in unmapped_report:
                    writer.writerow(r)
            print('Report written to', rep_file)
            print('Unmapped fields report written to', unmapped_file)
        else:
            if report:
                print('Report suppressed; there are', len(report), 'report items')

    finally:
        src.close()
        dst.close()

if __name__ == '__main__':
    main()
