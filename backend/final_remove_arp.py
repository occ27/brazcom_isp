#!/usr/bin/env python3
"""
Script final para remover completamente as entradas ARP de teste usando o controlador
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

def final_remove_test_entries(router_data):
    """Remove definitivamente as entradas ARP de teste usando o controlador"""
    print(f"🎯 Remoção final das entradas ARP de teste")
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

        # IPs de teste a serem removidos
        test_ips = ['192.168.18.100', '192.168.18.200', '192.168.18.201']

        print("\n📋 Situação antes da remoção final:")
        arp_resource = controller._api.get_resource('ip/arp')
        current_entries = arp_resource.get()
        print(f"   Total: {len(current_entries)} entradas")

        for entry in current_entries:
            ip = entry.get('address', 'N/A')
            mac = entry.get('mac-address', 'N/A')
            interface = entry.get('interface', 'N/A')
            is_test = ip in test_ips
            marker = "🎯" if is_test else "   "
            print(f"{marker} • {ip:15} -> {mac:17} ({interface})")

        # Remover cada entrada de teste usando o método do controlador
        total_removed = 0

        for test_ip in test_ips:
            print(f"\n🗑️  Removendo entrada para IP: {test_ip}")
            removed = controller.remove_arp_entry(ip=test_ip)
            if removed > 0:
                print(f"   ✅ Removidas {removed} entrada(s) para {test_ip}")
                total_removed += removed
            else:
                print(f"   ℹ️  Nenhuma entrada encontrada para {test_ip}")

        # Verificação final
        print(f"\n🔍 Verificação final:")
        final_entries = arp_resource.get()
        print(f"   Total restante: {len(final_entries)} entradas")
        print(f"   Total removidas: {total_removed}")

        # Verificar se restaram entradas de teste
        test_remaining = [e for e in final_entries if e.get('address') in test_ips]

        if test_remaining:
            print("   ❌ Ainda restam entradas de teste:")
            for entry in test_remaining:
                ip = entry.get('address')
                mac = entry.get('mac-address')
                print(f"      • {ip} -> {mac}")
            return False
        else:
            print("   ✅ Nenhuma entrada de teste restante!")

        print("\n📋 Tabela ARP limpa (apenas entradas originais):")
        original_entries = [e for e in final_entries if e.get('address') not in test_ips]
        for entry in original_entries:
            ip = entry.get('address', 'N/A')
            mac = entry.get('mac-address', 'N/A')
            interface = entry.get('interface', 'N/A')
            print(f"   • {ip:15} -> {mac:17} ({interface})")

        controller.close()
        print("\n🔌 Conexão fechada")

        return len(test_remaining) == 0

    except Exception as e:
        print(f"❌ Erro na remoção final: {e}")
        return False

def main():
    print("🎯 Remoção Final das Entradas ARP de Teste - Brazcom ISP")
    print("=" * 70)

    router_data = get_router_from_db()

    if not router_data:
        print("❌ Não foi possível obter dados do router do banco")
        return

    print(f"📋 Router: {router_data['nome']} ({router_data['ip']})")
    print()

    print("🎯 Objetivo: Remover completamente todas as entradas de teste")
    print("   • 192.168.18.100 → AA:BB:CC:DD:EE:FF")
    print("   • 192.168.18.200 → DE:AD:BE:EF:CA:FE")
    print("   • 192.168.18.201 → BA:DC:0F:FE:ED:01")
    print()

    success = final_remove_test_entries(router_data)

    if success:
        print("\n🎉 SUCESSO TOTAL! Tabela ARP completamente limpa!")
        print("💡 Verificações no Winbox:")
        print("   • IP → ARP")
        print("   • Deve mostrar apenas as 2 entradas originais:")
        print("     - 192.168.18.1 → 1C:73:E2:54:25:3B")
        print("     - 192.168.18.4 → A8:A1:59:7C:AD:FF")
    else:
        print("\n⚠️  Ainda podem restar algumas entradas de teste")

if __name__ == "__main__":
    main()