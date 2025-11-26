#!/usr/bin/env python3
"""
Script para testar a correção do método add_pppoe_server diretamente
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.mikrotik.controller import MikrotikController

def test_pppoe_server_fix():
    """Testa se a correção do método add_pppoe_server funciona"""
    controller = MikrotikController(
        host='192.168.18.101',
        username='admin',
        password='gruta765'
    )

    try:
        print("🔍 Testando correção do método add_pppoe_server...")

        # Conectar
        controller.connect()
        print("✅ Conexão estabelecida")

        # Tentar criar servidor PPPoE
        result = controller.add_pppoe_server("test-server", "ether2", "pppoe-default")
        print(f"✅ Servidor PPPoE criado com sucesso: {result}")

        print("🎉 Correção funcionando!")

    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

    finally:
        try:
            controller.disconnect()
        except:
            pass

if __name__ == "__main__":
    test_pppoe_server_fix()