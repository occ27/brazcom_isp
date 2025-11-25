#!/usr/bin/env python3
"""
Remove a entrada ARP para 192.168.18.199 no router cadastrado
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


def main():
    target_ip = '192.168.18.199'
    print(f"🗂 Removendo entrada ARP de teste: {target_ip}")

    router = get_router_from_db()
    if not router:
        print("❌ Router não encontrado no banco de dados")
        return

    controller = MikrotikController(
        host=router['ip'],
        username=router['usuario'],
        password=router['senha'],
        port=router['porta'],
        plaintext_login=True
    )

    try:
        controller.connect()
        print(f"🔗 Conectado ao router {router['nome']} ({router['ip']})")

        # Usar método do controlador para remoção
        removed = controller.remove_arp_entry(ip=target_ip)
        print(f"🗑️  Entradas removidas (segundo controller): {removed}")

        # Verificação direta via recurso
        arp = controller._api.get_resource('ip/arp')
        remaining = arp.get(address=target_ip)
        if remaining:
            print(f"❌ Entrada ainda presente: {len(remaining)} registro(s)")
            for r in remaining:
                print(f"   - id={r.get('.id')} address={r.get('address')} mac={r.get('mac-address')} dynamic={r.get('dynamic')}")
        else:
            print("✅ Entrada removida com sucesso (não encontrada na tabela ARP)")

    except Exception as e:
        print(f"❌ Erro ao remover entrada ARP: {e}")
    finally:
        controller.close()

if __name__ == '__main__':
    main()
