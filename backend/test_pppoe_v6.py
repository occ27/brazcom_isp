#!/usr/bin/env python3
"""
Script para testar configuração de PPPoE server no RouterOS 6.49.19
"""

import librouteros

def test_pppoe_server_v6():
    """Testa PPPoE server para RouterOS 6.x"""
    try:
        api = librouteros.connect(
            host='192.168.18.101',
            username='admin',
            password='gruta765'
        )

        print("🔍 Testando PPPoE server para RouterOS 6.49.19...")

        # No RouterOS 6.x, PPPoE server pode ser configurado diretamente na interface
        # ou usando /interface/pppoe-server

        # Primeiro, verificar interfaces existentes
        print("\n📋 Interfaces existentes:")
        try:
            interfaces_gen = api.rawCmd('/interface/print')
            interfaces = list(interfaces_gen)
            for iface in interfaces:
                print(f"  - {iface.get('name', 'unnamed')}: {iface.get('type', 'unknown')}")
        except Exception as e:
            print(f"❌ Erro ao listar interfaces: {e}")

        # Tentar comando PPPoE server básico
        print("\n🧪 Testando /interface/pppoe-server add...")
        try:
            # No RouterOS 6.x, pode ser apenas 'add' sem parâmetros específicos
            result_gen = api.rawCmd('/interface/pppoe-server/add')
            result = list(result_gen)
            print(f"✅ Comando básico funcionou: {result}")
        except Exception as e:
            print(f"❌ Comando básico falhou: {e}")

        # Verificar se foi criado algo
        print("\n📊 Verificando após criação...")
        try:
            after_gen = api.rawCmd('/interface/print')
            after = list(after_gen)
            print(f"Interfaces após: {len(after)} (antes: {len(interfaces) if 'interfaces' in locals() else 'unknown'})")
        except Exception as e:
            print(f"❌ Erro ao verificar: {e}")

        # Tentar configurar uma interface específica como PPPoE server
        print("\n🎯 Testando configuração em interface específica...")
        try:
            # Talvez seja necessário configurar a interface ether2 como pppoe-server
            config_gen = api.rawCmd('/interface/set ether2 type=pppoe-server')
            config_result = list(config_gen)
            print(f"✅ Configuração de interface: {config_result}")
        except Exception as e:
            print(f"❌ Configuração falhou: {e}")

        # Verificar profiles PPP
        print("\n📋 Verificando profiles PPP...")
        try:
            profiles_gen = api.rawCmd('/ppp/profile/print')
            profiles = list(profiles_gen)
            print(f"Profiles PPP: {len(profiles)}")
            for profile in profiles:
                print(f"  - {profile.get('name', 'unnamed')}")
        except Exception as e:
            print(f"❌ Erro ao listar profiles: {e}")

        api.close()

    except Exception as e:
        print(f"❌ Erro geral: {e}")

if __name__ == "__main__":
    test_pppoe_server_v6()