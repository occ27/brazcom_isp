from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.core.database import get_db
from app.models.models import ServicoContratado, StatusContrato
from app.crud import crud_servico_contratado, crud_empresa, crud_cliente, crud_servico
from app.services.contract_generator import generate_contract_html

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public-contrato", tags=["PublicContracts"])

@router.get("/{token}")
def get_public_contract(token: str, db: Session = Depends(get_db)):
    """Busca o contrato pelo token único para visualização pública."""
    contrato = db.query(ServicoContratado).filter(ServicoContratado.assinatura_token == token).first()
    
    if not contrato:
        raise HTTPException(status_code=404, detail="Link de contrato inválido ou expirado")
        
    # Buscar dados para o template
    empresa = crud_empresa.get_empresa(db, empresa_id=contrato.empresa_id)
    cliente = crud_cliente.get_cliente(db, cliente_id=contrato.cliente_id)
    servico = crud_servico.get_servico(db, servico_id=contrato.servico_id, empresa_id=contrato.empresa_id)
    c_dict = crud_servico_contratado.get_servico_contratado_with_relations(db, contrato_id=contrato.id)
    
    html_content = generate_contract_html(c_dict, cliente, empresa, servico)
    
    return {
        "id": contrato.id,
        "cliente_nome": cliente.nome_razao_social,
        "empresa_nome": empresa.razao_social,
        "empresa_logo": empresa.logo_url,
        "html": html_content,
        "assinado": contrato.assinado_em is not None,
        "assinado_em": contrato.assinado_em
    }

from pydantic import BaseModel
from fastapi import Body

class SignaturePayload(BaseModel):
    signature: str

@router.post("/{token}/assinar")
async def sign_public_contract(
    token: str, 
    request: Request, 
    payload: SignaturePayload = Body(...), 
    db: Session = Depends(get_db)
):
    """Registra a assinatura do cliente no contrato."""
    logger.info(f"Tentativa de assinatura recebida para o token: {token}")
    
    contrato = db.query(ServicoContratado).filter(ServicoContratado.assinatura_token == token).first()
    
    if not contrato:
        logger.warning(f"Contrato não encontrado para o token: {token}")
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
        
    if contrato.assinado_em:
        logger.info(f"Contrato {contrato.id} já estava assinado.")
        return {"message": "Este contrato já foi assinado anteriormente", "status": "already_signed"}
        
    # Capturar IP do cliente
    client_ip = request.headers.get("X-Forwarded-For")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = request.headers.get("X-Real-IP") or request.client.host
        
    # Pegar dados da assinatura do payload
    signature_data = payload.signature
    if not signature_data:
        logger.error("Payload recebido sem os dados da assinatura.")
        raise HTTPException(status_code=400, detail="Dados da assinatura não fornecidos")
        
    # Atualizar contrato
    contrato.assinado_em = datetime.now()
    contrato.assinatura_ip = client_ip
    contrato.assinatura_data = signature_data
    
    # Se o contrato estava aguardando assinatura, muda para pendente de instalação
    # ou mantém o fluxo definido pelo provedor.
    if contrato.status == StatusContrato.AGUARDANDO_ASSINATURA:
        contrato.status = StatusContrato.PENDENTE_INSTALACAO
        
    db.commit()
    
    logger.info(f"Contrato {contrato.id} assinado digitalmente pelo IP {client_ip}")
    
    return {
        "message": "Contrato assinado com sucesso!",
        "assinado_em": contrato.assinado_em,
        "status": contrato.status
    }

@router.get("/{token}/visualizar")
def view_public_signed_contract(token: str, db: Session = Depends(get_db)):
    """Permite visualizar o contrato assinado em HTML/Impressão por até 24 horas."""
    contrato = db.query(ServicoContratado).filter(ServicoContratado.assinatura_token == token).first()
    
    if not contrato:
        raise HTTPException(status_code=404, detail="Link de contrato inválido ou expirado")
        
    if not contrato.assinado_em:
        raise HTTPException(status_code=403, detail="Este contrato ainda não foi assinado.")
        
    # Validar prazo de 24 horas
    from datetime import timedelta
    if datetime.now() > contrato.assinado_em + timedelta(hours=24):
        raise HTTPException(
            status_code=403, 
            detail="O prazo de 24 horas para visualização pública deste contrato assinado expirou por segurança."
        )
        
    # Buscar dados para o template
    empresa = crud_empresa.get_empresa(db, empresa_id=contrato.empresa_id)
    cliente = crud_cliente.get_cliente(db, cliente_id=contrato.cliente_id)
    servico = crud_servico.get_servico(db, servico_id=contrato.servico_id, empresa_id=contrato.empresa_id)
    c_dict = crud_servico_contratado.get_servico_contratado_with_relations(db, contrato_id=contrato.id)
    
    html_content = generate_contract_html(c_dict, cliente, empresa, servico)
    
    # Retornar HTML puro para o navegador renderizar/imprimir
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html_content)
