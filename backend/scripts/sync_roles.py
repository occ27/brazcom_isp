import sys
import os
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import Empresa
from app.models.access_control import Role, Permission

def fix_missing_roles():
    db = SessionLocal()
    try:
        source_empresa_id = 1
        source_roles = db.query(Role).filter(Role.empresa_id == source_empresa_id).all()
        
        if not source_roles:
            print("Nenhum perfil encontrado na Empresa ID 1 para usar como modelo.")
            return

        # Buscar todas as empresas exceto a 1
        empresas = db.query(Empresa).filter(Empresa.id != source_empresa_id).all()
        
        for empresa in empresas:
            print(f"Verificando Empresa: {empresa.razao_social} (ID: {empresa.id})")
            
            for src_role in source_roles:
                # Verificar se a empresa já tem uma role com este nome
                exists = db.query(Role).filter(
                    Role.empresa_id == empresa.id,
                    Role.name == src_role.name
                ).first()
                
                if not exists:
                    print(f"  -> Clonando perfil: {src_role.name}")
                    new_role = Role(
                        name=src_role.name,
                        description=src_role.description,
                        empresa_id=empresa.id
                    )
                    # Copiar permissões associadas
                    new_role.permissions = src_role.permissions[:]
                    db.add(new_role)
                else:
                    # Se a role já existe, garantir que as permissões estejam sincronizadas (opcional)
                    print(f"  -> Perfil {src_role.name} já existe. Sincronizando permissões...")
                    # Adicionar permissões que faltam
                    current_p_ids = {p.id for p in exists.permissions}
                    for p in src_role.permissions:
                        if p.id not in current_p_ids:
                            exists.permissions.append(p)
            
            db.commit()
            print(f"Empresa {empresa.id} processada.\n")

        print("Processo concluído com sucesso!")

    except Exception as e:
        print(f"Erro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Garantir que o python encontre o módulo 'app'
    sys.path.append(os.getcwd())
    fix_missing_roles()
