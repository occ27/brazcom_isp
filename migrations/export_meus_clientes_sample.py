import pymysql
import csv
import os

def main():
    c = pymysql.connect(host='localhost', port=3306, user='occ', password='Altavista740', db='nfcom', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
    cur = c.cursor()
    cur.execute('SELECT * FROM empresa_cliente_enderecos LIMIT 50')
    rows = cur.fetchall()
    keys = list(rows[0].keys()) if rows else []
    fp = os.path.join(os.path.dirname(__file__), 'meus_clientes_enderecos_sample.csv')
    with open(fp, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print('wrote', len(rows), 'to', fp)
    c.close()

if __name__ == '__main__':
    main()
