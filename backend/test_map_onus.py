from app.core.database import SessionLocal
from app.models.models import ServicoContratado, Empresa

db = SessionLocal()
try:
    empresas = db.query(Empresa).all()
    for emp in empresas:
        onus = db.query(ServicoContratado).filter(
            ServicoContratado.empresa_id == emp.id,
            ServicoContratado.is_active == True,
            (ServicoContratado.onu_serial.isnot(None)) | (ServicoContratado.tipo_conexao == "FIBRA")
        ).all()
        
        has_coords = 0
        no_coords = 0
        for onu in onus:
            if onu.coordenadas_gps:
                has_coords += 1
            else:
                no_coords += 1
        print(f"Empresa {emp.id}: Total={len(onus)}, Com GPS={has_coords}, Sem GPS={no_coords}")
finally:
    db.close()
