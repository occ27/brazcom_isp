#!/usr/bin/env python3
"""
Investigação completa de servidores PPPoE no MikroTik
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.mikrotik.controller import MikrotikController

def deep_pppoe_investigation():
    """Investigação profunda de configurações PPPoE"""

    router_ip = "192.168.18.101"
    router_user = "admin"
    router_password = "gruta765"

    print(f"🔍 Investigação profunda de PPPoE no router {router_ip}...")

    try:
        mk = MikrotikController(
            host=router_ip,
            username=router_user,
            password=router_password,
            port=8728
        )

        print("✅ Conexão estabelecida")

        # Verificar status das bibliotecas
        status = mk.get_connection_status()
        print(f"📊 Bibliotecas ativas: routeros_api={status['routeros_api']}, librouteros={status['librouteros']}")

        # Mas vamos testar se conseguimos usar as APIs mesmo assim
        print(f"📊 _api disponível: {mk._api is not None}")
        print(f"📊 _librouteros_api disponível: {mk._librouteros_api is not None}")

        # Testar o método que funciona
        print("\n🔍 Testando get_pppoe_server_status()...")
        pppoe_status = mk.get_pppoe_server_status()
        print(f"   📊 Status obtido com sucesso!")
        print(f"   - Profiles: {len(pppoe_status.get('profiles', []))}")
        print(f"   - Servers: {len(pppoe_status.get('servers', []))}")
        print(f"   - Interfaces: {len(pppoe_status.get('interfaces', []))}")

        # Mostrar detalhes dos servers encontrados pelo método que funciona
        servers = pppoe_status.get('servers', [])
        if servers:
            print("   🎯 SERVIDORES PPPoE ENCONTRADOS:")
            for server in servers:
                print(f"      - {server}")
        else:
            print("   ❌ Nenhum servidor encontrado pelo método get_pppoe_server_status")
        print("\n🔍 1. Verificando interfaces PPPoE...")
        try:
            if mk._api:
                interfaces = mk._api.get_resource('interface').get()
                pppoe_interfaces = [i for i in interfaces if 'pppoe' in i.get('type', '').lower() or 'pppoe' in i.get('name', '').lower()]
                print(f"   📊 Interfaces PPPoE encontradas: {len(pppoe_interfaces)}")
                for iface in pppoe_interfaces:
                    print(f"   - {iface}")
            else:
                print("   ❌ _api não disponível")
        except Exception as e:
            print(f"   ❌ Erro: {str(e)}")

        # 2. Verificar configurações PPP
        print("\n🔍 2. Verificando configurações PPP...")
        try:
            if mk._api:
                ppp_configs = mk._api.get_resource('ppp').get()
                print(f"   📊 Configurações PPP: {len(ppp_configs)}")
                for config in ppp_configs:
                    print(f"   - {config}")
        except Exception as e:
            print(f"   ❌ Erro: {str(e)}")

        # 3. Tentar todos os caminhos possíveis para servidores PPPoE
        print("\n🔍 3. Testando todos os caminhos possíveis para servidores PPPoE...")
        possible_paths = [
            'interface/pppoe-server',
            'ppp/pppoe-server',
            'ppp/server',
            'interface/pppoe',
            'ppp/pppoe',
            'pppoe-server',
            'pppoe/server',
        ]

        for path in possible_paths:
            try:
                print(f"   🔍 Testando: {path}")
                if mk._api:
                    resource = mk._api.get_resource(path)
                    items = resource.get()
                    print(f"      📊 Encontrados: {len(items)} itens")
                    if items:
                        for item in items:
                            print(f"         - {item}")
                else:
                    print("      ❌ _api não disponível")
            except Exception as e:
                print(f"      ❌ Erro: {str(e)[:100]}...")

        # 4. Verificar se há algum servidor através de comandos raw
        print("\n🔍 4. Testando comandos raw do RouterOS...")
        raw_commands = [
            '/interface/pppoe-server/print',
            '/ppp/pppoe-server/print',
            '/ppp/server/print',
            '/interface/print where type=pppoe-server',
            '/interface/print where type=pppoe',
        ]

        if mk._librouteros_api:
            for cmd in raw_commands:
                try:
                    print(f"   🔍 Comando: {cmd}")
                    result = list(mk._librouteros_api.rawCmd(cmd))
                    print(f"      📊 Resultados: {len(result)}")
                    for item in result[:2]:  # Mostrar apenas os primeiros 2
                        print(f"         - {item}")
                except Exception as e:
                    print(f"      ❌ Erro: {str(e)[:100]}...")
        else:
            print("   ❌ _librouteros_api não disponível")

        # 5. Verificar se o servidor PPPoE está configurado como interface
        print("\n🔍 5. Verificando se PPPoE está configurado como interface...")
        try:
            if mk._api:
                all_interfaces = mk._api.get_resource('interface').get()
                print(f"   📊 Total de interfaces: {len(all_interfaces)}")
                for iface in all_interfaces:
                    name = iface.get('name', '')
                    tipo = iface.get('type', '')
                    if 'pppoe' in tipo.lower() or 'pppoe' in name.lower():
                        print(f"   🔍 POSSÍVEL PPPoE: {iface}")
                    elif tipo in ['pppoe-server', 'pppoe-client']:
                        print(f"   🎯 PPPoE ENCONTRADO: {iface}")
        except Exception as e:
            print(f"   ❌ Erro: {str(e)}")

    except Exception as e:
        print(f"❌ Erro geral: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deep_pppoe_investigation()