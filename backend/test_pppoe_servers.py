#!/usr/bin/env python3
"""
Teste para verificar servidores PPPoE no MikroTik
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.mikrotik.controller import MikrotikController
from app.core.security import decrypt_password

def test_pppoe_servers():
    """Testa obtenção de servidores PPPoE"""

    # Configurações do router (ajuste conforme necessário)
    router_ip = "192.168.18.101"  # IP do seu router
    router_user = "admin"
    router_password = "gruta765"  # Senha descriptografada

    print(f"🔍 Testando conexão com router {router_ip}...")

    try:
        mk = MikrotikController(
            host=router_ip,
            username=router_user,
            password=router_password,
            port=8728
        )

        print("✅ Conexão estabelecida")

        # Testar obtenção de servidores PPPoE
        print("\n🔍 Obtendo servidores PPPoE...")
        servers = mk.get_pppoe_servers()

        print(f"📊 Encontrados {len(servers)} servidores PPPoE:")
        for i, server in enumerate(servers):
            print(f"  {i+1}. {server}")

        # Testar status completo
        print("\n🔍 Obtendo status completo...")
        status = mk.get_pppoe_server_status()
        print(f"📊 Status - Servidores: {len(status.get('servers', []))}")
        for i, server in enumerate(status.get('servers', [])):
            print(f"  {i+1}. {server}")

    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pppoe_servers()