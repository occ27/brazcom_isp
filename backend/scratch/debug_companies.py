from app.core.database import SessionLocal
from app.models.models import ServicoContratado, Cliente, Empresa
from app.models.models import StatusContrato

db = SessionLocal()
try:
    empresas = db.query(Empresa).all()
    for emp in empresas:
        onus = db.query(ServicoContratado).filter(
            ServicoContratado.empresa_id == emp.id,
            ServicoContratado.is_active == True,
            ServicoContratado.status != StatusContrato.CANCELADO,
            (ServicoContratado.onu_serial.isnot(None)) | (ServicoContratado.tipo_conexao == "FIBRA")
        ).all()
        
        with_gps = [o for o in onus if o.coordenadas_gps is not None]
        print(f"Empresa: ID={emp.id}, Nome={emp.nome_fantasia or emp.razao_social}")
        print(f"  Total active ONUs: {len(onus)}")
        print(f"  With GPS: {len(with_gps)}")
        for o in with_gps:
            print(f"    - ONU ID={o.id}, GPS={o.coordenadas_gps}")
finally:
    db.close()
