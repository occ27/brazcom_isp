#!/usr/bin/env python3
"""
Script de teste para os endpoints de autenticação de clientes
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_client_login():
    """Testa o login de cliente (agora deve funcionar)"""
    print("🧪 Testando login de cliente...")

    payload = {
        "cpf_cnpj": "68867271920",  # CPF sem formatação
        "password": "teste123",
        "empresa_id": 1
    }

    try:
        response = requests.post(f"{BASE_URL}/client-auth/login", json=payload)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("✅ Login bem-sucedido!")
            print(f"Token type: {data.get('token_type')}")
            print(f"Expires in: {data.get('expires_in')} segundos")
            print(f"Cliente: {data.get('cliente', {}).get('nome_razao_social')}")
            print(f"Empresa: {data.get('empresa', {}).get('nome_fantasia')}")
            # Salvar token para próximos testes
            global client_token
            client_token = data.get('access_token')
        else:
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Erro na requisição: {e}")

def test_client_profile():
    """Testa o acesso ao perfil do cliente logado"""
    print("\n🧪 Testando acesso ao perfil do cliente...")

    if not client_token:
        print("❌ Nenhum token disponível")
        return

    headers = {"Authorization": f"Bearer {client_token}"}

    try:
        response = requests.get(f"{BASE_URL}/client-auth/me", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("✅ Perfil acessado com sucesso!")
            print(f"Nome: {data.get('nome_razao_social')}")
            print(f"CPF/CNPJ: {data.get('cpf_cnpj')}")
            print(f"Email: {data.get('email')}")
            print(f"Email verificado: {data.get('email_verified')}")
        else:
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Erro na requisição: {e}")

# Variável global para armazenar o token
client_token = None

def test_client_forgot_password():
    """Testa o forgot password de cliente"""
    print("\n🧪 Testando forgot password de cliente...")

    payload = {
        "cpf_cnpj": "68867271920",  # CPF sem formatação
        "empresa_id": 1
    }

    try:
        # Primeira solicitação
        response1 = requests.post(f"{BASE_URL}/client-auth/forgot-password", json=payload)
        print(f"Primeira solicitação - Status: {response1.status_code}")
        print(f"Primeira solicitação - Response: {response1.json()}")

        # Segunda solicitação imediata (deve ser bloqueada pelo rate limiting)
        response2 = requests.post(f"{BASE_URL}/client-auth/forgot-password", json=payload)
        print(f"Segunda solicitação - Status: {response2.status_code}")
        print(f"Segunda solicitação - Response: {response2.json()}")
    except Exception as e:
        print(f"Erro na requisição: {e}")

def test_client_set_password():
    """Testa a definição de senha (deve falhar sem token)"""
    print("\n🧪 Testando set password sem autenticação...")

    payload = {
        "password": "senha123",
        "confirm_password": "senha123"
    }

    try:
        response = requests.post(f"{BASE_URL}/client-auth/set-password", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Erro na requisição: {e}")

def test_invalid_cpf_cnpj():
    """Testa com CPF/CNPJ inválido"""
    print("\n🧪 Testando com CPF/CNPJ inválido...")

    payload = {
        "cpf_cnpj": "99999999999",
        "password": "senha123",
        "empresa_id": 1
    }

    try:
        response = requests.post(f"{BASE_URL}/client-auth/login", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Erro na requisição: {e}")

if __name__ == "__main__":
    print("🚀 Iniciando testes dos endpoints de autenticação de clientes")
    print("=" * 60)

    test_client_login()
    test_client_profile()
    test_client_forgot_password()
    test_client_set_password()
    test_invalid_cpf_cnpj()

    print("\n✅ Testes concluídos!")