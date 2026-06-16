from app.core.database import SessionLocal
from app.models.ftth import CTO

db = SessionLocal()
try:
    from app.models.models import Empresa
    empresas = db.query(Empresa).all()
    for emp in empresas:
        ctos = db.query(CTO).filter(
            CTO.empresa_id == emp.id,
            CTO.is_active == True
        ).all()
        
        has_coords = 0
        no_coords = 0
        for cto in ctos:
            if cto.coordenadas_gps:
                has_coords += 1
            else:
                no_coords += 1
                
        print(f"Empresa {emp.id}: Total CTOs: {len(ctos)}, With GPS: {has_coords}, Without GPS: {no_coords}")
finally:
    db.close()
