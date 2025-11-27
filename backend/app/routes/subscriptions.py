from fastapi import APIRouter, Depends, HTTPException
import logging
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

    # Provision based on auth_method
    try:
        password = decrypt_password(router_db.senha) if router_db.senha else ""
        mk = MikrotikController(host=router_db.ip, username=router_db.usuario, password=password, port=router_db.porta)

        if sub_in.auth_method == 'ip_mac' or sub_in.auth_method is None:
            # IP + MAC Authentication - Add ARP entry
            mk.set_arp_entry(ip=str(sub_in.ip), mac=sub_in.mac, interface=sub_in.interface)

        elif sub_in.auth_method == 'pppoe':
            # PPPoE Authentication - Add PPPoE user
            # Get PPP profile from service and rate limit from service max_limit
            ppp_profile_name = None
            rate_limit = None
            if sub_in.servico_id:
                servico = db.query(models.Servico).filter(models.Servico.id == sub_in.servico_id, models.Servico.empresa_id == empresa_id).first()
                if servico:
                    # Get PPP profile name
                    if servico.ppp_profile_id:
                        ppp_profile = db.query(models.PPPProfile).filter(models.PPPProfile.id == servico.ppp_profile_id).first()
                        if ppp_profile:
                            ppp_profile_name = ppp_profile.nome
                            # Ensure PPP profile exists on router and verify creation
                            try:
                                logger = logging.getLogger(__name__)
                                logger.debug(f"Sincronizando PPP profile '{ppp_profile_name}' no roteador {router_db.ip}")
                                mk.add_pppoe_profile(
                                    name=ppp_profile.nome,
                                    local_address=ppp_profile.local_address,
                                    remote_address_pool=ppp_profile.remote_address_pool.nome if ppp_profile.remote_address_pool else "",
                                    rate_limit=ppp_profile.rate_limit,
                                    comment=ppp_profile.comentario
                                )
                                # Verify the profile exists on the router
                                try:
                                    profiles = mk.get_ppp_profiles()
                                    found = any((p.get('name') == ppp_profile_name or p.get('name') == str(ppp_profile_name)) for p in profiles)
                                    if not found:
                                        logger.warning(f"Perfil PPP '{ppp_profile_name}' não apareceu no roteador após criação")
                                except Exception as e2:
                                    logger.debug(f"Falha ao listar ppp profiles no roteador: {e2}")
                            except Exception as e:
                                # Log error but continue - profile might already exist or router rejected it
                                logging.getLogger(__name__).warning(f"Falha ao criar/sincronizar PPP profile '{ppp_profile_name}' no roteador: {e}")
                    # Get rate limit from service max_limit
                    if hasattr(servico, 'max_limit') and servico.max_limit:
                        rate_limit = servico.max_limit

            # Add PPPoE user with profile from service, rate limit from service, and credentials from contract
            mk.add_pppoe_user(
                username=sub_in.username,
                password=sub_in.password,
                profile=ppp_profile_name,
                rate_limit=rate_limit
            )

        elif sub_in.auth_method == 'hotspot':
            # Hotspot Authentication - Configure Hotspot user
            # TODO: Implement Hotspot user creation
            # mk.add_hotspot_user(username=f"user_{subscription.id}", password=sub_in.password, profile="default")
            pass  # Placeholder for Hotspot implementation

        elif sub_in.auth_method == 'radius':
            # RADIUS Authentication - Configure RADIUS client
            # TODO: Implement RADIUS configuration
            # mk.configure_radius_client(server="radius-server-ip", secret="radius-secret")
            pass  # Placeholder for RADIUS implementation

        # Create queue for bandwidth control (common to all methods)
        servico = None
        if sub_in.servico_id:
            servico = db.query(models.Servico).filter(models.Servico.id == sub_in.servico_id, models.Servico.empresa_id == empresa_id).first()
        if servico and hasattr(servico, 'max_limit') and servico.max_limit:
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
            if sub_in.auth_method == 'ip_mac' or sub_in.auth_method is None:
                mk.remove_arp_entry(ip=str(sub_in.ip), mac=sub_in.mac)
            elif sub_in.auth_method == 'pppoe':
                mk.remove_pppoe_user(username=sub_in.username)
        except Exception:
            pass
        subscription = crud.crud_subscription.update_subscription_status(db=db, db_sub=subscription, status='failed', notes=str(exc))
        raise HTTPException(status_code=500, detail=f"Erro ao provisionar assinatura: {exc}")

    return subscription
