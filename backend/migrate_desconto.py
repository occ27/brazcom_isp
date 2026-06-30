from sqlalchemy import create_engine, text

engine = create_engine("mysql+pymysql://occ:Altavista740@localhost:3306/brazcom_db")
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE bank_accounts ADD COLUMN desconto_pontualidade_tipo VARCHAR(20) NOT NULL DEFAULT 'VALOR'"))
        print("Added desconto_pontualidade_tipo")
    except Exception as e:
        print(f"desconto_pontualidade_tipo: {e}")
    try:
        conn.execute(text("ALTER TABLE bank_accounts ADD COLUMN desconto_pontualidade_valor FLOAT NOT NULL DEFAULT 0.0"))
        print("Added desconto_pontualidade_valor")
    except Exception as e:
        print(f"desconto_pontualidade_valor: {e}")
    try:
        conn.execute(text("ALTER TABLE bank_accounts ADD COLUMN desconto_pontualidade_dias INT NOT NULL DEFAULT 0"))
        print("Added desconto_pontualidade_dias")
    except Exception as e:
        print(f"desconto_pontualidade_dias: {e}")
    conn.commit()
    print("Done.")
