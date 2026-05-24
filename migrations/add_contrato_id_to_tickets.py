import sys
import os

# Adicionar o diretório pai ao path para importar as configurações
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.core.config import settings
from sqlalchemy import create_engine, text

def run_migration():
    print(f"Conectando ao banco de dados: {settings.DATABASE_URL}")
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("Adicionando coluna contrato_id à tabela tickets...")
        try:
            conn.execute(text("ALTER TABLE tickets ADD COLUMN contrato_id INT NULL"))
            print("Coluna contrato_id adicionada com sucesso.")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("Coluna contrato_id já existe.")
            else:
                print(f"Erro ao adicionar coluna contrato_id: {e}")
                
        print("Adicionando foreign key constraint para contrato_id...")
        try:
            conn.execute(text("ALTER TABLE tickets ADD CONSTRAINT fk_tickets_contrato FOREIGN KEY (contrato_id) REFERENCES servicos_contratados(id) ON DELETE SET NULL"))
            print("Foreign key constraint fk_tickets_contrato adicionada com sucesso.")
        except Exception as e:
            if "Duplicate key name" in str(e) or "already exists" in str(e) or "Duplicate foreign key constraint" in str(e):
                print("Constraint fk_tickets_contrato já existe.")
            else:
                print(f"Erro ao adicionar constraint fk_tickets_contrato: {e}")
        
        conn.commit()
    print("\nMigração concluída com sucesso!")

if __name__ == "__main__":
    run_migration()
