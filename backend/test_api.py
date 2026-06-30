import sys
sys.path.append("/Users/orlando/python/FastAPI/brazcom_isp/backend")
from app.core.database import SessionLocal
from app.models.models import Usuario
from fastapi.testclient import TestClient
from app.main import app

db = SessionLocal()
user = db.query(Usuario).filter(Usuario.is_superuser == True).first()

# Create a token for the user (we just mock it if we can't easily, but let's just call the route function directly)
from app.routes.usuarios import get_my_active_empresa
try:
    emp = get_my_active_empresa(db, user)
    print("Active empresa returned:", emp.id)
except Exception as e:
    print("Error:", e)

