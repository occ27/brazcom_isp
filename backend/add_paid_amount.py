from sqlalchemy import create_engine, text

DATABASE_URL="mysql+pymysql://occ:Altavista740@localhost:3306/brazcom_db"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE receivables ADD COLUMN paid_amount FLOAT DEFAULT NULL AFTER amount;"))
        conn.commit()
        print("Coluna paid_amount adicionada com sucesso!")
    except Exception as e:
        print(f"Erro ao adicionar coluna: {e}")
