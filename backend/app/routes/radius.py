"""
Endpoints da API RADIUS.

Incluem gerenciamento de servidores, usuários e sessões —
com sincronização automática para as tabelas nativas do FreeRadius.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app import crud, models
from app.api import deps
from app.schemas import radius as radius_schemas
from app.core.radius_db import get_radius_db
from app.services.radius_sync_service import RadiusSyncService

router = APIRouter(prefix="/radius", tags=["RADIUS"])


# ─────────────────────────────────────────────
# RadiusServer endpoints
# ─────────────────────────────────────────────

@router.post("/servers/", response_model=radius_schemas.RadiusServer)
def create_radius_server(
    *,
    db: Session = Depends(deps.get_db),
    server_in: radius_schemas.RadiusServerCreate,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_manage"))
):
    """Criar um novo servidor RADIUS para a empresa do usuário atual."""
    return crud.crud_radius.create_radius_server(db=db, server=server_in, empresa_id=current_user.active_empresa_id)


@router.get("/servers/", response_model=List[radius_schemas.RadiusServer])
def read_radius_servers(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_view"))
):
    """Buscar todos os servidores RADIUS da empresa do usuário atual."""
    return crud.crud_radius.get_radius_servers_by_empresa(
        db=db, empresa_id=current_user.active_empresa_id, skip=skip, limit=limit
    )


@router.get("/servers/{server_id}", response_model=radius_schemas.RadiusServer)
def read_radius_server(
    *,
    db: Session = Depends(deps.get_db),
    server_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_view"))
):
    """Buscar um servidor RADIUS específico da empresa do usuário atual."""
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
    """Atualizar um servidor RADIUS da empresa do usuário atual."""
    server = crud.crud_radius.get_radius_server(db=db, server_id=server_id, empresa_id=current_user.active_empresa_id)
    if not server:
        raise HTTPException(status_code=404, detail="Servidor RADIUS não encontrado")
    return crud.crud_radius.update_radius_server(db=db, db_server=server, server_in=server_in)


@router.delete("/servers/{server_id}", response_model=radius_schemas.RadiusServer)
def delete_radius_server(
    *,
    db: Session = Depends(deps.get_db),
    server_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_manage"))
):
    """Deletar um servidor RADIUS da empresa do usuário atual."""
    server = crud.crud_radius.get_radius_server(db=db, server_id=server_id, empresa_id=current_user.active_empresa_id)
    if not server:
        raise HTTPException(status_code=404, detail="Servidor RADIUS não encontrado")
    return crud.crud_radius.remove_radius_server(db=db, db_server=server)


# ─────────────────────────────────────────────
# RadiusUser endpoints — com sincronização FreeRadius
# ─────────────────────────────────────────────

@router.post("/users/", response_model=radius_schemas.RadiusUser)
def create_radius_user(
    *,
    db: Session = Depends(deps.get_db),
    radius_db: Session = Depends(get_radius_db),
    user_in: radius_schemas.RadiusUserCreate,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_manage"))
):
    """
    Criar um novo usuário RADIUS para a empresa do usuário atual.
    Sincroniza automaticamente com as tabelas radcheck/radreply do FreeRadius.
    """
    return crud.crud_radius.create_radius_user(
        db=db, user=user_in, empresa_id=current_user.active_empresa_id, radius_db=radius_db
    )


@router.get("/users/", response_model=List[radius_schemas.RadiusUser])
def read_radius_users(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_view"))
):
    """Buscar todos os usuários RADIUS da empresa do usuário atual."""
    return crud.crud_radius.get_radius_users_by_empresa(
        db=db, empresa_id=current_user.active_empresa_id, skip=skip, limit=limit
    )


@router.get("/users/{user_id}", response_model=radius_schemas.RadiusUser)
def read_radius_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_view"))
):
    """Buscar um usuário RADIUS específico da empresa do usuário atual."""
    user = crud.crud_radius.get_radius_user(db=db, user_id=user_id, empresa_id=current_user.active_empresa_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário RADIUS não encontrado")
    return user


@router.put("/users/{user_id}", response_model=radius_schemas.RadiusUser)
def update_radius_user(
    *,
    db: Session = Depends(deps.get_db),
    radius_db: Session = Depends(get_radius_db),
    user_id: int,
    user_in: radius_schemas.RadiusUserUpdate,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_manage"))
):
    """
    Atualizar um usuário RADIUS da empresa do usuário atual.
    Suspensão automática no FreeRadius se is_active=False.
    """
    user = crud.crud_radius.get_radius_user(db=db, user_id=user_id, empresa_id=current_user.active_empresa_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário RADIUS não encontrado")
    return crud.crud_radius.update_radius_user(db=db, db_user=user, user_in=user_in, radius_db=radius_db)


@router.delete("/users/{user_id}", response_model=radius_schemas.RadiusUser)
def delete_radius_user(
    *,
    db: Session = Depends(deps.get_db),
    radius_db: Session = Depends(get_radius_db),
    user_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_manage"))
):
    """
    Deletar um usuário RADIUS da empresa do usuário atual.
    Remove também do FreeRadius (radcheck e radreply).
    """
    user = crud.crud_radius.get_radius_user(db=db, user_id=user_id, empresa_id=current_user.active_empresa_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário RADIUS não encontrado")
    return crud.crud_radius.remove_radius_user(db=db, db_user=user, radius_db=radius_db)


# ─────────────────────────────────────────────
# Sessões Ativas — lidas diretamente do FreeRadius (radacct)
# ─────────────────────────────────────────────

@router.get("/sessions/live/")
def read_live_sessions(
    username: Optional[str] = None,
    radius_db: Session = Depends(get_radius_db),
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_view"))
):
    """
    Sessões PPPoE ativas lidas em tempo real da tabela radacct do FreeRadius.
    Parâmetro opcional: ?username=joao para filtrar por usuário.
    """
    sync = RadiusSyncService(radius_db)
    return sync.get_active_sessions(username=username)


@router.get("/sessions/history/{username}")
def read_auth_history(
    username: str,
    limit: int = 50,
    radius_db: Session = Depends(get_radius_db),
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_view"))
):
    """
    Histórico de autenticações de um usuário (tabela radpostauth do FreeRadius).
    Mostra Access-Accept e Access-Reject com timestamps.
    """
    sync = RadiusSyncService(radius_db)
    return sync.get_auth_history(username=username, limit=limit)


@router.get("/sessions/", response_model=List[radius_schemas.RadiusSession])
def read_active_sessions(
    db: Session = Depends(deps.get_db),
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_view"))
):
    """Buscar sessões ativas no banco interno do Brazcom."""
    return crud.crud_radius.get_active_sessions_by_empresa(db=db, empresa_id=current_user.active_empresa_id)


@router.get("/sessions/{session_id}", response_model=radius_schemas.RadiusSession)
def read_radius_session(
    *,
    db: Session = Depends(deps.get_db),
    session_id: str,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_view"))
):
    """Buscar uma sessão RADIUS específica da empresa do usuário atual."""
    session = crud.crud_radius.get_radius_session(db=db, session_id=session_id, empresa_id=current_user.active_empresa_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão RADIUS não encontrada")
    return session


# ─────────────────────────────────────────────
# Ações manuais de suspensão/reativação
# ─────────────────────────────────────────────

@router.post("/users/{user_id}/suspend")
def suspend_radius_user(
    *,
    db: Session = Depends(deps.get_db),
    radius_db: Session = Depends(get_radius_db),
    user_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_manage"))
):
    """
    Suspende imediatamente um usuário no FreeRadius (Auth-Type = Reject).
    O cliente PPPoE cai na próxima reautenticação.
    """
    user = crud.crud_radius.get_radius_user(db=db, user_id=user_id, empresa_id=current_user.active_empresa_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário RADIUS não encontrado")

    sync = RadiusSyncService(radius_db)
    success = sync.disable_user(user.username)

    # Atualiza status no banco interno
    user.is_active = False
    db.add(user)
    db.commit()

    return {"success": success, "username": user.username, "status": "suspenso"}


@router.post("/users/{user_id}/activate")
def activate_radius_user(
    *,
    db: Session = Depends(deps.get_db),
    radius_db: Session = Depends(get_radius_db),
    user_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_manage"))
):
    """
    Reativa um usuário suspenso no FreeRadius removendo o Auth-Type = Reject.
    """
    user = crud.crud_radius.get_radius_user(db=db, user_id=user_id, empresa_id=current_user.active_empresa_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário RADIUS não encontrado")

    sync = RadiusSyncService(radius_db)
    success = sync.enable_user(user.username)

    # Atualiza status no banco interno
    user.is_active = True
    db.add(user)
    db.commit()

    return {"success": success, "username": user.username, "status": "ativo"}


# ─────────────────────────────────────────────
# Clientes NAS — gerenciamento via tabela `nas`
# Substitui o clients.conf sem precisar de root
# ─────────────────────────────────────────────

@router.get("/nas/")
def list_nas_clients(
    radius_db: Session = Depends(get_radius_db),
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_view"))
):
    """
    Lista todos os roteadores/Mikrotik autorizados a usar o RADIUS.

    Equivalente ao conteúdo do arquivo clients.conf, gerenciado pelo banco.
    Não precisa de acesso root ao servidor.
    """
    sync = RadiusSyncService(radius_db)
    return sync.list_nas_clients()


@router.get("/nas/{nas_id}")
def get_nas_client(
    nas_id: int,
    radius_db: Session = Depends(get_radius_db),
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_view"))
):
    """Busca um cliente NAS pelo ID."""
    sync = RadiusSyncService(radius_db)
    nas = sync.get_nas_client(nas_id)
    if not nas:
        raise HTTPException(status_code=404, detail="Cliente NAS não encontrado")
    return nas


@router.post("/nas/", status_code=201)
def create_nas_client(
    nasname: str,
    secret: str,
    shortname: str = "",
    nas_type: str = "other",
    description: str = "",
    ports: Optional[int] = None,
    radius_db: Session = Depends(get_radius_db),
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_manage"))
):
    """
    Registra um novo roteador/Mikrotik como cliente NAS no FreeRadius.

    Equivale a adicionar um bloco `client { }` no clients.conf — sem root,
    sem editar arquivos, sem restart do FreeRadius.

    - **nasname**: IP ou hostname do roteador (ex: `192.168.100.1`)
    - **secret**: Segredo compartilhado RADIUS (deve coincidir com o configurado na Mikrotik)
    - **shortname**: Nome curto para identificação (ex: `rb-sede`)
    - **nas_type**: Tipo do NAS — use `other` para Mikrotik RouterOS
    - **description**: Descrição livre (ex: `Mikrotik Torre Sede`)
    """
    sync = RadiusSyncService(radius_db)
    nas_id = sync.create_nas_client(
        nasname=nasname,
        secret=secret,
        shortname=shortname,
        nas_type=nas_type,
        description=description,
        ports=ports,
    )
    if nas_id is None:
        raise HTTPException(status_code=500, detail="Erro ao registrar cliente NAS")
    return {"id": nas_id, "nasname": nasname, "shortname": shortname, "status": "registrado"}


@router.put("/nas/{nas_id}")
def update_nas_client(
    nas_id: int,
    nasname: Optional[str] = None,
    secret: Optional[str] = None,
    shortname: Optional[str] = None,
    nas_type: Optional[str] = None,
    description: Optional[str] = None,
    ports: Optional[int] = None,
    radius_db: Session = Depends(get_radius_db),
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_manage"))
):
    """
    Atualiza dados de um cliente NAS (IP, segredo, descrição, etc.).
    Apenas os parâmetros fornecidos são alterados.
    """
    sync = RadiusSyncService(radius_db)
    # Verifica se existe
    nas = sync.get_nas_client(nas_id)
    if not nas:
        raise HTTPException(status_code=404, detail="Cliente NAS não encontrado")

    success = sync.delete_nas_client(nas_id)
    if not success:
        raise HTTPException(status_code=500, detail="Erro ao remover cliente NAS")
    return {"success": True, "id": nas_id, "nasname": nas["nasname"], "status": "removido"}


# ─────────────────────────────────────────────
# Provisionamento automático de RADIUS no Mikrotik
# ─────────────────────────────────────────────

@router.post("/nas/{nas_id}/provision")
def provision_radius_on_router(
    nas_id: int,
    db: Session = Depends(deps.get_db),
    radius_db: Session = Depends(get_radius_db),
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_manage"))
):
    """
    Provisiona automaticamente a configuração RADIUS no Mikrotik associado a este NAS.
    """
    sync = RadiusSyncService(radius_db)
    nas = sync.get_nas_client(nas_id)
    if not nas:
        raise HTTPException(status_code=404, detail="Cliente NAS não encontrado")

    nas_ip = nas.get("nasname")
    nas_secret = nas.get("secret")

    from app.models.network import Router as RouterModel
    router_db = db.query(RouterModel).filter(
        RouterModel.ip == nas_ip,
        RouterModel.empresa_id == current_user.active_empresa_id
    ).first()

    if not router_db:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum Router cadastrado no sistema com o IP '{nas_ip}'."
        )

    return _execute_router_provision(db, router_db, nas_secret)


@router.post("/router/{router_id}/provision")
def provision_radius_by_router_id(
    router_id: int,
    db: Session = Depends(deps.get_db),
    radius_db: Session = Depends(get_radius_db),
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    _: bool = Depends(deps.permission_checker("radius_manage"))
):
    """
    Provisiona RADIUS no Mikrotik usando o ID do Router.
    Se não houver um NAS cadastrado para este IP, ele cria um automaticamente.
    """
    from app.models.network import Router as RouterModel
    router_db = db.query(RouterModel).filter(
        RouterModel.id == router_id,
        RouterModel.empresa_id == current_user.active_empresa_id
    ).first()

    if not router_db:
        raise HTTPException(status_code=404, detail="Roteador não encontrado")

    # Verifica se já existe um NAS para este IP
    sync = RadiusSyncService(radius_db)
    nas = sync.get_nas_client_by_ip(router_db.ip)
    
    nas_secret = router_db.radius_secret
    if not nas:
        # Cria o NAS automaticamente se não existir
        if not nas_secret:
            import secrets
            nas_secret = secrets.token_hex(8)
        
        sync.create_nas_client(
            nasname=router_db.ip,
            shortname=router_db.nome,
            secret=nas_secret,
            description=f"Criado automaticamente via Router {router_db.id}"
        )
    else:
        nas_secret = nas.get("secret")

    return _execute_router_provision(db, router_db, nas_secret)


def _execute_router_provision(db: Session, router_db: any, nas_secret: str):
    """Lógica interna de conexão e configuração do Mikrotik."""
    from app.mikrotik.controller import MikrotikController
    from app.core.security import decrypt_password
    import os

    try:
        password = decrypt_password(router_db.senha)
    except Exception:
        password = router_db.senha or ""

    radius_server_ip = router_db.radius_server_address or os.getenv("RADIUS_DB_HOST", "127.0.0.1")

    try:
        mk = MikrotikController(
            host=router_db.ip,
            username=router_db.usuario,
            password=password,
            port=router_db.porta or 8728
        )
        result = mk.configure_radius_on_mikrotik(
            radius_server_ip=radius_server_ip,
            radius_secret=nas_secret,
        )
        mk.close()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao conectar ao Mikrotik {router_db.ip}: {e}")

    # Atualiza o router para RADIUS se não estiver
    if router_db.metodo_autenticacao_padrao != "RADIUS":
        router_db.metodo_autenticacao_padrao = "RADIUS"
        router_db.radius_server_address = radius_server_ip
        router_db.radius_secret = nas_secret
        db.commit()
        result["steps"].append("✅ Router atualizado: metodo_autenticacao_padrao = RADIUS")

    return {
        "router_id": router_db.id,
        "router_nome": router_db.nome,
        "radius_server": radius_server_ip,
        **result
    }