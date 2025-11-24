import pymysql
from datetime import datetime

params = dict(host='localhost', user='occ', password='Altavista740', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
src = pymysql.connect(db='nf21', **params)
dst = pymysql.connect(db='nfcom', **params)
try:
    with src.cursor() as cur:
        cur.execute('SELECT * FROM clientes WHERE id=1')
        c = cur.fetchone()
    empresa_id = None
    with src.cursor() as cur:
        cur.execute('SELECT m.id_empresa FROM meus_clientes mc JOIN minha_empresa m ON mc.id_minha_empresa = m.id WHERE mc.id_cliente=%s LIMIT 1', (1,))
        r = cur.fetchone()
        empresa_id = r.get('id_empresa') if r else None
    print('empresa_id for client 1:', empresa_id)
    cpfcnpj = c.get('cnpj')
    cleaned = cpfcnpj.replace('.','').replace('/','').replace('-','').strip() if cpfcnpj else ''
    tipo = 'JURIDICA' if len(cleaned) > 11 else 'FISICA'
    ind_ie_dest = 'NAO_CONTRIBUINTE'
    values = [
        c.get('id'),
        empresa_id,
        c.get('nome'),
        c.get('cnpj'),
        None,
        tipo,
        ind_ie_dest,
        c.get('inscricao'),
        c.get('email'),
        c.get('telefone'),
        1 if c.get('ativo') else 0,
        c.get('data_cadastro') or datetime.now(),
    ]
    print('Values to insert:', values)
    try:
        with dst.cursor() as cur:
            cur.execute('INSERT INTO clientes (id, empresa_id, nome_razao_social, cpf_cnpj, idOutros, tipo_pessoa, ind_ie_dest, inscricao_estadual, email, telefone, is_active, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', values)
            dst.commit()
            print('Insert OK')
    except Exception as e:
        print('Insert error:', e)
finally:
    src.close(); dst.close()
