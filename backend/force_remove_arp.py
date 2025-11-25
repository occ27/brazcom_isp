#!/usr/bin/env python3
"""
Script para forçar remoção completa das entradas ARP de teste
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

def force_remove_arp_entries(router_data):
    """Força remoção completa das entradas ARP de teste"""
    print(f"💪 Forçando remoção completa das entradas ARP de teste")
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

        arp_resource = controller._api.get_resource('ip/arp')

        # IPs de teste a serem removidos
        test_ips = ['192.168.18.100', '192.168.18.200', '192.168.18.201']

        print("\n📋 Situação atual da tabela ARP:")
        current_entries = arp_resource.get()
        print(f"   Total: {len(current_entries)} entradas")

        for entry in current_entries:
            ip = entry.get('address', 'N/A')
            mac = entry.get('mac-address', 'N/A')
            interface = entry.get('interface', 'N/A')
            entry_id = entry.get('.id', 'N/A')
            is_test = ip in test_ips
            marker = "🎯" if is_test else "   "
            print(f"{marker} • {ip:15} -> {mac:17} ({interface}) [ID: {entry_id}]")

        # Estratégia: Remover TODAS as entradas que correspondem aos IPs de teste
        removed_count = 0

        for test_ip in test_ips:
            print(f"\n🗑️  Removendo TODAS as entradas para IP: {test_ip}")

            # Buscar todas as entradas com este IP
            entries_to_remove = arp_resource.get(address=test_ip)

            if entries_to_remove:
                for entry in entries_to_remove:
                    entry_id = entry.get('.id')
                    mac = entry.get('mac-address', 'N/A')
                    try:
                        arp_resource.remove(id=entry_id)
                        print(f"   ✅ Removida: {test_ip} -> {mac} (ID: {entry_id})")
                        removed_count += 1
                    except Exception as e:
                        print(f"   ❌ Erro ao remover {entry_id}: {e}")
            else:
                print(f"   ℹ️  Nenhuma entrada encontrada para {test_ip}")

        # Verificação final
        print(f"\n🔍 Verificação final após remoção:")
        final_entries = arp_resource.get()
        print(f"   Total restante: {len(final_entries)} entradas")
        print(f"   Removidas: {removed_count}")

        test_entries_remaining = [e for e in final_entries if e.get('address') in test_ips]

        if test_entries_remaining:
            print("   ⚠️  Ainda restam entradas de teste:")
            for entry in test_entries_remaining:
                ip = entry.get('address', 'N/A')
                mac = entry.get('mac-address', 'N/A')
                print(f"      • {ip} -> {mac}")
        else:
            print("   ✅ Nenhuma entrada de teste restante!")

        print("\n📋 Tabela ARP final (apenas entradas originais):")
        original_entries = [e for e in final_entries if e.get('address') not in test_ips]
        for entry in original_entries:
            ip = entry.get('address', 'N/A')
            mac = entry.get('mac-address', 'N/A')
            interface = entry.get('interface', 'N/A')
            print(f"   • {ip:15} -> {mac:17} ({interface})")

        controller.close()
        print("\n🔌 Conexão fechada")

        return len(test_entries_remaining) == 0

    except Exception as e:
        print(f"❌ Erro na remoção forçada: {e}")
        return False

def main():
    print("💪 Remoção Forçada de Entradas ARP de Teste - Brazcom ISP")
    print("=" * 70)

    router_data = get_router_from_db()

    if not router_data:
        print("❌ Não foi possível obter dados do router do banco")
        return

    print(f"📋 Router: {router_data['nome']} ({router_data['ip']})")
    print()

    print("🎯 Estratégia: Remover completamente as entradas de teste")
    print("   • 192.168.18.100 → AA:BB:CC:DD:EE:FF")
    print("   • 192.168.18.200 → DE:AD:BE:EF:CA:FE")
    print("   • 192.168.18.201 → BA:DC:0F:FE:ED:01")
    print()

    success = force_remove_arp_entries(router_data)

    if success:
        print("\n🎉 SUCESSO TOTAL! Todas as entradas ARP de teste foram removidas!")
        print("💡 Verificações no Winbox:")
        print("   • IP → ARP (deve mostrar apenas entradas originais)")
        print("   • Deve haver apenas 2 entradas: 192.168.18.1 e 192.168.18.4")
    else:
        print("\n⚠️  Algumas entradas de teste podem ter permanecido")

if __name__ == "__main__":
    main()