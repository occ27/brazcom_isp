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
    texto: Optional[str] = Query(None),
    
    phone: Optional[str] = Query(None),
    pdf_base64: Optional[str] = Query(None)
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
                to_phone = to_phone or body.get("to") or body.get("dest") or body.get("number") or body.get("celular") or body.get("phone")
                msg_text = msg_text or body.get("msg") or body.get("message") or body.get("text") or body.get("texto")
                pdf_base64 = pdf_base64 or body.get("pdf_base64")
        except Exception:
            pass # Sem body JSON válido

    # Tenta obter o token de autorização do Header (padrão do HoleshotMX)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        bearer_token = auth_header.split("Bearer ")[1]
        if not api_password:
            api_password = bearer_token
            # Se não enviou user, podemos assumir um default ou buscar apenas pelo token depois
            api_user = api_user or "integracao_holeshot"

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
    # Se api_user for o fallback, tenta buscar apenas pela senha (token)
    if api_user == "integracao_holeshot":
        empresa = db.query(Empresa).filter(Empresa.whatsapp_api_password == api_password).first()
    else:
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
    if pdf_base64:
        # Se contiver base64_, remove o prefixo
        if "base64," in pdf_base64:
            pdf_base64 = pdf_base64.split("base64,")[1]
            
        success = WhatsAppService.send_document_base64(
            empresa=empresa,
            to_phone=to_phone,
            caption=msg_text,
            file_data=pdf_base64,
            file_name="resultado_oficial.pdf"
        )
    else:
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

@router.post("/message/sendText/{instance_name}")
async def mock_evolution_api_send_text(
    instance_name: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Simula o endpoint da Evolution API para que o Brazcom ISP sirva de Drop-In Replacement
    (O Holeshot Site baterá aqui achando que é a Evolution API, e o Brazcom ISP enfileirará)
    """
    api_key = request.headers.get("apikey")
    body = await request.json()
    
    number = body.get("number")
    text = body.get("text")
    if not text and "textMessage" in body:
        text = body["textMessage"].get("text")
        
    empresa = db.query(Empresa).filter(
        Empresa.whatsapp_api_instance == instance_name
    ).first()
    
    if not empresa:
        # Tenta achar qualquer empresa com a api_key se a instância não bater
        empresa = db.query(Empresa).filter(Empresa.whatsapp_api_password == api_key).first()
        if not empresa:
            empresa = db.query(Empresa).first() # Fallback supremo para não quebrar a bridge
            
    success = WhatsAppService.send_message(
        empresa=empresa,
        to_phone=number,
        message=text or ""
    )
    
    if success:
        return {"key": {"id": "mock_brazcom_id"}, "message": "Enfileirado pelo Brazcom ISP"}
    raise HTTPException(status_code=500, detail="Erro interno ao enfileirar")

@router.post("/message/sendMedia/{instance_name}")
async def mock_evolution_api_send_media(
    instance_name: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Simula o endpoint da Evolution API para envio de Mídia, interceptando e enfileirando
    """
    api_key = request.headers.get("apikey")
    body = await request.json()
    
    number = body.get("number")
    caption = body.get("caption", "")
    media = body.get("media")
    file_name = body.get("fileName", "arquivo_gateway.pdf")
    
    if not media and "mediaMessage" in body:
        caption = body["mediaMessage"].get("caption", "")
        media = body["mediaMessage"].get("media")
        file_name = body["mediaMessage"].get("fileName", file_name)
        
    empresa = db.query(Empresa).filter(
        Empresa.whatsapp_api_instance == instance_name
    ).first()
    
    if not empresa:
        empresa = db.query(Empresa).filter(Empresa.whatsapp_api_password == api_key).first()
        if not empresa:
            empresa = db.query(Empresa).first()
            
    if media and "base64," in media:
        media = media.split("base64,")[1]
            
    success = WhatsAppService.send_document_base64(
        empresa=empresa,
        to_phone=number,
        caption=caption,
        file_data=media,
        file_name=file_name
    )
    
    if success:
        return {"key": {"id": "mock_brazcom_media_id"}, "message": "Mídia Enfileirada pelo Brazcom ISP"}
    raise HTTPException(status_code=500, detail="Erro interno ao enfileirar mídia")
