#!/usr/bin/env python3
"""
Script de diagnóstico para testar conexão e criação de servidor PPPoE no router.
Usa as credenciais fornecidas pelo usuário para testar diretamente.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.mikrotik.controller import MikrotikController

def test_router_connection():
    """Testa conexão básica com o router."""
    print("🔍 Testando conexão com router 192.168.18.101...")

    mc = MikrotikController('192.168.18.101', 'admin', 'gruta765')

    try:
        mc.connect()
        status = mc.get_connection_status()
        print(f"✅ Conexão estabelecida. Status: {status}")
        return True
    except Exception as e:
        print(f"❌ Falha na conexão: {e}")
        return False

def test_pppoe_server_creation():
    """Testa criação de servidor PPPoE."""
    print("\n🔧 Testando criação de servidor PPPoE...")

    mc = MikrotikController('192.168.18.101', 'admin', 'gruta765')

    try:
        # Primeiro, verificar se já existe algum servidor PPPoE
        print("Verificando servidores PPPoE existentes...")
        status = mc.get_pppoe_server_status()
        print(f"Status atual: {status}")

        # Tentar criar servidor PPPoE
        print("Tentando criar servidor PPPoE...")
        result = mc.add_pppoe_server("test-pppoe", "ether2", "default")
        print(f"✅ Servidor PPPoE criado: {result}")

        return True

    except Exception as e:
        print(f"❌ Falha ao criar servidor PPPoE: {e}")
        return False

def test_wan_detection():
    """Testa detecção de interface WAN."""
    print("\n🌐 Testando detecção de interface WAN...")

    mc = MikrotikController('192.168.18.101', 'admin', 'gruta765')

    try:
        # Testar ether1 (provavelmente WAN)
        is_wan = mc.is_wan_interface("ether1")
        print(f"ether1 é WAN? {is_wan}")

        # Testar ether2 (provavelmente LAN)
        is_wan = mc.is_wan_interface("ether2")
        print(f"ether2 é WAN? {is_wan}")

        return True

    except Exception as e:
        print(f"❌ Falha na detecção WAN: {e}")
        return False

def test_full_setup():
    """Testa configuração completa do servidor PPPoE."""
    print("\n🚀 Testando configuração completa do servidor PPPoE...")

    mc = MikrotikController('192.168.18.101', 'admin', 'gruta765')

    try:
        # Usar ether2 (não WAN) para o teste
        result = mc.setup_pppoe_server(
            interface="ether2",
            ip_pool_name="test-pool",
            local_address="192.168.2.1",
            first_ip="192.168.2.2",
            last_ip="192.168.2.254",
            default_profile="test-profile"
        )
        print(f"✅ Configuração completa realizada: {result}")
        return True

    except Exception as e:
        print(f"❌ Falha na configuração completa: {e}")
        return False

if __name__ == "__main__":
    print("=== DIAGNÓSTICO DO ROUTER MIKROTIK ===")
    print("IP: 192.168.18.101 | User: admin | Password: gruta765")
    print()

    # Executar testes
    conn_ok = test_router_connection()
    if not conn_ok:
        print("\n❌ Conexão falhou. Abortando testes restantes.")
        sys.exit(1)

    wan_ok = test_wan_detection()
    pppoe_ok = test_pppoe_server_creation()
    full_ok = test_full_setup()

    print("\n=== RESUMO DOS TESTES ===")
    print(f"Conexão: {'✅' if conn_ok else '❌'}")
    print(f"Detecção WAN: {'✅' if wan_ok else '❌'}")
    print(f"Servidor PPPoE: {'✅' if pppoe_ok else '❌'}")
    print(f"Configuração completa: {'✅' if full_ok else '❌'}")

    if conn_ok and wan_ok and pppoe_ok and full_ok:
        print("\n🎉 Todos os testes passaram! O sistema está funcionando.")
    else:
        print("\n⚠️ Alguns testes falharam. Verifique os logs acima.")