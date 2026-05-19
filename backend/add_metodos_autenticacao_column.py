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
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'routers' AND COLUMN_NAME = 'metodos_autenticacao'"
            ))
            column_exists = result.scalar() > 0
        elif db_type == "sqlite":
            result = conn.execute(text("PRAGMA table_info(routers)"))
            columns = [row[1] for row in result.fetchall()]
            column_exists = "metodos_autenticacao" in columns
            
        if not column_exists:
            logger.info("Column 'metodos_autenticacao' does not exist in 'routers' table. Adding it...")
            if db_type == "mysql":
                conn.execute(text(
                    "ALTER TABLE routers ADD COLUMN metodos_autenticacao JSON NULL "
                    "COMMENT 'Lista de métodos de autenticação habilitados para este router (ex: [\"PPPOE\", \"RADIUS\"])'"
                ))
            elif db_type == "sqlite":
                conn.execute(text("ALTER TABLE routers ADD COLUMN metodos_autenticacao TEXT NULL"))
            # Commit the transaction explicitly
            conn.commit()
            logger.info("Column 'metodos_autenticacao' added successfully!")
        else:
            logger.info("Column 'metodos_autenticacao' already exists in 'routers' table.")

if __name__ == "__main__":
    add_column()
