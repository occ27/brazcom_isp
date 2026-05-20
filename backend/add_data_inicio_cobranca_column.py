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
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'servicos_contratados' AND COLUMN_NAME = 'data_inicio_cobranca'"
            ))
            column_exists = result.scalar() > 0
        elif db_type == "sqlite":
            result = conn.execute(text("PRAGMA table_info(servicos_contratados)"))
            columns = [row[1] for row in result.fetchall()]
            column_exists = "data_inicio_cobranca" in columns
            
        if not column_exists:
            logger.info("Column 'data_inicio_cobranca' does not exist in 'servicos_contratados' table. Adding it...")
            if db_type == "mysql":
                conn.execute(text(
                    "ALTER TABLE servicos_contratados ADD COLUMN data_inicio_cobranca DATE NULL "
                    "COMMENT 'Data personalizada de início de cobrança para o contrato'"
                ))
            elif db_type == "sqlite":
                conn.execute(text("ALTER TABLE servicos_contratados ADD COLUMN data_inicio_cobranca DATE NULL"))
            
            conn.commit()
            logger.info("Column 'data_inicio_cobranca' added successfully!")
            
            # Backfill existing records
            logger.info("Backfilling 'data_inicio_cobranca' with 'd_contrato_ini'...")
            conn.execute(text(
                "UPDATE servicos_contratados SET data_inicio_cobranca = d_contrato_ini WHERE data_inicio_cobranca IS NULL"
            ))
            conn.commit()
            logger.info("Backfill completed successfully!")
        else:
            logger.info("Column 'data_inicio_cobranca' already exists in 'servicos_contratados' table.")

if __name__ == "__main__":
    add_column()
