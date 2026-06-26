"""
Script para preencher as coordenadas GPS dos contratos da empresa 5 em produção.
Busca os endereços na API do Nominatim (OpenStreetMap), seguindo a mesma lógica do frontend.
Respeita o limite de requisições do Nominatim (1 req/s).
"""
import sys
import os
import time
import requests
import traceback

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ─── Banco de Produção ────────────────────────────────────────────────────────
DB_URL = "mysql+pymysql://occ:Altavista740@192.168.18.4:3315/brazcom_db"
EMPRESA_ID = 6
# ─────────────────────────────────────────────────────────────────────────────

def get_coordinates(queries):
    """
    Tenta as queries no Nominatim até encontrar uma coordenada.
    """
    headers = {
        'Accept-Language': 'pt-BR,pt;q=0.9',
        'User-Agent': 'BrazcomISP-ImportScript/1.0 (orlando@brazcom.com.br)'
    }
    
    for query in queries:
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={requests.utils.quote(query)}&limit=1"
        try:
            # Respeitar limite do Nominatim de 1 req/segundo
            time.sleep(1.2)
            
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    return f"{data[0]['lat']},{data[0]['lon']}"
        except Exception as e:
            print(f"    Erro na API (query: {query}): {e}")
    return None


def main():
    engine = create_engine(DB_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()

    print(f"🔗 Conectado: {DB_URL.split('@')[1]}")
    print(f"🏢 Buscando contratos sem GPS da empresa {EMPRESA_ID}...")

    # Buscar todos os contratos da empresa 5 sem coordenadas e que possuam um endereço vinculado
    query = text("""
        SELECT 
            sc.id, 
            e.endereco, 
            e.numero, 
            e.bairro, 
            e.municipio, 
            e.uf
        FROM servicos_contratados sc
        JOIN empresa_cliente_enderecos e ON sc.endereco_id = e.id
        WHERE sc.empresa_id = :empresa_id 
          AND (sc.coordenadas_gps IS NULL OR sc.coordenadas_gps = '')
    """)
    
    result = db.execute(query, {'empresa_id': EMPRESA_ID}).fetchall()
    total = len(result)
    print(f"Encontrados {total} contratos para processar.\n")
    
    updated = 0
    not_found = 0
    errors = 0

    for i, row in enumerate(result, 1):
        contrato_id = row[0]
        endereco = row[1] or ''
        numero = row[2] or ''
        bairro = row[3] or ''
        municipio = row[4] or ''
        uf = row[5] or ''
        
        # Ignorar se faltar município (mínimo necessário para uma busca razoável)
        if not municipio:
            not_found += 1
            continue

        # Montar as 3 queries de fallback (igual ao frontend)
        queries = []
        if bairro:
            queries.append(f"{endereco}, {numero}, {bairro}, {municipio} - {uf}, Brasil")
        queries.append(f"{endereco}, {numero}, {municipio} - {uf}, Brasil")
        queries.append(f"{endereco}, {municipio} - {uf}, Brasil")
        
        print(f"[{i}/{total}] Buscando ID {contrato_id}: {queries[0]}")
        
        coords = get_coordinates(queries)
        
        if coords:
            try:
                db.execute(text(
                    "UPDATE servicos_contratados SET coordenadas_gps = :coords WHERE id = :id"
                ), {'coords': coords, 'id': contrato_id})
                db.commit()
                updated += 1
                print(f"  ✅ Encontrado: {coords}")
            except Exception as e:
                db.rollback()
                errors += 1
                print(f"  ❌ Erro ao salvar: {e}")
        else:
            not_found += 1
            print("  ⚠️  Não encontrado")

    db.close()
    
    print("\n" + "="*50)
    print("Resumo da Busca GPS:")
    print(f"✅ Atualizados com sucesso: {updated}")
    print(f"⚠️  Não encontrados na API: {not_found}")
    print(f"❌ Erros no DB:             {errors}")
    print("="*50)


if __name__ == "__main__":
    main()
