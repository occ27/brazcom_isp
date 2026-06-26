import sys, os
sys.path.insert(0, os.path.abspath('.'))
from app.core.database import engine
from sqlalchemy import text

with engine.connect() as con:
    con.execute(text("ALTER TABLE empresas ADD COLUMN dias_cancelamento_inadimplentes INT DEFAULT 90"))
    con.execute(text("UPDATE empresas SET dias_cancelamento_inadimplentes = 90"))
    con.commit()
