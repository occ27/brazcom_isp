import sys
import os

sys.path.append(os.path.abspath("backend"))

from app.core.database import SessionLocal
from app.models.models import Router
from app.core.security import decrypt_password
from app.mikrotik.controller import MikrotikController

def test_api():
    db = SessionLocal()
    try:
        router = db.query(Router).filter(Router.is_active == True).first()
        try:
            password = decrypt_password(router.senha)
        except Exception:
            password = router.senha

        mk = MikrotikController(host=router.ip, username=router.usuario, password=password, port=router.porta or 8728)
        mk.connect()
        
        proxy = mk._api.get_resource('ip/proxy/access')
        suspension_url = "http://brazcom.com.br/aviso/final"
        
        # Remove existentes
        for rule in proxy.get():
            if rule.get('comment') == 'TESTE_FINAL':
                rid = rule.get('.id') or rule.get('id')
                if rid: proxy.remove(id=rid)
                
        print("Tentando padrao 1 (Moderno)...")
        try:
            proxy.add(action='deny', **{'redirect-to': suspension_url}, comment='TESTE_FINAL')
            print("Padrao 1 funcionou!")
        except Exception as e1:
            print(f"Padrao 1 falhou: {e1}")
            print("Tentando padrao 2 (Legado)...")
            try:
                proxy.add(action='redirect', **{'action-data': suspension_url}, comment='TESTE_FINAL')
                print("Padrao 2 funcionou!")
            except Exception as e2:
                print(f"Padrao 2 falhou: {e2}")
                
        # Limpa
        for rule in proxy.get():
            if rule.get('comment') == 'TESTE_FINAL':
                rid = rule.get('.id') or rule.get('id')
                if rid: proxy.remove(id=rid)
    finally:
        db.close()

if __name__ == "__main__":
    test_api()
