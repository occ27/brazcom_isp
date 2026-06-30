import sys
sys.path.append("/Users/orlando/python/FastAPI/brazcom_isp/backend")

from app.core.database import SessionLocal
from app.models.models import Permission

db = SessionLocal()
perms = db.query(Permission).all()
for p in perms:
    print(f"{p.id}: {p.name} - {p.description}")
