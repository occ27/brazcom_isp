from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import os
import shutil
import uuid
from typing import Optional

from app.core.config import settings
from app.routes.auth import get_current_user
from app.models.models import Usuario

router = APIRouter(
    prefix="/uploads",
    tags=["uploads"],
    dependencies=[Depends(get_current_user)]
)

ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
ALLOWED_CERTIFICATE_EXTENSIONS = {".p12", ".pfx", ".cer", ".crt", ".pem"}

def _validate_file_type(filename: str, allowed_extensions: set) -> bool:
    """Valida se a extensão do arquivo é permitida."""
    if not filename:
        return False
    ext = Path(filename).suffix.lower()
    return ext in allowed_extensions

def _save_uploaded_file(file: UploadFile, subfolder: str, empresa_id: int, use_empresa_subfolder: bool = True, use_certificates_dir: bool = False) -> str:
    """Salva um arquivo enviado e retorna o caminho relativo."""
    # Valida tamanho do arquivo
    file.file.seek(0, 2)  # Vai para o final do arquivo
    file_size = file.file.tell()
    file.file.seek(0)  # Volta para o início

    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo muito grande. Tamanho máximo: {settings.MAX_UPLOAD_SIZE / (1024*1024):.1f}MB"
        )

    # Gera nome único para o arquivo
    safe_ext = Path(file.filename or "").suffix.lower() or ".dat"
    file_id = f"{uuid.uuid4().hex[:8]}-{Path(file.filename or 'file').stem}"
    filename = f"{file_id}{safe_ext}"

    # Cria diretório de destino
    base_dir = Path(settings.CERTIFICATES_DIR) if use_certificates_dir else Path(settings.UPLOAD_DIR)
    if use_empresa_subfolder:
        destination_dir = base_dir / subfolder / str(empresa_id)
    else:
        destination_dir = base_dir / subfolder
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_path = destination_dir / filename

    # Salva o arquivo
    with destination_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Retorna caminho relativo
    base_dir = Path(settings.CERTIFICATES_DIR) if use_certificates_dir else Path(settings.UPLOAD_DIR)
    relative_path = destination_path.relative_to(base_dir)
    return f"/secure/{relative_path.as_posix()}" if use_certificates_dir else f"/files/{relative_path.as_posix()}"

@router.post("/empresa/{empresa_id}/logo")
async def upload_empresa_logo(
    empresa_id: int,
    file: UploadFile = File(..., description="Arquivo de imagem do logo da empresa"),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Faz upload do logo da empresa.

    - **empresa_id**: ID da empresa
    - **file**: Arquivo de imagem (PNG, JPG, JPEG, GIF, SVG, WebP)
    """
    # Valida tipo de arquivo
    if not _validate_file_type(file.filename, ALLOWED_LOGO_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de arquivo não permitido. Use: {', '.join(ALLOWED_LOGO_EXTENSIONS)}"
        )

    try:
        file_path = _save_uploaded_file(file, "logos", empresa_id, use_empresa_subfolder=False)
        return JSONResponse(
            content={
                "message": "Logo enviado com sucesso",
                "file_path": file_path,
                "file_name": file.filename
            },
            status_code=200
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {str(e)}")

@router.post("/empresa/{empresa_id}/certificado")
async def upload_empresa_certificado(
    empresa_id: int,
    file: UploadFile = File(..., description="Arquivo do certificado digital"),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Faz upload do certificado digital da empresa.

    - **empresa_id**: ID da empresa
    - **file**: Arquivo do certificado (P12, PFX, CER, CRT, PEM)
    """
    # Valida tipo de arquivo
    if not _validate_file_type(file.filename, ALLOWED_CERTIFICATE_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de arquivo não permitido. Use: {', '.join(ALLOWED_CERTIFICATE_EXTENSIONS)}"
        )

    try:
        file_path = _save_uploaded_file(file, "certificates", empresa_id, use_certificates_dir=True)
        return JSONResponse(
            content={
                "message": "Certificado enviado com sucesso",
                "file_path": file_path,
                "file_name": file.filename
            },
            status_code=200
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {str(e)}")

@router.delete("/empresa/{empresa_id}/logo")
async def delete_empresa_logo(
    empresa_id: int,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Remove o logo da empresa.

    - **empresa_id**: ID da empresa
    """
    logo_dir = Path(settings.UPLOAD_DIR) / "logos" / str(empresa_id)

    if not logo_dir.exists():
        raise HTTPException(status_code=404, detail="Diretório de logos não encontrado")

    # Remove todos os arquivos do diretório
    deleted_files = []
    for file_path in logo_dir.glob("*"):
        if file_path.is_file():
            file_path.unlink()
            deleted_files.append(file_path.name)

    if not deleted_files:
        raise HTTPException(status_code=404, detail="Nenhum logo encontrado")

    return JSONResponse(
        content={
            "message": "Logo(s) removido(s) com sucesso",
            "deleted_files": deleted_files
        },
        status_code=200
    )

@router.get("/empresa/{empresa_id}/certificado/download")
async def download_empresa_certificado(
    empresa_id: int,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Baixa o certificado digital da empresa (apenas para usuários autorizados).

    - **empresa_id**: ID da empresa
    """
    # Verificar se o usuário tem acesso à empresa
    from app.crud.crud_empresa import get_empresas_by_usuario
    from app.core.database import get_db
    from sqlalchemy.orm import Session
    from fastapi import Depends

    db = next(get_db())
    try:
        empresas_usuario = get_empresas_by_usuario(db, current_user.id)
        empresa_ids = [emp.id for emp in empresas_usuario]

        if empresa_id not in empresa_ids:
            raise HTTPException(status_code=403, detail="Acesso negado ao certificado da empresa")

        # Procurar arquivo de certificado
        cert_dir = Path(settings.CERTIFICATES_DIR) / "certificates" / str(empresa_id)
        if not cert_dir.exists():
            raise HTTPException(status_code=404, detail="Certificado não encontrado")

        # Pegar o primeiro arquivo encontrado (deve haver apenas um)
        cert_files = list(cert_dir.glob("*"))
        if not cert_files:
            raise HTTPException(status_code=404, detail="Certificado não encontrado")

        cert_file = cert_files[0]
        return FileResponse(
            path=cert_file,
            filename=cert_file.name,
            media_type="application/x-pkcs12"
        )
    finally:
        db.close()