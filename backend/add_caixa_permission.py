import sys
sys.path.append("/Users/orlando/python/FastAPI/brazcom_isp/backend")

from app.core.database import SessionLocal
from app.models.models import Permission

db = SessionLocal()

# Check if it exists
existing = db.query(Permission).filter(Permission.name == 'caixa_manage').first()
if existing:
    print(f"Permission already exists with ID: {existing.id}")
else:
    new_perm = Permission(name='caixa_manage', description='Gerenciar caixas (histórico e operações avançadas)')
    db.add(new_perm)
    db.commit()
    db.refresh(new_perm)
    print(f"Created permission 'caixa_manage' with ID: {new_perm.id}")

