import pymysql
params = dict(host='localhost', user='occ', password='Altavista740', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
conn = pymysql.connect(db='nf21', **params)
try:
    with conn.cursor() as cur:
        cur.execute('SELECT * FROM clientes WHERE id=1')
        print(cur.fetchone())
finally:
    conn.close()
