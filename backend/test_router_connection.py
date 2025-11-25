#!/usr/bin/env python3
"""
Script para testar conexão com RouterBoard MikroTik RB 433AH
"""

import sys
import socket
from app.mikrotik.controller import MikrotikController

def test_connection(host: str, username: str, password: str, port: int = 8728):
    """Testa conexão com o router MikroTik"""
    print(f"🔌 Testando conexão com {host}:{port}")
    print(f"👤 Usuário: {username}")

    try:
        # Criar controlador
        controller = MikrotikController(
            host=host,
            username=username,
            password=password,
            port=port,
            plaintext_login=True
        )

        # Tentar conectar
        print("🔗 Conectando...")
        controller.connect()
        print("✅ Conexão estabelecida com sucesso!")

        # Testar comando básico - obter informações do sistema
        print("📊 Obtendo informações do sistema...")
        system_resource = controller._api.get_resource('/system/identity')
        identity = system_resource.get()
        if identity:
            print(f"🏷️  Nome do router: {identity[0].get('name', 'N/A')}")

        # Obter informações da placa
        board_resource = controller._api.get_resource('/system/routerboard')
        board_info = board_resource.get()
        if board_info:
            info = board_info[0]
            print(f"🔧 Modelo: {info.get('model', 'N/A')}")
            print(f"📋 Versão: {info.get('current-firmware', 'N/A')}")
            print(f"⚡ Serial: {info.get('serial-number', 'N/A')}")

        # Obter interfaces
        print("🌐 Interfaces disponíveis:")
        interface_resource = controller._api.get_resource('/interface')
        interfaces = interface_resource.get()
        for iface in interfaces[:5]:  # Mostra apenas as primeiras 5
            name = iface.get('name', 'N/A')
            tipo = iface.get('type', 'N/A')
            status = 'UP' if iface.get('running') == 'true' else 'DOWN'
            print(f"   • {name} ({tipo}) - {status}")

        # Fechar conexão
        controller.close()
        print("🔌 Conexão fechada")

        return True

    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False

def main():
    print("🔍 Teste de Conexão com RouterBoard MikroTik")
    print("=" * 50)

    # Configurações padrão para RB 433AH
    default_configs = [
        {
            'host': '192.168.88.1',
            'username': 'admin',
            'password': '',
            'description': 'IP padrão MikroTik (sem senha)'
        },
        {
            'host': '192.168.88.1',
            'username': 'admin',
            'password': 'admin',
            'description': 'IP padrão MikroTik (senha admin)'
        },
        {
            'host': '192.168.1.1',
            'username': 'admin',
            'password': '',
            'description': 'IP comum de roteadores'
        }
    ]

    # Tentar configurações padrão
    for config in default_configs:
        print(f"\n🎯 Testando: {config['description']}")
        print("-" * 40)

        success = test_connection(
            host=config['host'],
            username=config['username'],
            password=config['password']
        )

        if success:
            print(f"\n🎉 Conexão bem-sucedida com {config['host']}!")
            print("💡 Use essas credenciais no sistema Brazcom ISP")
            return

    # Se nenhuma configuração padrão funcionou, pedir entrada manual
    print("\n❌ Nenhuma configuração padrão funcionou.")
    print("🔧 Por favor, forneça as informações da sua RB 433AH:")

    try:
        host = input("IP do router (ex: 192.168.88.1): ").strip()
        username = input("Usuário (padrão: admin): ").strip() or 'admin'
        password = input("Senha (deixe vazio se não houver): ").strip()
        port_input = input("Porta (padrão: 8728): ").strip()
        port = int(port_input) if port_input else 8728

        print(f"\n🎯 Testando configuração personalizada...")
        success = test_connection(host, username, password, port)

        if success:
            print("\n🎉 Conexão bem-sucedida!")
            print("💡 Use essas credenciais no sistema Brazcom ISP")
        else:
            print("\n❌ Falha na conexão. Verifique:")
            print("   • IP correto do router")
            print("   • Credenciais válidas")
            print("   • Router ligado e acessível")
            print("   • Firewall não bloqueando a porta")

    except KeyboardInterrupt:
        print("\n\n👋 Teste cancelado pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")

if __name__ == "__main__":
    main()