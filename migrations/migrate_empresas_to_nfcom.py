"""
Migrate empresas from nf21 -> nfcom preserving IDs and mapping fields.
Usage:
  python migrations/migrate_empresas_to_nfcom.py --host localhost --user occ --password Altavista740

This script inserts rows into nfcom.empresas preserving id. It will skip rows with conflicting id and report errors.
"""
import argparse
import pymysql


def connect(host, port, user, password, db):
    return pymysql.connect(host=host, port=port, user=user, password=password, db=db, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


def fetch_src(conn):
    # actual source column names in nf21: see inspect_empresas_columns.py
    cols = ['id','razao_social','fantasia','cnpj','inscricao','email','logo','cep','endereco','numero','complemento','bairro','cidade','uf','telefone','data_cadastro','ativo','ibge','id_user','observacao']
    sql = 'SELECT ' + ','.join(cols) + ' FROM empresas ORDER BY id'
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def id_exists(conn, id_):
    with conn.cursor() as cur:
        cur.execute('SELECT 1 FROM empresas WHERE id=%s', (id_,))
        return cur.fetchone() is not None


def insert_dst(conn, e):
    # Map source columns to destination columns
    cols = ['id','razao_social','nome_fantasia','cnpj','inscricao_estadual','endereco','numero','complemento','bairro','municipio','uf','cep','telefone','email','regime_tributario','is_active','created_at','updated_at','codigo_ibge','user_id','cnae_principal','logo_url','certificado_path','certificado_senha','smtp_server','smtp_port','smtp_user','smtp_password','pais','codigo_pais','ambiente_nfcom']
    placeholders = ','.join(['%s'] * len(cols))
    sql = f"INSERT INTO empresas ({','.join(cols)}) VALUES ({placeholders})"

    # Build values mapping from source row e (source keys from fetch_src)
    values = [
        e.get('id'),
        e.get('razao_social'),
        e.get('fantasia'),
        e.get('cnpj'),
        e.get('inscricao'),
        e.get('endereco'),
        e.get('numero'),
        e.get('complemento'),
        e.get('bairro'),
        e.get('cidade'),
        e.get('uf'),
        e.get('cep'),
        e.get('telefone'),
        e.get('email'),
        None,  # regime_tributario not present in source
        1 if e.get('ativo') else 0,
        e.get('data_cadastro'),
        None,  # updated_at
        e.get('ibge'),
        e.get('id_user'),
        None,  # cnae_principal
        e.get('logo'),
        None,  # certificado_path
        None,  # certificado_senha
        None,  # smtp_server
        None,  # smtp_port
        None,  # smtp_user
        None,  # smtp_password
        'BRASIL',
        '1058',
        'producao',
    ]
    with conn.cursor() as cur:
        cur.execute(sql, values)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=3306)
    parser.add_argument('--user', default='occ')
    parser.add_argument('--password', default='Altavista740')
    args = parser.parse_args()

    src = connect(args.host, args.port, args.user, args.password, 'nf21')
    dst = connect(args.host, args.port, args.user, args.password, 'nfcom')

    try:
        companies = fetch_src(src)
        print(f'Found {len(companies)} empresas in nf21')
        if not companies:
            print('Nothing to migrate')
            return

        dst.begin()
        with dst.cursor() as cur:
            cur.execute('SET FOREIGN_KEY_CHECKS=0')

        inserted = 0
        skipped = 0
        errors = []
        for e in companies:
            eid = e.get('id')
            if id_exists(dst, eid):
                skipped += 1
                errors.append({'id': eid, 'error': 'id_exists_in_destination'})
                continue
            # ensure user_id exists in destination users
            uid = e.get('user_id')
            if uid is not None:
                with dst.cursor() as cur:
                    cur.execute('SELECT 1 FROM users WHERE id=%s', (uid,))
                    if cur.fetchone() is None:
                        errors.append({'id': eid, 'error': f'user_id_{uid}_missing_in_destination'})
                        skipped += 1
                        continue
            try:
                insert_dst(dst, e)
                inserted += 1
            except Exception as ex:
                errors.append({'id': eid, 'error': str(ex)})
                skipped += 1

        # reset auto_increment
        with dst.cursor() as cur:
            cur.execute('SELECT COALESCE(MAX(id), 0) as m FROM empresas')
            m = cur.fetchone().get('m')
            nextv = m + 1
            cur.execute(f'ALTER TABLE empresas AUTO_INCREMENT = {nextv}')
            cur.execute('SET FOREIGN_KEY_CHECKS=1')
        dst.commit()

        print(f'Inserted: {inserted}, Skipped: {skipped}, Errors: {len(errors)}')
        if errors:
            for err in errors:
                print(err)

    finally:
        src.close()
        dst.close()

if __name__ == '__main__':
    main()
