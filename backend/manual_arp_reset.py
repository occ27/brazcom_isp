#!/usr/bin/env python3
"""
Script final: Reset manual da tabela ARP via comandos RouterOS
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

def manual_arp_reset(router_data):
    """Reset manual da tabela ARP via comandos do sistema"""
    print(f"🔧 Reset Manual da Tabela ARP via RouterOS")
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

        print("\n📋 Situação atual da tabela ARP:")
        arp_resource = controller._api.get_resource('ip/arp')
        current_entries = arp_resource.get()
        print(f"   Total: {len(current_entries)} entradas")

        test_ips = ['192.168.18.100', '192.168.18.200', '192.168.18.201']

        for entry in current_entries:
            ip = entry.get('address', 'N/A')
            mac = entry.get('mac-address', 'N/A')
            interface = entry.get('interface', 'N/A')
            is_test = ip in test_ips
            marker = "🎯" if is_test else "   "
            print(f"{marker} • {ip:15} -> {mac:17} ({interface})")

        # Tentar executar comandos do sistema RouterOS
        print("\n🔧 EXECUTANDO COMANDOS DO SISTEMA ROUTEROS:")

        # Comando 1: Limpar cache ARP
        print("   📡 Executando: /ip arp flush")
        try:
            # Tentar executar comando via API
            system_resource = controller._api.get_resource('/')
            result = system_resource.call('ip/arp/flush', {})
            print("   ✅ Comando flush executado")
        except Exception as e:
            print(f"   ❌ Erro no flush: {e}")

        # Comando 2: Remover entradas específicas via terminal
        print("   📡 Executando remoções específicas...")

        for test_ip in test_ips:
            try:
                # Tentar executar: /ip arp remove [find address=IP]
                command = f'/ip arp remove [find address={test_ip}]'
                print(f"      Executando: {command}")

                # Usar o método execute para comandos do terminal
                result = controller._api.execute(command)
                print(f"      ✅ Comando executado para {test_ip}")

            except Exception as e:
                print(f"      ❌ Erro ao executar comando para {test_ip}: {e}")

        # Aguardar processamento
        print("\n⏳ Aguardando processamento dos comandos...")
        import time
        time.sleep(5)

        # Verificação final
        print("\n🎯 VERIFICAÇÃO FINAL APÓS RESET MANUAL:")
        final_entries = arp_resource.get()
        print(f"   Total final: {len(final_entries)} entradas")

        final_test_entries = [e for e in final_entries if e.get('address') in test_ips]

        if final_test_entries:
            print("   ❌ AINDA RESTAM ENTRADAS DE TESTE:")
            for entry in final_test_entries:
                ip = entry.get('address')
                mac = entry.get('mac-address')
                print(f"      🚨 {ip} -> {mac}")

            print("\n🔧 INSTRUÇÕES PARA RESET MANUAL NO WINBOX:")
            print("   1. Abra o Winbox e conecte ao router")
            print("   2. Vá em: IP → ARP")
            print("   3. Selecione as entradas de teste:")
            print("      • 192.168.18.100")
            print("      • 192.168.18.200")
            print("      • 192.168.18.201")
            print("   4. Clique no botão '-' (remover)")
            print("   5. Confirme a remoção")

            success = False
        else:
            print("   ✅ TABELA ARP COMPLETAMENTE LIMPA!")
            success = True

        print("\n📋 Tabela ARP final:")
        clean_entries = [e for e in final_entries if e.get('address') not in test_ips]
        for entry in clean_entries:
            ip = entry.get('address', 'N/A')
            mac = entry.get('mac-address', 'N/A')
            interface = entry.get('interface', 'N/A')
            print(f"   • {ip:15} -> {mac:17} ({interface})")

        controller.close()
        print("\n🔌 Conexão fechada")

        return success

    except Exception as e:
        print(f"❌ Erro no reset manual: {e}")
        return False

def main():
    print("🔧 Reset Manual da Tabela ARP - Brazcom ISP")
    print("=" * 70)

    router_data = get_router_from_db()

    if not router_data:
        print("❌ Não foi possível obter dados do router do banco")
        return

    print(f"📋 Router: {router_data['nome']} ({router_data['ip']})")
    print()

    print("🔧 ESTRATÉGIA: Reset via comandos do sistema RouterOS")
    print("   • Flush do cache ARP")
    print("   • Remoção específica por comandos")
    print("   • Verificação final")
    print()

    success = manual_arp_reset(router_data)

    if success:
        print("\n🎉 RESET MANUAL BEM-SUCEDIDO!")
        print("💡 A tabela ARP está limpa e pronta!")
    else:
        print("\n⚠️  Reset automático falhou")
        print("💡 Use as instruções acima para limpeza manual no Winbox")

if __name__ == "__main__":
    main()