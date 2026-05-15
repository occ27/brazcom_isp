import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.core.database import engine
from sqlalchemy import text

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE servicos_contratados ADD COLUMN endereco_id INT DEFAULT NULL;"))
        conn.execute(text("ALTER TABLE servicos_contratados ADD CONSTRAINT fk_servico_contratado_endereco FOREIGN KEY (endereco_id) REFERENCES empresa_cliente_enderecos(id);"))
    print("Migracao concluida com sucesso!")
except Exception as e:
    print(f"Erro: {e}")
