from sqlalchemy import create_engine, text
from app.core.config import settings

def fix_payment_urls():
    # Conectar ao banco de dados
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("Buscando recebíveis com URLs incorretas...")
        
        # 1. Corrigir URLs que apontam para localhost:3000
        # Trocando 'http://localhost:3000' por 'https://brazcom.com.br'
        result = conn.execute(text("""
            UPDATE receivables 
            SET payment_url = REPLACE(payment_url, 'http://localhost:3000', 'https://brazcom.com.br')
            WHERE payment_url LIKE '%localhost:3000%'
        """))
        conn.commit()
        print(f"Sucesso! {result.rowcount} URLs de localhost foram corrigidas.")
        
        # 2. Corrigir URLs que podem estar com http em vez de https (opcional, mas recomendado)
        result = conn.execute(text("""
            UPDATE receivables 
            SET payment_url = REPLACE(payment_url, 'http://brazcom.com.br', 'https://brazcom.com.br')
            WHERE payment_url LIKE 'http://brazcom.com.br%'
        """))
        conn.commit()
        print(f"Ajustadas {result.rowcount} URLs de http para https.")

if __name__ == "__main__":
    fix_payment_urls()
