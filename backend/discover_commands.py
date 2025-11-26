#!/usr/bin/env python3
"""
Script para descobrir comandos disponíveis no RouterOS 6.49.19
"""

import librouteros

def discover_commands():
    """Descobre comandos disponíveis no RouterOS"""
    try:
        api = librouteros.connect(
            host='192.168.18.101',
            username='admin',
            password='gruta765'
        )

        print("🔍 Descobrindo comandos disponíveis no RouterOS 6.49.19...")

        # Tentar listar comandos no nível raiz
        root_commands = [
            '/', '/interface', '/ip', '/system', '/tool', '/ppp', '/queue', '/user'
        ]

        for cmd in root_commands:
            print(f"\n📂 Explorando {cmd}...")
            try:
                # Tentar listar subcomandos
                list_cmd = f"{cmd}/?"
                result_gen = api.rawCmd(list_cmd)
                result = list(result_gen)
                print(f"  ✅ Subcomandos: {len(result)} encontrados")
                # Mostrar primeiros 5
                for item in result[:5]:
                    print(f"    - {item}")
                if len(result) > 5:
                    print(f"    ... e mais {len(result) - 5}")
            except Exception as e:
                print(f"  ❌ Erro: {e}")

        # Verificar especificamente PPPoE
        print("\n🔧 Verificando PPPoE especificamente...")
        pppoe_commands = [
            '/interface/pppoe',
            '/interface/pppoe-client',
            '/interface/pppoe-server',
            '/ppp/pppoe',
            '/ppp/pppoe-client',
            '/ppp/pppoe-server'
        ]

        for cmd in pppoe_commands:
            try:
                result_gen = api.rawCmd(f"{cmd}/?")
                result = list(result_gen)
                print(f"  ✅ {cmd}: {len(result)} subcomandos")
                for item in result:
                    print(f"    - {item}")
            except Exception as e:
                print(f"  ❌ {cmd}: {e}")

        api.close()

    except Exception as e:
        print(f"❌ Erro geral: {e}")

if __name__ == "__main__":
    discover_commands()