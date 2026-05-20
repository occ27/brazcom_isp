from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import crud, models
from app.core.database import get_db
from app.core.radius_db import get_radius_db
from app.routes.auth import get_current_active_user
from app.api.deps import permission_checker
from app.schemas.router import RouterCreate, RouterUpdate, RouterResponse

router_api = APIRouter(prefix="/routers", tags=["Routers"])

@router_api.post("/", response_model=RouterResponse)
def create_router(
    *,
    db: Session = Depends(get_db),
    radius_db: Session = Depends(get_radius_db),
    router_in: RouterCreate,
    current_user: models.Usuario = Depends(get_current_active_user),
    _: bool = Depends(permission_checker("router_manage"))
):
    """
    Criar um novo roteador para a empresa do usuário atual.
    """
    empresa_id = current_user.active_empresa_id or 2  # Usar 2 como fallback
    return crud.crud_router.create_router(
        db=db, 
        router=router_in, 
        empresa_id=empresa_id,
        radius_db=radius_db
    )

@router_api.get("/", response_model=List[RouterResponse])
def read_routers(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.Usuario = Depends(get_current_active_user),
    _: bool = Depends(permission_checker("router_view"))
):
    """
    Buscar todos os roteadores da empresa do usuário atual.
    """
    empresa_id = current_user.active_empresa_id or 2  # Usar 2 como fallback
    routers = crud.crud_router.get_routers_by_provider(
        db=db, empresa_id=empresa_id, skip=skip, limit=limit
    )
    return routers

@router_api.get("/{router_id}", response_model=RouterResponse)
def read_router(
    *,
    db: Session = Depends(get_db),
    router_id: int,
    current_user: models.Usuario = Depends(get_current_active_user),
    _: bool = Depends(permission_checker("router_view"))
):
    """
    Buscar um roteador específico da empresa do usuário atual.
    """
    router = crud.crud_router.get_router(db=db, router_id=router_id, empresa_id=current_user.active_empresa_id)
    if not router:
        raise HTTPException(status_code=404, detail="Roteador não encontrado")
    return router

@router_api.put("/{router_id}", response_model=RouterResponse)
def update_router(
    *,
    db: Session = Depends(get_db),
    radius_db: Session = Depends(get_radius_db),
    router_id: int,
    router_in: RouterUpdate,
    current_user: models.Usuario = Depends(get_current_active_user),
    _: bool = Depends(permission_checker("router_manage"))
):
    """
    Atualizar um roteador da empresa do usuário atual.
    """
    router = crud.crud_router.get_router(db=db, router_id=router_id, empresa_id=current_user.active_empresa_id)
    if not router:
        raise HTTPException(status_code=404, detail="Roteador não encontrado")
    router = crud.crud_router.update_router(
        db=db, 
        db_router=router, 
        router_in=router_in,
        radius_db=radius_db
    )
    return router

@router_api.delete("/{router_id}", response_model=RouterResponse)
def delete_router(
    *,
    db: Session = Depends(get_db),
    radius_db: Session = Depends(get_radius_db),
    router_id: int,
    current_user: models.Usuario = Depends(get_current_active_user),
    _: bool = Depends(permission_checker("router_manage"))
):
    """
    Deletar um roteador da empresa do usuário atual.
    """
    router = crud.crud_router.get_router(db=db, router_id=router_id, empresa_id=current_user.active_empresa_id)
    if not router:
        raise HTTPException(status_code=404, detail="Roteador não encontrado")
    router = crud.crud_router.remove_router(
        db=db, 
        db_router=router,
        radius_db=radius_db
    )
    return router

@router_api.post("/{router_id}/setup-suspension/")
def setup_router_suspension(
    *,
    db: Session = Depends(get_db),
    router_id: int,
    current_user: models.Usuario = Depends(get_current_active_user),
    _: bool = Depends(permission_checker("router_manage"))
):
    """
    Configura automaticamente as regras de suspensão (Proxy, NAT, Firewall) no roteador.
    """
    # Buscar roteador e empresa
    router_db = crud.crud_router.get_router(db=db, router_id=router_id, empresa_id=current_user.active_empresa_id)
    if not router_db:
        raise HTTPException(status_code=404, detail="Roteador não encontrado")
    
    empresa = db.query(models.Empresa).filter(models.Empresa.id == current_user.active_empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # URL do portal captivo — é para cá que o MikroTik fará DST-NAT do tráfego HTTP
    # dos clientes bloqueados. O empresa_id já está embutido na URL, então o sistema
    # sabe qual página de aviso exibir sem precisar de Web Proxy.
    #
    # Formato: http://<IP_DO_SISTEMA>:<PORTA>/servicos-contratados/public/captive-portal/<empresa_id>
    # O backend responde com HTTP 302 → /public/aviso/empresa/<empresa_id>
    #
    # Se a empresa tiver uma suspension_url personalizada (IP próprio do servidor),
    # usamos ela como base; caso contrário, usamos o host padrão do sistema.
    from app.core.config import settings
    base_host = empresa.suspension_url.rstrip("/") if empresa.suspension_url else settings.BACKEND_URL.rstrip("/")
    suspension_url = f"{base_host}/servicos-contratados/public/captive-portal/{empresa.id}"

    from app.mikrotik.controller import MikrotikController
    from app.core.security import decrypt_password
    
    try:
        try:
            password = decrypt_password(router_db.senha)
        except Exception:
            password = router_db.senha

        mk = MikrotikController(
            host=router_db.ip,
            username=router_db.usuario,
            password=password,
            port=router_db.porta or 8728
        )
        
        results = mk.setup_full_suspension_system(suspension_url)
        return {"success": True, "details": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao configurar roteador: {str(e)}")

@router_api.post("/{router_id}/process-delinquents")
def process_router_delinquents(
    *,
    db: Session = Depends(get_db),
    router_id: int,
    current_user: models.Usuario = Depends(get_current_active_user),
    _: bool = Depends(permission_checker("router_manage"))
):
    """
    Executa o bloqueio e desbloqueio automático de inadimplentes associados a este roteador.
    """
    # 1. Buscar o roteador e verificar se pertence à empresa ativa do usuário
    empresa_id = current_user.active_empresa_id or 2
    router_db = crud.crud_router.get_router(db=db, router_id=router_id, empresa_id=empresa_id)
    if not router_db:
        raise HTTPException(status_code=404, detail="Roteador não encontrado")

    empresa = db.query(models.Empresa).filter(models.Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    dias_limite = empresa.dias_bloqueio_inadimplentes
    if dias_limite is None or dias_limite < 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Bloqueio automático desabilitado ou não configurado para esta empresa (limite atual: {dias_limite})."
        )

    # 2. Executar a lógica de bloqueio/desbloqueio apenas para contratos deste roteador
    from datetime import datetime, timezone, timedelta
    from app.models.models import Cliente, Receivable, ServicoContratado, StatusContrato
    from app.services.isp_service import process_block_if_needed, process_unblock_if_needed

    now = datetime.now(timezone.utc)
    limit_date = now - timedelta(days=dias_limite)

    # Buscar todos os clientes ativos da empresa
    clients = db.query(Cliente).filter(
        Cliente.empresa_id == empresa_id,
        Cliente.is_active == True
    ).all()

    contracts_blocked = 0
    contracts_reactivated = 0
    blocked_details = []
    reactivated_details = []
    errors = []

    for client in clients:
        # Encontrar cobranças pendentes e vencidas acima do limite
        overdue_receivables = db.query(Receivable).filter(
            Receivable.cliente_id == client.id,
            Receivable.empresa_id == empresa_id,
            Receivable.status == 'PENDING',
            Receivable.due_date <= limit_date
        ).all()

        should_be_blocked = len(overdue_receivables) > 0

        if should_be_blocked:
            # Buscar apenas os contratos ativos deste cliente que pertencem a ESTE roteador
            contracts = db.query(ServicoContratado).filter(
                ServicoContratado.cliente_id == client.id,
                ServicoContratado.empresa_id == empresa_id,
                ServicoContratado.router_id == router_id,
                ServicoContratado.status != StatusContrato.SUSPENSO,
                ServicoContratado.status != StatusContrato.CANCELADO
            ).all()

            for contract in contracts:
                try:
                    success = process_block_if_needed(db, contract.id)
                    if success:
                        contracts_blocked += 1
                        blocked_details.append(f"Contrato #{contract.id} - {client.nome_razao_social}")
                    else:
                        errors.append(f"Não foi possível bloquear o contrato #{contract.id} ({client.nome_razao_social})")
                except Exception as e:
                    errors.append(f"Erro ao processar bloqueio do contrato #{contract.id}: {str(e)}")
        else:
            # Buscar apenas os contratos suspensos deste cliente que pertencem a ESTE roteador
            suspended_contracts = db.query(ServicoContratado).filter(
                ServicoContratado.cliente_id == client.id,
                ServicoContratado.empresa_id == empresa_id,
                ServicoContratado.router_id == router_id,
                ServicoContratado.status == StatusContrato.SUSPENSO
            ).all()

            for contract in suspended_contracts:
                try:
                    success = process_unblock_if_needed(db, contract.id)
                    if success:
                        contracts_reactivated += 1
                        reactivated_details.append(f"Contrato #{contract.id} - {client.nome_razao_social}")
                    else:
                        errors.append(f"Não foi possível reativar o contrato #{contract.id} ({client.nome_razao_social})")
                except Exception as e:
                    errors.append(f"Erro ao processar reativação do contrato #{contract.id}: {str(e)}")

    if contracts_blocked > 0 or contracts_reactivated > 0:
        db.commit()

    return {
        "success": True,
        "contracts_blocked": contracts_blocked,
        "contracts_reactivated": contracts_reactivated,
        "blocked_details": blocked_details,
        "reactivated_details": reactivated_details,
        "errors": errors
    }