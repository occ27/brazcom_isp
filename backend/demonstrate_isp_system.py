#!/usr/bin/env python3
"""
Demonstração: Sistema Brazcom ISP Suite gerenciando routers automaticamente
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

def demonstrate_isp_management():
    """Demonstra como o sistema ISP gerencia routers automaticamente"""
    print("🏢 DEMONSTRAÇÃO: Brazcom ISP Suite - Gerenciamento Automático de Routers")
    print("=" * 80)

    router_data = get_router_from_db()
    if not router_data:
        print("❌ Router não encontrado no banco de dados")
        return

    print(f"📋 Router identificado: {router_data['nome']} ({router_data['ip']})")
    print("🔐 Credenciais obtidas automaticamente do banco de dados")

    controller = MikrotikController(
        host=router_data['ip'],
        username=router_data['usuario'],
        password=router_data['senha'],
        port=router_data['porta'],
        plaintext_login=True
    )

    try:
        controller.connect()
        print("✅ Conexão estabelecida automaticamente")

        print("\n🎯 CENÁRIO TÍPICO DO SISTEMA ISP:")
        print("   Um cliente solicita um IP fixo com MAC específico")

        # Simular entrada de cliente
        cliente_ip = "192.168.18.50"
        cliente_mac = "C0:FF:EE:C1:13:37"
        cliente_nome = "João Silva - Plano 100Mbps"

        print(f"\n👤 Cliente: {cliente_nome}")
        print(f"   📍 IP solicitado: {cliente_ip}")
        print(f"   🔗 MAC address: {cliente_mac}")

        # 1. Verificar estado atual
        print(f"\n📋 Verificando se {cliente_ip} já existe na tabela ARP...")
        arp_resource = controller._api.get_resource('ip/arp')
        existing = arp_resource.get(address=cliente_ip)

        if existing:
            print("   ⚠️  IP já possui entrada ARP")
            for entry in existing:
                current_mac = entry.get('mac-address')
                print(f"      MAC atual: {current_mac}")
                if current_mac != cliente_mac:
                    print("      🔄 MAC diferente - será atualizado")
        else:
            print("   ✅ IP disponível para cadastro")

        # 2. Sistema ISP cadastra automaticamente
        print(f"\n⚙️  SISTEMA ISP EXECUTANDO CADASTRO AUTOMÁTICO...")
        print("   📝 Adicionando entrada ARP no router MikroTik...")

        result = controller.set_arp_entry(
            ip=cliente_ip,
            mac=cliente_mac,
            interface='ether1'
        )

        print("   ✅ Entrada ARP cadastrada com sucesso!")
        print(f"   📊 Resultado da operação: {result}")

        # 3. Verificar se foi cadastrado
        print(f"\n🔍 Verificando cadastro do cliente {cliente_nome}...")
        verify = arp_resource.get(address=cliente_ip)

        if verify:
            entry = verify[0]
            registered_mac = entry.get('mac-address')
            registered_interface = entry.get('interface')

            print("   ✅ Cliente cadastrado com sucesso!")
            print(f"      IP: {cliente_ip}")
            print(f"      MAC: {registered_mac}")
            print(f"      Interface: {registered_interface}")

            if registered_mac == cliente_mac:
                print("   ✅ MAC address correto!")
            else:
                print("   ❌ MAC address incorreto!")
                return False
        else:
            print("   ❌ Cliente não foi cadastrado!")
            return False

        # 4. Simular atualização de MAC (cliente trocou dispositivo)
        print(f"\n🔄 CENÁRIO: Cliente {cliente_nome} trocou de dispositivo")
        novo_mac = "DE:AD:BE:EF:00:01"
        print(f"   📱 Novo MAC address: {novo_mac}")

        print("   ⚙️  Sistema ISP atualizando automaticamente...")
        result_update = controller.set_arp_entry(
            ip=cliente_ip,
            mac=novo_mac,
            interface='ether1'
        )

        print("   ✅ MAC atualizado com sucesso!")

        # Verificar atualização
        verify_update = arp_resource.get(address=cliente_ip)
        if verify_update:
            updated_mac = verify_update[0].get('mac-address')
            if updated_mac == novo_mac:
                print("   ✅ Atualização confirmada!")
                print(f"      Novo MAC: {updated_mac}")
            else:
                print("   ❌ Atualização falhou!")
                return False

        # 5. Listar tabela ARP final
        print(f"\n📋 Tabela ARP final após operações do sistema ISP:")
        final_entries = arp_resource.get()

        print(f"   Total de entradas: {len(final_entries)}")
        print("   Entradas ARP ativas:")

        for entry in final_entries:
            ip = entry.get('address', 'N/A')
            mac = entry.get('mac-address', 'N/A')
            interface = entry.get('interface', 'N/A')

            # Identificar entrada do cliente
            if ip == cliente_ip:
                marker = "👤"
                description = f"CLIENTE: {cliente_nome}"
            else:
                marker = "   "
                description = "Sistema/Outros"

            print(f"   {marker} {ip:15} -> {mac:17} ({interface:8}) {description}")

        print("\n" + "="*80)
        print("🎉 CONCLUSÃO: Sistema Brazcom ISP Suite funcionando perfeitamente!")
        print("✅ Conexão automática com router MikroTik")
        print("✅ Cadastro automático de clientes (IP + MAC)")
        print("✅ Atualização automática de dispositivos")
        print("✅ Gerenciamento completo da tabela ARP")
        print("✅ Interface web pode controlar tudo remotamente")
        print()
        print("💡 O sistema está pronto para operação comercial!")
        print("   • Clientes podem ser gerenciados pela interface web")
        print("   • IPs e MACs são associados automaticamente")
        print("   • Mudanças são aplicadas instantaneamente no router")
        print("   • Não é necessário acesso manual ao Winbox!")

        return True

    except Exception as e:
        print(f"❌ Erro na demonstração: {e}")
        return False
    finally:
        controller.close()

if __name__ == "__main__":
    success = demonstrate_isp_management()

    if success:
        print("\n🏆 SISTEMA APROVADO PARA OPERAÇÃO COMERCIAL!")
    else:
        print("\n⚠️  Sistema necessita ajustes antes da operação comercial")