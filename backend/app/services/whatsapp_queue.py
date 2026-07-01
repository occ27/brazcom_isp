import threading
import queue
import time
import logging

logger = logging.getLogger(__name__)

# Fila thread-safe em memória
wa_queue = queue.Queue()

class MockEmpresa:
    """Classe mock para não passar instâncias do SQLAlchemy entre threads"""
    pass

def _wa_worker():
    """
    Worker que processa os disparos do WhatsApp em background.
    Garante o intervalo fixo de 5 segundos entre as mensagens para evitar
    quedas na Evolution API (anti-spam).
    """
    from app.services.whatsapp_service import WhatsAppService
    logger.info("[WA Queue] Iniciando worker de fila do WhatsApp (Brazcom ISP)...")
    
    while True:
        try:
            task = wa_queue.get()
            if task is None:
                # Sinal para finalizar a thread (usado no shutdown)
                break
                
            empresa_data = task.get("empresa")
            to_phone = task.get("to_phone")
            message = task.get("message")
            is_media = task.get("is_media", False)
            file_path = task.get("file_path")
            
            # Recria o objeto mock da empresa para o WhatsAppService
            empresa = MockEmpresa()
            for k, v in empresa_data.items():
                setattr(empresa, k, v)
                
            logger.info(f"[WA Queue] Processando mensagem para {to_phone}")
            
            # Chama o método síncrono real de envio na WhatsAppService
            if is_media:
                WhatsAppService._send_document_sync_real(empresa, to_phone, message, file_path)
            else:
                WhatsAppService._send_message_sync_real(empresa, to_phone, message)
                
            # Informa que a tarefa foi concluída
            wa_queue.task_done()
            
            # RATE LIMIT (5 Segundos de espera obrigatória entre envios)
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"[WA Queue] Erro no processamento da fila: {e}", exc_info=True)
            time.sleep(5)

# Thread em modo daemon: será encerrada automaticamente quando o servidor FastAPI parar
_worker_thread = threading.Thread(target=_wa_worker, daemon=True)

def start_whatsapp_worker():
    if not _worker_thread.is_alive():
        _worker_thread.start()
        logger.info("[WA Queue] Fila iniciada com sucesso.")
