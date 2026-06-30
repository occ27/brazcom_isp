import sys
sys.path.append("/Users/orlando/python/FastAPI/brazcom_isp/backend")

from app.core.database import SessionLocal
from app.models.models import Permission

db = SessionLocal()

existing = db.query(Permission).filter(Permission.name == 'company_manage').first()
if not existing:
    new_perm = Permission(name='company_manage', description='Gerenciar dados da empresa (Locais e Formas de Pagamento)')
    db.add(new_perm)
    db.commit()
    db.refresh(new_perm)
    print(f"Created company_manage with ID: {new_perm.id}")
