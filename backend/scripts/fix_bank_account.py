import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models.models import ServicoContratado

def main():
    db = SessionLocal()
    try:
        contracts = db.query(ServicoContratado).filter(
            ServicoContratado.empresa_id == 6,
        ).all()

        count_fixed = 0
        for c in contracts:
            if c.bank_account_id != 6:
                c.bank_account_id = 6
                count_fixed += 1

        print(f"Total de contratos encontrados: {len(contracts)}")
        print(f"Total atualizados com bank_account_id = 6: {count_fixed}")

        if count_fixed > 0:
            db.commit()
            print("Atualização da conta bancária concluída no banco de dados!")
        else:
            db.rollback()
            print("Nenhum contrato precisou ser atualizado.")
    finally:
        db.close()

if __name__ == '__main__':
    main()
