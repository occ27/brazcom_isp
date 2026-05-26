#!/usr/bin/env python3
"""
Script de Polling Automático FTTH — Brazcom ISP Suite

Executado pelo cron a cada 5 minutos para verificar a conectividade
das ONUs FTTH de todas as empresas ativas.

Uso:
    python -m app.scripts.ftth_poller
    python -m app.scripts.ftth_poller --empresa-id 1   # Apenas uma empresa
"""
import sys
import os
import logging
import argparse
from datetime import datetime

# Garante que o diretório pai (backend/) está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [FTTH_POLLER] %(levelname)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def run_poller(empresa_id: int = None):
    """
    Executa o polling de todas as ONUs FTTH.
    
    Args:
        empresa_id: Se informado, verifica apenas a empresa especificada.
                    Se None, verifica todas as empresas ativas.
    """
    from app.core.database import SessionLocal
    from app.models.models import Empresa
    from app.services.ftth_monitor_service import FTTHMonitorService

    db = SessionLocal()
    try:
        if empresa_id:
            empresas = db.query(Empresa).filter(
                Empresa.id == empresa_id, Empresa.is_active == True
            ).all()
        else:
            empresas = db.query(Empresa).filter(Empresa.is_active == True).all()

        if not empresas:
            logger.info("Nenhuma empresa ativa encontrada para polling")
            return

        logger.info(f"Iniciando polling FTTH para {len(empresas)} empresa(s) — {datetime.utcnow().isoformat()}")

        total_geral = {"ONLINE": 0, "OFFLINE": 0, "DEGRADADO": 0, "DESCONHECIDO": 0, "total": 0}

        for empresa in empresas:
            try:
                logger.info(f"  [{empresa.id}] {empresa.razao_social} — verificando ONUs...")
                resumo = FTTHMonitorService.poll_all_onus(db, empresa.id)
                logger.info(
                    f"  [{empresa.id}] Resultado: {resumo['total']} ONUs | "
                    f"Online={resumo['ONLINE']} Offline={resumo['OFFLINE']} "
                    f"Degradado={resumo['DEGRADADO']} Desconhecido={resumo['DESCONHECIDO']}"
                )
                for k in ["ONLINE", "OFFLINE", "DEGRADADO", "DESCONHECIDO", "total"]:
                    total_geral[k] += resumo.get(k, 0)
            except Exception as e:
                logger.error(f"  [{empresa.id}] Erro ao fazer polling: {e}")

        logger.info(
            f"Polling concluído — Total: {total_geral['total']} ONUs | "
            f"Online={total_geral['ONLINE']} Offline={total_geral['OFFLINE']} "
            f"Degradado={total_geral['DEGRADADO']}"
        )

    except Exception as e:
        logger.error(f"Erro crítico no poller: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FTTH Poller — Brazcom ISP Suite")
    parser.add_argument(
        "--empresa-id",
        type=int,
        default=None,
        help="ID da empresa específica a verificar (padrão: todas)"
    )
    args = parser.parse_args()
    run_poller(empresa_id=args.empresa_id)
