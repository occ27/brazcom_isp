#!/usr/bin/env python3
"""
Verificar se PPPoE está configurado nas interfaces ethernet
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.mikrotik.controller import MikrotikController

def check_interface_pppoe_config():
    """Verificar se há configuração PPPoE nas interfaces"""

    router_ip = "192.168.18.101"
    router_user = "admin"
    router_password = "gruta765"

    print(f"🔍 Verificando configuração PPPoE nas interfaces do router {router_ip}...")

    try:
        mk = MikrotikController(
            host=router_ip,
            username=router_user,
            password=router_password,
            port=8728
        )

        print("✅ Conexão estabelecida")

        # Usar a mesma abordagem do get_pppoe_server_status que funciona
        status = mk.get_pppoe_server_status()
        print("📊 Status obtido com sucesso!")

        # Verificar interfaces detalhadamente
        print("\n🔍 Verificando interfaces em detalhes...")
        try:
            if mk._api:
                interfaces = mk._api.get_resource('interface').get()
                print(f"📊 Total de interfaces: {len(interfaces)}")

                for i, iface in enumerate(interfaces):
                    name = iface.get('name', 'N/A')
                    tipo = iface.get('type', 'N/A')
                    print(f"\n   {i+1}. {name} (tipo: {tipo})")

                    # Verificar se há propriedades relacionadas a PPPoE
                    pppoe_related = {}
                    for key, value in iface.items():
                        if 'pppoe' in key.lower() or 'ppp' in key.lower():
                            pppoe_related[key] = value

                    if pppoe_related:
                        print(f"      🎯 PROPRIEDADES PPPoE ENCONTRADAS:")
                        for key, value in pppoe_related.items():
                            print(f"         {key}: {value}")

                    # Verificar se o tipo indica PPPoE
                    if tipo in ['pppoe-server', 'pppoe-client', 'pppoe-in', 'pppoe-out']:
                        print(f"      🎯 TIPO PPPoE ENCONTRADO: {tipo}")

                    # Verificar se há comentários indicando PPPoE
                    comment = iface.get('comment', '')
                    if comment and ('pppoe' in comment.lower() or 'ppp' in comment.lower()):
                        print(f"      💬 COMENTÁRIO PPPoE: {comment}")

            else:
                print("❌ _api não disponível para verificar interfaces")
        except Exception as e:
            print(f"❌ Erro ao verificar interfaces: {str(e)}")

        # Verificar se há alguma configuração PPP especial
        print("\n🔍 Verificando configurações PPP especiais...")
        try:
            if mk._api:
                # Tentar obter configurações PPP
                ppp_resource = mk._api.get_resource('ppp')
                ppp_configs = ppp_resource.get()
                print(f"📊 Configurações PPP: {len(ppp_configs)}")

                for config in ppp_configs:
                    print(f"   - {config}")
                    # Verificar se alguma configuração é relacionada a PPPoE server
                    if 'pppoe' in str(config).lower():
                        print(f"     🎯 CONFIG PPPoE ENCONTRADA: {config}")
        except Exception as e:
            print(f"❌ Erro ao verificar configurações PPP: {str(e)}")

    except Exception as e:
        print(f"❌ Erro geral: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_interface_pppoe_config()