import logging
from sqlalchemy import create_engine, text
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_columns():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        db_type = engine.name
        logger.info(f"Connecting to database of type: {db_type}")
        
        # 1. Check/Add auto_send_notifications to empresas
        emp_column_exists = False
        if db_type == "mysql":
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'empresas' AND COLUMN_NAME = 'auto_send_notifications'"
            ))
            emp_column_exists = result.scalar() > 0
        elif db_type == "sqlite":
            result = conn.execute(text("PRAGMA table_info(empresas)"))
            columns = [row[1] for row in result.fetchall()]
            emp_column_exists = "auto_send_notifications" in columns
            
        if not emp_column_exists:
            logger.info("Column 'auto_send_notifications' does not exist in 'empresas' table. Adding it...")
            if db_type == "mysql":
                conn.execute(text(
                    "ALTER TABLE empresas ADD COLUMN auto_send_notifications BOOLEAN NOT NULL DEFAULT TRUE "
                    "COMMENT 'Define se a empresa realiza o envio automático de notificações de cobrança'"
                ))
            elif db_type == "sqlite":
                conn.execute(text("ALTER TABLE empresas ADD COLUMN auto_send_notifications BOOLEAN NOT NULL DEFAULT 1"))
            
            conn.commit()
            logger.info("Column 'auto_send_notifications' added successfully to 'empresas'!")
        else:
            logger.info("Column 'auto_send_notifications' already exists in 'empresas' table.")
            
        # 2. Check/Add recebe_notificacoes to clientes
        cli_column_exists = False
        if db_type == "mysql":
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'clientes' AND COLUMN_NAME = 'recebe_notificacoes'"
            ))
            cli_column_exists = result.scalar() > 0
        elif db_type == "sqlite":
            result = conn.execute(text("PRAGMA table_info(clientes)"))
            columns = [row[1] for row in result.fetchall()]
            cli_column_exists = "recebe_notificacoes" in columns
            
        if not cli_column_exists:
            logger.info("Column 'recebe_notificacoes' does not exist in 'clientes' table. Adding it...")
            if db_type == "mysql":
                conn.execute(text(
                    "ALTER TABLE clientes ADD COLUMN recebe_notificacoes BOOLEAN NOT NULL DEFAULT TRUE "
                    "COMMENT 'Define se o cliente aceita receber notificações automáticas do sistema'"
                ))
            elif db_type == "sqlite":
                conn.execute(text("ALTER TABLE clientes ADD COLUMN recebe_notificacoes BOOLEAN NOT NULL DEFAULT 1"))
            
            conn.commit()
            logger.info("Column 'recebe_notificacoes' added successfully to 'clientes'!")
        else:
            logger.info("Column 'recebe_notificacoes' already exists in 'clientes' table.")

if __name__ == "__main__":
    add_columns()
