#!/usr/bin/env python3
"""
Teste para verificar qual biblioteca RouterOS está sendo usada
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.mikrotik.controller import MikrotikController

def test_connection_status():
    """Testa o status da conexão"""

    router_ip = "192.168.18.101"
    router_user = "admin"
    router_password = "gruta765"

    print(f"🔍 Verificando status da conexão no router {router_ip}...")

    try:
        mk = MikrotikController(
            host=router_ip,
            username=router_user,
            password=router_password,
            port=8728
        )

        print("✅ Conexão estabelecida")

        # Verificar status das conexões
        status = mk.get_connection_status()
        print(f"📊 Status das bibliotecas:")
        print(f"  - routeros_api: {status['routeros_api']}")
        print(f"  - librouteros: {status['librouteros']}")

        # Testar get_pppoe_server_status que funciona
        print("\n🔍 Testando get_pppoe_server_status...")
        pppoe_status = mk.get_pppoe_server_status()
        print(f"  - Profiles: {len(pppoe_status.get('profiles', []))}")
        print(f"  - Servers: {len(pppoe_status.get('servers', []))}")
        print(f"  - Interfaces: {len(pppoe_status.get('interfaces', []))}")

        # Mostrar um profile de exemplo
        profiles = pppoe_status.get('profiles', [])
        if profiles:
            print(f"  - Exemplo de profile: {profiles[0]}")

    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_connection_status()