#!/usr/bin/env python3
"""
Script para adicionar entrada ARP de teste na RouterBoard
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

def add_test_arp_entry(router_data):
    """Adiciona uma entrada ARP de teste"""
    print(f"🔧 Adicionando entrada ARP de teste no router: {router_data['nome']}")
    print("-" * 60)

    try:
        # Criar controlador MikroTik
        controller = MikrotikController(
            host=router_data['ip'],
            username=router_data['usuario'],
            password=router_data['senha'],
            port=router_data['porta'],
            plaintext_login=True
        )

        # Conectar
        print("🔗 Conectando ao router...")
        controller.connect()
        print("✅ Conexão estabelecida!")

        # Dados da entrada ARP de teste
        test_ip = "192.168.18.100"  # IP de teste na mesma rede
        test_mac = "AA:BB:CC:DD:EE:FF"  # MAC fictício para teste
        test_interface = "ether1"  # Interface principal

        print(f"📝 Adicionando entrada ARP:")
        print(f"   IP: {test_ip}")
        print(f"   MAC: {test_mac}")
        print(f"   Interface: {test_interface}")

        # Adicionar entrada ARP
        result = controller.set_arp_entry(
            ip=test_ip,
            mac=test_mac,
            interface=test_interface
        )

        if result:
            print("✅ Entrada ARP adicionada com sucesso!")
        else:
            print("❌ Falha ao adicionar entrada ARP")

        # Listar entradas ARP para verificar
        print("\n📋 Verificando entradas ARP atuais:")
        try:
            arp_resource = controller._api.get_resource('ip/arp')
            arp_entries = arp_resource.get()

            print(f"   Total de entradas ARP: {len(arp_entries)}")
            print("   Últimas 5 entradas:")

            for entry in arp_entries[-5:]:
                ip = entry.get('address', 'N/A')
                mac = entry.get('mac-address', 'N/A')
                interface = entry.get('interface', 'N/A')
                status = entry.get('status', 'N/A')
                print(f"   • {ip} -> {mac} ({interface}) [{status}]")

        except Exception as e:
            print(f"   ❌ Erro ao listar ARP: {e}")

        # Fechar conexão
        controller.close()
        print("\n🔌 Conexão fechada")

        return True

    except Exception as e:
        print(f"❌ Erro ao adicionar entrada ARP: {e}")
        return False

def main():
    print("🔧 Teste de Adição de Entrada ARP - Brazcom ISP")
    print("=" * 60)

    # Obter dados do router do banco
    router_data = get_router_from_db()

    if not router_data:
        print("❌ Não foi possível obter dados do router do banco")
        return

    print(f"📋 Router: {router_data['nome']} ({router_data['ip']})")
    print()

    # Adicionar entrada ARP de teste
    success = add_test_arp_entry(router_data)

    if success:
        print("\n🎉 Entrada ARP de teste adicionada com sucesso!")
        print("💡 Verifique no Winbox: IP → ARP")
        print("💡 Procure por: 192.168.18.100 -> AA:BB:CC:DD:EE:FF")
    else:
        print("\n❌ Falha ao adicionar entrada ARP")

if __name__ == "__main__":
    main()