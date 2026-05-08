import sys
import os

sys.path.append(os.path.abspath("backend"))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import Router, Empresa
from app.core.security import decrypt_password
from app.mikrotik.controller import MikrotikController

def test_proxy():
    db = SessionLocal()
    try:
        # Pega o router de teste (vamos pegar o ID 4 que você tentou por último, ou 2)
        # Vamos buscar o primeiro ativo
        router = db.query(Router).filter(Router.is_active == True).first()
        if not router:
            print("Nenhum router encontrado.")
            return

        try:
            password = decrypt_password(router.senha)
        except Exception:
            password = router.senha

        print(f"Testando no roteador {router.nome} ({router.ip})...")
        mk = MikrotikController(host=router.ip, username=router.usuario, password=password, port=router.porta or 8728)
        mk.connect()
        
        suspension_url = "http://brazcom.com.br/aviso/teste"
        
        # Tentativa 1: Via API direta
        print("Tentativa 1: API Direta...")
        proxy = mk._api.get_resource('ip/proxy/access')
        try:
            # limpar primeiro
            for rule in proxy.get():
                if rule.get('comment') == 'REDIRECIONAMENTO_TESTE':
                    proxy.remove(id=rule['.id'])
            proxy.add(action='deny', **{'redirect-to': suspension_url}, comment='REDIRECIONAMENTO_TESTE')
            print("API Direta funcionou!")
        except Exception as e:
            print(f"Falha na API Direta: {e}")
            
        # Tentativa 2: Via Script (Como está no código)
        print("Tentativa 2: Via Script...")
        script_resource = mk._api.get_resource('system/script')
        script_name = "test_script"
        script_content = f':local rules [/ip proxy access find comment="REDIRECIONAMENTO_TESTE"]; :if ([:len $rules] > 0) do={{/ip proxy access remove $rules}}; /ip proxy access add action=deny redirect-to="{suspension_url}" comment="REDIRECIONAMENTO_TESTE"'
        
        try:
            existing = script_resource.get(name=script_name)
            if existing:
                script_resource.remove(id=existing[0]['.id'])
            
            script_resource.add(name=script_name, source=script_content)
            print("Script adicionado. Tentando rodar...")
            
            # Formato de run
            try:
                # O que tínhamos no código:
                mk._api.get_binary_resource('/').call('system/script/run', {'number': script_name})
                print("Rodou via get_binary_resource!")
            except Exception as e1:
                print(f"Erro no get_binary_resource: {e1}")
                try:
                    # Alternativa
                    script_resource.call('run', **{'.id': script_name})
                    print("Rodou via .call('run', {'.id': script_name})!")
                except Exception as e2:
                    print(f"Erro na Alternativa: {e2}")
        except Exception as e:
            print(f"Erro ao adicionar/preparar script: {e}")
            
    finally:
        db.close()

if __name__ == "__main__":
    test_proxy()
