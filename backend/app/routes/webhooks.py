from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import logging
from datetime import datetime
from decimal import Decimal

from app.core.database import get_db
from app.models.models import Receivable
from app.services import bb_api_service, isp_service

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
logger = logging.getLogger(__name__)

@router.post("/bb", include_in_schema=False)
async def bb_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Endpoint de webhook para receber notificações de eventos do Banco do Brasil.
    Registre esta URL no portal BB Developer como webhook de cobrança.

    O BB envia um POST com JSON contendo a lista de eventos.
    """
    try:
        body = await request.json()
    except Exception:
        logger.error("BB webhook: Payload JSON inválido")
        return {"ok": False, "error": "Payload inválido"}

    # O BB pode enviar uma lista direta ou um objeto com a chave "boletos"
    boletos = body.get('boletos') or (body if isinstance(body, list) else [])
    processed = []

    for b in boletos:
        numero = str(b.get('numero', '')).strip()
        if not numero:
            continue
            
        # Localiza a cobrança pelo número do boleto no BB
        ar = db.query(Receivable).filter(
            Receivable.bb_boleto_numero == numero,
        ).first()
        
        if not ar:
            logger.warning(f"BB webhook: Boleto {numero} não encontrado no sistema")
            continue

        codigo_sit = str(b.get('codigoEstadoTituloCobranca', ''))
        new_status = bb_api_service.situacao_para_status(codigo_sit)
        
        # Atualiza o status interno
        if new_status:
            ar.status = new_status
            
        # Se foi liquidado (pago), marca a data de pagamento
        if new_status == 'PAID' and not ar.paid_at:
            ar.paid_at = datetime.now()
            logger.info(f"BB webhook: Boleto {numero} marcado como PAGO")
            
            # Se a cobrança estiver vinculada a um contrato ISP, realiza o desbloqueio automático
            if ar.servico_contratado_id:
                try:
                    isp_service.process_unblock_if_needed(db, ar.servico_contratado_id)
                except Exception as e:
                    logger.error(f"Erro ao processar desbloqueio automático ISP para contrato {ar.servico_contratado_id}: {e}")
        elif new_status == 'CANCELLED':
            logger.info(f"BB webhook: Boleto {numero} marcado como CANCELADO")

        db.add(ar)
        processed.append({"numero": numero, "status": ar.status})

    try:
        db.commit()
        logger.info(f"BB webhook: {len(processed)} eventos processados com sucesso")
    except Exception:
        db.rollback()
        logger.exception("BB webhook: Erro ao salvar alterações no banco")
        
    return {"ok": True, "processed": len(processed)}
