#!/usr/bin/env python3
"""
Script para testar configuração de PPPoE server baseada no conhecimento do RouterOS 6.x
"""

import librouteros

def test_pppoe_server_setup():
    """Testa configuração de PPPoE server baseada na documentação RouterOS 6.x"""
    try:
        api = librouteros.connect(
            host='192.168.18.101',
            username='admin',
            password='gruta765'
        )

        print("🔍 Testando configuração de PPPoE server no RouterOS 6.49.19...")

        # No RouterOS 6.x, PPPoE server pode ser configurado de diferentes formas

        # 1. Tentar comando básico sem parâmetros
        print("\n1️⃣ Testando /interface/pppoe-server (sem parâmetros)...")
        try:
            result_gen = api.rawCmd('/interface/pppoe-server')
            result = list(result_gen)
            print(f"✅ Comando básico funcionou: {result}")
        except Exception as e:
            print(f"❌ Comando básico falhou: {e}")

        # 2. Tentar configurar uma interface como PPPoE server
        print("\n2️⃣ Testando configuração de interface como servidor...")
        try:
            # No RouterOS, algumas interfaces podem ser configuradas como servidor
            config_gen = api.rawCmd('/interface/set ether2 type=pppoe-server')
            config_result = list(config_gen)
            print(f"✅ Configuração type=pppoe-server: {config_result}")
        except Exception as e:
            print(f"❌ Configuração type falhou: {e}")

        # 3. Verificar se PPP está disponível
        print("\n3️⃣ Verificando PPP profiles...")
        try:
            profiles_gen = api.rawCmd('/ppp/profile/print')
            profiles = list(profiles_gen)
            print(f"Profiles PPP: {len(profiles)}")
            for profile in profiles:
                print(f"  - {profile.get('name', 'unnamed')}: local-address={profile.get('local-address', 'N/A')}")
        except Exception as e:
            print(f"❌ Erro ao listar profiles: {e}")

        # 4. Tentar criar um servidor PPPoE através de PPP
        print("\n4️⃣ Testando criação através de /ppp/pppoe...")
        try:
            # Talvez seja /ppp/pppoe add
            ppp_gen = api.rawCmd('/ppp/pppoe/add interface=ether2')
            ppp_result = list(ppp_gen)
            print(f"✅ /ppp/pppoe/add funcionou: {ppp_result}")
        except Exception as e:
            print(f"❌ /ppp/pppoe/add falhou: {e}")

        # 5. Verificar interfaces após tentativas
        print("\n5️⃣ Verificando interfaces finais...")
        try:
            final_gen = api.rawCmd('/interface/print')
            final = list(final_gen)
            print(f"Total de interfaces: {len(final)}")
            for iface in final:
                if 'pppoe' in iface.get('name', '').lower() or iface.get('type', '').startswith('pppoe'):
                    print(f"  📡 PPPoE: {iface}")
        except Exception as e:
            print(f"❌ Erro ao verificar interfaces: {e}")

        api.close()

    except Exception as e:
        print(f"❌ Erro geral: {e}")

if __name__ == "__main__":
    test_pppoe_server_setup()