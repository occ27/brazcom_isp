import pymysql

params = dict(host='localhost', user='occ', password='Altavista740', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
conn = pymysql.connect(db='brazcom_db', **params)
try:
    with conn.cursor() as cur:
        cur.execute('SELECT id, nome_razao_social, empresa_id FROM clientes WHERE empresa_id IS NOT NULL LIMIT 5')
        clientes = cur.fetchall()
        print(f'Encontrados {len(clientes)} clientes com empresa_id:')
        for cliente in clientes:
            print(f'Cliente ID: {cliente["id"]}, Nome: {cliente["nome_razao_social"]}, Empresa ID: {cliente["empresa_id"]}')
finally:
    conn.close()