import os
import tempfile

# Cria um diretório temporário para os certificados e configura as variáveis de ambiente
temp_dir = tempfile.mkdtemp()
os.environ["CERTIFICATES_DIR"] = temp_dir

from fastapi.testclient import TestClient
from app.main import app
from app.api import deps
from app.models.models import Usuario, Empresa
from app.core.database import SessionLocal

db = SessionLocal()
try:
    # Busca um usuário e uma empresa ativa no banco
    user = db.query(Usuario).filter(Usuario.is_active == True).first()
    emp = db.query(Empresa).filter(Empresa.id == 3).first()
    
    if not user or not emp:
        print("Usuário ou empresa não encontrados no banco.")
    else:
        # Override dependencies
        app.dependency_overrides[deps.get_current_active_user] = lambda: user
        app.dependency_overrides[deps.get_active_empresa] = lambda: emp
        app.dependency_overrides[deps.permission_checker("network_manage")] = lambda: True
        
        client = TestClient(app)
        
        # Test 1: Sem parâmetros
        r1 = client.get("/ftth/onts", headers={"Host": "localhost"})
        print(f"Status 1: {r1.status_code}")
        print(f"Text 1: {r1.text[:200]}")
        data1 = r1.json()
        print(f"Sem params: data length={len(data1.get('data', []))}, total={data1.get('total')}")
        
        # Test 2: Com limit=10000
        r2 = client.get("/ftth/onts?limit=10000&skip=0", headers={"Host": "localhost"})
        data2 = r2.json()
        print(f"Com limit=10000: data length={len(data2.get('data', []))}, total={data2.get('total')}")
        
        # Test 3: Com limit=10
        r3 = client.get("/ftth/onts?limit=10&skip=0", headers={"Host": "localhost"})
        data3 = r3.json()
        print(f"Com limit=10: data length={len(data3.get('data', []))}, total={data3.get('total')}")
        
finally:
    db.close()
    import shutil
    shutil.rmtree(temp_dir)
