#!/usr/bin/env python3
"""
Script definitivo para limpeza total da tabela ARP
"""

import sys
import os
import time
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

def nuclear_arp_cleanup(router_data):
    """Limpeza nuclear da tabela ARP - múltiplas tentativas"""
    print(f"💣 Limpeza Nuclear da Tabela ARP")
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

        # IPs de teste a eliminar
        test_ips = ['192.168.18.100', '192.168.18.200', '192.168.18.201']

        print("\n📋 Estado inicial da tabela ARP:")
        initial_entries = arp_resource.get()
        print(f"   Total: {len(initial_entries)} entradas")

        for entry in initial_entries:
            ip = entry.get('address', 'N/A')
            mac = entry.get('mac-address', 'N/A')
            interface = entry.get('interface', 'N/A')
            entry_id = entry.get('.id', 'N/A')
            is_test = ip in test_ips
            marker = "🎯" if is_test else "   "
            print(f"{marker} • {ip:15} -> {mac:17} ({interface}) [ID: {entry_id}]")

        # Estratégia 1: Remoção direta por ID
        print("\n💣 ESTRATÉGIA 1: Remoção direta por ID")
        removed_by_id = 0

        for entry in initial_entries:
            ip = entry.get('address')
            if ip in test_ips:
                entry_id = entry.get('.id')
                try:
                    arp_resource.remove(id=entry_id)
                    print(f"   ✅ Removida por ID: {ip} (ID: {entry_id})")
                    removed_by_id += 1
                except Exception as e:
                    print(f"   ❌ Erro ao remover {ip}: {e}")

        # Pausa para sincronização
        print("\n⏳ Aguardando sincronização...")
        time.sleep(2)

        # Estratégia 2: Verificação e limpeza residual
        print("\n🔍 ESTRATÉGIA 2: Verificação residual")
        residual_entries = arp_resource.get()

        for entry in residual_entries:
            ip = entry.get('address')
            if ip in test_ips:
                entry_id = entry.get('.id')
                mac = entry.get('mac-address')
                try:
                    arp_resource.remove(id=entry_id)
                    print(f"   ✅ Removida residual: {ip} -> {mac}")
                except Exception as e:
                    print(f"   ❌ Erro residual {ip}: {e}")

        # Estratégia 3: Reset da tabela ARP (se necessário)
        print("\n🔄 ESTRATÉGIA 3: Reset da tabela ARP")
        final_entries = arp_resource.get()
        test_remaining = [e for e in final_entries if e.get('address') in test_ips]

        if test_remaining:
            print("   ⚠️  Ainda restam entradas. Tentando reset...")
            # Tentar limpar todas as entradas estáticas
            for entry in final_entries:
                ip = entry.get('address')
                if ip in test_ips:
                    try:
                        # Forçar remoção múltiplas vezes
                        for _ in range(3):
                            arp_resource.remove(id=entry.get('.id'))
                            time.sleep(0.5)
                        print(f"   🔄 Reset aplicado em: {ip}")
                    except:
                        pass

        # Verificação final definitiva
        print("\n🎯 VERIFICAÇÃO FINAL DEFINITIVA")
        time.sleep(3)  # Aguardar mais tempo

        definitive_entries = arp_resource.get()
        print(f"   Total final: {len(definitive_entries)} entradas")

        final_test_entries = [e for e in definitive_entries if e.get('address') in test_ips]

        if final_test_entries:
            print("   ❌ ENTRADAS DE TESTE AINDA PRESENTES:")
            for entry in final_test_entries:
                ip = entry.get('address')
                mac = entry.get('mac-address')
                print(f"      🚨 {ip} -> {mac}")
            success = False
        else:
            print("   ✅ NENHUMA ENTRADA DE TESTE RESTANTE!")
            success = True

        print("\n📋 Tabela ARP final limpa:")
        clean_entries = [e for e in definitive_entries if e.get('address') not in test_ips]
        for entry in clean_entries:
            ip = entry.get('address', 'N/A')
            mac = entry.get('mac-address', 'N/A')
            interface = entry.get('interface', 'N/A')
            print(f"   • {ip:15} -> {mac:17} ({interface})")

        controller.close()
        print("\n🔌 Conexão fechada")

        return success

    except Exception as e:
        print(f"❌ Erro na limpeza nuclear: {e}")
        return False

def main():
    print("💣 Limpeza Nuclear da Tabela ARP - Brazcom ISP")
    print("=" * 70)

    router_data = get_router_from_db()

    if not router_data:
        print("❌ Não foi possível obter dados do router do banco")
        return

    print(f"📋 Router: {router_data['nome']} ({router_data['ip']})")
    print()

    print("💣 OBJETIVO: Eliminar completamente todas as entradas ARP de teste")
    print("   • Estratégia múltipla de remoção")
    print("   • Verificações repetidas")
    print("   • Reset forçado se necessário")
    print()

    success = nuclear_arp_cleanup(router_data)

    if success:
        print("\n🎉 LIMPEZA NUCLEAR BEM-SUCEDIDA!")
        print("💡 A tabela ARP está completamente limpa!")
        print("💡 Verificações no Winbox:")
        print("   • IP → ARP")
        print("   • Deve mostrar apenas as 2 entradas originais")
    else:
        print("\n⚠️  Limpeza nuclear encontrou resistência")
        print("💡 Pode ser necessário reset manual no Winbox")

if __name__ == "__main__":
    main()