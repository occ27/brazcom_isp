#!/usr/bin/env python3
"""
Script avançado para testar regras ARP na RouterBoard
"""

import sys
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Adicionar o diretório app ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.models.network import Router
from app.core.config import settings
from app.mikrotik.controller import MikrotikController

def get_router_from_db(router_id: int = None):
    """Obtém dados do router do banco de dados"""
    try:
        database_url = settings.DATABASE_URL
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        try:
            if router_id is None:
                router = db.query(Router).filter(Router.is_active == True).first()
            else:
                router = db.query(Router).filter(Router.id == router_id).first()

            if router:
                return {
                    'id': router.id,
                    'nome': router.nome,
                    'ip': router.ip,
                    'usuario': router.usuario,
                    'senha': router.senha,
                    'porta': router.porta or 8728,
                    'tipo': router.tipo,
                    'empresa_id': router.empresa_id
                }
            else:
                print("❌ Nenhum router encontrado no banco de dados")
                return None

        finally:
            db.close()

    except Exception as e:
        print(f"❌ Erro ao acessar banco de dados: {e}")
        return None

def test_arp_operations(router_data):
    """Testa várias operações ARP"""
    print(f"🔧 Testando operações ARP no router: {router_data['nome']}")
    print("-" * 70)

    try:
        controller = MikrotikController(
            host=router_data['ip'],
            username=router_data['usuario'],
            password=router_data['senha'],
            port=router_data['porta'],
            plaintext_login=True
        )

        controller.connect()
        print("✅ Conexão estabelecida!")

        # 1. Listar entradas ARP atuais
        print("\n📋 1. Entradas ARP atuais:")
        arp_resource = controller._api.get_resource('ip/arp')
        arp_entries = arp_resource.get()

        print(f"   Total: {len(arp_entries)} entradas")
        for entry in arp_entries:
            ip = entry.get('address', 'N/A')
            mac = entry.get('mac-address', 'N/A')
            interface = entry.get('interface', 'N/A')
            status = entry.get('status', 'N/A')
            print(f"   • {ip:15} -> {mac:17} ({interface:8}) [{status}]")

        # 2. Adicionar entrada ARP estática de teste
        print("\n📝 2. Adicionando entrada ARP estática de teste...")
        test_ip = "192.168.18.200"
        test_mac = "DE:AD:BE:EF:CA:FE"
        test_interface = "ether1"

        print(f"   IP: {test_ip}")
        print(f"   MAC: {test_mac}")
        print(f"   Interface: {test_interface}")

        # Remover se existir
        existing = arp_resource.get(address=test_ip)
        if existing:
            for e in existing:
                arp_resource.remove(id=e.get('.id'))
                print("   🗑️  Entrada existente removida")

        # Adicionar nova
        data = {
            'address': test_ip,
            'mac-address': test_mac,
            'interface': test_interface
        }
        result = arp_resource.add(**data)
        print(f"   ✅ Entrada ARP adicionada (ID: {result})")

        # 3. Verificar se foi adicionada
        print("\n🔍 3. Verificando entrada adicionada...")
        updated_entries = arp_resource.get(address=test_ip)
        if updated_entries:
            entry = updated_entries[0]
            print("   ✅ Entrada encontrada:")
            print(f"      IP: {entry.get('address')}")
            print(f"      MAC: {entry.get('mac-address')}")
            print(f"      Interface: {entry.get('interface')}")
        else:
            print("   ❌ Entrada não encontrada!")

        # 4. Adicionar mais uma entrada para teste
        print("\n📝 4. Adicionando segunda entrada ARP...")
        test_ip2 = "192.168.18.201"
        test_mac2 = "BA:DC:0F:FE:ED:01"

        data2 = {
            'address': test_ip2,
            'mac-address': test_mac2,
            'interface': test_interface
        }
        result2 = arp_resource.add(**data2)
        print(f"   ✅ Segunda entrada adicionada (ID: {result2})")

        # 5. Listar todas as entradas ARP novamente
        print("\n📋 5. Tabela ARP final:")
        final_entries = arp_resource.get()
        print(f"   Total: {len(final_entries)} entradas")

        static_entries = [e for e in final_entries if e.get('status') != 'dynamic']
        dynamic_entries = [e for e in final_entries if e.get('status') == 'dynamic']

        print(f"   Estáticas: {len(static_entries)}")
        print(f"   Dinâmicas: {len(dynamic_entries)}")

        print("\n   Entradas estáticas:")
        for entry in static_entries:
            ip = entry.get('address', 'N/A')
            mac = entry.get('mac-address', 'N/A')
            interface = entry.get('interface', 'N/A')
            print(f"   • {ip:15} -> {mac:17} ({interface})")

        controller.close()
        print("\n🔌 Conexão fechada")

        return True

    except Exception as e:
        print(f"❌ Erro nas operações ARP: {e}")
        return False

def main():
    print("🔧 Teste Avançado de Regras ARP - Brazcom ISP")
    print("=" * 70)

    router_data = get_router_from_db()

    if not router_data:
        print("❌ Não foi possível obter dados do router do banco")
        return

    print(f"📋 Router: {router_data['nome']} ({router_data['ip']})")
    print()

    success = test_arp_operations(router_data)

    if success:
        print("\n🎉 Teste de regras ARP concluído com sucesso!")
        print("💡 Verificações no Winbox:")
        print("   • IP → ARP (deve mostrar as entradas estáticas)")
        print("   • Procure por: 192.168.18.200 e 192.168.18.201")
        print("💡 Teste de conectividade:")
        print("   • ping 192.168.18.200 (deve resolver para DE:AD:BE:EF:CA:FE)")
        print("   • arp -a (no Windows) ou arp -n (no Linux)")
    else:
        print("\n❌ Falha no teste de regras ARP")

if __name__ == "__main__":
    main()