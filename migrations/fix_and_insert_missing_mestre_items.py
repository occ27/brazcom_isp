"""
Fix skipped mestre-item migrations by creating placeholder services for missing service ids (or when id_servico is NULL) and inserting the corresponding servicos_contratados rows.
Reads the report file `migrate_mestre_items_report_*.csv` to get item_ids to fix.
"""
import glob
import csv
import os
import pymysql
from datetime import datetime

REPORT_GLOB = os.path.join(os.path.dirname(__file__), 'migrate_mestre_items_report_*.csv')


def connect():
    return pymysql.connect(host='localhost', user='occ', password='Altavista740', db=None, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


def find_report():
    files = glob.glob(REPORT_GLOB)
    if not files:
        return None
    # pick most recent
    files.sort()
    return files[-1]


def fetch_item(src_conn, item_id):
    with src_conn.cursor() as cur:
        cur.execute('SELECT * FROM `nf21-item-agenda` WHERE id=%s', (item_id,))
        return cur.fetchone()


def fetch_mestre(src_conn, mestre_id):
    with src_conn.cursor() as cur:
        cur.execute('SELECT * FROM `nf21-mestre-agenda` WHERE id=%s', (mestre_id,))
        return cur.fetchone()


def servico_exists(dst_conn, servico_id):
    with dst_conn.cursor() as cur:
        cur.execute('SELECT 1 FROM servicos WHERE id=%s', (servico_id,))
        return cur.fetchone() is not None


def find_servico_in_nf21(src_conn, servico_id):
    with src_conn.cursor() as cur:
        cur.execute('SELECT * FROM `nf21-servicos` WHERE id=%s', (servico_id,))
        return cur.fetchone()


def insert_servico_placeholder(dst_conn, data_from_nf21=None, placeholder_code=None, empresa_id_override=None):
    # columns in servicos: id, empresa_id, codigo, descricao, cClass, unidade_medida, valor_unitario, is_active, cfop, ncm, base_calculo_icms_default, aliquota_icms_default, valor_desconto_default, valor_outros_default
    if data_from_nf21:
        # try to map
        vals = {
            'id': data_from_nf21.get('id'),
            'empresa_id': data_from_nf21.get('id_empresa'),
            'codigo': data_from_nf21.get('codigo'),
            'descricao': data_from_nf21.get('descricao'),
            'cClass': data_from_nf21.get('codigo_classificacao'),
            'unidade_medida': data_from_nf21.get('unidade'),
            'valor_unitario': data_from_nf21.get('valor'),
            'is_active': 1,
            'cfop': data_from_nf21.get('cfop'),
            'ncm': None,
            'base_calculo_icms_default': data_from_nf21.get('bc_icms'),
            'aliquota_icms_default': data_from_nf21.get('aliquota_icms'),
            'valor_desconto_default': None,
            'valor_outros_default': data_from_nf21.get('outras'),
        }
    else:
        vals = {
            'id': None,
            'empresa_id': empresa_id_override,
            'codigo': placeholder_code,
            'descricao': f'Placeholder service for {placeholder_code}',
            'cClass': 'MIG',
            'unidade_medida': 'UN',
            'valor_unitario': 0.0,
            'is_active': 1,
            'cfop': None,
            'ncm': None,
            'base_calculo_icms_default': None,
            'aliquota_icms_default': None,
            'valor_desconto_default': None,
            'valor_outros_default': None,
        }
    with dst_conn.cursor() as cur:
        if vals['id']:
            # try to insert preserving id
            sql = ('INSERT INTO servicos (id, empresa_id, codigo, descricao, cClass, unidade_medida, valor_unitario, is_active, cfop, ncm, base_calculo_icms_default, aliquota_icms_default, valor_desconto_default, valor_outros_default) '
                   'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)')
            params = [vals['id'], vals['empresa_id'], vals['codigo'], vals['descricao'], vals['cClass'], vals['unidade_medida'], vals['valor_unitario'], vals['is_active'], vals['cfop'], vals['ncm'], vals['base_calculo_icms_default'], vals['aliquota_icms_default'], vals['valor_desconto_default'], vals['valor_outros_default']]
            cur.execute(sql, params)
            return vals['id']
        else:
            sql = ('INSERT INTO servicos (empresa_id, codigo, descricao, cClass, unidade_medida, valor_unitario, is_active, cfop, ncm, base_calculo_icms_default, aliquota_icms_default, valor_desconto_default, valor_outros_default) '
                   'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)')
            params = [vals['empresa_id'], vals['codigo'], vals['descricao'], vals['cClass'], vals['unidade_medida'], vals['valor_unitario'], vals['is_active'], vals['cfop'], vals['ncm'], vals['base_calculo_icms_default'], vals['aliquota_icms_default'], vals['valor_desconto_default'], vals['valor_outros_default']]
            cur.execute(sql, params)
            cur.execute('SELECT LAST_INSERT_ID() as id')
            nid = cur.fetchone().get('id')
            return nid


def insert_servico_contratado_for_item(dst_conn, item_row, servico_id_to_use):
    # construct values similar to migration insert_dst
    cols = ['id','empresa_id','cliente_id','servico_id','numero_contrato','d_contrato_ini','d_contrato_fim','periodicidade','dia_emissao','quantidade','valor_unitario','valor_total','auto_emit','is_active','created_by_user_id','created_at','vencimento']
    values = [
        item_row['id'],
        item_row.get('id_empresa'),
        item_row.get('id_cliente'),
        servico_id_to_use,
        (f"{item_row.get('modelo')}-{item_row.get('serie')}" if item_row.get('modelo') and item_row.get('serie') else None),
        None,
        None,
        'MENSAL',
        item_row.get('dia_emissao') or None,
        item_row.get('quantidade_faturada') or 1,
        item_row.get('valor') or 0.0,
        (item_row.get('quantidade_faturada') or 1) * (item_row.get('valor') or 0.0),
        1,
        1,
        None,
        datetime.now(),
        None,
    ]
    with dst_conn.cursor() as cur:
        sql = f"INSERT INTO servicos_contratados ({','.join(cols)}) VALUES ({','.join(['%s']*len(cols))})"
        cur.execute(sql, values)


if __name__ == '__main__':
    report_file = find_report()
    if not report_file:
        print('No report file found matching', REPORT_GLOB)
        raise SystemExit(1)
    item_ids = []
    with open(report_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            iid = r.get('item_id') or r.get('id') or r.get('item')
            try:
                iid = int(iid)
            except Exception:
                continue
            item_ids.append(iid)
    if not item_ids:
        print('No item ids found in report')
        raise SystemExit(0)

    src_conn = pymysql.connect(host='localhost', user='occ', password='Altavista740', db='nf21', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
    dst_conn = pymysql.connect(host='localhost', user='occ', password='Altavista740', db='nfcom', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
    try:
        dst_conn.begin()
        with dst_conn.cursor() as cur:
            cur.execute('SET FOREIGN_KEY_CHECKS=0')

        created = []
        inserted_contracts = []
        errors = []
        for iid in item_ids:
            item = fetch_item(src_conn, iid)
            if not item:
                errors.append({'item_id': iid, 'error': 'item_not_found'})
                continue
            mestre = fetch_mestre(src_conn, item.get('id_mestre'))
            # combine fields for insert
            row = {
                'id': item.get('id'),
                'item_id': item.get('id'),
                'id_empresa': mestre.get('id_empresa') if mestre else None,
                'modelo': mestre.get('modelo') if mestre else None,
                'serie': mestre.get('serie') if mestre else None,
                'id_cliente': mestre.get('id_cliente') if mestre else None,
                'dia_emissao': mestre.get('dia') if mestre else None,
                'data_proxima_emissao': mestre.get('data_proxima_emissao') if mestre else None,
                'observacao': mestre.get('observacao') if mestre else None,
                'id_servico': item.get('id_servico'),
                'valor': item.get('valor'),
                'bc_icms': item.get('bc_icms'),
                'isentos': item.get('isentos'),
                'outros': item.get('outros'),
                'aliquota_icms': item.get('aliquota_icms'),
                'quantidade_faturada': item.get('quantidade_faturada'),
            }
            sid = row.get('id_servico')
            if sid:
                if servico_exists(dst_conn, sid):
                    servico_to_use = sid
                else:
                    # try to find in nf21-servicos and insert preserving id
                    nf21serv = find_servico_in_nf21(src_conn, sid)
                    if nf21serv:
                        try:
                            new_sid = insert_servico_placeholder(dst_conn, data_from_nf21=nf21serv)
                            created.append({'servico_id_created': new_sid, 'from_nf21serv_id': sid})
                            servico_to_use = new_sid
                        except Exception as e:
                            errors.append({'item_id': iid, 'error': f'servico_insert_error: {e}'})
                            continue
                    else:
                        # create placeholder with code referencing original id
                        try:
                            new_sid = insert_servico_placeholder(dst_conn, data_from_nf21=None, placeholder_code=f'NF21_SRV_{sid}', empresa_id_override=row.get('id_empresa'))
                            created.append({'servico_id_created': new_sid, 'placeholder_for': sid})
                            servico_to_use = new_sid
                        except Exception as e:
                            errors.append({'item_id': iid, 'error': f'placeholder_error: {e}'})
                            continue
            else:
                # no sid in item — create placeholder
                try:
                    new_sid = insert_servico_placeholder(dst_conn, data_from_nf21=None, placeholder_code=f'ITEM_PLACEHOLDER_{iid}', empresa_id_override=row.get('id_empresa'))
                    created.append({'servico_id_created': new_sid, 'placeholder_for_item': iid})
                    servico_to_use = new_sid
                except Exception as e:
                    errors.append({'item_id': iid, 'error': f'placeholder_error: {e}'})
                    continue

            # insert servicos_contratados row now
            try:
                insert_servico_contratado_for_item(dst_conn, {**row, **{'modelo': row.get('modelo'),'serie': row.get('serie'),'valor': row.get('valor'),'quantidade_faturada': row.get('quantidade_faturada')}}, servico_to_use)
                inserted_contracts.append({'item_id': iid, 'servico_id_used': servico_to_use})
            except Exception as e:
                errors.append({'item_id': iid, 'error': f'contract_insert_error: {e}'})
                continue

        # reset auto_increment for servicos and servicos_contratados
        with dst_conn.cursor() as cur:
            cur.execute('SELECT COALESCE(MAX(id),0) as m FROM servicos')
            m = cur.fetchone().get('m')
            cur.execute(f'ALTER TABLE servicos AUTO_INCREMENT = {m+1}')
            cur.execute('SELECT COALESCE(MAX(id),0) as m2 FROM servicos_contratados')
            m2 = cur.fetchone().get('m2')
            cur.execute(f'ALTER TABLE servicos_contratados AUTO_INCREMENT = {m2+1}')
            cur.execute('SET FOREIGN_KEY_CHECKS=1')
        dst_conn.commit()

        # write summary
        print('Created services:', created)
        print('Inserted contracts:', inserted_contracts)
        print('Errors:', errors)

        # write CSVs
        rep_dir = os.path.dirname(os.path.abspath(__file__))
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        with open(os.path.join(rep_dir, f'fix_mestre_items_created_{ts}.csv'), 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['servico_id_created','from_nf21serv_id','placeholder_for','placeholder_for_item'])
            w.writeheader()
            for r in created:
                w.writerow(r)
        with open(os.path.join(rep_dir, f'fix_mestre_items_inserted_contracts_{ts}.csv'), 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['item_id','servico_id_used'])
            w.writeheader()
            for r in inserted_contracts:
                w.writerow(r)
        with open(os.path.join(rep_dir, f'fix_mestre_items_errors_{ts}.csv'), 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['item_id','error'])
            w.writeheader()
            for r in errors:
                w.writerow(r)

    finally:
        src_conn.close()
        dst_conn.close()
