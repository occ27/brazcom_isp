import sys
import os

sys.path.append(os.path.abspath("backend"))

from app.core.database import SessionLocal
from app.models.models import Router
from app.core.security import decrypt_password
from app.mikrotik.controller import MikrotikController

def test_proxy():
    db = SessionLocal()
    try:
        router = db.query(Router).filter(Router.is_active == True).first()
        try:
            password = decrypt_password(router.senha)
        except Exception:
            password = router.senha

        mk = MikrotikController(host=router.ip, username=router.usuario, password=password, port=router.porta or 8728)
        mk.connect()
        
        # Teste de sintaxe no Mikrotik:
        scripts = [
            '/ip proxy access add action=deny redirect-to="http://192.168.18.1" comment="T1"',
            '/ip proxy access add action=deny redirect-to="http://192.168.18.1" comment=T2',
            '/ip proxy access add dst-port=80 action=deny redirect-to="http://192.168.18.1" comment="T3"',
        ]
        
        script_resource = mk._api.get_resource('system/script')
        
        for i, cmd in enumerate(scripts):
            name = f"test_{i}"
            try:
                # Remove se existir
                existing = script_resource.get(name=name)
                if existing:
                    script_resource.remove(id=existing[0]['.id'])
                
                # Adiciona
                script_resource.add(name=name, source=cmd)
                
                # Roda via run do librouteros
                res = mk._api.get_resource('/system/script').call('run', **{'.id': name})
                print(f"Comando {i} FUNCIONOU!")
            except Exception as e:
                print(f"Comando {i} FALHOU: {e}")
            finally:
                existing = script_resource.get(name=name)
                if existing:
                    script_resource.remove(id=existing[0]['.id'])
    finally:
        db.close()

if __name__ == "__main__":
    test_proxy()
