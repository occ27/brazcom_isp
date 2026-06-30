from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine("mysql+pymysql://occ:Altavista740@localhost:3306/brazcom_db")
Session = sessionmaker(bind=engine)
session = Session()

next_seq = 81366
session.execute(text(f"UPDATE bank_accounts SET nosso_numero_sequence = {next_seq} WHERE id = 6"))
session.execute(text(f"UPDATE receivables SET nosso_numero = '{next_seq}', status = 'PENDING', registro_result = NULL WHERE id = 161305"))
session.commit()
print("Updated to 81366")
