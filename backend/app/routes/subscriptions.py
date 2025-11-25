from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app import crud, models
from app.schemas.subscription import SubscriptionCreate, SubscriptionResponse
from app.core.security import decrypt_password
from app.mikrotik.controller import MikrotikController

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.post("/", response_model=SubscriptionResponse)
def create_subscription(
    *,
    sub_in: SubscriptionCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.Usuario = Depends(deps.get_current_active_user),
):
    empresa_id = current_user.active_empresa_id or 0

    # Validations
    cliente = db.query(models.Cliente).filter(models.Cliente.id == sub_in.cliente_id, models.Cliente.empresa_id == empresa_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado na empresa")

    router_db = db.query(models.Router).filter(models.Router.id == sub_in.router_id, models.Router.empresa_id == empresa_id).first()
    if not router_db:
        raise HTTPException(status_code=404, detail="Roteador não encontrado na empresa")

    # Persist subscription as pending
    subscription = crud.crud_subscription.create_subscription(db=db, sub_in=sub_in, empresa_id=empresa_id)

    # Provision synchronously (MVP) - IP+MAC
    try:
        if sub_in.auth_method != 'ip_mac' and sub_in.auth_method is not None:
            # For MVP we only support ip_mac; reject others for now
            raise HTTPException(status_code=400, detail="Somente auth_method 'ip_mac' é suportado no MVP")

        password = decrypt_password(router_db.senha) if router_db.senha else ""
        mk = MikrotikController(host=router_db.ip, username=router_db.usuario, password=password, port=router_db.porta)

        # Add ARP entry
        mk.set_arp_entry(ip=str(sub_in.ip), mac=sub_in.mac, interface=sub_in.interface)

        # Optionally create queue if servico provides limits (best-effort)
        servico = None
        if sub_in.servico_id:
            servico = db.query(models.Servico).filter(models.Servico.id == sub_in.servico_id, models.Servico.empresa_id == empresa_id).first()
        if servico and hasattr(servico, 'max_limit') and servico.max_limit:
            # use name unique to subscription
            queue_name = f"sub-{subscription.id}"
            mk.set_queue_simple(name=queue_name, target=f"{subscription.ip}/32", max_limit=servico.max_limit)

        mk.close()
        # mark active
        subscription = crud.crud_subscription.update_subscription_status(db=db, db_sub=subscription, status='active')
    except HTTPException:
        # re-raise explicit HTTP errors
        raise
    except Exception as exc:
        try:
            # try best-effort rollback
            mk.remove_arp_entry(ip=str(sub_in.ip), mac=sub_in.mac)
        except Exception:
            pass
        subscription = crud.crud_subscription.update_subscription_status(db=db, db_sub=subscription, status='failed', notes=str(exc))
        raise HTTPException(status_code=500, detail=f"Erro ao provisionar assinatura: {exc}")

    return subscription
