from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import deps
from app.core.database import get_db
from app.models.access_control import Role, Permission, user_role_association
from app.models.models import Usuario

router = APIRouter(prefix="/access", tags=["Access Control"])


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    empresa_id: Optional[int] = None


class PermissionCreate(BaseModel):
    name: str
    description: Optional[str] = None


class AssignRolePayload(BaseModel):
    user_id: int
    empresa_id: Optional[int] = None


@router.post('/roles', status_code=status.HTTP_201_CREATED)
def create_role(payload: RoleCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(deps.get_current_active_user)):
    # Checa permissão gerencial de roles
    deps.permission_checker('role_manage')(db=db, current_user=current_user)
    # Se empresa_id não informado, usa active_empresa do usuário
    empresa_id = payload.empresa_id or getattr(current_user, 'active_empresa_id', None)
    r = Role(name=payload.name, description=payload.description, empresa_id=empresa_id)
    db.add(r)
    db.commit()
    db.refresh(r)
    return {'id': r.id, 'name': r.name, 'description': r.description, 'empresa_id': r.empresa_id}


@router.get('/roles', response_model=List[dict])
def list_roles(db: Session = Depends(get_db), current_user: Usuario = Depends(deps.get_current_active_user)):
    empresa_id = getattr(current_user, 'active_empresa_id', None)
    q = db.query(Role)
    if empresa_id is not None:
        q = q.filter((Role.empresa_id == None) | (Role.empresa_id == empresa_id))
    return [ {'id': r.id, 'name': r.name, 'description': r.description, 'empresa_id': r.empresa_id } for r in q.all() ]


@router.post('/permissions', status_code=status.HTTP_201_CREATED)
def create_permission(payload: PermissionCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(deps.get_current_active_user)):
    deps.permission_checker('permission_manage')(db=db, current_user=current_user)
    p = Permission(name=payload.name, description=payload.description)
    db.add(p)
    db.commit()
    db.refresh(p)
    return {'id': p.id, 'name': p.name, 'description': p.description}


@router.post('/roles/{role_id}/assign', status_code=status.HTTP_200_OK)
def assign_role(role_id: int, payload: AssignRolePayload, db: Session = Depends(get_db), current_user: Usuario = Depends(deps.get_current_active_user)):
    deps.permission_checker('role_assign')(db=db, current_user=current_user)
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail='Role não encontrada')
    # Verifica escopo: se role tem empresa_id diferente da payload e usuário não superuser, recusa
    if role.empresa_id and role.empresa_id != payload.empresa_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail='Role pertence a outro provedor')
    # Verifica se já existe associação para evitar duplicate key
    existing = db.execute(
        user_role_association.select().where(
            (user_role_association.c.user_id == payload.user_id) &
            (user_role_association.c.role_id == role_id) &
            (user_role_association.c.empresa_id == payload.empresa_id)
        )
    ).first()
    if existing:
        return {'status': 'ok', 'message': 'already_assigned'}
    # Insere na tabela de associação
    ins = user_role_association.insert().values(user_id=payload.user_id, role_id=role_id, empresa_id=payload.empresa_id)
    try:
        db.execute(ins)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {'status': 'ok'}


@router.post('/roles/{role_id}/unassign', status_code=status.HTTP_200_OK)
def unassign_role(role_id: int, payload: AssignRolePayload, db: Session = Depends(get_db), current_user: Usuario = Depends(deps.get_current_active_user)):
    deps.permission_checker('role_assign')(db=db, current_user=current_user)
    delete = user_role_association.delete().where(
        (user_role_association.c.user_id == payload.user_id) &
        (user_role_association.c.role_id == role_id)
    )
    db.execute(delete)
    db.commit()
    return {'status': 'ok'}


@router.get('/permissions', response_model=List[dict])
def list_permissions(db: Session = Depends(get_db), current_user: Usuario = Depends(deps.get_current_active_user)):
    # Lista todas as permissões (não há escopo por empresa para permissões)
    return [ {'id': p.id, 'name': p.name, 'description': p.description} for p in db.query(Permission).all() ]


@router.put('/permissions/{permission_id}', status_code=status.HTTP_200_OK)
def update_permission(permission_id: int, payload: PermissionCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(deps.get_current_active_user)):
    deps.permission_checker('permission_manage')(db=db, current_user=current_user)
    perm = db.query(Permission).filter(Permission.id == permission_id).first()
    if not perm:
        raise HTTPException(status_code=404, detail='Permissão não encontrada')
    perm.name = payload.name
    perm.description = payload.description
    db.commit()
    db.refresh(perm)
    return {'id': perm.id, 'name': perm.name, 'description': perm.description}


@router.delete('/permissions/{permission_id}', status_code=status.HTTP_200_OK)
def delete_permission(permission_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(deps.get_current_active_user)):
    deps.permission_checker('permission_manage')(db=db, current_user=current_user)
    perm = db.query(Permission).filter(Permission.id == permission_id).first()
    if not perm:
        raise HTTPException(status_code=404, detail='Permissão não encontrada')
    # Verifica se permissão está associada a roles
    if perm.roles:
        raise HTTPException(status_code=400, detail='Permissão está associada a roles e não pode ser excluída')
    db.delete(perm)
    db.commit()
    return {'status': 'ok'}


@router.post('/roles/{role_id}/permissions/{permission_id}', status_code=status.HTTP_200_OK)
def add_permission_to_role(role_id: int, permission_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(deps.get_current_active_user)):
    deps.permission_checker('role_manage')(db=db, current_user=current_user)
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail='Role não encontrada')
    perm = db.query(Permission).filter(Permission.id == permission_id).first()
    if not perm:
        raise HTTPException(status_code=404, detail='Permissão não encontrada')
    # Verifica escopo
    if role.empresa_id and role.empresa_id != getattr(current_user, 'active_empresa_id', None) and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail='Role pertence a outro provedor')
    # Adiciona se não estiver já associada
    if perm not in role.permissions:
        role.permissions.append(perm)
        db.commit()
    return {'status': 'ok'}


@router.delete('/roles/{role_id}/permissions/{permission_id}', status_code=status.HTTP_200_OK)
def remove_permission_from_role(role_id: int, permission_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(deps.get_current_active_user)):
    deps.permission_checker('role_manage')(db=db, current_user=current_user)
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail='Role não encontrada')
    perm = db.query(Permission).filter(Permission.id == permission_id).first()
    if not perm:
        raise HTTPException(status_code=404, detail='Permissão não encontrada')
    # Verifica escopo
    if role.empresa_id and role.empresa_id != getattr(current_user, 'active_empresa_id', None) and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail='Role pertence a outro provedor')
    # Remove se estiver associada
    if perm in role.permissions:
        role.permissions.remove(perm)
        db.commit()
    return {'status': 'ok'}


@router.get('/roles/{role_id}/permissions', response_model=List[dict])
def list_role_permissions(role_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(deps.get_current_active_user)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail='Role não encontrada')
    # Respeita escopo: se role é de outra empresa e usuário não é superuser, recusa
    if role.empresa_id and role.empresa_id != getattr(current_user, 'active_empresa_id', None) and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail='Role pertence a outro provedor')
    return [ {'id': p.id, 'name': p.name, 'description': p.description} for p in role.permissions ]


@router.get('/users/{user_id}/roles', response_model=List[dict])
def list_user_roles(user_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(deps.get_current_active_user)):
    """Lista roles atribuídas a um usuário. Retorna apenas associações globais (empresa_id NULL) ou vinculadas
    à empresa ativa do usuário atual."""
    empresa_id = getattr(current_user, 'active_empresa_id', None)
    ura = user_role_association
    rows = db.execute(ura.select().where(ura.c.user_id == user_id)).fetchall()
    out = []
    for r in rows:
        # r is a Row, attributes as r.role_id, r.empresa_id
        if empresa_id is not None:
            # include only global or same-empresa associations
            if r.empresa_id is not None and r.empresa_id != empresa_id:
                continue
        role = db.query(Role).filter(Role.id == r.role_id).first()
        if not role:
            continue
        out.append({'id': role.id, 'name': role.name, 'description': role.description, 'empresa_id': r.empresa_id})
    return out


@router.get('/users/{user_id}/permissions', response_model=List[str])
def list_user_permissions(user_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(deps.get_current_active_user)):
    """Lista nomes de permissões agregadas para um usuário, respeitando o escopo da empresa ativa do requisitante.
    Retorna apenas permissões provenientes de roles que sejam globais (empresa_id NULL) ou vinculadas
    à mesma empresa ativa do `current_user`.
    """
    empresa_id = getattr(current_user, 'active_empresa_id', None)
    ura = user_role_association
    rows = db.execute(ura.select().where(ura.c.user_id == user_id)).fetchall()
    perms = set()
    for r in rows:
        # r is a Row; r.empresa_id can be None
        if empresa_id is not None:
            if r.empresa_id is not None and r.empresa_id != empresa_id:
                continue
        role = db.query(Role).filter(Role.id == r.role_id).first()
        if not role:
            continue
        for p in role.permissions:
            perms.add(p.name)
    return sorted(list(perms))


@router.put('/roles/{role_id}', status_code=status.HTTP_200_OK)
def update_role(role_id: int, payload: RoleCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(deps.get_current_active_user)):
    deps.permission_checker('role_manage')(db=db, current_user=current_user)
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail='Role não encontrada')
    # Verifica se role pertence à empresa do usuário ou é global
    if role.empresa_id and role.empresa_id != getattr(current_user, 'active_empresa_id', None) and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail='Role pertence a outro provedor')
    role.name = payload.name
    role.description = payload.description
    db.commit()
    db.refresh(role)
    return {'id': role.id, 'name': role.name, 'description': role.description, 'empresa_id': role.empresa_id}


@router.delete('/roles/{role_id}', status_code=status.HTTP_200_OK)
def delete_role(role_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(deps.get_current_active_user)):
    deps.permission_checker('role_manage')(db=db, current_user=current_user)
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail='Role não encontrada')
    # Verifica se role pertence à empresa do usuário ou é global
    if role.empresa_id and role.empresa_id != getattr(current_user, 'active_empresa_id', None) and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail='Role pertence a outro provedor')
    # Verifica se role está atribuída a usuários
    ura = user_role_association
    assigned = db.execute(ura.select().where(ura.c.role_id == role_id)).first()
    if assigned:
        raise HTTPException(status_code=400, detail='Role está atribuída a usuários e não pode ser excluída')
    db.delete(role)
    db.commit()
    return {'status': 'ok'}
