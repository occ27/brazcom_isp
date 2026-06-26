import sys
import os
import getpass
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models.models import BankAccount
from app.core.security import encrypt_sensitive_data

def main():
    db = SessionLocal()
    try:
        ba = db.query(BankAccount).filter(BankAccount.id == 6).first()
        if not ba:
            print("BankAccount ID 6 não encontrado!")
            return

        print("=== Atualizar Credenciais do Banco do Brasil ===")
        print(f"Conta: {ba.name} - Agência: {ba.agencia} - Conta: {ba.conta}")
        print("-------------------------------------------------")
        
        client_id = input(f"Client ID [{ba.bb_client_id}]: ").strip()
        app_key = input(f"App Key [{ba.bb_app_key}]: ").strip()
        client_secret = getpass.getpass("Client Secret (oculto): ").strip()
        
        if client_id:
            ba.bb_client_id = client_id
        if app_key:
            ba.bb_app_key = app_key
        if client_secret:
            ba.bb_client_secret = encrypt_sensitive_data(client_secret)
            
        db.commit()
        print("-------------------------------------------------")
        print("Credenciais atualizadas e criptografadas com sucesso!")
    except Exception as e:
        db.rollback()
        print(f"Erro ao atualizar: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    main()
