import sys
sys.path.append("/Users/orlando/python/FastAPI/brazcom_isp/backend")
from app.core.database import SessionLocal
from app.models.models import Role, Permission

db = SessionLocal()
sec_role = db.query(Role).filter(Role.name == "secretary").first()
if sec_role:
    # Add router_view (5) and radius_view (7)
    p5 = db.query(Permission).filter(Permission.id == 5).first()
    p7 = db.query(Permission).filter(Permission.id == 7).first()
    if p5 and p5 not in sec_role.permissions:
        sec_role.permissions.append(p5)
    if p7 and p7 not in sec_role.permissions:
        sec_role.permissions.append(p7)
    db.commit()
    print("Permissions added.")
else:
    print("Secretary role not found.")
