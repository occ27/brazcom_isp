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

def test_ppp_profiles():
    """Testa obtenção de perfis PPP e verificação de remote-address"""

    # Configurações do router (ajuste conforme necessário)
    router_ip = "192.168.18.101"  # IP do seu router
    router_user = "admin"
    router_password = "gruta765"  # Senha descriptografada

    print(f"🔍 Testando perfis PPP no router {router_ip}...")

    try:
        mk = MikrotikController(
            host=router_ip,
            username=router_user,
            password=router_password,
            port=8728
        )

        print("✅ Conexão estabelecida")

        # Testar obtenção de perfis PPP
        print("\n🔍 Obtendo perfis PPP...")
        profiles = mk.get_ppp_profiles()

        print(f"📊 Encontrados {len(profiles)} perfis PPP:")
        for i, profile in enumerate(profiles):
            name = profile.get('name', 'N/A')
            local_addr = profile.get('local-address', 'N/A')
            remote_addr = profile.get('remote-address', 'N/A')
            rate_limit = profile.get('rate-limit', 'N/A')
            
            print(f"  {i+1}. Nome: {name}")
            print(f"      Local Address: {local_addr}")
            print(f"      Remote Address: {remote_addr}")
            print(f"      Rate Limit: {rate_limit}")
            print()

    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "profiles":
        test_ppp_profiles()
    else:
        test_pppoe_servers()