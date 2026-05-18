import logging
from sqlalchemy import create_engine, text
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_column():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        # Check if the column already exists
        # We can use information_schema for MySQL, or pragma for SQLite
        db_type = engine.name
        logger.info(f"Connecting to database of type: {db_type}")
        
        column_exists = False
        if db_type == "mysql":
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'routers' AND COLUMN_NAME = 'api_encoding'"
            ))
            column_exists = result.scalar() > 0
        elif db_type == "sqlite":
            result = conn.execute(text("PRAGMA table_info(routers)"))
            columns = [row[1] for row in result.fetchall()]
            column_exists = "api_encoding" in columns
            
        if not column_exists:
            logger.info("Column 'api_encoding' does not exist in 'routers' table. Adding it...")
            if db_type == "mysql":
                conn.execute(text(
                    "ALTER TABLE routers ADD COLUMN api_encoding VARCHAR(20) DEFAULT 'utf-8' "
                    "COMMENT 'Codificação da API do MikroTik: utf-8 ou latin1'"
                ))
            elif db_type == "sqlite":
                conn.execute(text("ALTER TABLE routers ADD COLUMN api_encoding VARCHAR(20) DEFAULT 'utf-8'"))
            # Commit the transaction explicitly
            conn.commit()
            logger.info("Column 'api_encoding' added successfully!")
        else:
            logger.info("Column 'api_encoding' already exists in 'routers' table.")

if __name__ == "__main__":
    add_column()
