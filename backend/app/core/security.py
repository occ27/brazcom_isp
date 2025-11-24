from datetime import datetime, timedelta
from typing import Optional
import os

from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import base64
from dotenv import load_dotenv

# Carregar variáveis de ambiente imediatamente
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha corresponde ao hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Gera hash da senha"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "sub": str(to_encode["sub"])})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """Decodifica token JWT"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

# --- Criptografia para senhas de roteadores e outros dados sensíveis ---

# IMPORTANTE: Esta chave deve ser gerada uma vez e mantida em segurança!
# Para gerar uma chave: print(Fernet.generate_key().decode())
ROUTER_ENCRYPTION_KEY = os.getenv("ROUTER_ENCRYPTION_KEY")

if not ROUTER_ENCRYPTION_KEY:
    raise ValueError("ROUTER_ENCRYPTION_KEY não definida no ambiente.")

router_fernet = Fernet(ROUTER_ENCRYPTION_KEY.encode())

def encrypt_password(password: str) -> str:
    """Criptografa senhas de roteadores."""
    return router_fernet.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    """Descriptografa senhas de roteadores."""
    return router_fernet.decrypt(encrypted_password.encode()).decode()

# Criptografia Fernet para dados sensíveis
def _get_fernet_key() -> bytes:
    """Gera ou obtém chave Fernet baseada na SECRET_KEY"""
    # Usa os primeiros 32 bytes da SECRET_KEY como chave Fernet
    key = settings.SECRET_KEY.encode()[:32]
    # Garante que tenha exatamente 32 bytes
    if len(key) < 32:
        key = key.ljust(32, b'\0')
    # Codifica em base64 para Fernet
    return base64.urlsafe_b64encode(key)

def encrypt_sensitive_data(data: str) -> str:
    """Criptografa dados sensíveis (senhas de certificado, SMTP, etc.)"""
    if not data:
        return ""
    fernet = Fernet(_get_fernet_key())
    encrypted = fernet.encrypt(data.encode())
    return encrypted.decode()

def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Descriptografa dados sensíveis"""
    if not encrypted_data:
        return ""
    try:
        fernet = Fernet(_get_fernet_key())
        decrypted = fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
    except Exception as e:
        # Log do erro para debug
        print(f"ERRO ao descriptografar dados: {type(e).__name__}: {e}")
        print(f"Dados criptografados (primeiros 50 chars): {encrypted_data[:50]}")
        # Se falhar a descriptografia, retorna string vazia por segurança
        return ""
