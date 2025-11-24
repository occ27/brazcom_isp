import pymysql

params = dict(host='localhost', user='occ', password='Altavista740', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
conn = pymysql.connect(db='nf21', **params)
try:
    with conn.cursor() as cur:
        cur.execute('SHOW COLUMNS FROM clientes')
        cols = cur.fetchall()
        print('DB: nf21 TABLE: clientes')
        for c in cols:
            print(' ', c['Field'], c['Type'])
finally:
    conn.close()
