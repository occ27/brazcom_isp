from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api import deps
from app import crud, models
from app.schemas.isp import IspClientCreate, IspClientResponse
from app.mikrotik.controller import MikrotikController
from app.core.security import decrypt_password

router = APIRouter(prefix="/isp", tags=["ISP"])


@router.post("/clients/", response_model=IspClientResponse)
def create_isp_client(
    *,
    isp_in: IspClientCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.Usuario = Depends(deps.get_current_active_user),
):
    empresa_id = current_user.active_empresa_id or isp_in.router_id  # fallback minimal

    # Backend permission: require contract_manage to provision ISP clients
    deps.permission_checker('contract_manage')(db=db, current_user=current_user)
    # Valida se cliente e servico existem (simples check)
    cliente = db.query(models.Cliente).filter(models.Cliente.id == isp_in.cliente_id, models.Cliente.empresa_id == empresa_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado na empresa")

    router_db = db.query(models.Router).filter(models.Router.id == isp_in.router_id, models.Router.empresa_id == empresa_id).first()
    if not router_db:
        raise HTTPException(status_code=404, detail="Roteador não encontrado na empresa")

    # Persiste o cliente ISP no banco
    isp_client = crud.crud_isp.create_isp_client(db=db, isp_in=isp_in, empresa_id=empresa_id)

    # Tenta aplicar a regra no roteador (ARP + queue opcional)
    try:
        # Descriptografa senha armazenada (usar decrypt_password do core.security)
        password = decrypt_password(router_db.senha) if router_db.senha else ""
        mk = MikrotikController(host=router_db.ip, username=router_db.usuario, password=password, port=router_db.porta)
        mk.set_arp_entry(ip=str(isp_in.ip), mac=isp_in.mac, interface=isp_in.interface)
        # Se existir informação de plano/servico, podemos aplicar queue_simple — omitido por agora
        mk.close()
    except Exception as exc:
        # Não reverte criação no banco, mas reporta erro para o cliente API.
        raise HTTPException(status_code=500, detail=f"Erro ao aplicar regra no roteador: {exc}")

    return isp_client
