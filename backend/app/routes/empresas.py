from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.crud import crud_empresa, crud_usuario, crud_nfcom, crud_servico
from app.schemas.empresa import EmpresaCreate, EmpresaUpdate, EmpresaResponse, UsuarioEmpresaCreate, SMTPTest, EmpresaIn
from app.schemas.nfcom import NFComCreate, NFComResponse, NFComListResponse
from app.schemas import servico as servico_schema
from app.routes.auth import get_current_active_superuser, get_current_active_user
from app.models.models import Usuario, Empresa, UsuarioEmpresa
from app.services.email_service import EmailService, _safe_print
from app.core.config import settings

router = APIRouter(prefix="/empresas", tags=["Empresas"])

# Helper function for permission checking
def _check_user_permission_for_empresa(empresa_id: int, current_user: Usuario, db: Session):
    """Helper function to check if a user can access a company's resources."""
    # Usar get_empresa_raw para evitar descriptografar a senha e causar efeitos colaterais
    db_empresa = crud_empresa.get_empresa_raw(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    user_empresas_ids = [assoc.empresa_id for assoc in current_user.empresas]
    if not current_user.is_superuser and empresa_id not in user_empresas_ids:
        raise HTTPException(status_code=403, detail="Usuário não tem permissão para acessar recursos desta empresa")
    return db_empresa

@router.post("/", response_model=EmpresaResponse, status_code=status.HTTP_201_CREATED)
def create_empresa(
    empresa: EmpresaIn,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_superuser)
):
    """Cria uma nova empresa. Apenas superusuários podem criar empresas."""
    # monta um EmpresaCreate com user_id vindo do usuário autenticado (superuser)
    empresa_data = empresa.model_dump()
    empresa_create = EmpresaCreate(**empresa_data, user_id=current_user.id)
    db_empresa = crud_empresa.get_empresa_by_cnpj(db, cnpj=empresa_create.cnpj)
    if db_empresa:
        raise HTTPException(status_code=400, detail="CNPJ já registrado")
    return crud_empresa.create_empresa(db=db, empresa=empresa_create, user_id=current_user.id)

@router.get("/", response_model=List[EmpresaResponse])
def read_empresas(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Lista empresas. Superusuários veem todas, usuários normais veem apenas suas empresas."""
    if current_user.is_superuser:
        empresas = crud_empresa.get_empresas(db, skip=skip, limit=limit)
    else:
        empresas = crud_empresa.get_empresas_by_usuario(db, usuario_id=current_user.id, skip=skip, limit=limit)
    return empresas

@router.get("/{empresa_id}", response_model=EmpresaResponse)
def read_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Obtém uma empresa específica pelo ID."""
    return _check_user_permission_for_empresa(empresa_id, current_user, db)

@router.put("/{empresa_id}", response_model=EmpresaResponse)
def update_empresa(
    empresa_id: int,
    empresa: EmpresaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Atualiza uma empresa."""
    db_empresa = _check_user_permission_for_empresa(empresa_id, current_user, db)
    if not current_user.is_superuser and db_empresa.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado para atualização")
    return crud_empresa.update_empresa(db=db, db_obj=db_empresa, obj_in=empresa)

@router.delete("/{empresa_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_superuser)
):
    """Deleta uma empresa. Apenas superusuários."""
    db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if db_empresa is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    crud_empresa.delete_empresa(db=db, db_obj=db_empresa)
    return None

@router.post("/associar-usuario/", status_code=status.HTTP_201_CREATED)
def associar_usuario_empresa(
    associacao: UsuarioEmpresaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Associa um usuário a uma empresa."""
    is_admin_of_empresa = any(e.empresa_id == associacao.empresa_id and e.is_admin for e in current_user.empresas)
    if not current_user.is_superuser and not is_admin_of_empresa:
        raise HTTPException(status_code=403, detail="Permissão negada")
    _check_user_permission_for_empresa(associacao.empresa_id, current_user, db)
    db_usuario = crud_usuario.get_usuario(db, usuario_id=associacao.usuario_id)
    if not db_usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    crud_empresa.associar_usuario(db, associacao=associacao)
    return {"message": "Associação criada com sucesso"}

# NFCom-related routes moved to `app.routes.nfcom` to avoid duplication and route conflicts.

#
# Serviços
#

@router.post("/{empresa_id}/servicos", response_model=servico_schema.ServicoResponse, status_code=status.HTTP_201_CREATED)
def create_servico_for_empresa(
    empresa_id: int,
    servico: servico_schema.ServicoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Cria um novo serviço para uma empresa."""
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    # Backend permission: require services_manage to create/update/delete services
    from app.api import deps as _deps
    _deps.permission_checker('services_manage')(db=db, current_user=current_user)
    return crud_servico.create_servico(db=db, servico_in=servico, empresa_id=empresa_id)

@router.get("/{empresa_id}/servicos", response_model=List[servico_schema.ServicoResponse])
def read_servicos_from_empresa(
    empresa_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
    response: Response = None
):
    """Lista os serviços de uma empresa."""
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    total = crud_servico.count_servicos_by_empresa(db, empresa_id=empresa_id)
    if response is not None:
        response.headers['X-Total-Count'] = str(total)
    return crud_servico.get_servicos_by_empresa(db, empresa_id=empresa_id, skip=skip, limit=limit)

@router.put("/{empresa_id}/servicos/{servico_id}", response_model=servico_schema.ServicoResponse)
def update_servico_for_empresa(
    empresa_id: int,
    servico_id: int,
    servico: servico_schema.ServicoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Atualiza um serviço de uma empresa."""
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    from app.api import deps as _deps
    _deps.permission_checker('services_manage')(db=db, current_user=current_user)
    db_servico = crud_servico.get_servico(db, servico_id=servico_id, empresa_id=empresa_id)
    if not db_servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    return crud_servico.update_servico(db=db, db_obj=db_servico, obj_in=servico)

@router.delete("/{empresa_id}/servicos/{servico_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_servico_from_empresa(
    empresa_id: int,
    servico_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Deleta um serviço de uma empresa."""
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    from app.api import deps as _deps
    _deps.permission_checker('services_manage')(db=db, current_user=current_user)
    db_servico = crud_servico.get_servico(db, servico_id=servico_id, empresa_id=empresa_id)
    if not db_servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    crud_servico.delete_servico(db=db, db_obj=db_servico)
    return None

@router.get("/{empresa_id}/certificado/status")
def verificar_certificado_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Verifica se uma empresa tem certificado digital configurado."""
    _check_user_permission_for_empresa(empresa_id, current_user, db)
    
    tem_certificado = crud_empresa.empresa_tem_certificado(db, empresa_id)
    return {
        "empresa_id": empresa_id,
        "certificado_configurado": tem_certificado
    }

@router.post("/{empresa_id}/test-smtp")
def test_smtp_config(
    empresa_id: int,
    smtp_data: Optional[SMTPTest] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Testa a configuração SMTP da empresa."""
    db_empresa = _check_user_permission_for_empresa(empresa_id, current_user, db)
    
    if smtp_data:
        # Usar credenciais fornecidas (não salvas)
        # Log seguro do que foi recebido (não imprime a senha inteira)
        pwd = smtp_data.smtp_password or ''
        masked = (pwd[:3] + '...' + pwd[-3:]) if len(pwd) > 6 else ('*' * len(pwd))
        _safe_print(f"DEBUG: /test-smtp received smtp_data - server={smtp_data.smtp_server}, port={smtp_data.smtp_port}, user={smtp_data.smtp_user}, pwd_len={len(pwd)}, pwd_mask={masked}")

        result = EmailService.test_smtp_connection_with_credentials(
            smtp_data.smtp_server,
            smtp_data.smtp_port,
            smtp_data.smtp_user,
            smtp_data.smtp_password
        )
    else:
        # Usar configuração salva; se incompleta, usar o SMTP padrão do sistema (BRAZCOM)
        if not db_empresa.smtp_server or not db_empresa.smtp_port or not db_empresa.smtp_user or not db_empresa.smtp_password:
            # fallback para configurações globais
            print("DEBUG: configuração SMTP da empresa incompleta; usando BRAZCOM defaults")
            result = EmailService.test_smtp_connection_with_credentials(
                settings.BRAZCOM_SMTP_SERVER,
                settings.BRAZCOM_SMTP_PORT,
                settings.BRAZCOM_SMTP_USERNAME,
                settings.BRAZCOM_SMTP_PASSWORD
            )
        else:
            result = EmailService.test_smtp_connection(db_empresa)
    
    return result