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
    # Insere na tabela de associação
    ins = user_role_association.insert().values(user_id=payload.user_id, role_id=role_id, empresa_id=payload.empresa_id)
    db.execute(ins)
    db.commit()
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


@router.get('/users/{user_id}/permissions', response_model=List[str])
def list_user_permissions(user_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(deps.get_current_active_user)):
    # Lista permissões agregadas das roles atribuídas ao usuário (globais + do active_empresa)
    empresa_id = getattr(current_user, 'active_empresa_id', None)
    ura = user_role_association
    # Simpler approach: load roles for user and collect permissions in Python
    roles = db.execute(ura.select().where(ura.c.user_id == user_id)).fetchall()
    perm_set = set()
    for r in roles:
        role = db.query(Role).filter(Role.id == r.role_id).first()
        if not role:
            continue
        # role.permissions relationship may be lazy; access
        for p in role.permissions:
            perm_set.add(p.name)
    return list(perm_set)


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
