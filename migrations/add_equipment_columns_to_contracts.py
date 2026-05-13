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
        ("tipo_equipamento", "VARCHAR(50)"),
        ("modelo_equipamento", "VARCHAR(100)"),
        ("patrimonio_equipamento", "VARCHAR(50)"),
        ("is_comodato", "BOOLEAN DEFAULT TRUE"),
        ("observacoes_instalacao", "TEXT"),
        ("contrato_anatel_url", "VARCHAR(500)")
    ]
    
    with engine.connect() as conn:
        print("Adicionando novas colunas à tabela servicos_contratados...")
        for col_name, col_type in columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE servicos_contratados ADD COLUMN {col_name} {col_type}"))
                print(f"Coluna {col_name} adicionada com sucesso.")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    print(f"Coluna {col_name} já existe.")
                else:
                    print(f"Erro ao adicionar coluna {col_name}: {e}")
        
        print("\nAtualizando tamanho da coluna assigned_ip para 45 caracteres...")
        try:
            conn.execute(text("ALTER TABLE servicos_contratados MODIFY COLUMN assigned_ip VARCHAR(45)"))
            print("Coluna assigned_ip atualizada com sucesso.")
        except Exception as e:
            print(f"Erro ao atualizar coluna assigned_ip: {e}")
            
        conn.commit()
    print("\nMigração concluída com sucesso!")

if __name__ == "__main__":
    run_migration()
