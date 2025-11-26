#!/usr/bin/env python3
"""
Script para explorar comandos disponíveis no RouterOS relacionados a PPPoE
"""

import librouteros

def explore_routeros_commands():
    """Explora comandos disponíveis no RouterOS"""
    try:
        api = librouteros.connect(
            host='192.168.18.101',
            username='admin',
            password='gruta765'
        )

        print("🔍 Explorando comandos disponíveis no RouterOS...")

        # Verificar o que existe em /interface/
        print("\n📂 Explorando /interface/...")
        try:
            # Tentar listar interfaces
            interfaces = tuple(api.path('interface').select())
            print(f"Interfaces encontradas: {len(interfaces)}")
            for iface in interfaces[:3]:  # Mostrar primeiras 3
                print(f"  - {iface.get('name', 'unnamed')}: {iface.get('type', 'unknown')}")

            # Verificar se há pppoe-server como subcomando
            print("\n🔧 Verificando subcomandos PPPoE...")
            pppoe_commands = ['pppoe-server', 'pppoe-client', 'pppoe']
            for cmd in pppoe_commands:
                try:
                    path = f'interface/{cmd}'
                    items = tuple(api.path(path).select())
                    print(f"  ✅ {path}: {len(items)} itens")
                    if items:
                        print(f"    📋 Exemplo: {items[0]}")
                except Exception as e:
                    print(f"  ❌ {path}: {e}")

        except Exception as e:
            print(f"❌ Erro ao explorar /interface/: {e}")

        # Verificar /ppp/
        print("\n📂 Explorando /ppp/...")
        try:
            ppp_items = tuple(api.path('ppp').select())
            print(f"Itens PPP encontrados: {len(ppp_items)}")
            for item in ppp_items[:3]:
                print(f"  - {item}")

            # Verificar subcomandos PPP
            ppp_commands = ['secret', 'profile', 'active']
            for cmd in ppp_commands:
                try:
                    path = f'ppp/{cmd}'
                    items = tuple(api.path(path).select())
                    print(f"  ✅ {path}: {len(items)} itens")
                except Exception as e:
                    print(f"  ❌ {path}: {e}")

        except Exception as e:
            print(f"❌ Erro ao explorar /ppp/: {e}")

        # Tentar comando direto para PPPoE server
        print("\n🎯 Testando criação direta de PPPoE server...")
        try:
            # Talvez o comando seja /interface/pppoe-server/add com parâmetros diferentes
            result = api.path('interface/pppoe-server').add(name='test-server', interface='ether2')
            print(f"✅ Criado com name + interface: {result}")
            if '.id' in result:
                api.path('interface/pppoe-server').remove(**{'.id': result['.id']})
        except Exception as e:
            print(f"❌ name + interface falhou: {e}")

        api.close()

    except Exception as e:
        print(f"❌ Erro geral: {e}")

if __name__ == "__main__":
    explore_routeros_commands()