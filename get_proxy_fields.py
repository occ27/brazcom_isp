import sys
import os

sys.path.append(os.path.abspath("backend"))

from app.core.database import SessionLocal
from app.models.models import Router
from app.core.security import decrypt_password
from app.mikrotik.controller import MikrotikController

def get_fields():
    db = SessionLocal()
    try:
        router = db.query(Router).filter(Router.is_active == True).first()
        try:
            password = decrypt_password(router.senha)
        except Exception:
            password = router.senha

        mk = MikrotikController(host=router.ip, username=router.usuario, password=password, port=router.porta or 8728)
        mk.connect()
        
        # Cria uma regra via script sem "Action data" para podermos ler as propriedades
        script_resource = mk._api.get_resource('system/script')
        name = "test_fields"
        
        # Remove se existir
        for s in script_resource.get():
            rid = s.get('.id') or s.get('id')
            if s.get('name') == name and rid:
                script_resource.remove(id=rid)
                
        # Vamos adicionar uma regra com action=redirect e ler as propriedades que o router retorna
        script_resource.add(name=name, source='/ip proxy access add action=redirect comment="LER_CAMPOS"')
        mk._api.get_binary_resource('/').call('system/script/run', {'number': name})
        
        # Agora lemos a regra via API
        proxy = mk._api.get_resource('ip/proxy/access')
        for rule in proxy.get():
            if rule.get('comment') == 'LER_CAMPOS':
                print("Campos da regra:")
                for k, v in rule.items():
                    print(f"  {k} = {v}")
                
                # limpa
                rid = rule.get('.id') or rule.get('id')
                if rid: proxy.remove(id=rid)
                break
                
        # Limpa o script
        for s in script_resource.get():
            rid = s.get('.id') or s.get('id')
            if s.get('name') == name and rid:
                script_resource.remove(id=rid)
                
    finally:
        db.close()

if __name__ == "__main__":
    get_fields()
