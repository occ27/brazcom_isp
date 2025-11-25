#!/usr/bin/env python3
"""Script de teste para debug da sincronização de interfaces."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.crud import crud_router
from app.core.security import decrypt_password
from app.mikrotik.controller import MikrotikController

def test_sync_interfaces(router_id: int = 1):
    """Testa a sincronização de interfaces para debug."""
    try:
        db = SessionLocal()

        # Buscar router
        router = crud_router.get_router(db=db, router_id=router_id, empresa_id=1)
        if not router:
            print("Router não encontrado")
            return

        print(f"Router encontrado: {router.nome} - IP: {router.ip}")

        # Descriptografar senha
        try:
            password = decrypt_password(router.senha)
            print("Senha descriptografada com sucesso")
        except Exception as e:
            print(f"Erro ao descriptografar senha: {e}")
            return

        # Conectar ao MikroTik
        try:
            mk = MikrotikController(
                host=router.ip,
                username=router.usuario,
                password=password,
                port=router.porta or 8728
            )
            print("MikrotikController criado com sucesso")
        except Exception as e:
            print(f"Erro ao criar MikrotikController: {e}")
            return

        # Testar conexão e buscar interfaces
        try:
            print("Tentando conectar...")
            mikrotik_interfaces = mk.get_interfaces()
            print(f"Interfaces encontradas: {len(mikrotik_interfaces)}")
            for interface in mikrotik_interfaces[:3]:  # Mostrar primeiras 3
                print(f"  - {interface.get('name')}: {interface.get('type')}")

            mk.close()
            print("Conexão fechada com sucesso")

        except Exception as e:
            print(f"Erro ao buscar interfaces: {e}")
            print(f"Tipo do erro: {type(e)}")
            import traceback
            traceback.print_exc()

        db.close()

    except Exception as e:
        print(f"Erro geral: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    router_id = 1  # Você pode alterar este ID
    test_sync_interfaces(router_id)