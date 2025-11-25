from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.isp import IspClient
from app.schemas.isp import IspClientCreate


def create_isp_client(db: Session, isp_in: IspClientCreate, empresa_id: int) -> IspClient:
    db_obj = IspClient(
        empresa_id=empresa_id,
        cliente_id=isp_in.cliente_id,
        servico_id=isp_in.servico_id,
        router_id=isp_in.router_id,
        ip=str(isp_in.ip),
        mac=isp_in.mac,
        interface=isp_in.interface,
        is_active=isp_in.is_active,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_isp_client(db: Session, client_id: int, empresa_id: int) -> Optional[IspClient]:
    return db.query(IspClient).filter(IspClient.id == client_id, IspClient.empresa_id == empresa_id).first()


def get_isp_clients_by_empresa(db: Session, empresa_id: int, skip: int = 0, limit: int = 100) -> List[IspClient]:
    return db.query(IspClient).filter(IspClient.empresa_id == empresa_id).offset(skip).limit(limit).all()
