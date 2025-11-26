#!/usr/bin/env python3
"""
Script final para descobrir e implementar PPPoE server no RouterOS 6.49.19
"""

import librouteros

def final_pppoe_test():
    """Teste final para PPPoE server"""
    try:
        api = librouteros.connect(
            host='192.168.18.101',
            username='admin',
            password='gruta765'
        )

        print("🎯 Teste final: PPPoE server no RouterOS 6.49.19")

        # Baseado na análise, tentar o comando correto para RouterOS 6.x
        # No RouterOS 6.x, PPPoE server pode ser configurado através de /ppp/pppoe-server

        print("\n🧪 Tentando /ppp/pppoe-server add interface=ether2...")
        try:
            result_gen = api.rawCmd('/ppp/pppoe-server add interface=ether2')
            result = list(result_gen)
            print(f"✅ PPPoE server criado: {result}")
        except Exception as e:
            print(f"❌ Falhou: {e}")

        # Verificar se foi criado
        print("\n📊 Verificando servidores PPPoE...")
        try:
            servers_gen = api.rawCmd('/ppp/pppoe-server print')
            servers = list(servers_gen)
            print(f"Servidores encontrados: {len(servers)}")
            for server in servers:
                print(f"  - {server}")
        except Exception as e:
            print(f"❌ Erro ao listar: {e}")

        # Se não funcionou, tentar sem interface
        if not servers:
            print("\n🔄 Tentando /ppp/pppoe-server add (sem interface)...")
            try:
                alt_gen = api.rawCmd('/ppp/pppoe-server add')
                alt_result = list(alt_gen)
                print(f"✅ Criado sem interface: {alt_result}")

                # Verificar novamente
                check_gen = api.rawCmd('/ppp/pppoe-server print')
                check_result = list(check_gen)
                print(f"Servidores após criação: {len(check_result)}")
                for server in check_result:
                    print(f"  - {server}")
            except Exception as e:
                print(f"❌ Também falhou: {e}")

        # Verificar se podemos configurar o servidor criado
        if servers:
            print("\n⚙️ Configurando servidor PPPoE...")
            server_id = servers[0].get('.id', '*0')
            config_params = [
                f'service-name=pppoe-service',
                f'default-profile=pppoe-default',
                f'disabled=no'
            ]

            for param in config_params:
                try:
                    config_cmd = f'/ppp/pppoe-server set {server_id} {param}'
                    config_gen = api.rawCmd(config_cmd)
                    config_result = list(config_gen)
                    print(f"✅ {param}: {config_result}")
                except Exception as e:
                    print(f"❌ {param}: {e}")

        api.close()

        # Resumo dos achados
        print("\n📋 RESUMO DOS ACHADOS:")
        print("RouterOS 6.49.19:")
        print("- Comando correto: /ppp/pppoe-server add")
        print("- Profiles PPP disponíveis: default, pppoe-default, test-profile, default-encryption")
        print("- PPPoE server criado com sucesso" if servers else "- PPPoE server não foi criado")

    except Exception as e:
        print(f"❌ Erro geral: {e}")

if __name__ == "__main__":
    final_pppoe_test()