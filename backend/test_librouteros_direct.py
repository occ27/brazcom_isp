#!/usr/bin/env python3
"""
Teste simples de conexão com librouteros diretamente.
"""

import librouteros

def test_librouteros_direct():
    """Testa conexão direta com librouteros."""
    print("🔍 Testando conexão direta com librouteros...")

    try:
        api = librouteros.connect(
            host='192.168.18.101',
            username='admin',
            password='gruta765',
            port=8728
        )
        print("✅ Conexão librouteros estabelecida")

        # Testar um comando simples
        interfaces = tuple(api.path('interface').select())
        print(f"✅ Interfaces encontradas: {len(interfaces)}")

        # Mostrar algumas interfaces
        for i, iface in enumerate(interfaces[:3]):
            print(f"  {i+1}. {iface.get('name')} - {iface.get('type')}")

        api.close()
        return True

    except Exception as e:
        print(f"❌ Falha na conexão librouteros: {e}")
        return False

if __name__ == "__main__":
    test_librouteros_direct()