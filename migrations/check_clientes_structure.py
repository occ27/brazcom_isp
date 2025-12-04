import pymysql

params = dict(host='localhost', user='occ', password='Altavista740', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
conn = pymysql.connect(db='brazcom_db', **params)
try:
    with conn.cursor() as cur:
        cur.execute('DESCRIBE clientes')
        columns = cur.fetchall()
        print('Estrutura atual da tabela clientes:')
        for col in columns:
            print(f'  {col["Field"]}: {col["Type"]}')
finally:
    conn.close()