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
        
        script_resource = mk._api.get_resource('system/script')
        url = "http://brazcom.com.br"
        
        scripts = [
            # Teste 1: on-error
            f':do {{ /ip proxy access remove [find comment="T1"] }} on-error={{}}; /ip proxy access add action=deny redirect-to="{url}" comment="T1"',
            # Teste 2: sem action=deny (algumas versoes antigas assumem deny se tem redirect-to)
            f':do {{ /ip proxy access remove [find comment="T2"] }} on-error={{}}; /ip proxy access add redirect-to="{url}" comment="T2"',
            # Teste 3: quebrando linha
            f':do {{ /ip proxy access remove [find comment="T3"] }} on-error={{}}\n/ip proxy access add action=deny redirect-to="{url}" comment="T3"'
        ]
        
        for i, cmd in enumerate(scripts):
            name = f"test_{i}"
            try:
                # Usa API para remover o script se existir (tentativa e erro silencioso)
                for s in script_resource.get():
                    if s.get('name') == name:
                        rid = s.get('.id') or s.get('id')
                        if rid:
                            script_resource.remove(id=rid)
                        
                script_resource.add(name=name, source=cmd)
                mk._api.get_binary_resource('/').call('system/script/run', {'number': name})
                print(f"Comando {i} FUNCIONOU!")
            except Exception as e:
                print(f"Comando {i} FALHOU: {e}")
            finally:
                for s in script_resource.get():
                    rid = s.get('.id') or s.get('id')
                    if rid:
                        script_resource.remove(id=rid)
    finally:
        db.close()

if __name__ == "__main__":
    test_proxy()
