import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.models import Receivable, BankAccount
from app.services.billing_service import BillingService
from sqlalchemy import desc

engine = create_engine("mysql+pymysql://occ:Altavista740@localhost:3306/brazcom_db")
Session = sessionmaker(bind=engine)
db = Session()

async def main():
    ba = db.query(BankAccount).filter(BankAccount.id == 6).first()
    # Let's pick the latest manual receivable
    recv = db.query(Receivable).filter(Receivable.empresa_id == 6, Receivable.status == 'REGISTRATION_FAILED').order_by(desc(Receivable.id)).first()
    if not recv:
        print("No failed receivable found.")
        return
        
    print(f"Testing with receivable {recv.id}")
    
    # Try testing sequence numbers to see where it stops failing
    for seq in [81385, 82000, 85000, 90000, 100000, 200000]:
        print(f"Testing sequence {seq}...")
        recv.nosso_numero = str(seq)
        db.commit()
        
        success, err = await BillingService._register_bb(db, recv, ba)
        if success:
            print(f"SUCCESS with sequence {seq}!")
            break
        else:
            print(f"FAILED with sequence {seq}: {err}")

asyncio.run(main())
