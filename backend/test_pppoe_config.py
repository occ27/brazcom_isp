#!/usr/bin/env python3
"""
Verificar se há alguma configuração PPPoE no router
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.mikrotik.controller import MikrotikController

def check_pppoe_config():
    """Verifica se há alguma configuração PPPoE no router"""

    router_ip = "192.168.18.101"
    router_user = "admin"
    router_password = "gruta765"

    print(f"🔍 Verificando configurações PPPoE no router {router_ip}...")

    try:
        mk = MikrotikController(
            host=router_ip,
            username=router_user,
            password=router_password,
            port=8728
        )

        print("✅ Conexão estabelecida")

        # Verificar todas as interfaces
        print("\n🔍 Verificando todas as interfaces...")
        try:
            interfaces = mk._api.get_resource('interface').get()
            print(f"📊 Total de interfaces: {len(interfaces)}")
            for iface in interfaces:
                name = iface.get('name', '')
                tipo = iface.get('type', '')
                print(f"  - {name}: {tipo}")
                if 'pppoe' in tipo.lower() or 'pppoe' in name.lower():
                    print(f"    🔍 POSSÍVEL PPPoE: {iface}")
        except Exception as e:
            print(f"❌ Erro ao obter interfaces: {str(e)}")

        # Verificar configurações PPP
        print("\n🔍 Verificando configurações PPP...")
        try:
            ppp_configs = mk._api.get_resource('ppp').get()
            print(f"📊 Configurações PPP: {len(ppp_configs)}")
            for config in ppp_configs:
                print(f"  - {config}")
        except Exception as e:
            print(f"❌ Erro ao obter configurações PPP: {str(e)}")

        # Verificar se há algum secret PPPoE
        print("\n🔍 Verificando secrets PPP...")
        try:
            secrets = mk._api.get_resource('ppp/secret').get()
            print(f"📊 Secrets PPP: {len(secrets)}")
            for secret in secrets[:3]:  # Mostrar apenas os primeiros 3
                name = secret.get('name', '')
                service = secret.get('service', '')
                print(f"  - {name}: {service}")
        except Exception as e:
            print(f"❌ Erro ao obter secrets PPP: {str(e)}")

        # Verificar IP pools
        print("\n🔍 Verificando IP pools...")
        try:
            pools = mk._api.get_resource('ip/pool').get()
            print(f"📊 IP Pools: {len(pools)}")
            for pool in pools:
                name = pool.get('name', '')
                ranges = pool.get('ranges', '')
                print(f"  - {name}: {ranges}")
        except Exception as e:
            print(f"❌ Erro ao obter IP pools: {str(e)}")

    except Exception as e:
        print(f"❌ Erro geral: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_pppoe_config()