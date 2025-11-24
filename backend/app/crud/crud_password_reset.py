from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.models import PasswordResetToken, Usuario


def create_password_reset_token(db: Session, usuario: Usuario, code: str, expires_minutes: int = 15):
    expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
    token = PasswordResetToken(usuario_id=usuario.id, code=code, expires_at=expires_at, used=False)
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def get_reset_token_by_code(db: Session, code: str):
    return db.query(PasswordResetToken).filter(PasswordResetToken.code == code).first()


def get_active_token_for_user(db: Session, usuario_id: int):
    now = datetime.utcnow()
    return db.query(PasswordResetToken).filter(
        PasswordResetToken.usuario_id == usuario_id,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at >= now
    ).order_by(PasswordResetToken.created_at.desc()).first()


def mark_token_used(db: Session, token: PasswordResetToken):
    token.used = True
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def cleanup_expired_tokens(db: Session):
    now = datetime.utcnow()
    expired = db.query(PasswordResetToken).filter(PasswordResetToken.expires_at < now).all()
    for t in expired:
        db.delete(t)
    db.commit()
    return True
