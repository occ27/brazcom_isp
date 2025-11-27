#!/usr/bin/env python3
"""
Script de teste para verificar servidores PPPoE no MikroTik
Execute com: python test_pppoe.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.mikrotik.controller import MikrotikController
import logging

# Configurar logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def test_pppoe_servers():
    # Substitua pelas suas credenciais
    HOST = '192.168.18.101'  # Ex: '192.168.88.1'
    USERNAME = 'admin'   # Ex: 'admin'
    PASSWORD = 'gruta765'     # Ex: 'password'
    PORT = 8728

    print(f"Tentando conectar ao router {HOST}:{PORT}...")

    try:
        mk = MikrotikController(HOST, USERNAME, PASSWORD, PORT)
        mk.connect()

        print("✅ Conexão estabelecida!")

        # Testar diferentes caminhos
        paths_to_test = [
            'interface/pppoe-server server',
            'interface/pppoe-server',
            'ppp/pppoe-server',
            'ppp/server',
            'interface/pppoe',
        ]

        print("\n🔍 Testando caminhos para servidores PPPoE:")
        print("=" * 50)

        for path in paths_to_test:
            try:
                print(f"\nTestando caminho: {path}")
                if mk._api:
                    resource = mk._api.get_resource(path)
                    servers = resource.get()
                    print(f"  📊 Resultado: {len(servers)} servidores encontrados")

                    if servers:
                        print("  📋 Detalhes dos servidores:")
                        for i, server in enumerate(servers, 1):
                            print(f"    {i}. {server}")
                    else:
                        print("  ❌ Nenhum servidor encontrado neste caminho")
                else:
                    print("  ❌ API não disponível")

            except Exception as e:
                print(f"  ❌ Erro: {str(e)}")

        print("\n🔍 Testando comandos raw (como no Winbox):")
        print("=" * 50)

        raw_commands = [
            '/interface/pppoe-server/server/print',
            '/interface/pppoe-server/print',
            '/ppp/pppoe-server/print',
            '/ppp/server/print',
            '/interface/print where type=pppoe-server',
        ]

        for cmd in raw_commands:
            try:
                print(f"\nTestando comando raw: {cmd}")
                if mk._api:
                    # Tentar executar comando raw
                    result = mk._api.talk(cmd)
                    print(f"  📊 Resultado: {len(result) if isinstance(result, list) else 'não é lista'} itens")
                    if isinstance(result, list) and result:
                        print("  📋 Detalhes:")
                        for i, item in enumerate(result, 1):
                            print(f"    {i}. {item}")
                    else:
                        print("  ❌ Nenhum resultado ou resultado não é lista")
                else:
                    print("  ❌ API não disponível")
            except Exception as e:
                print(f"  ❌ Erro: {str(e)}")

        print("\n🔍 Testando via librouteros (fallback):")
        print("=" * 50)

        if mk._librouteros_api:
            lib_paths = [
                'interface/pppoe-server',
                'interface/pppoe-server/server',
                'ppp/pppoe-server',
                'interface/pppoe',
                'ppp',
            ]
            
            for lp in lib_paths:
                try:
                    print(f"\nTestando librouteros caminho: {lp}")
                    items = list(mk._librouteros_api.path(lp).select())
                    print(f"  📊 Resultado: {len(items)} registros encontrados")
                    if items:
                        print("  📋 Detalhes:")
                        for i, item in enumerate(items, 1):
                            print(f"    {i}. {dict(item)}")
                    else:
                        print("  ❌ Nenhum registro encontrado")
                except Exception as e:
                    print(f"  ❌ Erro: {str(e)}")
        else:
            print("❌ librouteros não disponível")

        print("\n" + "=" * 50)
        print("✅ Teste concluído!")

    except Exception as e:
        print(f"❌ Erro na conexão: {str(e)}")
        print("\nVerifique:")
        print("- IP do router está correto")
        print("- Credenciais estão corretas")
        print("- Router está acessível na rede")
        print("- Porta 8728 não está bloqueada")

if __name__ == "__main__":
    test_pppoe_servers()