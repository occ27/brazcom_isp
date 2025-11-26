#!/usr/bin/env python3
"""
Script para testar configuração correta de PPPoE server no RouterOS 6.49.19
Baseado na documentação: /interface/pppoe-server server
"""

import librouteros

def test_correct_pppoe_server():
    """Testa a configuração correta de PPPoE server"""
    try:
        api = librouteros.connect(
            host='192.168.18.101',
            username='admin',
            password='gruta765'
        )

        print("🔍 Testando configuração correta de PPPoE server...")

        # Tentar o comando correto baseado na documentação RouterOS 6.x
        print("\n🧪 Testando /interface/pppoe-server add interface=ether2...")
        try:
            result_gen = api.rawCmd('/interface/pppoe-server add interface=ether2')
            result = list(result_gen)
            print(f"✅ add interface funcionou: {result}")
        except Exception as e:
            print(f"❌ add interface falhou: {e}")

        # Verificar se foi criado
        print("\n📊 Verificando servidores PPPoE...")
        servers = []
        try:
            servers_gen = api.rawCmd('/interface/pppoe-server print')
            servers = list(servers_gen)
            print(f"Servidores encontrados: {len(servers)}")
            for server in servers:
                print(f"  - {server}")
        except Exception as e:
            print(f"❌ Erro ao listar servidores: {e}")

        # Se não funcionou, tentar outro caminho
        if not servers:
            print("\n🔄 Tentando caminho alternativo...")
            # Talvez seja /ppp/pppoe-server
            try:
                alt_gen = api.rawCmd('/ppp/pppoe-server add interface=ether2')
                alt_result = list(alt_gen)
                print(f"✅ /ppp/pppoe-server funcionou: {alt_result}")
            except Exception as e:
                print(f"❌ /ppp/pppoe-server falhou: {e}")

            # Verificar novamente
            try:
                check_gen = api.rawCmd('/ppp/pppoe-server print')
                check_result = list(check_gen)
                print(f"Servidores PPP encontrados: {len(check_result)}")
                for server in check_result:
                    print(f"  - {server}")
            except Exception as e:
                print(f"❌ Erro ao verificar /ppp/: {e}")

        # Limpar interfaces criadas desnecessariamente
        print("\n🧹 Limpando interfaces PPPoE-in criadas...")
        try:
            # Listar interfaces PPPoE atuais
            current_gen = api.rawCmd('/interface/pppoe-server print')
            current = list(current_gen)
            print(f"Interfaces atuais antes da limpeza: {len(current)}")

            # Remover as interfaces pppoe-in que foram criadas por engano
            for iface in current:
                iface_id = iface.get('.id')
                if iface_id and iface.get('type') == 'pppoe-in':
                    try:
                        remove_gen = api.rawCmd(f'/interface/pppoe-server remove {iface_id}')
                        remove_result = list(remove_gen)
                        print(f"✅ Removido {iface_id}: {remove_result}")
                    except Exception as e:
                        print(f"❌ Erro ao remover {iface_id}: {e}")
        except Exception as e:
            print(f"❌ Erro geral na limpeza: {e}")

        api.close()

    except Exception as e:
        print(f"❌ Erro geral: {e}")

if __name__ == "__main__":
    test_correct_pppoe_server()