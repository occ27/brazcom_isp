from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random

from app.core.database import get_db
from app.core.security import create_access_token, verify_password, get_password_hash
from app.core.config import settings
from app.models.models import Cliente, Empresa, PasswordResetTokenCliente
from app.crud import crud_cliente
from app.schemas.cliente import (
    ClienteLogin,
    ClienteAuthResponse,
    ClienteForgotPassword,
    ClienteResetPassword,
    ClienteSetPassword
)
from app.services.email_service import EmailService
from app.crud import crud_password_reset_cliente
from app.schemas.password_reset import PasswordResetRequest, PasswordResetVerify, PasswordResetConfirm

router = APIRouter(prefix="/client-auth", tags=["Autenticação de Clientes"])

oauth2_scheme_client = OAuth2PasswordBearer(tokenUrl="client-auth/login")

def get_current_cliente(token: str = Depends(oauth2_scheme_client), db: Session = Depends(get_db)) -> Cliente:
    """Obtém o cliente atual a partir do token JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    from app.core.security import decode_access_token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    cliente_id = payload.get("sub")
    if cliente_id is None:
        raise credentials_exception

    # Verifica se é um token de cliente (não de usuário admin)
    token_type = payload.get("type")
    if token_type != "cliente":
        raise credentials_exception

    cliente = crud_cliente.get_cliente(db, cliente_id=int(cliente_id))
    if cliente is None:
        raise credentials_exception
    return cliente

def get_current_active_cliente(current_cliente: Cliente = Depends(get_current_cliente)) -> Cliente:
    """Obtém o cliente ativo atual."""
    if not current_cliente.is_active:
        raise HTTPException(status_code=400, detail="Cliente inativo")
    return current_cliente

def _generate_code(length: int = 6) -> str:
    """Gera código numérico de tamanho definido."""
    start = 10 ** (length - 1)
    end = (10 ** length) - 1
    return str(random.randint(start, end))

@router.post("/login", response_model=ClienteAuthResponse)
def cliente_login(login_data: ClienteLogin, db: Session = Depends(get_db)):
    """Login de cliente usando CPF/CNPJ e senha."""

    # Busca cliente por CPF/CNPJ e empresa
    cliente = crud_cliente.get_cliente_by_cpf_cnpj_and_empresa(
        db, cpf_cnpj=login_data.cpf_cnpj, empresa_id=login_data.empresa_id
    )

    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CPF/CNPJ ou senha incorretos"
        )

    # Verifica se tem senha configurada
    if not cliente.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cliente não possui senha configurada. Entre em contato com o suporte."
        )

    # Verifica senha
    if not verify_password(login_data.password, cliente.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CPF/CNPJ ou senha incorretos"
        )

    if not cliente.is_active:
        raise HTTPException(status_code=400, detail="Cliente inativo")

    # Atualiza último login
    cliente.last_login = datetime.utcnow()
    db.commit()

    # Busca dados da empresa
    empresa = db.query(Empresa).filter(Empresa.id == cliente.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=400, detail="Empresa não encontrada")

    # Cria token JWT para cliente
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(cliente.id), "type": "cliente"},
        expires_delta=access_token_expires
    )

    return ClienteAuthResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        cliente={
            "id": cliente.id,
            "nome_razao_social": cliente.nome_razao_social,
            "cpf_cnpj": cliente.cpf_cnpj,
            "email": cliente.email,
            "telefone": cliente.telefone,
            "tipo_pessoa": cliente.tipo_pessoa.value if hasattr(cliente.tipo_pessoa, 'value') else str(cliente.tipo_pessoa)
        },
        empresa={
            "id": empresa.id,
            "nome_fantasia": empresa.nome_fantasia,
            "razao_social": empresa.razao_social,
            "cnpj": empresa.cnpj
        }
    )

@router.post("/forgot-password")
def cliente_forgot_password(
    payload: ClienteForgotPassword,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Solicita redefinição de senha do cliente. Envia código por email."""

    # Busca cliente por CPF/CNPJ e empresa
    cliente = crud_cliente.get_cliente_by_cpf_cnpj_and_empresa(
        db, cpf_cnpj=payload.cpf_cnpj, empresa_id=payload.empresa_id
    )

    # Sempre retorna 200 para não vazar existência do cliente
    if not cliente or not cliente.email:
        return {"message": "Se o CPF/CNPJ existir, o email estiver cadastrado e corresponder ao informado, você receberá um código para redefinir a senha."}

    # Valida se o email informado corresponde ao email cadastrado
    if cliente.email.lower() != payload.email.lower():
        return {"message": "Se o CPF/CNPJ existir, o email estiver cadastrado e corresponder ao informado, você receberá um código para redefinir a senha."}

    # Verifica rate limiting - não permite nova solicitação nos últimos 5 minutos
    now = datetime.utcnow()
    if cliente.last_password_reset_request and (now - cliente.last_password_reset_request).total_seconds() < 300:  # 5 minutos
        remaining_time = int(300 - (now - cliente.last_password_reset_request).total_seconds()) // 60
        return {"message": f"Uma solicitação recente foi feita. Aguarde {remaining_time} minutos antes de tentar novamente."}

    # Atualiza o timestamp da última solicitação
    cliente.last_password_reset_request = now
    db.add(cliente)
    db.commit()

    # Gera código e armazena token
    code = _generate_code(6)
    token = crud_password_reset_cliente.create_password_reset_token(
        db=db, cliente=cliente, code=code, expires_minutes=15
    )

    # Busca empresa para personalizar email
    empresa = db.query(Empresa).filter(Empresa.id == cliente.empresa_id).first()
    empresa_nome = empresa.nome_fantasia if empresa else "Sistema"

    # Monta email
    subject = f"{empresa_nome} - Recuperação de Senha"
    body = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recuperação de Senha - {empresa_nome}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            background-color: #f8f9fa;
        }}
        .container {{
            background-color: #ffffff;
            margin: 20px;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #007bff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .logo {{
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
            margin-bottom: 10px;
        }}
        .subtitle {{
            color: #6c757d;
            font-size: 14px;
        }}
        .content {{
            margin-bottom: 30px;
        }}
        .greeting {{
            font-size: 18px;
            margin-bottom: 20px;
        }}
        .code-container {{
            background-color: #f8f9fa;
            border: 2px solid #007bff;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            margin: 20px 0;
        }}
        .code {{
            font-size: 32px;
            font-weight: bold;
            color: #007bff;
            letter-spacing: 4px;
            font-family: 'Courier New', monospace;
        }}
        .instructions {{
            background-color: #e9ecef;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .warning {{
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .footer {{
            border-top: 1px solid #dee2e6;
            padding-top: 20px;
            text-align: center;
            color: #6c757d;
            font-size: 12px;
        }}
        .signature {{
            font-weight: bold;
            color: #007bff;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">{empresa_nome}</div>
            <div class="subtitle">Portal do Cliente</div>
        </div>

        <div class="content">
            <div class="greeting">
                Olá, <strong>{cliente.nome_razao_social}</strong>!
            </div>

            <p>Recebemos uma solicitação para redefinir a senha da sua conta no portal do cliente.</p>

            <p>Para continuar com a redefinição, utilize o código de verificação abaixo:</p>

            <div class="code-container">
                <div class="code">{code}</div>
            </div>

            <div class="instructions">
                <strong>Instruções:</strong>
                <ol>
                    <li>Copie ou anote o código acima</li>
                    <li>Retorne à página de login do portal</li>
                    <li>Clique em "Esqueci a senha"</li>
                    <li>Digite seu CPF/CNPJ e o código recebido</li>
                    <li>Defina sua nova senha</li>
                </ol>
            </div>

            <div class="warning">
                <strong>⚠️ Importante:</strong>
                <ul>
                    <li>Este código é válido por <strong>15 minutos</strong></li>
                    <li>Não compartilhe este código com ninguém</li>
                    <li>Se você não solicitou esta redefinição, ignore este email</li>
                    <li>Sua conta permanecerá segura</li>
                </ul>
            </div>

            <p>Se você tiver qualquer dúvida ou dificuldade, entre em contato conosco.</p>
        </div>

        <div class="footer">
            <p>Este é um email automático, por favor não responda diretamente.</p>
            <div class="signature">
                Equipe {empresa_nome}
            </div>
            <p>© 2025 {empresa_nome}. Todos os direitos reservados.</p>
        </div>
    </div>
</body>
</html>
    """.strip()

    # Envia email
    def _send():
        EmailService.send_using_credentials(
            smtp_server=settings.BRAZCOM_SMTP_SERVER,
            smtp_port=settings.BRAZCOM_SMTP_PORT,
            smtp_user=settings.BRAZCOM_SMTP_USERNAME,
            smtp_password=settings.BRAZCOM_SMTP_PASSWORD,
            to_email=cliente.email,
            subject=subject,
            body=body,
            is_html=True
        )

    background_tasks.add_task(_send)

    return {"message": "Se o CPF/CNPJ existir, o email estiver cadastrado e corresponder ao informado, você receberá um código para redefinir a senha."}

@router.post("/reset-password")
def cliente_reset_password(payload: ClienteResetPassword, db: Session = Depends(get_db)):
    """Confirma o código e redefine a senha do cliente."""

    # Busca cliente por CPF/CNPJ e empresa
    cliente = crud_cliente.get_cliente_by_cpf_cnpj_and_empresa(
        db, cpf_cnpj=payload.cpf_cnpj, empresa_id=payload.empresa_id
    )

    if not cliente:
        raise HTTPException(status_code=400, detail="Cliente não encontrado")

    # Busca token ativo do cliente
    token = crud_password_reset_cliente.get_active_token_for_cliente(db, cliente_id=cliente.id)
    if not token or token.code != payload.reset_code:
        raise HTTPException(status_code=400, detail="Código inválido ou expirado")

    # Atualiza senha
    hashed = get_password_hash(payload.new_password)
    cliente.password_hash = hashed
    cliente.reset_token = None
    cliente.reset_token_expires = None
    db.add(cliente)
    db.commit()

    # Marca token como usado
    crud_password_reset_cliente.mark_token_used(db, token)

    return {"message": "Senha atualizada com sucesso"}

@router.post("/set-password")
def cliente_set_password(
    payload: ClienteSetPassword,
    cliente: Cliente = Depends(get_current_active_cliente),
    db: Session = Depends(get_db)
):
    """Define senha inicial para cliente logado (usado quando cliente não tem senha)."""

    # Verifica se cliente já tem senha
    if cliente.password_hash:
        raise HTTPException(
            status_code=400,
            detail="Cliente já possui senha configurada. Use a funcionalidade de reset de senha."
        )

    # Define senha
    hashed = get_password_hash(payload.password)
    cliente.password_hash = hashed
    cliente.email_verified = True  # Marca email como verificado quando define senha
    db.add(cliente)
    db.commit()

    return {"message": "Senha definida com sucesso"}

@router.get("/me")
def get_cliente_profile(cliente: Cliente = Depends(get_current_active_cliente)):
    """Retorna perfil do cliente logado."""
    return {
        "id": cliente.id,
        "nome_razao_social": cliente.nome_razao_social,
        "cpf_cnpj": cliente.cpf_cnpj,
        "email": cliente.email,
        "telefone": cliente.telefone,
        "tipo_pessoa": cliente.tipo_pessoa.value if hasattr(cliente.tipo_pessoa, 'value') else str(cliente.tipo_pessoa),
        "email_verified": cliente.email_verified,
        "last_login": cliente.last_login.isoformat() if cliente.last_login else None
    }