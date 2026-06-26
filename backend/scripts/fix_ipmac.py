import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models.models import ServicoContratado
import re

def main():
    db = SessionLocal()
    try:
        # Find all contracts for Empresa 6 that were set as PPPOE
        contracts = db.query(ServicoContratado).filter(
            ServicoContratado.empresa_id == 6,
            ServicoContratado.metodo_autenticacao == 'PPPOE'
        ).all()

        count_fixed = 0
        for c in contracts:
            # If the password is an IP address or username looks like an IP
            is_ip_mac = False
            if c.pppoe_password and re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', c.pppoe_password.strip()):
                is_ip_mac = True
            elif c.pppoe_username and re.match(r'^\d+\.\d+\.\d+\.\d+\.\d+$', c.pppoe_username.strip()):
                is_ip_mac = True
                
            if is_ip_mac:
                c.metodo_autenticacao = 'IP_MAC'
                # For IP_MAC, Pydantic validation might complain if mac_address is empty but since we just query/commit it's fine for the DB.
                count_fixed += 1

        print(f"Total de contratos PPPOE encontrados: {len(contracts)}")
        print(f"Total que deveriam ser IP_MAC e serão atualizados: {count_fixed}")

        if count_fixed > 0:
            db.commit()
            print("Atualização concluída no banco de dados!")
        else:
            db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    main()
