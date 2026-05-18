import logging
from sqlalchemy import create_engine, text
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_column():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        db_type = engine.name
        logger.info(f"Connecting to database of type: {db_type}")
        
        column_exists = False
        if db_type == "mysql":
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'empresas' AND COLUMN_NAME = 'dias_bloqueio_inadimplentes'"
            ))
            column_exists = result.scalar() > 0
        elif db_type == "sqlite":
            result = conn.execute(text("PRAGMA table_info(empresas)"))
            columns = [row[1] for row in result.fetchall()]
            column_exists = "dias_bloqueio_inadimplentes" in columns
            
        if not column_exists:
            logger.info("Column 'dias_bloqueio_inadimplentes' does not exist in 'empresas' table. Adding it...")
            if db_type == "mysql":
                conn.execute(text(
                    "ALTER TABLE empresas ADD COLUMN dias_bloqueio_inadimplentes INT DEFAULT 15 "
                    "COMMENT 'Prazo em dias após o vencimento para bloqueio automático de clientes inadimplentes'"
                ))
            elif db_type == "sqlite":
                conn.execute(text("ALTER TABLE empresas ADD COLUMN dias_bloqueio_inadimplentes INTEGER DEFAULT 15"))
            conn.commit()
            logger.info("Column 'dias_bloqueio_inadimplentes' added successfully!")
        else:
            logger.info("Column 'dias_bloqueio_inadimplentes' already exists in 'empresas' table.")

if __name__ == "__main__":
    add_column()
