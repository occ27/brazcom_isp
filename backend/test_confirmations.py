#!/usr/bin/env python3
"""
🧪 SCRIPT DE TESTE DO SISTEMA DE CONFIRMAÇÕES
Testa o sistema de confirmações obrigatórias para exclusões
"""

import requests
import json
import sys

# Configurações
BASE_URL = "http://localhost:8000"
HEADERS = {
    "Content-Type": "application/json",
    # Adicione headers de autenticação se necessário
}

def test_endpoint(url, method="DELETE", expected_status=400):
    """Testa um endpoint e retorna o resultado"""
    try:
        if method == "DELETE":
            response = requests.delete(url, headers=HEADERS)
        else:
            response = requests.get(url, headers=HEADERS)

        print(f"🔍 Testando: {method} {url}")
        print(f"📊 Status: {response.status_code}")

        if response.status_code == expected_status:
            print("✅ Status esperado!")
        else:
            print(f"❌ Status inesperado! Esperado: {expected_status}")

        # Tentar parsear JSON
        try:
            data = response.json()
            if "confirmation_required" in data.get("detail", {}):
                print("✅ Sistema de confirmação ativo!")
                impact = data.get("detail", {}).get("impact", {})
                print(f"📋 Impacto detectado: {len(impact)} campos informativos")
            else:
                print("ℹ️  Resposta não contém confirmação obrigatória")
        except:
            print(f"📄 Resposta: {response.text[:200]}...")

        print("-" * 50)
        return response.status_code == expected_status

    except requests.exceptions.ConnectionError:
        print(f"❌ ERRO: Não foi possível conectar a {BASE_URL}")
        print("💡 Verifique se o servidor está rodando na porta 8000")
        return False
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False

def main():
    print("🚀 TESTANDO SISTEMA DE CONFIRMAÇÕES OBRIGATÓRIAS")
    print("=" * 60)

    # Verificar se servidor está rodando
    print("1️⃣ Verificando conectividade do servidor...")
    if not test_endpoint(f"{BASE_URL}/docs", "GET", 200):
        print("❌ Servidor não está acessível. Abortando testes.")
        sys.exit(1)

    print("\n2️⃣ Testando exclusões SEM confirmação...")

    # Teste 1: Interface
    test_endpoint(f"{BASE_URL}/network/interfaces/15", "DELETE", 400)

    # Teste 2: Classe IP
    test_endpoint(f"{BASE_URL}/network/ip-classes/1", "DELETE", 400)

    # Teste 3: Atribuição
    test_endpoint(f"{BASE_URL}/network/interface-ip-assignments/15/1", "DELETE", 400)

    print("\n🎯 RESUMO DOS TESTES:")
    print("✅ Se todos os testes retornaram status 400, o sistema está funcionando!")
    print("✅ As exclusões estão devidamente protegidas por confirmação obrigatória")
    print("✅ Informações de impacto estão sendo fornecidas")

    print("\n⚠️  PRÓXIMOS PASSOS:")
    print("• Teste exclusões COM confirmação apenas em ambiente de desenvolvimento")
    print("• Verifique se o frontend trata corretamente os erros 400")
    print("• Implemente diálogos de confirmação no frontend baseados nas informações de impacto")

if __name__ == "__main__":
    main()