from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.database import Base, engine
from sqlalchemy import text
from app.core.config import settings
from app.routes import usuarios, empresas, clientes, nfcom, auth, uploads
from app.routes import servicos
from app.routes import servicos_contratados
from app.routes import dashboard
from app.routes import access_control
from app.routes import router
from app.routes import radius
from app.routes import subscriptions
from app.routes import isp

# A criação das tabelas será feita no evento de startup, após o DB ficar disponível

from pathlib import Path
import time
import logging

# Cria diretório de uploads se não existir
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Cria diretório de certificados (CERTIFICATES_DIR) se não existir
cert_dir = Path(settings.CERTIFICATES_DIR)
cert_dir.mkdir(parents=True, exist_ok=True)
# Cria um link simbólico /secure apontando para o diretório de certificados
# Alguns registros no banco podem armazenar caminhos absolutos como
# /secure/certificates/..; para compatibilidade local/criacao por compose,
# criamos um symlink quando possível que aponta para o CERTIFICATES_DIR.
try:
    secure_link = Path('/secure')
    log = logging.getLogger("uvicorn.error")
    if not secure_link.exists():
        secure_link.symlink_to(cert_dir)
        log.info("Criado symlink /secure -> %s", cert_dir)
    else:
        # Se já existe, apenas logamos (poderia ser um diretório real)
        log.info("/secure já existe: %s", secure_link)
except Exception as e:
    logging.getLogger("uvicorn.error").warning("Não foi possível criar symlink /secure -> %s: %s", cert_dir, e)

app = FastAPI(
    title="Brazcom API",
    description="API para Gestão do sistema Brazcom ISP Suite",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    redirect_slashes=False  # Desabilitado para evitar conflitos com proxy
)


logger = logging.getLogger("uvicorn.error")


def wait_for_db_and_migrate(retries: int = 10, delay: int = 2) -> None:
    """Tentativa simples de conectar no banco até que esteja pronto, então cria as tabelas.

    retries: número de tentativas
    delay: segundos entre tentativas
    """
    attempt = 0
    while attempt < retries:
        try:
            logger.info("Tentando conectar ao banco de dados (tentativa %d/%d)", attempt + 1, retries)
            with engine.connect():
                logger.info("Conexão com o banco estabelecida, aplicando migrations (create_all)")
                Base.metadata.create_all(bind=engine)
                return
        except Exception as exc:
            logger.warning("Banco não disponível ainda: %s", exc)
            attempt += 1
            time.sleep(delay)

    # Se chegou aqui, não conseguiu conectar
    logger.error("Não foi possível conectar ao banco após %d tentativas", retries)

# Configuração do CORS
cors_origins = settings.cors_origins_list
# Se a configuração indicar '*', não habilitamos allow_credentials (navegadores
# bloqueiam Access-Control-Allow-Credentials: true com Access-Control-Allow-Origin: *).
allow_credentials = False if len(cors_origins) == 1 and cors_origins[0] == '*' else True
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    # Expor cabeçalhos customizados que o frontend precisa ler (por exemplo X-Total-Count)
    expose_headers=["X-Total-Count"] if "X-Total-Count" not in [] else ["X-Total-Count"],
)

# Serve arquivos estáticos (APENAS logos) - certificados são servidos via rota protegida
from pathlib import Path
uploads_dir = Path(settings.UPLOAD_DIR)
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount(f"/files", StaticFiles(directory=str(uploads_dir)), name="uploads")

# Inclui os roteadores
app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(empresas.router)
app.include_router(clientes.router)
app.include_router(nfcom.router)
app.include_router(servicos.router)
app.include_router(servicos_contratados.router)
app.include_router(uploads.router)
app.include_router(dashboard.router)
app.include_router(access_control.router)
app.include_router(router.router)
app.include_router(radius.router)
app.include_router(subscriptions.router)
app.include_router(isp.router)

@app.get("/")
def read_root():
    return {"message": "Bem-vindo à API Brazcom ISP Suite!"}


@app.get("/api/health")
def health():
    """Health check endpoint. Verifica se a API está no ar e tenta uma conexão simples com o banco."""
    db_ok = False
    try:
        # tentativa rápida de selecionar 1 do banco para checar conectividade
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    status = "ok" if db_ok else "degraded"
    return {"status": status, "db": ("ok" if db_ok else "error")}


@app.on_event("startup")
def on_startup():
    """Evento de startup do FastAPI: aguarda DB e cria tabelas."""
    wait_for_db_and_migrate(retries=30, delay=2)