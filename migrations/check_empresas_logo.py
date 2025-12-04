import pymysql

params = dict(host='localhost', user='occ', password='Altavista740', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
conn = pymysql.connect(db='brazcom_db', **params)
try:
    with conn.cursor() as cur:
        cur.execute('SELECT id, razao_social, nome_fantasia, logo_url FROM empresas WHERE logo_url IS NOT NULL AND logo_url != ""')
        empresas = cur.fetchall()
        print(f'Encontradas {len(empresas)} empresas com logo:')
        for empresa in empresas:
            print(f'ID: {empresa["id"]}, Razão: {empresa["razao_social"]}, Logo: {empresa["logo_url"]}')

        if len(empresas) == 0:
            print('Nenhuma empresa tem logo definida.')
            cur.execute('SELECT COUNT(*) as total FROM empresas')
            total = cur.fetchone()['total']
            print(f'Total de empresas: {total}')
finally:
    conn.close()