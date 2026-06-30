import sys
sys.path.append("/Users/orlando/python/FastAPI/brazcom_isp/backend")

from app.core.database import SessionLocal
from app.models.models import Permission

db = SessionLocal()

existing = db.query(Permission).filter(Permission.name == 'company_manage').first()
if existing:
    print(f"company_manage ID: {existing.id}")
else:
    print("company_manage not found!")

