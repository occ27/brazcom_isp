from sqlalchemy import create_engine, text
from app.core.config import settings

def migrate():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        print("Adicionando colunas de configuração do Mercado Pago à tabela empresas...")
        
        # Adicionar mp_allow_boleto
        try:
            conn.execute(text("ALTER TABLE empresas ADD COLUMN mp_allow_boleto BOOLEAN DEFAULT TRUE"))
            print("Coluna mp_allow_boleto adicionada.")
        except Exception as e:
            print(f"Erro ao adicionar mp_allow_boleto (pode já existir): {e}")

        # Adicionar mp_allow_pix
        try:
            conn.execute(text("ALTER TABLE empresas ADD COLUMN mp_allow_pix BOOLEAN DEFAULT TRUE"))
            print("Coluna mp_allow_pix adicionada.")
        except Exception as e:
            print(f"Erro ao adicionar mp_allow_pix (pode já existir): {e}")

        # Adicionar mp_allow_credit_card
        try:
            conn.execute(text("ALTER TABLE empresas ADD COLUMN mp_allow_credit_card BOOLEAN DEFAULT TRUE"))
            print("Coluna mp_allow_credit_card adicionada.")
        except Exception as e:
            print(f"Erro ao adicionar mp_allow_credit_card (pode já existir): {e}")
            
        conn.commit()
        print("Migração concluída com sucesso!")

if __name__ == "__main__":
    migrate()
