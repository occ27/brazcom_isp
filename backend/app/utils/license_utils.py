from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
from app.models.license import CompanyLicense, LicenseStatus
from app.models.models import Usuario

def check_company_license(db: Session, empresa_id: int, current_user: Usuario):
    """
    Verifica se a empresa possui uma licença de software ativa e válida.
    Superusers ignoram essa verificação.
    Lança HTTPException(402) se não houver licença válida.
    """
    # Superusers podem opcionalmente ignorar, mas para fins de teste de bloqueio do sistema
    # e para garantir que ninguém use recursos sem licença, vamos remover o bypass.
    # Se o superuser precisar de acesso de emergência, ele pode ativar a licença manualmente.
    # if current_user.is_superuser:
    #     return None

    license_db = db.query(CompanyLicense).filter(
        CompanyLicense.empresa_id == empresa_id,
        CompanyLicense.status == LicenseStatus.ACTIVE,
        CompanyLicense.end_date > datetime.now()
    ).first()
    
    if not license_db:
        raise HTTPException(
            status_code=402,
            detail="A empresa não possui uma licença ativa. Por favor, regularize sua licença para continuar acessando os recursos."
        )
    return license_db
