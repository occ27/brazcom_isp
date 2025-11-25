#!/usr/bin/env python3
"""
Teste de diferentes métodos de remoção ARP
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

def test_removal_methods():
    print("🔧 TESTE DE DIFERENTES MÉTODOS DE REMOÇÃO ARP")
    print("=" * 60)

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

        # 1. Estado inicial
        print("\n📋 Estado inicial:")
        entries = arp_resource.get()
        test_entries = [e for e in entries if e.get('address') in ['192.168.18.200', '192.168.18.201']]

        for entry in test_entries:
            ip = entry.get('address')
            mac = entry.get('mac-address')
            entry_id = entry.get('.id')
            print(f"   🎯 {ip} -> {mac} [ID: {entry_id}]")

        # 2. Método 1: Remoção direta com ID original
        print("\n🔧 MÉTODO 1: Remoção direta com ID original")
        for entry in test_entries:
            ip = entry.get('address')
            entry_id = entry.get('.id')
            print(f"   Removendo {ip} com ID {entry_id}...")

            try:
                arp_resource.remove(id=entry_id)
                print("      ✅ Comando executado")
            except Exception as e:
                print(f"      ❌ Erro: {e}")

        # Verificar
        check_entries = arp_resource.get(address='192.168.18.200')
        if check_entries:
            print("      ⚠️  Ainda existe após Método 1")
        else:
            print("      ✅ Removido com Método 1")
            return True

        # 3. Método 2: Remoção com ID sem asterisco
        print("\n🔧 MÉTODO 2: Remoção com ID sem asterisco")
        for entry in test_entries:
            ip = entry.get('address')
            entry_id = entry.get('.id')
            clean_id = entry_id.lstrip('*') if entry_id.startswith('*') else entry_id
            print(f"   Removendo {ip} com ID limpo {clean_id}...")

            try:
                arp_resource.remove(id=clean_id)
                print("      ✅ Comando executado")
            except Exception as e:
                print(f"      ❌ Erro: {e}")

        # Verificar
        check_entries = arp_resource.get(address='192.168.18.200')
        if check_entries:
            print("      ⚠️  Ainda existe após Método 2")
        else:
            print("      ✅ Removido com Método 2")
            return True

        # 4. Método 3: Usar set para sobrescrever com dados vazios
        print("\n🔧 MÉTODO 3: Sobrescrever com dados inválidos")
        try:
            # Tentar definir uma entrada com MAC inválido
            arp_resource.add(
                address='192.168.18.200',
                mac_address='00:00:00:00:00:00',
                interface='ether1'
            )
            print("      ✅ Entrada sobrescrita com MAC inválido")
        except Exception as e:
            print(f"      ❌ Erro na sobrescrita: {e}")

        # 5. Método 4: Verificar se existe método 'set' ou 'update'
        print("\n🔧 MÉTODO 4: Investigar métodos disponíveis")
        methods = [m for m in dir(arp_resource) if not m.startswith('_')]
        print("      Métodos disponíveis:")
        for method in methods:
            print(f"         • {method}")

        # Tentar método 'set' se existir
        if hasattr(arp_resource, 'set'):
            print("      🧪 Testando método 'set'...")
            try:
                arp_resource.set('.id=*4', 'disabled=yes')
                print("         ✅ Método set executado")
            except Exception as e:
                print(f"         ❌ Erro no set: {e}")

        # 6. Verificação final
        print("\n🎯 VERIFICAÇÃO FINAL:")
        final_entries = arp_resource.get()
        test_remaining = [e for e in final_entries if e.get('address') in ['192.168.18.200', '192.168.18.201']]

        if test_remaining:
            print("❌ FALHA: Entradas persistem após todos os métodos")
            for entry in test_remaining:
                print(f"   🚨 {entry.get('address')} -> {entry.get('mac-address')}")
            return False
        else:
            print("✅ SUCESSO: Entradas removidas!")
            return True

    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return False
    finally:
        controller.close()

if __name__ == "__main__":
    success = test_removal_methods()
    if success:
        print("\n🎉 REMOÇÃO ARP FUNCIONANDO!")
    else:
        print("\n⚠️  Problemas persistentes na remoção ARP")