#!/usr/bin/env python3
"""
Script para descobrir parâmetros corretos do comando /interface/pppoe-server/add
no RouterOS através de testes incrementais
"""

import librouteros

def test_single_parameter(api, param_name, param_value):
    """Testa um único parâmetro"""
    try:
        result = api.path('interface/pppoe-server').add(**{param_name: param_value})
        print(f"✅ {param_name}={param_value} funcionou: {result}")
        # Remover se foi criado
        if '.id' in result:
            api.path('interface/pppoe-server').remove(**{'.id': result['.id']})
        return True
    except Exception as e:
        print(f"❌ {param_name}={param_value} falhou: {e}")
        return False

def discover_pppoe_parameters():
    """Descobre parâmetros aceitos para PPPoE server"""
    try:
        api = librouteros.connect(
            host='192.168.18.101',
            username='admin',
            password='gruta765'
        )

        print("🔍 Descobrindo parâmetros aceitos para PPPoE server...")

        # Testar diferentes caminhos
        paths_to_test = [
            'interface/pppoe-server',
            'ppp/pppoe-server',
            'interface/pppoe',
            'ppp/pppoe'
        ]

        for path in paths_to_test:
            print(f"\n🧪 Testando caminho: {path}")
            try:
                # Verificar se o caminho existe listando
                items = tuple(api.path(path).select())
                print(f"  ✅ Caminho existe, {len(items)} itens encontrados")
                if items:
                    print(f"  📋 Primeiro item: {items[0]}")
            except Exception as e:
                print(f"  ❌ Caminho não existe: {e}")

        # Usar o caminho correto (provavelmente ppp/pppoe-server)
        correct_path = 'ppp/pppoe-server'
        print(f"\n🎯 Usando caminho correto: {correct_path}")

        # Testar parâmetros um por vez
        test_params = [
            ('interface', 'ether2'),
            ('disabled', 'no'),
            ('service-name', 'test-service'),
            ('default-profile', 'default'),
            ('max-mtu', '1480'),
            ('max-mru', '1480'),
            ('keepalive-timeout', '10'),
            ('authentication', 'pap,chap,mschap1,mschap2'),
        ]

        working_params = []

        for param_name, param_value in test_params:
            print(f"\nTestando {param_name}...")
            try:
                result = api.path(correct_path).add(**{param_name: param_value})
                print(f"✅ {param_name}={param_value} funcionou: {result}")
                # Remover se foi criado
                if '.id' in result:
                    api.path(correct_path).remove(**{'.id': result['.id']})
                working_params.append((param_name, param_value))
            except Exception as e:
                print(f"❌ {param_name}={param_value} falhou: {e}")

        print(f"\n📋 Parâmetros que funcionaram: {working_params}")

        # Tentar combinação mínima
        if working_params:
            print("\n🔧 Testando combinação mínima...")
            try:
                params = dict(working_params[:2])  # interface + primeiro que funcionou
                result = api.path(correct_path).add(**params)
                print(f"✅ Combinação mínima funcionou: {result}")
                if '.id' in result:
                    api.path(correct_path).remove(**{'.id': result['.id']})
            except Exception as e:
                print(f"❌ Combinação mínima falhou: {e}")

        api.close()

    except Exception as e:
        print(f"❌ Erro geral: {e}")

if __name__ == "__main__":
    discover_pppoe_parameters()