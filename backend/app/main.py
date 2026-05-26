from fastapi import FastAPI, Request
# pyrefly: ignore [missing-import]
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
from app.routes import network
from app.routes import receivables
from app.routes import bank_accounts
from app.routes import tickets
from app.routes import client_portal
from app.routes import client_auth
from app.routes import webhooks
from app.routes import public_contracts
from app.routes import mercadopago
from app.routes import reports
from app.routes import licenses
from app.routes import license_plans
from app.routes import whatsapp
from app.routes import ftth

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
    redirect_slashes=True  # Habilitado para resolver problemas com barras finais nas URLs
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
app.include_router(router.router_api)
app.include_router(radius.router)
app.include_router(subscriptions.router)
app.include_router(isp.router)
app.include_router(network.router)
app.include_router(receivables.router)
app.include_router(bank_accounts.router)
app.include_router(tickets.router)
app.include_router(client_portal.router)
app.include_router(client_auth.router)
app.include_router(webhooks.router)
app.include_router(public_contracts.router)
app.include_router(mercadopago.router)
app.include_router(reports.router)
app.include_router(licenses.router)
app.include_router(whatsapp.router)
app.include_router(ftth.router)

from fastapi.responses import RedirectResponse
from urllib.parse import urlparse
from app.core.database import SessionLocal
from app.models.network import Router
from app.models.models import ServicoContratado

@app.middleware("http")
async def captive_portal_middleware(request: Request, call_next):
    path = request.url.path

    # Permite passar endpoints públicos e recursos estáticos
    if path.startswith("/servicos-contratados/public/aviso/"):
        return await call_next(request)

    allowed_prefixes = [
        "/files", "/docs", "/redoc", "/openapi.json", 
        "/api/health", "/webhooks"
    ]
    if any(path.startswith(prefix) for prefix in allowed_prefixes):
        return await call_next(request)

    if request.method == "OPTIONS":
        return await call_next(request)

    # Identificar se a requisição tem Host diferente do nosso backend (redirecionada pelo MikroTik)
    host_header = request.headers.get("host", "").split(":")[0]  # Remove a porta do Host
    backend_host = ""
    try:
        backend_host = urlparse(settings.BACKEND_URL).hostname
    except Exception:
        pass

    # Hosts legítimos que o servidor atende diretamente (não devem ser redirecionados)
    valid_hosts = [backend_host, "localhost", "127.0.0.1", "10.20.0.1"]

    # Se o host solicitado é diferente dos hosts do nosso sistema
    is_external_request = host_header and host_header not in valid_hosts

    if is_external_request:
        # Detecta IP de origem (MikroTik VPN IP se houver SNAT, ou IP do Cliente se não houver SNAT)
        client_ip = request.headers.get("x-forwarded-for")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = request.headers.get("x-real-ip") or request.client.host

        db = SessionLocal()
        try:
            empresa_id = None
            
            # Caso 1: O IP de origem é o IP VPN do MikroTik (quando há SNAT masquerade)
            router_obj = db.query(Router).filter(Router.ip == client_ip).first()
            if router_obj:
                empresa_id = router_obj.empresa_id
                
            # Caso 2: O IP de origem é o IP direto do cliente (quando não há SNAT e a rota é direta)
            if not empresa_id:
                contrato = db.query(ServicoContratado).filter(ServicoContratado.assigned_ip == client_ip).first()
                if contrato:
                    empresa_id = contrato.empresa_id

            # Caso 3: Fallback de segurança. Se o IP do roteador (ex: VPN) estiver desatualizado
            # no cadastro do sistema, garantimos que o usuário seja bloqueado na empresa principal.
            if not empresa_id:
                from app.models.models import Empresa
                primeira_empresa = db.query(Empresa).first()
                if primeira_empresa:
                    empresa_id = primeira_empresa.id
                    import logging
                    logging.getLogger("uvicorn.error").warning(
                        f"IP {client_ip} nao reconhecido no captive portal. Usando fallback para empresa {empresa_id}."
                    )

            # Redireciona para o endpoint de aviso no backend (porta 8015).
            # O path /servicos-contratados/public/ esta na lista de allowed_prefixes do middleware
            # portanto nao causara loop de redirecionamento.
            if empresa_id:
                aviso_url = f"http://10.20.0.1:8015/servicos-contratados/public/aviso/empresa/{empresa_id}"
                return RedirectResponse(url=aviso_url, status_code=302)
        except Exception as e:
            import logging
            logging.getLogger("uvicorn.error").error(f"Erro no middleware do portal captivo: {e}")
        finally:
            db.close()

    return await call_next(request)

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
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    import logging
    log = logging.getLogger("uvicorn.error")
    log.error(f"ERRO DE VALIDAÇÃO: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

@app.exception_handler(ValueError)
async def value_error_exception_handler(request, exc):
    """Captura ValueError disparados em qualquer lugar e retorna como 400 Bad Request."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )
