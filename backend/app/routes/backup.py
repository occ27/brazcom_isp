import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routes.auth import get_current_active_user
from app.models.models import Usuario, Empresa, UsuarioEmpresa
from app.api import deps
from app.services.backup_service import BackupService

router = APIRouter(prefix="/backup", tags=["Backup"])

@router.get("/export")
def export_backup(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa)
):
    """Gera um backup completo em ZIP dos dados da empresa ativa para download."""
    # Verificação de segurança: apenas Superuser ou Administrador da empresa ativa
    is_admin = False
    if current_user.is_superuser:
        is_admin = True
    else:
        assoc = db.query(UsuarioEmpresa).filter(
            UsuarioEmpresa.usuario_id == current_user.id,
            UsuarioEmpresa.empresa_id == active_empresa.id,
            UsuarioEmpresa.is_admin == True
        ).first()
        if assoc:
            is_admin = True

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão negada. Apenas administradores podem fazer backup dos dados da empresa."
        )

    try:
        backup_bytes = BackupService.generate_company_backup(db, active_empresa.id)
        
        # Coloca os bytes gerados em um buffer BytesIO
        zip_buffer = io.BytesIO(backup_bytes)
        
        # Sanitiza a Razão Social para o nome do arquivo
        clean_razao_social = "".join(c for c in active_empresa.razao_social if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
        filename = f"backup_{clean_razao_social}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"  # Necessário para que o frontend leia o nome do arquivo
            }
        )
    except Exception as e:
        import logging
        logging.getLogger("uvicorn.error").error(f"Erro ao gerar backup da empresa {active_empresa.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno ao gerar o backup: {str(e)}"
        )
