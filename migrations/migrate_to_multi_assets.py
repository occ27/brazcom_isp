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
        print("Criando tabela ativos_contrato...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ativos_contrato (
                id INT AUTO_INCREMENT PRIMARY KEY,
                contrato_id INT NOT NULL,
                tipo_equipamento VARCHAR(50) NOT NULL,
                modelo VARCHAR(100),
                patrimonio VARCHAR(50),
                serial_number VARCHAR(100),
                login_acesso VARCHAR(100),
                senha_acesso VARCHAR(100),
                is_comodato BOOLEAN DEFAULT TRUE,
                observacoes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                CONSTRAINT fk_contrato_ativo FOREIGN KEY (contrato_id) 
                    REFERENCES servicos_contratados(id) ON DELETE CASCADE
            )
        """))
        
        print("Removendo colunas antigas de servicos_contratados (limpeza do modelo antigo)...")
        columns_to_drop = [
            "tipo_equipamento",
            "modelo_equipamento",
            "patrimonio_equipamento",
            "is_comodato",
            "observacoes_instalacao"
        ]
        
        for col in columns_to_drop:
            try:
                conn.execute(text(f"ALTER TABLE servicos_contratados DROP COLUMN {col}"))
                print(f"Coluna {col} removida.")
            except Exception as e:
                print(f"Aviso: Não foi possível remover a coluna {col} (provavelmente já removida ou inexistente).")
        
        conn.commit()
    print("\nMigração para novo modelo de Ativos concluída com sucesso!")

if __name__ == "__main__":
    run_migration()
