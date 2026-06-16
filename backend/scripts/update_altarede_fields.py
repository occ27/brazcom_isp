"""
Script de UPDATE para preencher campos faltantes nos contratos da empresa 5 em produção.
Atualiza: numero_contrato, d_contrato_ini, data_instalacao, data_inicio_cobranca

Usa o assigned_ip como chave de match (único por contrato no sistema IP_MAC).
NÃO toca em nenhuma outra empresa.
"""
import sys
import os
import xml.etree.ElementTree as ET
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ─── Banco de Produção ────────────────────────────────────────────────────────
DB_URL = "mysql+pymysql://occ:Altavista740@192.168.18.4:3315/brazcom_db"
EMPRESA_ID = 5
XLS_PATH = "/Users/orlando/python/FastAPI/brazcom_isp/Alpha/Logins.xls"
NAMESPACES = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
# ─────────────────────────────────────────────────────────────────────────────


def normalize_cod(cod: str) -> str:
    """Remove separadores de milhar (ponto) usados pelo Altarede: '1.152' → '1152'"""
    if not cod:
        return cod
    cleaned = cod.strip()
    parts = cleaned.split('.')
    if len(parts) > 1 and all(p.isdigit() for p in parts):
        return ''.join(parts)
    return cleaned


def parse_xml_spreadsheet(file_path):
    print(f"Lendo {file_path}...")
    tree = ET.parse(file_path)
    root = tree.getroot()
    for worksheet in root.findall('ss:Worksheet', NAMESPACES):
        table = worksheet.find('ss:Table', NAMESPACES)
        if table is None:
            continue
        rows = table.findall('ss:Row', NAMESPACES)
        if not rows:
            continue
        header_cells = rows[0].findall('ss:Cell', NAMESPACES)
        headers = []
        for cell in header_cells:
            data = cell.find('ss:Data', NAMESPACES)
            headers.append(data.text if data is not None else "")
        for row in rows[1:]:
            cells = row.findall('ss:Cell', NAMESPACES)
            row_data = {}
            current_col = 0
            for cell in cells:
                index_attr = cell.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
                if index_attr:
                    current_col = int(index_attr) - 1
                data = cell.find('ss:Data', NAMESPACES)
                val = data.text if data is not None and data.text else ""
                if current_col < len(headers):
                    row_data[headers[current_col]] = val
                current_col += 1
            yield row_data


def main():
    engine = create_engine(DB_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()

    print(f"🔗 Conectado: {DB_URL.split('@')[1]}")
    print(f"🏢 Empresa alvo: {EMPRESA_ID}")
    print()

    updated = 0
    skipped_no_ip = 0
    skipped_not_found = 0
    skipped_already_ok = 0

    for row in parse_xml_spreadsheet(XLS_PATH):
        assigned_ip = row.get('IP', '').strip()
        if not assigned_ip:
            skipped_no_ip += 1
            continue

        codigo_legado = normalize_cod(row.get('CODIGO', '').strip()) or None

        data_inst = None
        data_inst_str = row.get('DATA_INSTALACAO', '').strip()
        if data_inst_str and data_inst_str not in ('0000-00-00', ''):
            try:
                data_inst = datetime.strptime(data_inst_str[:10], '%Y-%m-%d')
            except Exception:
                pass

        # Busca o contrato pelo IP (único por cliente em IP_MAC) + empresa_id = 5
        result = db.execute(text("""
            SELECT id, numero_contrato, d_contrato_ini, data_instalacao, data_inicio_cobranca
            FROM servicos_contratados
            WHERE empresa_id = :empresa_id
              AND assigned_ip = :ip
            LIMIT 1
        """), {'empresa_id': EMPRESA_ID, 'ip': assigned_ip}).fetchone()

        if not result:
            skipped_not_found += 1
            continue

        contrato_id = result[0]
        current_numero = result[1]
        current_ini = result[2]

        # Só atualiza os campos que estão NULL/vazios — não sobrescreve dados preenchidos
        fields_to_update = {}

        if codigo_legado and not current_numero:
            fields_to_update['numero_contrato'] = codigo_legado

        if data_inst and not current_ini:
            fields_to_update['d_contrato_ini'] = data_inst
            if not result[3]:  # data_instalacao
                fields_to_update['data_instalacao'] = data_inst
            if not result[4]:  # data_inicio_cobranca
                fields_to_update['data_inicio_cobranca'] = data_inst

        if not fields_to_update:
            skipped_already_ok += 1
            continue

        # Monta o UPDATE dinamicamente
        set_clauses = ', '.join([f"{k} = :{k}" for k in fields_to_update])
        fields_to_update['contrato_id'] = contrato_id
        db.execute(
            text(f"UPDATE servicos_contratados SET {set_clauses} WHERE id = :contrato_id AND empresa_id = {EMPRESA_ID}"),
            fields_to_update
        )

        updated += 1
        if updated % 200 == 0:
            db.commit()
            print(f"  {updated} contratos atualizados...")

    db.commit()
    db.close()

    print()
    print("=" * 50)
    print(f"✅ Contratos atualizados:        {updated}")
    print(f"⏭  Já estavam preenchidos:       {skipped_already_ok}")
    print(f"⚠️  Sem IP (ignorados):           {skipped_no_ip}")
    print(f"❌ IP não encontrado no banco:    {skipped_not_found}")
    print("=" * 50)


if __name__ == "__main__":
    main()
