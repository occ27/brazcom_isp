#!/usr/bin/env python3
"""
Teste direto de operações ARP - abordagem simplificada
"""

import sys
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.models.network import Router
from app.core.config import settings
from app.mikrotik.controller import MikrotikController

def get_router_from_db():
    database_url = settings.DATABASE_URL
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        router = db.query(Router).filter(Router.is_active == True).first()
        if router:
            return {
                'id': router.id,
                'nome': router.nome,
                'ip': router.ip,
                'usuario': router.usuario,
                'senha': router.senha,
                'porta': router.porta or 8728,
                'tipo': router.tipo
            }
    finally:
        db.close()
    return None

def test_arp_operations():
    print("🧪 TESTE DIRETO DE OPERAÇÕES ARP")
    print("=" * 50)

    router_data = get_router_from_db()
    if not router_data:
        print("❌ Router não encontrado")
        return

    controller = MikrotikController(
        host=router_data['ip'],
        username=router_data['usuario'],
        password=router_data['senha'],
        port=router_data['porta'],
        plaintext_login=True
    )

    try:
        controller.connect()
        print("✅ Conectado ao router")

        arp_resource = controller._api.get_resource('ip/arp')

        # 1. Mostrar estado atual
        print("\n📋 Estado atual da tabela ARP:")
        entries = arp_resource.get()
        for entry in entries:
            ip = entry.get('address', 'N/A')
            mac = entry.get('mac-address', 'N/A')
            interface = entry.get('interface', 'N/A')
            is_test = ip in ['192.168.18.200', '192.168.18.201']
            marker = "🎯" if is_test else "   "
            print(f"{marker} {ip:15} -> {mac:17} ({interface})")

        # 2. Tentar remover entradas de teste diretamente
        test_ips = ['192.168.18.200', '192.168.18.201']
        removed = 0

        for ip in test_ips:
            print(f"\n🗑️  Removendo {ip}...")
            try:
                # Buscar e remover
                existing = arp_resource.get(address=ip)
                if existing:
                    for entry in existing:
                        entry_id = entry.get('.id')
                        print(f"   Removendo ID: {entry_id}")
                        arp_resource.remove(id=entry_id)
                        removed += 1
                        print("   ✅ Removido")
                else:
                    print("   ℹ️  Não encontrado")
            except Exception as e:
                print(f"   ❌ Erro: {e}")

        # 3. Verificar resultado
        print(f"\n📊 Removidos: {removed}")
        print("🔍 Verificação final:")
        final_entries = arp_resource.get()
        test_remaining = [e for e in final_entries if e.get('address') in test_ips]

        if test_remaining:
            print("❌ Ainda restam entradas de teste:")
            for entry in test_remaining:
                print(f"   🚨 {entry.get('address')} -> {entry.get('mac-address')}")
            return False
        else:
            print("✅ Nenhuma entrada de teste restante!")
            return True

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False
    finally:
        controller.close()

if __name__ == "__main__":
    success = test_arp_operations()
    if success:
        print("\n🎉 OPERAÇÕES ARP FUNCIONANDO!")
    else:
        print("\n⚠️  Problemas nas operações ARP")