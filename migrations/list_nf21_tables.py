import pymysql

params = dict(host='localhost', user='occ', password='Altavista740', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
conn = pymysql.connect(db='nf21', **params)
try:
    with conn.cursor() as cur:
        cur.execute('SHOW TABLES')
        rows = cur.fetchall()
        print('Tables in nf21:')
        for r in rows:
            print(' ', list(r.values())[0])
finally:
    conn.close()
