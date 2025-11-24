from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app import crud, models
from app.api import deps
from app.schemas import radius as radius_schemas
from app.radius.controller import RadiusController
from app.core.security import decrypt_password

router = APIRouter()

# RadiusServer endpoints
@router.post("/servers/", response_model=radius_schemas.RadiusServer)
def create_radius_server(
    *,
    db: Session = Depends(deps.get_db),
    server_in: radius_schemas.RadiusServerCreate,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_manage"))
):
    """
    Criar um novo servidor RADIUS para a empresa do usuário atual.
    """
    return crud.crud_radius.create_radius_server(db=db, server=server_in, empresa_id=current_user.active_empresa_id)

@router.get("/servers/", response_model=List[radius_schemas.RadiusServer])
def read_radius_servers(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_view"))
):
    """
    Buscar todos os servidores RADIUS da empresa do usuário atual.
    """
    servers = crud.crud_radius.get_radius_servers_by_empresa(
        db=db, empresa_id=current_user.active_empresa_id, skip=skip, limit=limit
    )
    return servers

@router.get("/servers/{server_id}", response_model=radius_schemas.RadiusServer)
def read_radius_server(
    *,
    db: Session = Depends(deps.get_db),
    server_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_view"))
):
    """
    Buscar um servidor RADIUS específico da empresa do usuário atual.
    """
    server = crud.crud_radius.get_radius_server(db=db, server_id=server_id, empresa_id=current_user.active_empresa_id)
    if not server:
        raise HTTPException(status_code=404, detail="Servidor RADIUS não encontrado")
    return server

@router.put("/servers/{server_id}", response_model=radius_schemas.RadiusServer)
def update_radius_server(
    *,
    db: Session = Depends(deps.get_db),
    server_id: int,
    server_in: radius_schemas.RadiusServerUpdate,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_manage"))
):
    """
    Atualizar um servidor RADIUS da empresa do usuário atual.
    """
    server = crud.crud_radius.get_radius_server(db=db, server_id=server_id, empresa_id=current_user.active_empresa_id)
    if not server:
        raise HTTPException(status_code=404, detail="Servidor RADIUS não encontrado")
    server = crud.crud_radius.update_radius_server(db=db, db_server=server, server_in=server_in)
    return server

@router.delete("/servers/{server_id}", response_model=radius_schemas.RadiusServer)
def delete_radius_server(
    *,
    db: Session = Depends(deps.get_db),
    server_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_manage"))
):
    """
    Deletar um servidor RADIUS da empresa do usuário atual.
    """
    server = crud.crud_radius.get_radius_server(db=db, server_id=server_id, empresa_id=current_user.active_empresa_id)
    if not server:
        raise HTTPException(status_code=404, detail="Servidor RADIUS não encontrado")
    server = crud.crud_radius.remove_radius_server(db=db, db_server=server)
    return server

# RadiusUser endpoints
@router.post("/users/", response_model=radius_schemas.RadiusUser)
def create_radius_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: radius_schemas.RadiusUserCreate,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_manage"))
):
    """
    Criar um novo usuário RADIUS para a empresa do usuário atual.
    """
    return crud.crud_radius.create_radius_user(db=db, user=user_in, empresa_id=current_user.active_empresa_id)

@router.get("/users/", response_model=List[radius_schemas.RadiusUser])
def read_radius_users(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_view"))
):
    """
    Buscar todos os usuários RADIUS da empresa do usuário atual.
    """
    users = crud.crud_radius.get_radius_users_by_empresa(
        db=db, empresa_id=current_user.active_empresa_id, skip=skip, limit=limit
    )
    return users

@router.get("/users/{user_id}", response_model=radius_schemas.RadiusUser)
def read_radius_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_view"))
):
    """
    Buscar um usuário RADIUS específico da empresa do usuário atual.
    """
    user = crud.crud_radius.get_radius_user(db=db, user_id=user_id, empresa_id=current_user.active_empresa_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário RADIUS não encontrado")
    return user

@router.put("/users/{user_id}", response_model=radius_schemas.RadiusUser)
def update_radius_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    user_in: radius_schemas.RadiusUserUpdate,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_manage"))
):
    """
    Atualizar um usuário RADIUS da empresa do usuário atual.
    """
    user = crud.crud_radius.get_radius_user(db=db, user_id=user_id, empresa_id=current_user.active_empresa_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário RADIUS não encontrado")
    user = crud.crud_radius.update_radius_user(db=db, db_user=user, user_in=user_in)
    return user

@router.delete("/users/{user_id}", response_model=radius_schemas.RadiusUser)
def delete_radius_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_manage"))
):
    """
    Deletar um usuário RADIUS da empresa do usuário atual.
    """
    user = crud.crud_radius.get_radius_user(db=db, user_id=user_id, empresa_id=current_user.active_empresa_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário RADIUS não encontrado")
    user = crud.crud_radius.remove_radius_user(db=db, db_user=user)
    return user

# RadiusSession endpoints
@router.get("/sessions/", response_model=List[radius_schemas.RadiusSession])
def read_active_sessions(
    db: Session = Depends(deps.get_db),
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_view"))
):
    """
    Buscar todas as sessões ativas RADIUS da empresa do usuário atual.
    """
    sessions = crud.crud_radius.get_active_sessions_by_empresa(db=db, empresa_id=current_user.active_empresa_id)
    return sessions

@router.get("/sessions/{session_id}", response_model=radius_schemas.RadiusSession)
def read_radius_session(
    *,
    db: Session = Depends(deps.get_db),
    session_id: str,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_view"))
):
    """
    Buscar uma sessão RADIUS específica da empresa do usuário atual.
    """
    session = crud.crud_radius.get_radius_session(db=db, session_id=session_id, empresa_id=current_user.active_empresa_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão RADIUS não encontrada")
    return session

# RADIUS Operations endpoints
@router.post("/test-server/{server_id}")
def test_radius_server(
    *,
    db: Session = Depends(deps.get_db),
    server_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_manage"))
):
    """
    Testar conectividade com um servidor RADIUS.
    """
    server = crud.crud_radius.get_radius_server(db=db, server_id=server_id, empresa_id=current_user.active_empresa_id)
    if not server:
        raise HTTPException(status_code=404, detail="Servidor RADIUS não encontrado")

    # Descriptografa o secret
    try:
        secret = decrypt_password(server.secret)
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao descriptografar secret do servidor")

    # Cria controller e testa conexão
    controller = RadiusController(
        server_ip=server.ip_address,
        secret=secret,
        port=server.port
    )

    success = controller.test_connection()
    return {"success": success, "message": "Conexão OK" if success else "Falha na conexão"}

@router.post("/authenticate/{server_id}")
def authenticate_radius_user(
    *,
    db: Session = Depends(deps.get_db),
    server_id: int,
    username: str,
    password: str,
    nas_ip: str = None,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_manage"))
):
    """
    Autenticar um usuário em um servidor RADIUS.
    """
    server = crud.crud_radius.get_radius_server(db=db, server_id=server_id, empresa_id=current_user.active_empresa_id)
    if not server:
        raise HTTPException(status_code=404, detail="Servidor RADIUS não encontrado")

    # Descriptografa o secret
    try:
        secret = decrypt_password(server.secret)
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao descriptografar secret do servidor")

    # Cria controller e autentica
    controller = RadiusController(
        server_ip=server.ip_address,
        secret=secret,
        port=server.port
    )

    result = controller.authenticate_user(username=username, password=password, nas_ip=nas_ip)
    return result