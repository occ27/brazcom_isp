import re
import pymysql
from pathlib import Path


def extract_tablenames(models_dir: Path):
    tablenames = set()
    for p in models_dir.glob('*.py'):
        text = p.read_text(encoding='utf-8')
        for m in re.finditer(r"__tablename__\s*=\s*['\"]([\w_]+)['\"]", text):
            tablenames.add(m.group(1))
    return tablenames


def db_tables(dbname, conn_params):
    conn = pymysql.connect(db=dbname, **conn_params)
    try:
        with conn.cursor() as cur:
            cur.execute('SHOW TABLES')
            rows = cur.fetchall()
            # Each row is like {'Tables_in_nfcom': 'users'}
            tables = set()
            for r in rows:
                # take the first value of the dict
                tables.add(list(r.values())[0])
            return tables
    finally:
        conn.close()


if __name__ == '__main__':
    base = Path(__file__).resolve().parents[1] / 'backend' / 'app' / 'models'
    models_tables = extract_tablenames(base)
    print('Model tables found:', sorted(models_tables))

    conn_params = dict(host='localhost', user='occ', password='Altavista740', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
    db_tables_set = db_tables('nfcom', conn_params)
    print('\nDB tables (nfcom):', sorted(db_tables_set))

    only_in_models = models_tables - db_tables_set
    only_in_db = db_tables_set - models_tables

    print('\nTables only in models (missing in DB):', sorted(only_in_models))
    print('Tables only in DB (no model):', sorted(only_in_db))
