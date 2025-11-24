from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Database
    # Padrão para desenvolvimento local: MySQL na porta 3306
    # Em produção (Docker), será sobrescrito via .env com db:3306
    DATABASE_URL: str = "mysql+pymysql://occ:Altavista740@localhost:3306/brazcom_db"

    # Security
    SECRET_KEY: str = "a_very_secret_key_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 dias

    # CORS
    # Em desenvolvimento local: permite frontend local (porta 3000)
    # Em produção: adicione o domínio https://nfcom.holeshot.com.br
    # Múltiplas origens separadas por vírgula no .env
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Uploads
    UPLOAD_DIR: str = "uploads"
    # Em desenvolvimento local (Windows): usa caminho Windows
    # Em produção (Docker/Linux): será sobrescrito via .env para /etc/ssl/nfcom
    CERTIFICATES_DIR: str = os.getenv("CERTIFICATES_DIR", "C:\\etc\\ssl\\nfcom" if os.name == 'nt' else "/etc/ssl/nfcom")
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    # NFCom - Ambiente de Transmissão
    # "homologacao" = Ambiente de testes (padrão para desenvolvimento)
    # "producao" = Ambiente de produção (emissão real)
    NFCOM_AMBIENTE: str = "homologacao"

    # Brazcom SMTP default (used for password reset emails)
    BRAZCOM_SMTP_SERVER: str = "smtp.gmail.com"
    BRAZCOM_SMTP_PORT: int = 587
    BRAZCOM_SMTP_USERNAME: str = "brazcom.contato@gmail.com"
    BRAZCOM_SMTP_PASSWORD: str = "nvnwobdqgfsfmfbb"

    @property
    def cors_origins_list(self) -> List[str]:
        vals = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        # Se o curinga '*' estiver presente, devolve ['*'] para permitir todas as origens
        if any(v == '*' for v in vals):
            return ['*']
        return vals

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = 'ignore'  # Ignore extra environment variables

settings = Settings()