from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine("mysql+pymysql://occ:Altavista740@localhost:3306/brazcom_db")
Session = sessionmaker(bind=engine)
session = Session()

next_seq = 81386
session.execute(text(f"UPDATE bank_accounts SET nosso_numero_sequence = {next_seq} WHERE id = 6"))
session.commit()
print("Updated to 81386")
