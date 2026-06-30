from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine("mysql+pymysql://occ:Altavista740@localhost:3306/brazcom_db")
Session = sessionmaker(bind=engine)
session = Session()

try:
    # Just set it to 161306
    next_seq = 161306
    session.execute(text(f"UPDATE bank_accounts SET nosso_numero_sequence = {next_seq} WHERE id = 6"))
    session.commit()
    print(f"Updated bank_account 6 sequence to {next_seq}")
    
    # Also fix the failed receivable
    session.execute(text(f"UPDATE receivables SET nosso_numero = '{next_seq}', status = 'PENDING', registro_result = NULL WHERE id = 161305"))
    session.commit()
    print(f"Fixed receivable 161305 to use new sequence {next_seq}")
except Exception as e:
    print(e)
