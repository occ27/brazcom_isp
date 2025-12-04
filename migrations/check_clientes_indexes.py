import pymysql

params = dict(host='localhost', user='occ', password='Altavista740', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
conn = pymysql.connect(db='brazcom_db', **params)
try:
    with conn.cursor() as cur:
        cur.execute('SHOW INDEX FROM clientes')
        indexes = cur.fetchall()
        print('Índices da tabela clientes:')
        for idx in indexes:
            print(f'  {idx["Key_name"]}: {idx["Column_name"]} (Unique: {idx["Non_unique"] == 0})')
finally:
    conn.close()