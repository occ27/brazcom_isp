from typing import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routes.auth import get_current_active_user
from app.models.access_control import role_permission_association, user_role_association, Permission, Role
from app.models.models import Usuario


def permission_checker(permission_name: str) -> Callable:
    """Retorna uma dependência que checa se o usuário atual tem a permissão especificada.

    Regras:
    - Superusers sempre têm todas as permissões.
    - Procurar roles atribuídas ao usuário (user_role_association) que contenham a permissão.
    - As atribuições podem ser globais (empresa_id NULL) ou associadas à empresa ativa do usuário.
    """
    def _checker(
        db: Session = Depends(get_db),
        current_user: Usuario = Depends(get_current_active_user),
    ):
        # Superuser bypass
        if getattr(current_user, "is_superuser", False):
            return True

        empresa_id = getattr(current_user, "active_empresa_id", None)

        # Monta query: existe role para este usuário com a permissão desejada?
        q = db.query(Role).join(user_role_association, Role.id == user_role_association.c.role_id)
        q = q.join(role_permission_association, Role.id == role_permission_association.c.role_id)
        q = q.join(Permission, Permission.id == role_permission_association.c.permission_id)
        q = q.filter(user_role_association.c.user_id == current_user.id)
        q = q.filter(Permission.name == permission_name)

        # Permite roles globais (empresa_id IS NULL) ou com empresa específica
        if empresa_id is not None:
            q = q.filter((user_role_association.c.empresa_id == None) | (user_role_association.c.empresa_id == empresa_id))

        has = db.query(q.exists()).scalar()
        if not has:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão negada")
        return True

    return _checker
