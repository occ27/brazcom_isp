#!/usr/bin/env python3
"""
Teste para descobrir quais parâmetros são aceitos pelo comando /interface/pppoe-server/add
"""

import librouteros

def test_pppoe_server_params():
    """Testa diferentes combinações de parâmetros para /interface/pppoe-server/add"""
    print("🔍 Testando parâmetros aceitos para /interface/pppoe-server/add...")

    try:
        api = librouteros.connect(
            host='192.168.18.101',
            username='admin',
            password='gruta765',
            port=8728
        )

        # Teste 1: Apenas interface (parâmetro obrigatório)
        print("\nTeste 1: Apenas interface")
        try:
            result = api.path('interface/pppoe-server').add(interface='ether2')
            print(f"✅ Sucesso: {result}")
            # Remover para limpar
            api.path('interface/pppoe-server').remove(**{'.id': result['.id']})
        except Exception as e:
            print(f"❌ Falhou: {e}")

        # Teste 2: Interface + disabled
        print("\nTeste 2: Interface + disabled")
        try:
            result = api.path('interface/pppoe-server').add(interface='ether2', disabled='no')
            print(f"✅ Sucesso: {result}")
            api.path('interface/pppoe-server').remove(**{'.id': result['.id']})
        except Exception as e:
            print(f"❌ Falhou: {e}")

        # Teste 3: Interface + service-name
        print("\nTeste 3: Interface + service-name")
        try:
            result = api.path('interface/pppoe-server').add(interface='ether2', **{'service-name': 'test'})
            print(f"✅ Sucesso: {result}")
            api.path('interface/pppoe-server').remove(**{'.id': result['.id']})
        except Exception as e:
            print(f"❌ Falhou: {e}")

        # Teste 4: Interface + default-profile
        print("\nTeste 4: Interface + default-profile")
        try:
            result = api.path('interface/pppoe-server').add(interface='ether2', **{'default-profile': 'default'})
            print(f"✅ Sucesso: {result}")
            api.path('interface/pppoe-server').remove(**{'.id': result['.id']})
        except Exception as e:
            print(f"❌ Falhou: {e}")

        # Verificar servidores existentes
        print("\n📋 Servidores PPPoE existentes:")
        servers = tuple(api.path('interface/pppoe-server').select())
        for server in servers:
            print(f"  - {server}")

        api.close()

    except Exception as e:
        print(f"❌ Erro geral: {e}")

if __name__ == "__main__":
    test_pppoe_server_params()