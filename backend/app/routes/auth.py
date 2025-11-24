from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import create_access_token, verify_password, get_password_hash
from app.core.config import settings
from app.models.models import Usuario
from app.crud import crud_usuario
from app.schemas.usuario import Token, UsuarioRegister, UsuarioCreate, UsuarioResponse
import random
from app.services.email_service import EmailService
from app.crud import crud_password_reset
from app.schemas.password_reset import PasswordResetRequest, PasswordResetVerify, PasswordResetConfirm

router = APIRouter(prefix="/auth", tags=["Autenticação"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    from app.core.security import decode_access_token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    user = crud_usuario.get_usuario(db, usuario_id=int(user_id))
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Usuário inativo")
    return current_user

def get_current_active_superuser(current_user: Usuario = Depends(get_current_active_user)) -> Usuario:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="O usuário não tem privilégios de administrador",
        )
    return current_user

@router.post("/login", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud_usuario.get_usuario_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuário inativo")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


def _generate_code(length: int = 6) -> str:
    # Gera código numérico de tamanho definido
    start = 10 ** (length - 1)
    end = (10 ** length) - 1
    return str(random.randint(start, end))


@router.post("/password-reset/request")
def password_reset_request(payload: PasswordResetRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Solicita redefinição de senha. Envia código por email se o usuário existir."""
    user = crud_usuario.get_usuario_by_email(db, email=payload.email)

    # Sempre retorna 200 para não vazar existência do usuário
    if not user:
        return {"message": "Se o email existir, você receberá um código para redefinir a senha."}

    # Gera código e armazena token
    code = _generate_code(6)
    token = crud_password_reset.create_password_reset_token(db=db, usuario=user, code=code, expires_minutes=15)

    # Monta email
    subject = "Brazcom - Recuperação de Senha"
    body = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recuperação de Senha - Brazcom</title>
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
            <div class="logo">Brazcom ISP Suite</div>
            <div class="subtitle">Sistema de Emissão de Nota Fiscal de Comunicação</div>
        </div>

        <div class="content">
            <div class="greeting">
                Olá, <strong>{user.full_name}</strong>!
            </div>

            <p>Recebemos uma solicitação para redefinir a senha da sua conta no sistema NFCom.</p>

            <p>Para continuar com a redefinição, utilize o código de verificação abaixo:</p>

            <div class="code-container">
                <div class="code">{code}</div>
            </div>

            <div class="instructions">
                <strong>Instruções:</strong>
                <ol>
                    <li>Copie ou anote o código acima</li>
                    <li>Retorne à página de login do NFCom</li>
                    <li>Clique em "Esqueci a senha"</li>
                    <li>Digite seu email e o código recebido</li>
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
                Equipe Brazcom Engenharia de Software
            </div>
            <p>© 2025 Brazcom. Todos os direitos reservados.</p>
        </div>
    </div>
</body>
</html>
    """.strip()

    # Envia usando as credenciais Brazcom (configuradas em settings)
    def _send():
        EmailService.send_using_credentials(
            smtp_server=settings.BRAZCOM_SMTP_SERVER,
            smtp_port=settings.BRAZCOM_SMTP_PORT,
            smtp_user=settings.BRAZCOM_SMTP_USERNAME,
            smtp_password=settings.BRAZCOM_SMTP_PASSWORD,
            to_email=user.email,
            subject=subject,
            body=body,
            is_html=True
        )

    background_tasks.add_task(_send)

    return {"message": "Se o email existir, você receberá um código para redefinir a senha."}


@router.post("/password-reset/verify")
def password_reset_verify(payload: PasswordResetVerify, db: Session = Depends(get_db)):
    """Verifica se o código informado é válido para o usuário."""
    user = crud_usuario.get_usuario_by_email(db, email=payload.email)
    if not user:
        raise HTTPException(status_code=400, detail="Código inválido ou expirado")

    # Busca token ativo do usuário
    token = crud_password_reset.get_active_token_for_user(db, usuario_id=user.id)
    if not token or token.code != payload.code:
        raise HTTPException(status_code=400, detail="Código inválido ou expirado")

    return {"valid": True}


@router.post("/password-reset/confirm")
def password_reset_confirm(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Confirma o código e permite troca de senha."""
    user = crud_usuario.get_usuario_by_email(db, email=payload.email)
    if not user:
        raise HTTPException(status_code=400, detail="Usuário não encontrado")

    token = crud_password_reset.get_active_token_for_user(db, usuario_id=user.id)
    if not token or token.code != payload.code:
        raise HTTPException(status_code=400, detail="Código inválido ou expirado")

    # Atualiza senha
    hashed = get_password_hash(payload.new_password)
    user.hashed_password = hashed
    db.add(user)
    db.commit()

    # Marca token como usado
    crud_password_reset.mark_token_used(db, token)

    return {"message": "Senha atualizada com sucesso"}


# Alias para compatibilidade com frontends que chamam /auth/register
@router.post("/register", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def register_via_auth(
    usuario: UsuarioRegister,
    db: Session = Depends(get_db)
):
    """Registra um novo usuário via rota /auth/register (compatibilidade)."""
    db_user = crud_usuario.get_usuario_by_email(db, email=usuario.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email já registrado")

    usuario_create = UsuarioCreate(
        full_name=usuario.full_name,
        email=usuario.email,
        password=usuario.password,
        is_superuser=False
    )
    return crud_usuario.create_usuario(db=db, usuario=usuario_create)