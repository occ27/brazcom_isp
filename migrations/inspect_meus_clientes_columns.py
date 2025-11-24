import pymysql

params = dict(host='localhost', user='occ', password='Altavista740', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
for table in ('meus_clientes','empresa_selecionada'):
    conn = pymysql.connect(db='nf21', **params)
    try:
        with conn.cursor() as cur:
            cur.execute(f'SHOW COLUMNS FROM `{table}`')
            cols = cur.fetchall()
            print('DB: nf21 TABLE:', table)
            for c in cols:
                print(' ', c['Field'], c['Type'])
            print()
    finally:
        conn.close()
