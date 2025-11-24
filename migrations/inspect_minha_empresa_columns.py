import pymysql

params = dict(host='localhost', user='occ', password='Altavista740', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
for db, table in (('nf21','minha_empresa'), ('nfcom','usuario_empresa')):
    conn = pymysql.connect(db=db, **params)
    try:
        with conn.cursor() as cur:
            cur.execute(f'SHOW COLUMNS FROM `{table}`')
            cols = cur.fetchall()
            print('DB:', db, 'TABLE:', table)
            for c in cols:
                print(' ', c['Field'], c['Type'])
            print()
    finally:
        conn.close()
