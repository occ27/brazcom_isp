"""Seed script para popular a tabela `permissions` e associar roles padrão.

Uso:
  cd backend
  venv\Scripts\Activate.ps1   # ou seu venv
  python -m app.scripts.seed_permissions

O script usa `app.core.database.SessionLocal` para obter sessão SQLAlchemy.
Ele cria permissões (se não existirem), cria roles padrão (`Admin`, `Viewer`) e associa permissões.
"""

from typing import List, Tuple

from app.core.database import SessionLocal
from app.models.access_control import Permission, Role

PERMISSIONS: List[Tuple[str, str]] = [
    ("role_manage", "Gerenciar roles (criar/editar/excluir)"),
    ("permission_manage", "Gerenciar permissões (criar/editar/excluir)"),
    ("role_assign", "Atribuir e desatribuir roles a usuários"),
    ("router_manage", "Gerenciar roteadores/MikroTik"),
    ("router_view", "Visualizar roteadores/MikroTik"),
    ("radius_manage", "Gerenciar RADIUS/PPP"),
    ("radius_view", "Visualizar RADIUS/PPP"),
    ("nfcom_manage", "Gerenciar emissão de NFCom"),
    ("clients_manage", "Gerenciar clientes"),
    ("services_manage", "Gerenciar serviços"),
    ("contract_manage", "Gerenciar contratos (criar/editar/excluir/ativar/reset)")
    ,("contract_view", "Visualizar contratos")
]

ROLE_DEFINITIONS = {
    "Admin": {"description": "Administrador global, tem todas as permissões"},
    "Viewer": {"description": "Apenas leitura para recursos críticos"},
    "Secretary": {"description": "Secretária: gerencia contratos, clientes e serviços"},
    "Technical": {"description": "Equipe técnica: visualiza contratos"},
}


def main():
    db = SessionLocal()
    try:
        print("Iniciando seed de permissões...")

        # Cria permissões
        created = 0
        for name, desc in PERMISSIONS:
            p = db.query(Permission).filter(Permission.name == name).first()
            if not p:
                p = Permission(name=name, description=desc)
                db.add(p)
                created += 1
        if created:
            db.commit()
            print(f"Criadas {created} permissões")
        else:
            print("Nenhuma permissão nova necessária")

        # Recarrega todas as permissões relevantes
        perms = db.query(Permission).filter(Permission.name.in_([p[0] for p in PERMISSIONS])).all()
        perm_map = {p.name: p for p in perms}

        # Cria roles e associa permissões
        for rname, meta in ROLE_DEFINITIONS.items():
            role = db.query(Role).filter(Role.name == rname).first()
            if not role:
                role = Role(name=rname, description=meta.get("description"), empresa_id=None)
                db.add(role)
                db.commit()
                db.refresh(role)
                print(f"Criada role: {rname}")
            # Associa permissões conforme papel
            if rname == "Admin":
                # Admin recebe todas as permissões
                role.permissions = list(perms)
            elif rname == "Viewer":
                # Viewer recebe apenas permissões de visualização
                viewer_perms = []
                for key in ["router_view", "radius_view"]:
                    p = perm_map.get(key)
                    if p:
                        viewer_perms.append(p)
                role.permissions = viewer_perms
            elif rname == "Secretary":
                secretary_perms = []
                for key in ["clients_manage", "services_manage", "contract_manage"]:
                    p = perm_map.get(key)
                    if p:
                        secretary_perms.append(p)
                role.permissions = secretary_perms
            elif rname == "Technical":
                tech_perms = []
                for key in ["contract_view"]:
                    p = perm_map.get(key)
                    if p:
                        tech_perms.append(p)
                role.permissions = tech_perms
            db.add(role)
            db.commit()

        print("Seed de permissões concluído com sucesso")
    finally:
        db.close()


if __name__ == "__main__":
    main()
