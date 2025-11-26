#!/usr/bin/env python3
"""
Script para testar comandos PPPoE server usando API raw do RouterOS
"""

import librouteros

def test_raw_pppoe_commands():
    """Testa comandos PPPoE usando API raw"""
    try:
        api = librouteros.connect(
            host='192.168.18.101',
            username='admin',
            password='gruta765'
        )

        print("🔍 Testando comandos PPPoE server com API raw...")

        # Tentar comandos raw do RouterOS
        commands_to_test = [
            '/interface/pppoe-server/server/add interface=ether2',
            '/interface/pppoe-server/add interface=ether2',
            '/ppp/pppoe-server/add interface=ether2',
            '/interface/pppoe/add interface=ether2 service=pppoe-server',
            '/interface/pppoe-server/server/set interface=ether2',
        ]

        for cmd in commands_to_test:
            print(f"\n🧪 Testando: {cmd}")
            try:
                # Usar raw command e consumir o generator
                result_gen = api.rawCmd(cmd)
                result = list(result_gen)
                print(f"✅ Sucesso: {result}")
            except Exception as e:
                print(f"❌ Falhou: {e}")

        # Verificar se há algum servidor PPPoE configurado
        print("\n📋 Verificando servidores PPPoE existentes...")
        try:
            servers_gen = api.rawCmd('/interface/pppoe-server/server/print')
            servers = list(servers_gen)
            print(f"Servidores encontrados: {servers}")
        except Exception as e:
            print(f"❌ Erro ao listar servidores: {e}")

        # Verificar interfaces PPPoE
        print("\n🔧 Verificando interfaces PPPoE...")
        try:
            interfaces_gen = api.rawCmd('/interface/print where type=pppoe-server')
            interfaces = list(interfaces_gen)
            print(f"Interfaces PPPoE: {interfaces}")
        except Exception as e:
            print(f"❌ Erro ao listar interfaces: {e}")

        # Verificar se algum servidor foi criado
        print("\n📊 Verificando estado final...")
        try:
            final_servers_gen = api.rawCmd('/interface/pppoe-server/server/print')
            final_servers = list(final_servers_gen)
            print(f"Servidores PPPoE finais: {final_servers}")
        except Exception as e:
            print(f"❌ Erro ao verificar estado final: {e}")

        api.close()

    except Exception as e:
        print(f"❌ Erro geral: {e}")

if __name__ == "__main__":
    test_raw_pppoe_commands()