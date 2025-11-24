import pymysql
params = dict(host='localhost', user='occ', password='Altavista740', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
conn = pymysql.connect(db='nfcom', **params)
try:
    with conn.cursor() as cur:
        cur.execute('SHOW CREATE TABLE clientes')
        print(cur.fetchone())
finally:
    conn.close()
