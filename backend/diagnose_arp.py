#!/usr/bin/env python3
"""
Diagnóstico detalhado das entradas ARP no RouterOS
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

def diagnose_arp_entries():
    print("🔍 DIAGNÓSTICO DETALHADO DAS ENTRADAS ARP")
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

        # 1. Obter TODAS as informações das entradas
        print("\n📋 ANÁLISE DETALHADA DAS ENTRADAS ARP:")
        entries = arp_resource.get()

        for i, entry in enumerate(entries, 1):
            print(f"\n🔹 Entrada {i}:")
            for key, value in entry.items():
                print(f"   {key:15} = {value}")

            # Classificar a entrada
            ip = entry.get('address', '')
            is_test = ip in ['192.168.18.200', '192.168.18.201']
            status = entry.get('status', 'unknown')
            interface = entry.get('interface', 'unknown')

            print(f"   📊 Classificação: {'🎯 TESTE' if is_test else '   NORMAL'}")
            print(f"   📊 Status: {status}")
            print(f"   📊 Interface: {interface}")

        # 2. Testar se conseguimos modificar uma entrada existente
        print("\n🔧 TESTE DE MODIFICAÇÃO:")
        test_entries = [e for e in entries if e.get('address') in ['192.168.18.200', '192.168.18.201']]

        if test_entries:
            entry = test_entries[0]
            entry_id = entry.get('.id')
            current_mac = entry.get('mac-address')
            new_mac = "FF:FF:FF:FF:FF:FF"

            print(f"   Modificando {entry.get('address')} de {current_mac} para {new_mac}")

            try:
                arp_resource.update(id=entry_id, **{'mac-address': new_mac})
                print("   ✅ Modificação aplicada")

                # Verificar se mudou
                updated = arp_resource.get(address=entry.get('address'))
                if updated:
                    updated_mac = updated[0].get('mac-address')
                    if updated_mac == new_mac:
                        print(f"   ✅ MAC alterado para: {updated_mac}")
                    else:
                        print(f"   ⚠️  MAC ainda é: {updated_mac}")

            except Exception as e:
                print(f"   ❌ Erro na modificação: {e}")

        # 3. Testar criação de uma entrada completamente nova
        print("\n🆕 TESTE DE CRIAÇÃO NOVA:")
        new_ip = "192.168.18.199"
        new_mac = "AA:BB:CC:DD:EE:FF"

        try:
            result = arp_resource.add(
                address=new_ip,
                mac_address=new_mac,
                interface='ether1'
            )
            print(f"   ✅ Nova entrada criada: {new_ip} -> {new_mac}")
            print(f"   📊 Resultado: {result}")

            # Verificar se foi criada
            verify = arp_resource.get(address=new_ip)
            if verify:
                print("   ✅ Verificação: Entrada existe")
                # Remover a entrada de teste
                arp_resource.remove(id=verify[0].get('.id'))
                print("   🗑️  Entrada de teste removida")
            else:
                print("   ❌ Verificação: Entrada não encontrada")

        except Exception as e:
            print(f"   ❌ Erro na criação: {e}")

        # 4. Verificação final
        print("\n🎯 RESUMO FINAL:")
        final_entries = arp_resource.get()
        test_entries_final = [e for e in final_entries if e.get('address') in ['192.168.18.200', '192.168.18.201']]

        print(f"   Total de entradas: {len(final_entries)}")
        print(f"   Entradas de teste restantes: {len(test_entries_final)}")

        if test_entries_final:
            print("   ❌ PROBLEMA: Entradas de teste persistem")
            for entry in test_entries_final:
                print(f"      🚨 {entry.get('address')} -> {entry.get('mac-address')}")
        else:
            print("   ✅ SUCESSO: Nenhuma entrada de teste restante")

    except Exception as e:
        print(f"❌ Erro no diagnóstico: {e}")
    finally:
        controller.close()

if __name__ == "__main__":
    diagnose_arp_entries()