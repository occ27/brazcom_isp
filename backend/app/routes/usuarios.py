from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.crud import crud_usuario
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate, UsuarioResponse, UsuarioRegister
from app.routes.auth import get_current_active_superuser, get_current_active_user
from app.models.models import Usuario
from app.crud import crud_usuario
from app.crud import crud_empresa
from app.schemas.empresa import EmpresaResponse

router = APIRouter(prefix="/usuarios", tags=["Usuários"])

@router.post("/register", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def register_usuario(
    usuario: UsuarioRegister,
    db: Session = Depends(get_db)
):
    """Registra um novo usuário. Endpoint público."""
    db_user = crud_usuario.get_usuario_by_email(db, email=usuario.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email já registrado")
    
    # Criar usuário com is_superuser=False por padrão
    usuario_create = UsuarioCreate(
        full_name=usuario.full_name,
        email=usuario.email,
        password=usuario.password,
        is_superuser=False
    )
    return crud_usuario.create_usuario(db=db, usuario=usuario_create)

@router.get("/me", response_model=UsuarioResponse)
def read_usuario_me(
    current_user: Usuario = Depends(get_current_active_user)
):
    """Obtém os dados do usuário autenticado."""
    return current_user


@router.get("/me/active-empresa", response_model=EmpresaResponse)
def get_my_active_empresa(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Retorna a empresa ativa do usuário, se existir."""
    empresa_id = getattr(current_user, 'active_empresa_id', None)
    if not empresa_id:
        raise HTTPException(status_code=404, detail="Nenhuma empresa ativa definida")
    empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return empresa


@router.post("/me/active-empresa", response_model=EmpresaResponse)
def set_my_active_empresa(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Define a empresa ativa do usuário. Body: {"empresa_id": int}."""
    empresa_id = payload.get('empresa_id')
    if empresa_id is None:
        raise HTTPException(status_code=400, detail="empresa_id é obrigatório")

    empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # Validar associação a menos que seja superuser — permitir também se o usuário for o dono (Empresa.user_id)
    if not current_user.is_superuser:
        from app.models.models import UsuarioEmpresa
        has_assoc = db.query(UsuarioEmpresa).filter(
            UsuarioEmpresa.usuario_id == current_user.id,
            UsuarioEmpresa.empresa_id == empresa_id
        ).first()
        if not has_assoc:
            # checar se o usuário é o dono/criador da empresa
            empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
            if not empresa or empresa.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Usuário não está associado à empresa")

    crud_usuario.set_active_empresa(db=db, db_obj=current_user, empresa_id=empresa_id)
    # Recarregar usuário atual antes de retornar a empresa (current_user pode ser instância antiga)
    empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    return empresa


@router.delete("/me/active-empresa", status_code=status.HTTP_204_NO_CONTENT)
def clear_my_active_empresa(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Limpa a preferência de empresa ativa do usuário."""
    crud_usuario.set_active_empresa(db=db, db_obj=current_user, empresa_id=None)
    return None

@router.put("/me", response_model=UsuarioResponse)
def update_usuario_me(
    usuario: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Atualiza os dados do usuário autenticado."""
    # Remover campos que não podem ser alterados pelo usuário
    update_dict = usuario.model_dump(exclude_unset=True)
    if 'is_superuser' in update_dict:
        del update_dict['is_superuser']  # Usuários não podem alterar seu status de superuser
    
    # Criar um objeto UsuarioUpdate apenas com os campos fornecidos
    filtered_update = UsuarioUpdate(**update_dict)
    return crud_usuario.update_usuario(db=db, db_obj=current_user, obj_in=filtered_update)

@router.post("/", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def create_usuario(
    usuario: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_superuser)
):
    """Cria um novo usuário. Apenas superusuários podem criar outros usuários."""
    db_user = crud_usuario.get_usuario_by_email(db, email=usuario.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email já registrado")
    return crud_usuario.create_usuario(db=db, usuario=usuario)

@router.get("/", response_model=List[UsuarioResponse])
def read_usuarios(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_superuser)
):
    """Lista todos os usuários. Apenas para superusuários."""
    users = crud_usuario.get_usuarios(db, skip=skip, limit=limit)
    return users

@router.get("/{usuario_id}", response_model=UsuarioResponse)
def read_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Obtém um usuário específico pelo ID."""
    db_user = crud_usuario.get_usuario(db, usuario_id=usuario_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if current_user.id != usuario_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Não tem permissão para ver este usuário")
    return db_user

@router.put("/{usuario_id}", response_model=UsuarioResponse)
def update_usuario(
    usuario_id: int,
    usuario: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Atualiza um usuário."""
    db_user = crud_usuario.get_usuario(db, usuario_id=usuario_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if current_user.id != usuario_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Não tem permissão para atualizar este usuário")
    return crud_usuario.update_usuario(db=db, db_obj=db_user, obj_in=usuario)

@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_superuser)
):
    """Deleta um usuário."""
    db_user = crud_usuario.get_usuario(db, usuario_id=usuario_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    crud_usuario.delete_usuario(db=db, db_obj=db_user)
    return None