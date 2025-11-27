#!/usr/bin/env python3
"""
Verificar todas as interfaces e configurações para encontrar PPPoE
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.mikrotik.controller import MikrotikController

def check_all_interfaces():
    """Verificar todas as interfaces em detalhes"""

    router_ip = "192.168.18.101"
    router_user = "admin"
    router_password = "gruta765"

    print(f"🔍 Verificando todas as interfaces no router {router_ip}...")

    try:
        mk = MikrotikController(
            host=router_ip,
            username=router_user,
            password=router_password,
            port=8728
        )

        print("✅ Conexão estabelecida")

        # Obter todas as interfaces
        print("\n🔍 Obtendo todas as interfaces...")
        if mk._librouteros_api:
            interfaces = list(mk._librouteros_api.path('interface').select())
            print(f"📊 Total de interfaces: {len(interfaces)}")

            for i, iface in enumerate(interfaces):
                name = iface.get('name', 'N/A')
                tipo = iface.get('type', 'N/A')
                print(f"\n   {i+1}. Interface: {name}")
                print(f"      Tipo: {tipo}")

                # Mostrar todas as propriedades da interface
                for key, value in iface.items():
                    if key not in ['name', 'type']:  # Já mostramos esses
                        print(f"      {key}: {value}")

                # Verificar se é PPPoE de alguma forma
                if 'pppoe' in name.lower() or 'pppoe' in tipo.lower():
                    print(f"      🎯 POSSÍVEL PPPoE ENCONTRADO!")
                elif tipo in ['pppoe-server', 'pppoe-client', 'pppoe-in', 'pppoe-out']:
                    print(f"      🎯 PPPoE DEFINITIVO ENCONTRADO!")
        else:
            print("❌ _librouteros_api não disponível")

        # Verificar se há configurações especiais
        print("\n🔍 Verificando configurações especiais...")

        # Tentar comandos que podem existir no RouterOS 6.x
        special_commands = [
            '/interface/pppoe-server/print',
            '/interface/pppoe/print',
            '/ppp/print',
            '/ppp/profile/print',
            '/ip/pool/print',
        ]

        for cmd in special_commands:
            try:
                print(f"\n🔍 Comando: {cmd}")
                if mk._librouteros_api:
                    result = list(mk._librouteros_api.rawCmd(cmd))
                    print(f"   📊 Resultados: {len(result)}")
                    for item in result:
                        print(f"      - {item}")
                else:
                    print("   ❌ API não disponível")
            except Exception as e:
                print(f"   ❌ Erro: {str(e)[:100]}...")

    except Exception as e:
        print(f"❌ Erro geral: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_all_interfaces()