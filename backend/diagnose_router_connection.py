#!/usr/bin/env python3
"""
Script de diagnóstico para testar conectividade com router Mikrotik.
Use este script para verificar se consegue conectar ao router antes de tentar configurar PPPoE.
"""

import sys
import os
import socket
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_basic_connectivity(host, port=8728):
    """Testa conectividade básica TCP."""
    print(f"🔍 Testando conectividade TCP básica: {host}:{port}")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            print("✅ Porta acessível via TCP")
            return True
        else:
            print(f"❌ Porta não acessível (código: {result})")
            return False
    except Exception as e:
        print(f"❌ Erro no teste TCP: {e}")
        return False

def test_routeros_api(host, username, password, port=8728):
    """Testa conexão via routeros_api."""
    try:
        import routeros_api
        print(f"🔍 Testando routeros_api: {host}:{port}")

        pool = routeros_api.RouterOsApiPool(
            host, username=username, password=password, port=port, plaintext_login=True
        )
        api = pool.get_api()

        # Teste simples: pegar informações do sistema
        system_resource = api.get_resource('system/resource')
        info = system_resource.get()[0]

        print("✅ routeros_api funcionando!")
        print(f"   RouterOS versão: {info.get('version', 'desconhecida')}")
        print(f"   Uptime: {info.get('uptime', 'desconhecido')}")
        print(f"   Arquitetura: {info.get('architecture-name', 'desconhecida')}")

        pool.disconnect()
        return True

    except ImportError:
        print("⚠️  routeros_api não instalado")
        return False
    except Exception as e:
        print(f"❌ routeros_api falhou: {e}")
        return False

def test_librouteros(host, username, password, port=8728):
    """Testa conexão via librouteros."""
    try:
        import librouteros
        print(f"🔍 Testando librouteros: {host}:{port}")

        api = librouteros.connect(
            host=host, username=username, password=password, port=port
        )

        # Teste simples: pegar informações do sistema
        info = list(api.path('system/resource').select())[0]

        print("✅ librouteros funcionando!")
        print(f"   RouterOS versão: {info.get('version', 'desconhecida')}")
        print(f"   Uptime: {info.get('uptime', 'desconhecido')}")
        print(f"   Arquitetura: {info.get('architecture-name', 'desconhecida')}")

        api.close()
        return True

    except ImportError:
        print("⚠️  librouteros não instalado")
        return False
    except Exception as e:
        print(f"❌ librouteros falhou: {e}")
        return False

def main():
    # Configurações - ALTERE CONFORME NECESSÁRIO
    HOST = '192.168.88.1'  # IP do seu router Mikrotik
    USERNAME = 'admin'     # Usuário
    PASSWORD = ''          # Senha (vazia para admin padrão)
    PORT = 8728            # Porta API

    print("🔧 DIAGNÓSTICO DE CONECTIVIDADE MIKROTIK")
    print("=" * 50)
    print(f"Router: {HOST}:{PORT}")
    print(f"Usuário: {USERNAME}")
    print()

    # Teste 1: Conectividade básica
    tcp_ok = test_basic_connectivity(HOST, PORT)
    print()

    if not tcp_ok:
        print("🚨 PROBLEMA: Não consegue conectar na porta TCP!")
        print("   Soluções:")
        print("   - Verifique se o IP do router está correto")
        print("   - Verifique se há firewall bloqueando a porta 8728")
        print("   - Teste: telnet 192.168.88.1 8728")
        return

    # Teste 2: routeros_api
    routeros_ok = test_routeros_api(HOST, USERNAME, PASSWORD, PORT)
    print()

    # Teste 3: librouteros
    librouteros_ok = test_librouteros(HOST, USERNAME, PASSWORD, PORT)
    print()

    # Resultado final
    print("📊 RESULTADO FINAL:")
    if routeros_ok or librouteros_ok:
        print("✅ Pelo menos uma biblioteca conseguiu conectar!")
        print("   O problema pode ser temporário ou específico da configuração PPPoE.")
        print("   Tente executar a configuração PPPoE novamente.")
    else:
        print("❌ Nenhuma biblioteca conseguiu conectar!")
        print("   Possíveis causas:")
        print("   1. Credenciais incorretas")
        print("   2. API não habilitada no router")
        print("   3. Usuário sem permissões suficientes")
        print("   4. RouterOS versão muito antiga")
        print()
        print("🔧 Verificações no router Mikrotik:")
        print("   - Winbox > IP > Services > API > Enable")
        print("   - Verificar usuário e senha")
        print("   - Verificar se o usuário tem direitos de admin")

if __name__ == '__main__':
    main()