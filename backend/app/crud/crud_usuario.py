from sqlalchemy.orm import Session
from app.models.models import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate
from passlib.context import CryptContext

# Configuração para hashing de senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_usuario(db: Session, usuario_id: int):
    return db.query(Usuario).filter(Usuario.id == usuario_id).first()

def get_usuario_by_email(db: Session, email: str):
    return db.query(Usuario).filter(Usuario.email == email).first()

def get_usuarios(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Usuario).offset(skip).limit(limit).all()

def create_usuario(db: Session, usuario: UsuarioCreate):
    hashed_password = get_password_hash(usuario.password)
    db_usuario = Usuario(
        email=usuario.email,
        full_name=usuario.full_name,
        hashed_password=hashed_password,
        is_superuser=usuario.is_superuser
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

def update_usuario(db: Session, db_obj: Usuario, obj_in: UsuarioUpdate):
    update_data = obj_in.model_dump(exclude_unset=True)
    
    for field in update_data:
        setattr(db_obj, field, update_data[field])

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete_usuario(db: Session, db_obj: Usuario):
    db.delete(db_obj)
    db.commit()
    return db_obj


def set_active_empresa(db: Session, db_obj: Usuario, empresa_id: int | None):
    """Define a empresa ativa do usuário (pode ser None para limpar)."""
    db_obj.active_empresa_id = empresa_id
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_active_empresa_id(db: Session, usuario_id: int):
    user = get_usuario(db, usuario_id=usuario_id)
    if not user:
        return None
    return user.active_empresa_id
