from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.subscription import Subscription
from app.schemas.subscription import SubscriptionCreate


def create_subscription(db: Session, sub_in: SubscriptionCreate, empresa_id: int) -> Subscription:
    db_obj = Subscription(
        empresa_id=empresa_id,
        cliente_id=sub_in.cliente_id,
        servico_id=sub_in.servico_id,
        router_id=sub_in.router_id,
        ip=str(sub_in.ip),
        mac=sub_in.mac,
        interface=sub_in.interface,
        auth_method=sub_in.auth_method,
        contract_length_months=sub_in.contract_length_months,
        price=sub_in.price,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_subscription(db: Session, subscription_id: int, empresa_id: int) -> Optional[Subscription]:
    return db.query(Subscription).filter(Subscription.id == subscription_id, Subscription.empresa_id == empresa_id).first()


def list_subscriptions(db: Session, empresa_id: int, skip: int = 0, limit: int = 100) -> List[Subscription]:
    return db.query(Subscription).filter(Subscription.empresa_id == empresa_id).offset(skip).limit(limit).all()


def update_subscription_status(db: Session, db_sub: Subscription, status: str, notes: Optional[str] = None) -> Subscription:
    db_sub.status = status
    if notes:
        db_sub.notes = notes
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)
    return db_sub
