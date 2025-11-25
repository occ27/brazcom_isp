#!/usr/bin/env python3
"""
Script para testar conexão com RouterBoard usando dados do banco Brazcom ISP
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
        # Criar engine do banco
        database_url = settings.DATABASE_URL
        engine = create_engine(database_url)

        # Criar sessão
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        try:
            # Se não especificou ID, pegar o primeiro router ativo
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
                    'porta': router.porta or 8728,  # Usar 8728 se porta for None
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

def test_router_connection(router_data):
    """Testa conexão com o router usando dados do banco"""
    print(f"🔌 Testando conexão com RouterBoard: {router_data['nome']}")
    print(f"🏠 IP: {router_data['ip']}:{router_data['porta']}")
    print(f"👤 Usuário: {router_data['usuario']}")
    print(f"🏷️  Tipo: {router_data['tipo']}")
    print("-" * 50)

    try:
        # Criar controlador MikroTik
        controller = MikrotikController(
            host=router_data['ip'],
            username=router_data['usuario'],
            password=router_data['senha'],
            port=router_data['porta'],
            plaintext_login=True
        )

        # Tentar conectar
        print("🔗 Conectando...")
        controller.connect()
        print("✅ Conexão estabelecida com sucesso!")

        # Obter informações do sistema
        print("\n📊 Informações do RouterBoard:")
        try:
            system_resource = controller._api.get_resource('/system/identity')
            identity = system_resource.get()
            if identity:
                print(f"   🏷️  Nome: {identity[0].get('name', 'N/A')}")
        except:
            print("   🏷️  Nome: Não foi possível obter")

        # Obter informações da placa
        try:
            board_resource = controller._api.get_resource('/system/routerboard')
            board_info = board_resource.get()
            if board_info:
                info = board_info[0]
                print(f"   🔧 Modelo: {info.get('model', 'N/A')}")
                print(f"   📋 Firmware: {info.get('current-firmware', 'N/A')}")
                print(f"   ⚡ Serial: {info.get('serial-number', 'N/A')}")
        except:
            print("   🔧 Informações da placa: Não foi possível obter")

        # Obter versão do RouterOS
        try:
            resource_resource = controller._api.get_resource('/system/resource')
            resource_info = resource_resource.get()
            if resource_info:
                info = resource_info[0]
                print(f"   🖥️  RouterOS: {info.get('version', 'N/A')}")
                print(f"   🏗️  Arquitetura: {info.get('architecture-name', 'N/A')}")
        except:
            print("   🖥️  RouterOS: Não foi possível obter")

        # Obter interfaces (limitado a primeiras 3)
        print("\n🌐 Interfaces (primeiras 3):")
        try:
            interface_resource = controller._api.get_resource('/interface')
            interfaces = interface_resource.get()
            for iface in interfaces[:3]:
                name = iface.get('name', 'N/A')
                tipo = iface.get('type', 'N/A')
                status = 'UP' if iface.get('running') == 'true' else 'DOWN'
                print(f"   • {name} ({tipo}) - {status}")
        except:
            print("   🌐 Interfaces: Não foi possível obter")

        # Fechar conexão
        controller.close()
        print("\n🔌 Conexão fechada")

        return True

    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        print("\n🔧 Possíveis causas:")
        print("   • Porta incorreta (padrão: 8728)")
        print("   • Credenciais inválidas")
        print("   • Router não acessível na rede")
        print("   • API RouterOS desabilitada")
        return False

def main():
    print("🔍 Teste de Conexão com RouterBoard - Dados do Banco Brazcom ISP")
    print("=" * 70)

    # Obter dados do router do banco
    router_data = get_router_from_db()

    if not router_data:
        print("❌ Não foi possível obter dados do router do banco")
        return

    print(f"📋 Router encontrado no banco:")
    print(f"   ID: {router_data['id']}")
    print(f"   Nome: {router_data['nome']}")
    print(f"   IP: {router_data['ip']}")
    print(f"   Porta: {router_data['porta']}")
    print(f"   Usuário: {router_data['usuario']}")
    print(f"   Tipo: {router_data['tipo']}")
    print()

    # Testar conexão
    success = test_router_connection(router_data)

    if success:
        print("\n🎉 SUCESSO! RouterBoard conectado com dados do banco!")
        print("💡 O router está funcionando corretamente no sistema Brazcom ISP")
    else:
        print("\n❌ FALHA na conexão com dados do banco")
        print("\n🔧 PARA DESCOBRIR A PORTA NO WINBOX:")
        print("   1. Abra o Winbox")
        print("   2. Clique em 'Neighbors' para descobrir routers")
        print("   3. Ou digite o IP manualmente")
        print("   4. Na tela de login, observe a porta (geralmente 8728)")
        print("   5. Se conseguir logar, vá em IP > Services")
        print("   6. Procure o serviço 'api' e veja a porta configurada")
        print()
        print("🔧 PORTAS COMUNS DO ROUTEROS:")
        print("   • API: 8728 (padrão)")
        print("   • API-SSL: 8729")
        print("   • Winbox: 8291")
        print("   • HTTP: 80")
        print("   • HTTPS: 443")

if __name__ == "__main__":
    main()