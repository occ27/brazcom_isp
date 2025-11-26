#!/usr/bin/env python3
"""
Script para verificar versão do RouterOS e descobrir comandos PPPoE corretos
"""

import librouteros

def check_routeros_version():
    """Verifica versão do RouterOS e sistema"""
    try:
        api = librouteros.connect(
            host='192.168.18.101',
            username='admin',
            password='gruta765'
        )

        print("🔍 Verificando versão do RouterOS...")

        # Verificar versão do sistema
        try:
            system_gen = api.rawCmd('/system/resource/print')
            system_info = list(system_gen)
            if system_info:
                print(f"📊 Informações do sistema: {system_info[0]}")
        except Exception as e:
            print(f"❌ Erro ao obter versão: {e}")

        # Verificar pacotes disponíveis
        try:
            packages_gen = api.rawCmd('/system/package/print')
            packages = list(packages_gen)
            print(f"\n📦 Pacotes instalados: {len(packages)}")
            for pkg in packages:
                if 'name' in pkg:
                    print(f"  - {pkg['name']}: {pkg.get('version', 'N/A')}")
        except Exception as e:
            print(f"❌ Erro ao listar pacotes: {e}")

        # Verificar se PPPoE está disponível
        print("\n🔧 Verificando disponibilidade de PPPoE...")
        try:
            pppoe_gen = api.rawCmd('/interface/pppoe/print')
            pppoe_interfaces = list(pppoe_gen)
            print(f"Interfaces PPPoE: {len(pppoe_interfaces)}")
            for iface in pppoe_interfaces:
                print(f"  - {iface}")
        except Exception as e:
            print(f"❌ PPPoE não disponível: {e}")

        # Tentar listar todos os comandos disponíveis em /interface/
        print("\n📋 Explorando comandos disponíveis em /interface/...")
        try:
            # Usar um comando que lista submenus
            interface_menu_gen = api.rawCmd('/interface/?')
            interface_menu = list(interface_menu_gen)
            print(f"Submenus em /interface/: {interface_menu}")
        except Exception as e:
            print(f"❌ Erro ao explorar /interface/: {e}")

        # Verificar se há menu ppp
        print("\n📂 Verificando menu /ppp/...")
        try:
            ppp_menu_gen = api.rawCmd('/ppp/?')
            ppp_menu = list(ppp_menu_gen)
            print(f"Submenus em /ppp/: {ppp_menu}")
        except Exception as e:
            print(f"❌ Menu /ppp/ não existe: {e}")

        api.close()

    except Exception as e:
        print(f"❌ Erro geral: {e}")

if __name__ == "__main__":
    check_routeros_version()