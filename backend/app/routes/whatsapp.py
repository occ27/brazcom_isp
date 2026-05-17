from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.core.database import get_db
from app.models.models import Empresa
from app.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["WhatsAppGateway"])

def get_client_ip(request: Request) -> str:
    """Tenta obter o IP real do remetente da requisição."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.headers.get("X-Real-IP") or request.client.host

@router.api_route("/send", methods=["GET", "POST"])
async def send_whatsapp_gateway(
    request: Request,
    db: Session = Depends(get_db),
    # Aceita os parâmetros via Query params (comum em integrações legadas)
    user: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    login: Optional[str] = Query(None),
    
    password: Optional[str] = Query(None),
    pwd: Optional[str] = Query(None),
    senha: Optional[str] = Query(None),
    
    to: Optional[str] = Query(None),
    dest: Optional[str] = Query(None),
    number: Optional[str] = Query(None),
    celular: Optional[str] = Query(None),
    
    msg: Optional[str] = Query(None),
    message: Optional[str] = Query(None),
    text: Optional[str] = Query(None),
    texto: Optional[str] = Query(None)
):
    """
    Gateway HTTP universal para envio de WhatsApp (compatível com SGP, MK-Auth, Vigo, IXC, etc.).
    Aceita parâmetros via Query String (GET/POST) ou JSON (POST).
    """
    client_ip = get_client_ip(request)
    logger.info(f"Requisição no gateway de WhatsApp vinda do IP: {client_ip}")

    # 1. Resolver parâmetros (priorizando query string, senão tenta do body se for POST)
    api_user = user or username or login
    api_password = password or pwd or senha
    to_phone = to or dest or number or celular
    msg_text = msg or message or text or texto

    # Se for POST e faltar parâmetros, tenta ler do JSON body
    if request.method == "POST" and (not api_user or not api_password or not to_phone or not msg_text):
        try:
            body = await request.json()
            if isinstance(body, dict):
                api_user = api_user or body.get("user") or body.get("username") or body.get("login")
                api_password = api_password or body.get("password") or body.get("pwd") or body.get("senha")
                to_phone = to_phone or body.get("to") or body.get("dest") or body.get("number") or body.get("celular")
                msg_text = msg_text or body.get("msg") or body.get("message") or body.get("text") or body.get("texto")
        except Exception:
            pass # Sem body JSON válido

    # Valida parâmetros mínimos obrigatórios
    if not api_user or not api_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais de autenticação (user/password) não informadas."
        )

    if not to_phone or not msg_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parâmetros de destino (to) e mensagem (msg) são obrigatórios."
        )

    # 2. Autenticar a empresa pelas credenciais do WhatsApp API
    empresa = db.query(Empresa).filter(
        Empresa.whatsapp_api_user == api_user,
        Empresa.whatsapp_api_password == api_password
    ).first()

    if not empresa:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais de integração inválidas."
        )

    # 3. Validar whitelist de IPs (Segurança)
    whitelist_ips = getattr(empresa, "whatsapp_api_ips", None)
    if whitelist_ips:
        # Divide por vírgula e limpa espaços
        allowed_ips = [ip.strip() for ip in whitelist_ips.split(",") if ip.strip()]
        if allowed_ips and client_ip not in allowed_ips:
            logger.warning(f"Acesso bloqueado: IP {client_ip} não está na whitelist de {empresa.razao_social}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Requisição de IP não autorizado (não está na whitelist)."
            )

    # 4. Disparar a mensagem de WhatsApp
    success = WhatsAppService.send_message(
        empresa=empresa,
        to_phone=to_phone,
        message=msg_text
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao processar envio do WhatsApp pelo gateway."
        )

    return {
        "status": "success",
        "message": "Mensagem enviada com sucesso para a fila de processamento.",
        "recipient": to_phone
    }
