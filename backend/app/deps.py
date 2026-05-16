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

    # Verificar Licença (Bloqueio do sistema se inválida)
    from app.utils.license_utils import check_company_license
    check_company_license(db, empresa_id, current_user)

    return empresa


def check_empresa_access(db: Session, empresa_id: int, current_user: Usuario):
    """Verifica se o usuário tem acesso à empresa e se a licença está ativa.
    
    Lança 404 se a empresa não existir.
    Lança 403 se o usuário não tiver permissão.
    Lança 402 se a licença estiver inválida.
    """
    db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # Verificar Licença (Bloqueio do sistema se inválida para QUALQUER usuário)
    from app.utils.license_utils import check_company_license
    check_company_license(db, empresa_id, current_user)

    # Superusers ignoram verificações de associação (podem acessar qualquer empresa com licença ativa)
    if current_user.is_superuser:
        return db_empresa

    # Verificar associação
    assoc = db.query(UsuarioEmpresa).filter(
        UsuarioEmpresa.usuario_id == current_user.id,
        UsuarioEmpresa.empresa_id == empresa_id
    ).first()
    
    if not assoc:
        raise HTTPException(status_code=403, detail="Usuário não tem permissão para acessar esta empresa")

    return db_empresa
