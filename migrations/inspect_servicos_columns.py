import pymysql

params = dict(host='localhost', user='occ', password='Altavista740', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
for db in ('nf21','nfcom'):
    conn = pymysql.connect(db=db, **params)
    try:
        with conn.cursor() as cur:
            cur.execute('SHOW COLUMNS FROM servicos')
            cols = cur.fetchall()
            print('DB:', db)
            for c in cols:
                print(' ', c['Field'], c['Type'])
            print()
    finally:
        conn.close()
