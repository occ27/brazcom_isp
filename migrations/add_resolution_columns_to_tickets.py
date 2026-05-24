import sys
import os

# Adicionar o diretório pai ao path para importar as configurações
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.core.config import settings
from sqlalchemy import create_engine, text

def run_migration():
    print(f"Conectando ao banco de dados: {settings.DATABASE_URL}")
    engine = create_engine(settings.DATABASE_URL)
    
    columns_to_add = [
        ("foto_onu_serial", "VARCHAR(500)"),
        ("foto_equipamentos", "VARCHAR(500)"),
        ("foto_velocidade", "VARCHAR(500)"),
        ("foto_cto", "VARCHAR(500)"),
        ("splitter_cto", "VARCHAR(100)"),
        ("material_utilizado", "TEXT"),
        ("problema_encontrado", "TEXT")
    ]
    
    with engine.connect() as conn:
        print("Adicionando novas colunas à tabela tickets...")
        for col_name, col_type in columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE tickets ADD COLUMN {col_name} {col_type}"))
                print(f"Coluna {col_name} adicionada com sucesso.")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    print(f"Coluna {col_name} já existe.")
                else:
                    print(f"Erro ao adicionar coluna {col_name}: {e}")
        
        conn.commit()
    print("\nMigração concluída com sucesso!")

if __name__ == "__main__":
    run_migration()
