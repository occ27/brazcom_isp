#!/usr/bin/env python3
"""
Script para testar PPPoE de forma básica no RouterOS 6.49.19
"""

import librouteros

def basic_pppoe_test():
    """Teste básico de PPPoE"""
    try:
        api = librouteros.connect(
            host='192.168.18.101',
            username='admin',
            password='gruta765'
        )

        print("🔍 Teste básico de PPPoE no RouterOS 6.49.19")

        # Tentar comando básico /interface/pppoe
        print("\n🧪 Testando /interface/pppoe...")
        try:
            result_gen = api.rawCmd('/interface/pppoe')
            result = list(result_gen)
            print(f"✅ /interface/pppoe funcionou: {result}")
        except Exception as e:
            print(f"❌ /interface/pppoe falhou: {e}")

        # Tentar listar PPPoE interfaces
        print("\n📋 Listando interfaces PPPoE...")
        try:
            pppoe_gen = api.rawCmd('/interface/pppoe/print')
            pppoe_list = list(pppoe_gen)
            print(f"Interfaces PPPoE: {len(pppoe_list)}")
            for iface in pppoe_list:
                print(f"  - {iface}")
        except Exception as e:
            print(f"❌ Erro ao listar PPPoE: {e}")

        # Verificar se podemos adicionar uma interface PPPoE
        print("\n➕ Tentando adicionar interface PPPoE...")
        try:
            add_gen = api.rawCmd('/interface/pppoe/add')
            add_result = list(add_gen)
            print(f"✅ Adicionado: {add_result}")
        except Exception as e:
            print(f"❌ Falhou ao adicionar: {e}")

        # Verificar interfaces após adição
        print("\n📊 Verificando interfaces após adição...")
        try:
            after_gen = api.rawCmd('/interface/print')
            after = list(after_gen)
            print(f"Total interfaces: {len(after)}")
            pppoe_count = sum(1 for iface in after if 'pppoe' in iface.get('name', '').lower())
            print(f"Interfaces PPPoE: {pppoe_count}")
        except Exception as e:
            print(f"❌ Erro ao verificar: {e}")

        # Verificar documentação ou ajuda
        print("\n❓ Tentando obter ajuda...")
        try:
            help_gen = api.rawCmd('/interface/pppoe/?')
            help_result = list(help_gen)
            print(f"Ajuda PPPoE: {help_result}")
        except Exception as e:
            print(f"❌ Sem ajuda disponível: {e}")

        api.close()

    except Exception as e:
        print(f"❌ Erro geral: {e}")

if __name__ == "__main__":
    basic_pppoe_test()