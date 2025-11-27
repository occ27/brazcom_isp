#!/usr/bin/env python3
"""
Script para testar a API de setup PPPoE após correção
"""

import requests
import json

def test_pppoe_api():
    """Testa a API de setup PPPoE"""
    url = 'http://127.0.0.1:8000/network/routers/2/setup-pppoe-server'
    data = {
        'interface': 'ether2',
        'ip_pool_name': 'pppoe-pool',
        'local_address': '192.168.1.1',
        'first_ip': '192.168.1.2',
        'last_ip': '192.168.1.254',
        'default_profile': 'pppoe-default'
    }

    try:
        print("🔍 Testando API de setup PPPoE...")
        response = requests.post(url, json=data, timeout=30)

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            print("✅ API funcionando corretamente!")
        elif response.status_code == 401:
            print("⚠️  API requer autenticação (401 Unauthorized)")
        elif response.status_code == 500:
            print("❌ Ainda há erro interno do servidor (500)")
        else:
            print(f"⚠️  Status inesperado: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("❌ Servidor não está respondendo (ConnectionError)")
    except requests.exceptions.Timeout:
        print("❌ Timeout na requisição")
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")

if __name__ == "__main__":
    test_pppoe_api()