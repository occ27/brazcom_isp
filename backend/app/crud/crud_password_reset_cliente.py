from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.models import PasswordResetTokenCliente, Cliente


def create_password_reset_token(db: Session, cliente: Cliente, code: str, expires_minutes: int = 15):
    expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
    token = PasswordResetTokenCliente(cliente_id=cliente.id, code=code, expires_at=expires_at, used=False)
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def get_reset_token_by_code(db: Session, code: str):
    return db.query(PasswordResetTokenCliente).filter(PasswordResetTokenCliente.code == code).first()


def get_active_token_for_cliente(db: Session, cliente_id: int):
    now = datetime.utcnow()
    return db.query(PasswordResetTokenCliente).filter(
        PasswordResetTokenCliente.cliente_id == cliente_id,
        PasswordResetTokenCliente.used == False,
        PasswordResetTokenCliente.expires_at >= now
    ).order_by(PasswordResetTokenCliente.created_at.desc()).first()


def mark_token_used(db: Session, token: PasswordResetTokenCliente):
    token.used = True
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def cleanup_expired_tokens(db: Session):
    now = datetime.utcnow()
    expired = db.query(PasswordResetTokenCliente).filter(PasswordResetTokenCliente.expires_at < now).all()
    for t in expired:
        db.delete(t)
    db.commit()
    return True