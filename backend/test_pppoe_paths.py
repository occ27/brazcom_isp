#!/usr/bin/env python3
"""
Teste detalhado para descobrir onde estão os servidores PPPoE no MikroTik
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.mikrotik.controller import MikrotikController

def test_pppoe_paths():
    """Testa diferentes caminhos da API para encontrar servidores PPPoE"""

    # Configurações do router
    router_ip = "192.168.18.101"
    router_user = "admin"
    router_password = "gruta765"

    print(f"🔍 Testando caminhos da API no router {router_ip}...")

    try:
        mk = MikrotikController(
            host=router_ip,
            username=router_user,
            password=router_password,
            port=8728
        )

        print("✅ Conexão estabelecida")

        # Testar diferentes caminhos
        paths_to_test = [
            'interface/pppoe-server',
            'ppp/pppoe-server',
            'interface/pppoe',
            'ppp/pppoe',
            'ppp/server',
            'interface',
        ]

        for path in paths_to_test:
            try:
                print(f"\n🔍 Testando caminho: {path}")
                resource = mk._api.get_resource(path)
                items = resource.get()
                print(f"  📊 Encontrados {len(items)} itens:")
                for i, item in enumerate(items[:3]):  # Mostrar apenas os primeiros 3
                    print(f"    {i+1}. {item}")
            except Exception as e:
                print(f"  ❌ Erro no caminho {path}: {str(e)[:100]}...")

        # Testar usando librouteros diretamente
        print("\n🔍 Testando com librouteros diretamente...")
        try:
            # Verificar interfaces PPPoE
            interfaces = list(mk._librouteros_api.path('interface').select())
            pppoe_interfaces = [i for i in interfaces if 'pppoe' in i.get('name', '').lower() or 'pppoe' in i.get('type', '').lower()]
            print(f"📊 Interfaces PPPoE encontradas: {len(pppoe_interfaces)}")
            for iface in pppoe_interfaces:
                print(f"  - {iface}")

            # Verificar configurações PPP
            try:
                ppp_configs = list(mk._librouteros_api.path('ppp').select())
                print(f"\n📊 Configurações PPP: {len(ppp_configs)}")
                for config in ppp_configs[:3]:
                    print(f"  - {config}")
            except Exception as e:
                print(f"❌ Erro ao obter configurações PPP: {str(e)[:100]}...")

        except Exception as e:
            print(f"❌ Erro com librouteros: {str(e)[:100]}...")

    except Exception as e:
        print(f"❌ Erro geral: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pppoe_paths()