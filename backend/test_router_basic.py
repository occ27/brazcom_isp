#!/usr/bin/env python3
"""
Script simples para testar conectividade básica com RouterBoard MikroTik
"""

import socket
import time

def test_port_connection(host: str, port: int = 8728, timeout: int = 5):
    """Testa se uma porta está aberta"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def test_http_connection(host: str, port: int = 80, timeout: int = 5):
    """Testa conexão HTTP básica"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        if result == 0:
            # Tentar enviar uma requisição HTTP simples
            sock.send(b'GET / HTTP/1.0\r\nHost: ' + host.encode() + b'\r\n\r\n')
            response = sock.recv(1024)
            sock.close()
            return b'200' in response or b'401' in response or b'MikroTik' in response
        sock.close()
        return False
    except:
        return False

def main():
    print("🔍 Teste Básico de Conectividade com RouterBoard MikroTik")
    print("=" * 60)

    # IPs comuns para MikroTik
    test_ips = [
        '192.168.88.1',   # IP padrão MikroTik
        '192.168.1.1',    # IP comum de roteadores
        '192.168.0.1',    # IP comum de roteadores
        '10.0.0.1',       # IP comum de roteadores
        '192.168.18.101', # IP fornecido pelo usuário
    ]

    print("🌐 Testando conectividade básica...")
    print()

    found_devices = []

    for ip in test_ips:
        print(f"🔌 Testando {ip}...")

        # Testar porta API RouterOS (8728)
        api_open = test_port_connection(ip, 8728, 3)
        print(f"   📡 API RouterOS (8728): {'✅ Aberta' if api_open else '❌ Fechada'}")

        # Testar porta Winbox (8291)
        winbox_open = test_port_connection(ip, 8291, 3)
        print(f"   🖥️  Winbox (8291): {'✅ Aberta' if winbox_open else '❌ Fechada'}")

        # Testar porta HTTP (80)
        http_open = test_http_connection(ip, 80, 3)
        print(f"   🌐 HTTP (80): {'✅ Responde' if http_open else '❌ Não responde'}")

        # Testar porta HTTPS (443)
        https_open = test_port_connection(ip, 443, 3)
        print(f"   🔒 HTTPS (443): {'✅ Aberta' if https_open else '❌ Fechada'}")

        if api_open or winbox_open or http_open or https_open:
            found_devices.append({
                'ip': ip,
                'api': api_open,
                'winbox': winbox_open,
                'http': http_open,
                'https': https_open
            })
            print(f"   🎯 POSSÍVEL ROUTER ENCONTRADO!")
        else:
            print(f"   ⚪ Nenhum serviço RouterOS detectado")

        print()

    print("=" * 60)
    print("📋 RESUMO DOS TESTES:")
    print("=" * 60)

    if found_devices:
        print("🎉 Dispositivos com serviços RouterOS encontrados:")
        print()

        for device in found_devices:
            print(f"🏠 IP: {device['ip']}")
            services = []
            if device['api']: services.append("API RouterOS (8728)")
            if device['winbox']: services.append("Winbox (8291)")
            if device['http']: services.append("Interface Web (80)")
            if device['https']: services.append("Interface Web SSL (443)")

            print(f"   📋 Serviços disponíveis: {', '.join(services)}")
            print()

        print("💡 PRÓXIMOS PASSOS:")
        print("   1. Use Winbox para conectar ao router")
        print("   2. Configure credenciais de acesso")
        print("   3. Teste a API RouterOS com as credenciais")
        print("   4. Configure o router no sistema Brazcom ISP")

    else:
        print("❌ Nenhum dispositivo RouterOS detectado na rede.")
        print()
        print("🔧 POSSÍVEIS CAUSAS:")
        print("   • RouterBoard não está ligada")
        print("   • IP diferente do esperado")
        print("   • Firewall bloqueando portas")
        print("   • RouterBoard em modo bridge ou configuração diferente")
        print("   • Conexão Ethernet não estabelecida")
        print()
        print("💡 DICAS PARA DIAGNOSTICAR:")
        print("   1. Verifique se os cabos Ethernet estão conectados")
        print("   2. Teste ping para o IP suspeito")
        print("   3. Use Winbox para descoberta de dispositivos")
        print("   4. Reset a RouterBoard (botão reset por 5-10 segundos)")
        print("   5. Conecte diretamente no PC para configuração inicial")

if __name__ == "__main__":
    main()