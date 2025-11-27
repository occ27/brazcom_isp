#!/usr/bin/env python3
"""
Teste simples para verificar servidores PPPoE usando o método existente
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.mikrotik.controller import MikrotikController

def test_existing_method():
    """Testa usando o método get_pppoe_server_status que já existe"""

    router_ip = "192.168.18.101"
    router_user = "admin"
    router_password = "gruta765"

    print(f"🔍 Testando método existente no router {router_ip}...")

    try:
        mk = MikrotikController(
            host=router_ip,
            username=router_user,
            password=router_password,
            port=8728
        )

        print("✅ Conexão estabelecida")

        # Usar o método que já funciona
        status = mk.get_pppoe_server_status()
        print("📊 Status completo:")
        print(f"  - Profiles: {len(status.get('profiles', []))}")
        print(f"  - Servers: {len(status.get('servers', []))}")
        print(f"  - Interfaces: {len(status.get('interfaces', []))}")
        print(f"  - Pools: {len(status.get('pools', []))}")

        # Mostrar detalhes dos servidores
        servers = status.get('servers', [])
        if servers:
            print("\n🔍 Detalhes dos servidores PPPoE:")
            for i, server in enumerate(servers):
                print(f"  {i+1}. {server}")
        else:
            print("\n❌ Nenhum servidor PPPoE encontrado")

        # Mostrar interfaces PPPoE
        interfaces = status.get('interfaces', [])
        if interfaces:
            print("\n🔍 Interfaces PPPoE:")
            for i, iface in enumerate(interfaces):
                print(f"  {i+1}. {iface}")

    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_existing_method()