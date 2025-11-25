#!/usr/bin/env python3
"""
Demonstração da Integração MikroTik para Interfaces de Router

Este script demonstra como usar o controlador MikroTik para:
1. Sincronizar interfaces do router
2. Aplicar configurações IP às interfaces
3. Gerenciar classes IP

Uso:
    python demonstrate_mikrotik_interfaces.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.mikrotik.controller import MikrotikController
from app.core.security import encrypt_password, decrypt_password

def demonstrate_interface_sync():
    """Demonstra sincronização de interfaces do router MikroTik."""
    print("🔄 Demonstrando Sincronização de Interfaces MikroTik")
    print("=" * 60)

    # Configurações do router (exemplo)
    router_config = {
        'host': '192.168.88.1',  # IP do router MikroTik
        'username': 'admin',
        'password': 'password',  # Em produção, descriptografar senha criptografada
        'port': 8728
    }

    try:
        print(f"📡 Conectando ao router {router_config['host']}...")

        # Criptografar senha para armazenamento seguro
        encrypted_pass = encrypt_password(router_config['password'])
        print(f"🔐 Senha criptografada: {encrypted_pass}")

        # Descriptografar para uso
        decrypted_pass = decrypt_password(encrypted_pass)

        # Criar controlador
        mk = MikrotikController(
            host=router_config['host'],
            username=router_config['username'],
            password=decrypted_pass,
            port=router_config['port']
        )

        print("✅ Conexão estabelecida com sucesso!")

        # Buscar interfaces
        print("\n🔍 Buscando interfaces do router...")
        interfaces = mk.get_interfaces()

        print(f"📋 Encontradas {len(interfaces)} interfaces:")
        for interface in interfaces:
            name = interface.get('name', 'N/A')
            tipo = interface.get('type', 'N/A')
            mac = interface.get('mac-address', 'N/A')
            status = 'UP' if interface.get('running') == 'true' else 'DOWN'

            print(f"  • {name} ({tipo}) - MAC: {mac} - Status: {status}")

        # Buscar endereços IP
        print("\n🌐 Buscando configurações IP...")
        ip_addresses = mk.get_ip_addresses()

        print(f"📋 Encontrados {len(ip_addresses)} endereços IP:")
        for ip in ip_addresses:
            address = ip.get('address', 'N/A')
            interface = ip.get('interface', 'N/A')
            comment = ip.get('comment', '')

            print(f"  • {address} na interface {interface}{f' ({comment})' if comment else ''}")

        # Demonstrar configuração IP
        print("\n⚙️  Demonstrando configuração IP...")

        # Exemplo: Configurar IP em uma interface
        test_interface = "ether2"
        test_ip = "192.168.2.1/24"

        print(f"🔧 Configurando {test_ip} na interface {test_interface}...")

        # Verificar se a interface existe
        interface_exists = any(i.get('name') == test_interface for i in interfaces)
        if interface_exists:
            result = mk.set_ip_address(test_ip, test_interface, "Configurado via API")
            print(f"✅ IP {test_ip} configurado com sucesso na interface {test_interface}")
        else:
            print(f"⚠️  Interface {test_interface} não encontrada no router")

        # Demonstrar configuração DNS
        print("\n🔧 Configurando servidores DNS...")
        dns_servers = ["8.8.8.8", "8.8.4.4"]
        mk.set_dns_servers(dns_servers)
        print(f"✅ DNS configurado: {', '.join(dns_servers)}")

        # Fechar conexão
        mk.close()
        print("\n🔌 Conexão encerrada com sucesso!")

    except Exception as e:
        print(f"❌ Erro durante demonstração: {e}")
        print("💡 Dica: Verifique se o router MikroTik está acessível e as credenciais estão corretas")

def demonstrate_ip_class_management():
    """Demonstra gerenciamento de classes IP."""
    print("\n\n🏷️  Demonstrando Gerenciamento de Classes IP")
    print("=" * 60)

    # Exemplo de classes IP
    ip_classes = [
        {
            'nome': 'Rede Interna',
            'rede': '192.168.1.0/24',
            'gateway': '192.168.1.1',
            'dns1': '192.168.1.1',
            'dns2': '8.8.8.8'
        },
        {
            'nome': 'DMZ',
            'rede': '192.168.2.0/24',
            'gateway': '192.168.2.1',
            'dns1': '8.8.8.8',
            'dns2': '8.8.4.4'
        },
        {
            'nome': 'Clientes PPPoE',
            'rede': '10.0.0.0/8',
            'gateway': None,
            'dns1': '8.8.8.8',
            'dns2': '8.8.4.4'
        }
    ]

    print("📋 Classes IP disponíveis:")
    for i, ip_class in enumerate(ip_classes, 1):
        print(f"\n{i}. {ip_class['nome']}")
        print(f"   Rede: {ip_class['rede']}")
        print(f"   Gateway: {ip_class['gateway'] or 'N/A'}")
        dns_info = ip_class['dns1'] or 'N/A'
        if ip_class['dns2']:
            dns_info += f", {ip_class['dns2']}"
        print(f"   DNS: {dns_info}")

    print("\n💡 Como usar no sistema:")
    print("1. Crie classes IP no menu 'Classes de IP'")
    print("2. Atribua classes às interfaces dos routers")
    print("3. Use 'Aplicar Configuração IP' para configurar o router automaticamente")

def main():
    """Função principal da demonstração."""
    print("🚀 Demonstração da Integração MikroTik - Interfaces de Router")
    print("=" * 70)
    print("Este script demonstra as funcionalidades de gerenciamento de interfaces")
    print("e configuração IP para routers MikroTik.\n")

    # Verificar dependências
    try:
        import routeros_api
        print("✅ Biblioteca routeros_api encontrada")
    except ImportError:
        print("⚠️  Biblioteca routeros_api não encontrada")
        print("   Instale com: pip install routeros-api")
        print("   Continuando demonstração sem conexão real...\n")

    # Demonstrar sincronização de interfaces
    demonstrate_interface_sync()

    # Demonstrar gerenciamento de classes IP
    demonstrate_ip_class_management()

    print("\n" + "=" * 70)
    print("🎉 Demonstração concluída!")
    print("\n📚 Próximos passos:")
    print("1. Configure um router MikroTik na sua rede")
    print("2. Adicione o router no sistema via interface web")
    print("3. Crie classes IP para suas redes")
    print("4. Sincronize interfaces e aplique configurações")
    print("\n🔧 Funcionalidades implementadas:")
    print("✅ Sincronização automática de interfaces")
    print("✅ Aplicação automática de configurações IP")
    print("✅ Gerenciamento de classes IP")
    print("✅ Interface web completa para gerenciamento")

if __name__ == "__main__":
    main()