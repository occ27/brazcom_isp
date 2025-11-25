#!/usr/bin/env python3
"""
Script para remover entradas ARP de teste da RouterBoard
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

def remove_test_arp_entries(router_data):
    """Remove as entradas ARP de teste"""
    print(f"🗑️  Removendo entradas ARP de teste do router: {router_data['nome']}")
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

        # Entradas ARP a serem removidas
        test_entries = [
            {'ip': '192.168.18.100', 'mac': 'AA:BB:CC:DD:EE:FF'},
            {'ip': '192.168.18.200', 'mac': 'DE:AD:BE:EF:CA:FE'},
            {'ip': '192.168.18.201', 'mac': 'BA:DC:0F:FE:ED:01'}
        ]

        arp_resource = controller._api.get_resource('ip/arp')

        # 1. Listar entradas ARP atuais antes da remoção
        print("\n📋 Entradas ARP antes da remoção:")
        current_entries = arp_resource.get()
        print(f"   Total: {len(current_entries)} entradas")

        for entry in current_entries:
            ip = entry.get('address', 'N/A')
            mac = entry.get('mac-address', 'N/A')
            interface = entry.get('interface', 'N/A')
            print(f"   • {ip:15} -> {mac:17} ({interface})")

        # 2. Remover cada entrada de teste
        removed_count = 0

        for test_entry in test_entries:
            ip = test_entry['ip']
            mac = test_entry['mac']

            print(f"\n🗑️  Removendo entrada: {ip} -> {mac}")

            # Procurar pela entrada específica
            existing = arp_resource.get(address=ip, mac_address=mac)

            if existing:
                for entry in existing:
                    entry_id = entry.get('.id')
                    arp_resource.remove(id=entry_id)
                    print(f"   ✅ Entrada removida (ID: {entry_id})")
                    removed_count += 1
            else:
                print(f"   ⚠️  Entrada não encontrada: {ip}")

        # 3. Verificar entradas restantes
        print(f"\n📋 Entradas ARP após remoção:")
        remaining_entries = arp_resource.get()
        print(f"   Total: {len(remaining_entries)} entradas")
        print(f"   Removidas: {removed_count}")

        if remaining_entries:
            print("   Entradas restantes:")
            for entry in remaining_entries:
                ip = entry.get('address', 'N/A')
                mac = entry.get('mac-address', 'N/A')
                interface = entry.get('interface', 'N/A')
                print(f"   • {ip:15} -> {mac:17} ({interface})")
        else:
            print("   ℹ️  Tabela ARP vazia")

        controller.close()
        print("\n🔌 Conexão fechada")

        return removed_count > 0

    except Exception as e:
        print(f"❌ Erro ao remover entradas ARP: {e}")
        return False

def main():
    print("🗑️  Remoção de Entradas ARP de Teste - Brazcom ISP")
    print("=" * 70)

    router_data = get_router_from_db()

    if not router_data:
        print("❌ Não foi possível obter dados do router do banco")
        return

    print(f"📋 Router: {router_data['nome']} ({router_data['ip']})")
    print()

    # Entradas que serão removidas
    print("🎯 Entradas ARP a serem removidas:")
    print("   • 192.168.18.100 → AA:BB:CC:DD:EE:FF")
    print("   • 192.168.18.200 → DE:AD:BE:EF:CA:FE")
    print("   • 192.168.18.201 → BA:DC:0F:FE:ED:01")
    print()

    success = remove_test_arp_entries(router_data)

    if success:
        print("\n🎉 Entradas ARP de teste removidas com sucesso!")
        print("💡 Verificações no Winbox:")
        print("   • IP → ARP (deve mostrar apenas entradas originais)")
        print("   • Não deve haver as entradas de teste")
    else:
        print("\n❌ Falha ao remover entradas ARP")

if __name__ == "__main__":
    main()