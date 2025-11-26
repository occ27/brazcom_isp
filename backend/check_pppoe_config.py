#!/usr/bin/env python3
"""
Script para verificar e configurar a interface PPPoE server criada
"""

import librouteros

def check_created_pppoe_server():
    """Verifica a interface PPPoE server criada"""
    try:
        api = librouteros.connect(
            host='192.168.18.101',
            username='admin',
            password='gruta765'
        )

        print("🔍 Verificando interface PPPoE server criada...")

        # Listar todas as interfaces
        print("\n📋 Todas as interfaces:")
        try:
            interfaces_gen = api.rawCmd('/interface/print')
            interfaces = list(interfaces_gen)
            for iface in interfaces:
                print(f"  - {iface.get('name', 'unnamed')} ({iface.get('type', 'unknown')})")
        except Exception as e:
            print(f"❌ Erro ao listar interfaces: {e}")

        # Verificar interfaces PPPoE especificamente
        print("\n🔧 Interfaces PPPoE:")
        try:
            pppoe_gen = api.rawCmd('/interface/pppoe-server/print')
            pppoe_interfaces = list(pppoe_gen)
            print(f"Encontradas: {len(pppoe_interfaces)}")
            for iface in pppoe_interfaces:
                print(f"  - {iface}")
        except Exception as e:
            print(f"❌ Erro ao listar PPPoE: {e}")

        # Tentar configurar a interface criada
        print("\n⚙️ Testando configuração da interface PPPoE server...")
        try:
            # Configurar interface com parâmetros básicos
            config_gen = api.rawCmd('/interface/pppoe-server/set *6 interface=ether2')
            config_result = list(config_gen)
            print(f"✅ Configuração interface=ether2: {config_result}")
        except Exception as e:
            print(f"❌ Configuração interface falhou: {e}")

        # Verificar novamente após configuração
        print("\n📊 Verificando após configuração:")
        try:
            after_gen = api.rawCmd('/interface/pppoe-server/print')
            after = list(after_gen)
            print(f"Interfaces PPPoE após config: {len(after)}")
            for iface in after:
                print(f"  - {iface}")
        except Exception as e:
            print(f"❌ Erro ao verificar: {e}")

        # Testar outros parâmetros
        print("\n🧪 Testando outros parâmetros...")
        params_to_test = [
            'service-name=pppoe-service',
            'default-profile=pppoe-default',
            'disabled=no'
        ]

        for param in params_to_test:
            try:
                cmd = f'/interface/pppoe-server/set *6 {param}'
                result_gen = api.rawCmd(cmd)
                result = list(result_gen)
                print(f"✅ {param}: {result}")
            except Exception as e:
                print(f"❌ {param}: {e}")

        api.close()

    except Exception as e:
        print(f"❌ Erro geral: {e}")

if __name__ == "__main__":
    check_created_pppoe_server()