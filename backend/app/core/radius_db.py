"""
Conexão secundária com o banco de dados do FreeRadius.

O FreeRadius lê/escreve nas tabelas radcheck, radreply, radacct, etc.
Este módulo fornece uma sessão direta a esse banco (porta 3315, banco 'radius')
para que o Brazcom ISP possa sincronizar usuários automaticamente.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Escapa caracteres especiais na senha (ex: '@', '#', '!' que quebram o parsing da URL)
_radius_password = quote_plus(settings.RADIUS_DB_PASSWORD)

# URL de conexão com o banco do FreeRadius (MySQL Docker porta 3315)
RADIUS_DB_URL = (
    f"mysql+pymysql://{settings.RADIUS_DB_USER}:{_radius_password}"
    f"@{settings.RADIUS_DB_HOST}:{settings.RADIUS_DB_PORT}/{settings.RADIUS_DB_NAME}"
)

try:
    radius_engine = create_engine(
        RADIUS_DB_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=5,
        max_overflow=10,
    )
    RadiusSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=radius_engine)
    logger.info("Conexão com banco FreeRadius configurada com sucesso.")
except Exception as e:
    logger.error(f"Erro ao configurar conexão com banco FreeRadius: {e}")
    RadiusSessionLocal = None


def get_radius_db():
    """
    Dependency FastAPI para obter sessão do banco FreeRadius.
    Uso: radius_db: Session = Depends(get_radius_db)
    """
    if RadiusSessionLocal is None:
        raise RuntimeError("Banco FreeRadius não configurado. Verifique as variáveis RADIUS_DB_* no .env")
    db = RadiusSessionLocal()
    try:
        yield db
    finally:
        db.close()
