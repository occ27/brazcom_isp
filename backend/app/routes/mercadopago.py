from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
import mercadopago
import logging
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.models import Usuario, Empresa, Receivable, BankAccount
from app.routes.auth import get_current_active_user
from app.schemas.mercadopago import MercadoPagoPaymentRequest, MercadoPagoResponse
from app.services import isp_service
from app.api import deps

router = APIRouter(prefix="/mercadopago", tags=["Mercado Pago"])
logger = logging.getLogger(__name__)

@router.get("/public-key/{empresa_id}")
def get_public_key(empresa_id: int, db: Session = Depends(get_db)):
    """Retorna a chave pública do Mercado Pago para a empresa."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa or not empresa.mp_public_key:
        raise HTTPException(status_code=404, detail="Configuração do Mercado Pago não encontrada para esta empresa")
    return {"public_key": empresa.mp_public_key}

@router.get("/receivable/{token}")
def get_receivable_by_token(token: str, db: Session = Depends(get_db)):
    """Busca informações de uma cobrança usando o token público."""
    receivable = db.query(Receivable).filter(Receivable.payment_token == token).first()
    if not receivable:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada ou link expirado")
    
    if receivable.status == 'PAID':
         return {
             "id": receivable.id,
             "status": "PAID",
             "message": "Esta fatura já foi paga."
         }

    # Buscar e-mail do cliente
    from app.models.models import Cliente
    cliente = db.query(Cliente).filter(Cliente.id == receivable.cliente_id).first()
    
    return {
        "id": receivable.id,
        "empresa_id": receivable.empresa_id,
        "amount": receivable.amount,
        "due_date": receivable.due_date,
        "cliente_email": cliente.email if cliente else "",
        "cliente_nome": cliente.nome_razao_social if cliente else "",
        "status": receivable.status
    }

@router.post("/process", response_model=MercadoPagoResponse)
async def process_payment(
    payload: MercadoPagoPaymentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[Usuario] = Depends(deps.get_current_user_optional)
):
    """Processa um pagamento vindo do Mercado Pago Brick."""
    # Buscar os recebíveis para validar valor e empresa
    receivables = db.query(Receivable).filter(Receivable.id.in_(payload.receivable_ids)).all()
    if not receivables:
        raise HTTPException(status_code=404, detail="Cobranças não encontradas")
    
    # Validar que todos pertencem à mesma empresa
    empresa_id = receivables[0].empresa_id
    for r in receivables:
        if r.empresa_id != empresa_id:
            raise HTTPException(status_code=400, detail="Cobranças pertencem a empresas diferentes")
        if r.status == 'PAID':
            raise HTTPException(status_code=400, detail=f"Cobrança {r.id} já está paga")

    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa or not empresa.mp_access_token:
        raise HTTPException(status_code=400, detail="Empresa não possui credenciais do Mercado Pago")

    # Validar valor total
    total_amount = sum(r.amount for r in receivables) - payload.discount_amount
    if abs(total_amount - payload.transaction_amount) > 0.01:
        raise HTTPException(status_code=400, detail=f"Valor total incorreto. Esperado: {total_amount}, Recebido: {payload.transaction_amount}")

    # Inicializar SDK
    sdk = mercadopago.SDK(empresa.mp_access_token)

    payment_data = {
        "transaction_amount": float(payload.transaction_amount),
        "token": payload.token,
        "description": f"Pagamento de {len(receivables)} faturas - {empresa.nome_fantasia or empresa.razao_social}",
        "payment_method_id": payload.payment_method_id,
        "installments": payload.installments,
        "payer": {
            "email": payload.payer.get("email"),
            "identification": payload.payer.get("identification"),
            "first_name": payload.payer.get("first_name"),
            "last_name": payload.payer.get("last_name"),
        },
        "external_reference": ",".join(map(str, payload.receivable_ids))
    }

    # Adicionar notification_url apenas se não for localhost (exigência do Mercado Pago)
    base_url = str(request.base_url).rstrip("/")
    if "localhost" not in base_url and "127.0.0.1" not in base_url:
        payment_data["notification_url"] = f"{base_url}/mercadopago/webhook"

    try:
        payment_response = sdk.payment().create(payment_data)
        payment = payment_response["response"]
        
        if payment_response["status"] not in [200, 201]:
            logger.error(f"Erro Mercado Pago: {payment_response}")
            raise HTTPException(status_code=400, detail=f"Erro ao processar pagamento no Mercado Pago: {payment.get('message', 'Erro desconhecido')}")

        # Atualizar recebíveis com o ID do pagamento e status inicial
        mp_id = str(payment["id"])
        mp_status = payment["status"]
        
        for r in receivables:
            r.mp_payment_id = mp_id
            r.mp_payment_status = mp_status
            r.mp_payment_method = payload.payment_method_id
            
            if mp_status == "approved":
                r.status = "PAID"
                r.paid_at = datetime.utcnow()
                # Se for ISP, processar desbloqueio
                if r.servico_contratado_id:
                    try:
                        isp_service.process_unblock_if_needed(db, r.servico_contratado_id)
                    except Exception as e:
                        logger.error(f"Erro no desbloqueio ISP: {e}")

        db.commit()

        return {
            "payment_id": mp_id,
            "status": mp_status,
            "detail": payment
        }

    except Exception as e:
        logger.error(f"Erro ao processar pagamento MP: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno ao processar pagamento: {str(e)}")

@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """Recebe notificações de alteração de status do Mercado Pago."""
    try:
        data = await request.json()
        logger.info(f"Webhook Mercado Pago recebido: {data}")
        
        # O MP envia o ID do recurso em data.id
        resource_id = data.get("data", {}).get("id")
        topic = data.get("type") or data.get("topic")

        if topic == "payment" and resource_id:
            # Buscar qualquer recebível que tenha este mp_payment_id para descobrir a empresa
            receivables = db.query(Receivable).filter(Receivable.mp_payment_id == str(resource_id)).all()
            if not receivables:
                logger.warning(f"Pagamento {resource_id} não encontrado no banco local")
                return {"status": "not_found"}

            empresa = receivables[0].empresa
            if not empresa or not empresa.mp_access_token:
                logger.error(f"Empresa {receivables[0].empresa_id} sem token MP para webhook")
                return {"status": "error"}

            # Consultar status atualizado no MP
            sdk = mercadopago.SDK(empresa.mp_access_token)
            payment_info = sdk.payment().get(resource_id)
            
            if payment_info["status"] == 200:
                payment = payment_info["response"]
                new_status = payment["status"]
                
                logger.info(f"Atualizando status do pagamento {resource_id} para {new_status}")
                
                for r in receivables:
                    r.mp_payment_status = new_status
                    if new_status == "approved" and r.status != "PAID":
                        r.status = "PAID"
                        r.paid_at = datetime.utcnow()
                        # Se for ISP, processar desbloqueio
                        if r.servico_contratado_id:
                            try:
                                isp_service.process_unblock_if_needed(db, r.servico_contratado_id)
                            except Exception as e:
                                logger.error(f"Erro no desbloqueio ISP via webhook: {e}")
                
                db.commit()
                return {"status": "ok"}

        return {"status": "ignored"}
    except Exception as e:
        logger.error(f"Erro no webhook Mercado Pago: {str(e)}")
        return {"status": "error", "message": str(e)}
