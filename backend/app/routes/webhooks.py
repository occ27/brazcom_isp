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

@router.api_route("/bb", methods=["GET", "POST"], include_in_schema=False)
async def bb_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Endpoint de webhook para receber notificações de eventos do Banco do Brasil.
    Registre esta URL no portal BB Developer como webhook de cobrança.

    O BB envia um POST com JSON contendo a lista de eventos (BAIXA OPERACIONAL).
    """
    if request.method == "GET":
        return {"ok": True, "message": "BB Webhook receiver is active"}

    try:
        body_bytes = await request.body()
        if not body_bytes:
            return {"ok": True, "message": "BB Webhook test ping received"}
        body = await request.json()
    except Exception:
        logger.error("BB webhook: Payload JSON inválido")
        return {"ok": False, "error": "Payload inválido"}

    # Log do payload completo para diagnóstico (primeiros 2000 chars)
    logger.info(f"BB webhook payload recebido: {str(body)[:2000]}")

    # O BB envia uma lista direta de eventos de baixa operacional
    # ou um objeto com a chave "boletos" (formato legado)
    if isinstance(body, list):
        boletos = body
    elif isinstance(body, dict):
        # Tenta as chaves conhecidas que o BB pode usar
        boletos = body.get('boletos') or body.get('eventos') or body.get('baixas') or []
    else:
        logger.warning(f"BB webhook: Tipo de payload inesperado: {type(body)}")
        return {"ok": True, "processed": 0}

    processed = []

    for b in boletos:
        if not isinstance(b, dict):
            logger.warning(f"BB webhook: Item inválido no payload: {b}")
            continue

        # --- Identificar o boleto ---
        # O BB usa o campo "id" (nosso número) no webhook de Baixa Operacional.
        # Formato completo: "000<convenio7><seq10>" (20 dígitos)
        # Fallbacks: "numero" (formato legado) e "numeroTituloCliente" 
        numero = (
            str(b.get('id', '')).strip() or
            str(b.get('numero', '')).strip() or
            str(b.get('numeroTituloCliente', '')).strip()
        )

        if not numero:
            logger.warning(f"BB webhook: Evento sem número de boleto identificável: {b}")
            continue

        # --- Buscar o boleto no banco de dados ---
        ar = None

        # 1. Busca pelo bb_boleto_numero (campo salvo no registro pelo nosso sistema)
        ar = db.query(Receivable).filter(
            Receivable.bb_boleto_numero == numero,
        ).first()

        # 2. Busca pelo nosso_numero (match exato — pode ser o numero completo de 20 digitos)
        if not ar:
            ar = db.query(Receivable).filter(
                Receivable.nosso_numero == numero,
            ).first()

        # 3. Fallback: extrai os últimos 10 dígitos e busca pelo nosso_numero numérico
        if not ar and len(numero) > 10:
            try:
                seq_10 = str(int(numero[-10:]))
                ar = db.query(Receivable).filter(
                    Receivable.nosso_numero == seq_10,
                ).first()
            except ValueError:
                pass

        # 4. Fallback para boletos Altarede: nosso_numero é curto (≤5 dígitos)
        #    O BB envia o numero completo (000 + convenio7 + seq10), então
        #    os últimos dígitos significativos são a sequência do Altarede.
        if not ar and len(numero) > 10:
            try:
                # Remove zeros à esquerda da parte final para match com o nosso_numero curto do Altarede
                seq_short = str(int(numero[-10:]))  # ex: "0000080823" -> "80823"
                ar = db.query(Receivable).filter(
                    Receivable.nosso_numero == seq_short,
                    Receivable.bb_boleto_numero == None,  # apenas boletos sem bb_numero (Altarede)
                ).first()
                if ar:
                    logger.info(f"BB webhook: Boleto Altarede encontrado via nosso_numero curto: {seq_short}")
            except ValueError:
                pass

        if not ar:
            logger.warning(f"BB webhook: Boleto '{numero}' não encontrado no sistema")
            continue

        # Salva o bb_boleto_numero nos boletos Altarede para facilitar próximas buscas
        if ar and not ar.bb_boleto_numero:
            ar.bb_boleto_numero = numero

        # --- Determinar o novo status ---
        # No webhook de Baixa Operacional, o campo de código de estado é:
        # "codigoEstadoBaixaOperacional" (novo formato, pós Nov/2024)
        # Fallback: "codigoEstadoTituloCobranca" (formato de consulta da API)
        codigo_sit = (
            str(b.get('codigoEstadoBaixaOperacional', '')).strip() or
            str(b.get('codigoEstadoTituloCobranca', '')).strip()
        )
        new_status = bb_api_service.situacao_para_status(codigo_sit) if codigo_sit else None

        logger.info(
            f"BB webhook: Boleto '{numero}' (ID={ar.id}) | "
            f"Código situação='{codigo_sit}' -> Status='{new_status}'"
        )

        # --- Atualizar o registro ---
        if new_status:
            ar.status = new_status

        # Se foi liquidado (pago), salva data e valor pago
        if new_status == 'PAID':
            if not ar.paid_at:
                ar.paid_at = datetime.now()
                logger.info(f"BB webhook: Boleto {numero} marcado como PAGO (ID={ar.id})")

            # Salva o valor efetivamente pago pelo cliente (pode incluir juros/multa)
            valor_pago_raw = b.get('valorPagoSacado') or b.get('valorPago')
            if valor_pago_raw is not None:
                try:
                    ar.paid_amount = float(valor_pago_raw)
                except (ValueError, TypeError):
                    pass

            # Se a cobrança estiver vinculada a um contrato ISP, realiza o desbloqueio automático
            if ar.servico_contratado_id:
                try:
                    isp_service.process_unblock_if_needed(db, ar.servico_contratado_id)
                except Exception as e:
                    logger.error(
                        f"BB webhook: Erro ao processar desbloqueio ISP para contrato "
                        f"{ar.servico_contratado_id}: {e}"
                    )

        elif new_status == 'CANCELLED':
            logger.info(f"BB webhook: Boleto {numero} marcado como CANCELADO (ID={ar.id})")

        db.add(ar)
        processed.append({"numero": numero, "id": ar.id, "status": ar.status})

    try:
        db.commit()
        logger.info(f"BB webhook: {len(processed)} evento(s) processado(s) com sucesso")
    except Exception:
        db.rollback()
        logger.exception("BB webhook: Erro ao salvar alterações no banco")

    # Sempre retornar 200 para o BB não ficar tentando reenviar indefinidamente
    return {"ok": True, "processed": len(processed)}
