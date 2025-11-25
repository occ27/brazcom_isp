#!/usr/bin/env python3
"""
Script para atualizar a senha do router no banco de dados
"""

import sys
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Adicionar o diretório app ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.models.network import Router
from app.core.config import settings

def update_router_password(router_id: int, new_password: str):
    """Atualiza a senha do router no banco de dados"""
    try:
        # Criar engine do banco
        database_url = settings.DATABASE_URL
        engine = create_engine(database_url)

        # Criar sessão
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        try:
            # Buscar router
            router = db.query(Router).filter(Router.id == router_id).first()

            if not router:
                print(f"❌ Router com ID {router_id} não encontrado")
                return False

            # Atualizar senha
            old_password = router.senha
            router.senha = new_password

            # Commit
            db.commit()

            print("✅ Senha atualizada com sucesso!")
            print(f"   Router: {router.nome}")
            print(f"   IP: {router.ip}")
            print(f"   Senha antiga: {old_password}")
            print(f"   Nova senha: {new_password}")

            return True

        finally:
            db.close()

    except Exception as e:
        print(f"❌ Erro ao atualizar senha: {e}")
        return False

def main():
    print("🔐 Atualização de Senha do Router - Brazcom ISP")
    print("=" * 50)

    # Dados do router que vimos no teste anterior
    router_id = 2  # RB 433AH
    new_password = "gruta765"  # Senha fornecida pelo usuário

    print(f"📋 Atualizando senha do Router ID: {router_id}")
    print(f"   Nova senha: {new_password}")
    print()

    success = update_router_password(router_id, new_password)

    if success:
        print("\n🎉 Senha atualizada! Agora teste a conexão novamente.")
        print("💡 Execute: python test_router_db.py")
    else:
        print("\n❌ Falha ao atualizar senha.")

if __name__ == "__main__":
    main()