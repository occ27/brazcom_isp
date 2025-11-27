#!/usr/bin/env python3
"""
Teste de comandos Winbox para investigar configuração PPPoE
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.mikrotik.controller import MikrotikController

def test_winbox_commands():
    """Testa comandos Winbox para investigar PPPoE"""

    router_ip = "192.168.18.101"
    router_user = "admin"
    router_password = "gruta765"

    print(f"🔍 Testando comandos Winbox no router {router_ip}...")

    try:
        mk = MikrotikController(
            host=router_ip,
            username=router_user,
            password=router_password,
            port=8728
        )

        print("✅ Conexão estabelecida")

        # Testar comandos Winbox diretamente
        commands_to_test = [
            '/interface/pppoe-server/server/print',
            '/interface/pppoe-server/print',
            '/interface/print where type=pppoe-server',
            '/ppp/pppoe-server/print',
            '/ppp/server/print',
            '/interface/pppoe/print',
            '/ppp/profile/print',
        ]

        for cmd in commands_to_test:
            try:
                print(f"\n🔍 Comando: {cmd}")
                result = list(mk._librouteros_api.rawCmd(cmd))
                print(f"  📊 Resultados: {len(result)}")
                for item in result[:3]:  # Mostrar apenas os primeiros 3
                    print(f"    - {item}")
            except Exception as e:
                print(f"  ❌ Erro: {str(e)[:100]}...")

        # Verificar interfaces disponíveis
        print("\n🔍 Interfaces disponíveis:")
        try:
            interfaces = list(mk._librouteros_api.path('interface').select())
            for iface in interfaces:
                name = iface.get('name', '')
                tipo = iface.get('type', '')
                if 'pppoe' in name.lower() or 'pppoe' in tipo.lower():
                    print(f"  🔍 PPPoE Interface: {name} ({tipo}) - {iface}")
                elif 'ether' in name.lower():
                    print(f"  🌐 Ethernet: {name} ({tipo})")
        except Exception as e:
            print(f"❌ Erro ao listar interfaces: {str(e)[:100]}...")

    except Exception as e:
        print(f"❌ Erro geral: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_winbox_commands()