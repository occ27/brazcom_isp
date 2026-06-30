import sys
sys.path.append("/Users/orlando/python/FastAPI/brazcom_isp/backend")
from app.core.database import SessionLocal
from app.models.models import Usuario
db = SessionLocal()
user = db.query(Usuario).filter(Usuario.is_superuser == True).first()
print(f"User: {user.email}, active_empresa_id: {user.active_empresa_id}")
