import sys
sys.path.append("/Users/orlando/python/FastAPI/brazcom_isp/backend")

from app.core.database import SessionLocal
from app.models.models import Usuario, Role
from app.crud import crud_caixa
from app.schemas import caixa as schema_caixa

db = SessionLocal()

secretary = db.query(Usuario).filter(Usuario.is_superuser == False).first()

if not secretary:
    print("No non-superuser found.")
    sys.exit(0)

print(f"Testing with user ID: {secretary.id}, empresa: {secretary.active_empresa_id}")

try:
    locais = crud_caixa.get_locais_pagamento(db, secretary.active_empresa_id)
    print(f"Locais: {[l.nome for l in locais]}")
    if locais:
        # Check if already open
        sessao_existente = crud_caixa.get_sessao_atual(db, secretary.active_empresa_id, secretary.id)
        if sessao_existente:
            print(f"User already has an open session: {sessao_existente.id}")
        else:
            # Check if someone else opened it
            sessoes_neste_local = crud_caixa.get_sessoes_abertas_local(db, secretary.active_empresa_id, locais[0].id)
            if sessoes_neste_local:
                print(f"Local {locais[0].id} already open by another user: {sessoes_neste_local[0].usuario_id}")
            else:
                print("Secretary CAN open the Caixa! No backend restrictions found.")
    else:
        print("No Locais de Pagamento found for this empresa.")
except Exception as e:
    print(f"Error: {str(e)}")

