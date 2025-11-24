import pymysql

params = dict(host='localhost', user='occ', password='Altavista740', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

checks = [
    ('nf21', 'nf21-mestre-agenda'),
    ('nf21', 'nf21-item-agenda'),
    ('nfcom', 'servicos_contratados'),
]

for db, table in checks:
    conn = pymysql.connect(db=db, **params)
    try:
        with conn.cursor() as cur:
            cur.execute(f"SHOW COLUMNS FROM `{table}`")
            cols = cur.fetchall()
            print('DB:', db, 'TABLE:', table)
            for c in cols:
                print(' ', c['Field'], c['Type'])
            print()
    finally:
        conn.close()
