#!/usr/bin/env python3
"""
Teste final com método melhorado de remoção ARP
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

def final_arp_test():
    print("🎯 TESTE FINAL - REMOÇÃO ARP COM MÉTODO MELHORADO")
    print("=" * 60)

    router_data = get_router_from_db()
    if not router_data:
        print("❌ Router não encontrado")
        return False

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

        # 1. Estado inicial
        print("\n📋 Estado inicial da tabela ARP:")
        arp_resource = controller._api.get_resource('ip/arp')
        entries = arp_resource.get()

        for entry in entries:
            ip = entry.get('address', 'N/A')
            mac = entry.get('mac-address', 'N/A')
            interface = entry.get('interface', 'N/A')
            entry_id = entry.get('.id') or entry.get('id', 'N/A')
            is_test = ip in ['192.168.18.200', '192.168.18.201']
            marker = "🎯" if is_test else "   "
            print(f"{marker} {ip:15} -> {mac:17} ({interface}) [ID: {entry_id}]")

        # 2. Testar remoção usando o método melhorado
        test_ips = ['192.168.18.200', '192.168.18.201']
        total_removed = 0

        for ip in test_ips:
            print(f"\n🗑️  Removendo entrada: {ip}")
            removed = controller.remove_arp_entry(ip=ip)
            if removed > 0:
                print(f"   ✅ {removed} entrada(s) removida(s) para {ip}")
                total_removed += removed
            else:
                print(f"   ❌ Falha ao remover {ip}")

        # 3. Verificação final
        print(f"\n📊 Total removido: {total_removed}")
        print("🔍 Verificação final:")

        final_entries = arp_resource.get()
        test_remaining = [e for e in final_entries if e.get('address') in test_ips]

        print(f"   Total de entradas restantes: {len(final_entries)}")
        print(f"   Entradas de teste restantes: {len(test_remaining)}")

        if test_remaining:
            print("❌ RESULTADO: Ainda restam entradas de teste")
            for entry in test_remaining:
                ip = entry.get('address')
                mac = entry.get('mac-address')
                print(f"   🚨 {ip} -> {mac}")
            return False
        else:
            print("✅ RESULTADO: SUCESSO! Nenhuma entrada de teste restante")
            return True

    except Exception as e:
        print(f"❌ Erro no teste final: {e}")
        return False
    finally:
        controller.close()

def test_full_workflow():
    """Testa o workflow completo: criar e remover"""
    print("\n🔄 TESTANDO WORKFLOW COMPLETO: CRIAR + REMOVER")
    print("-" * 60)

    router_data = get_router_from_db()
    if not router_data:
        return False

    controller = MikrotikController(
        host=router_data['ip'],
        username=router_data['usuario'],
        password=router_data['senha'],
        port=router_data['porta'],
        plaintext_login=True
    )

    try:
        controller.connect()

        # 1. Criar entrada de teste
        test_ip = "192.168.18.250"
        test_mac = "AB:CD:EF:01:23:45"

        print(f"📝 Criando entrada de teste: {test_ip} -> {test_mac}")
        result = controller.set_arp_entry(
            ip=test_ip,
            mac=test_mac,
            interface='ether1'
        )
        print(f"   ✅ Criada (resultado: {result})")

        # 2. Verificar se foi criada
        arp_resource = controller._api.get_resource('ip/arp')
        verify = arp_resource.get(address=test_ip)
        if verify:
            print("   ✅ Verificação: Entrada existe")
        else:
            print("   ❌ Verificação: Entrada não encontrada")
            return False

        # 3. Remover a entrada
        print(f"🗑️  Removendo entrada: {test_ip}")
        removed = controller.remove_arp_entry(ip=test_ip)
        if removed > 0:
            print(f"   ✅ Removida ({removed} entrada(s))")
        else:
            print("   ❌ Falha na remoção")
            return False

        # 4. Verificar se foi removida
        final_check = arp_resource.get(address=test_ip)
        if final_check:
            print("   ❌ Problema: Entrada ainda existe após remoção")
            return False
        else:
            print("   ✅ Confirmação: Entrada removida com sucesso")
            return True

    except Exception as e:
        print(f"❌ Erro no workflow: {e}")
        return False
    finally:
        controller.close()

if __name__ == "__main__":
    # Teste 1: Remover entradas existentes
    success1 = final_arp_test()

    # Teste 2: Workflow completo
    success2 = test_full_workflow()

    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES:")
    print(f"   Remoção de entradas existentes: {'✅ OK' if success1 else '❌ FALHA'}")
    print(f"   Workflow criar+remover: {'✅ OK' if success2 else '❌ FALHA'}")

    if success1 and success2:
        print("\n🎉 SUCESSO TOTAL! Sistema ARP funcionando perfeitamente!")
        print("💡 O Brazcom ISP Suite pode gerenciar routers automaticamente!")
    else:
        print("\n⚠️  Ainda há problemas com operações ARP")