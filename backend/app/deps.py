from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routes.auth import get_current_active_user
from app.models.models import Empresa, UsuarioEmpresa, Usuario
from app.crud import crud_empresa


def get_active_empresa(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
    x_active_empresa: Optional[int] = Header(None, convert_underscores=False)
) -> Empresa:
    """Retorna a empresa ativa para o request.

    Ordem de resolução:
    1. Se header X-Active-Empresa presente -> usar après validação.
    2. Se usuário tem active_empresa_id definido -> usar.
    3. Caso contrário -> HTTPException(400) indicando seleção necessária.
    """
    empresa_id = None

    if x_active_empresa is not None:
        empresa_id = x_active_empresa
    elif getattr(current_user, 'active_empresa_id', None):
        empresa_id = current_user.active_empresa_id

    if empresa_id is None:
        raise HTTPException(status_code=400, detail="Nenhuma empresa ativa selecionada")

    empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # Se usuário não é superuser, validar associação
    if not current_user.is_superuser:
        assoc = db.query(UsuarioEmpresa).filter(
            UsuarioEmpresa.usuario_id == current_user.id,
            UsuarioEmpresa.empresa_id == empresa_id
        ).first()
        if not assoc:
            raise HTTPException(status_code=403, detail="Usuário não está associado à empresa selecionada")

    return empresa
