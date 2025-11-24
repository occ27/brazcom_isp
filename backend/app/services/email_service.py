import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
import os
from pathlib import Path

from app.models.models import Empresa
from app.core.security import decrypt_sensitive_data

from typing import Tuple
import sys
import io


def _safe_exc_str(e: object) -> str:
    """Converte exceção ou objeto possivelmente contendo bytes em string segura para logs.

    Decodifica bytes com utf-8 e substitui caracteres inválidos; tenta extrair
    atributo `smtp_error` quando presente (é comum em exceptions do smtplib).
    """
    try:
        # bytes direto
        if isinstance(e, (bytes, bytearray)):
            return e.decode('utf-8', errors='replace')

        # objetos de exceção com atributo smtp_error
        smtp_err = getattr(e, 'smtp_error', None)
        if smtp_err is not None:
            if isinstance(smtp_err, (bytes, bytearray)):
                return smtp_err.decode('utf-8', errors='replace')
            return str(smtp_err)

        # fallback para str()
        return str(e)
    except Exception:
        return repr(e)


def _safe_print(msg: str) -> None:
    """Imprime uma mensagem no stdout garantindo codificação utf-8 com fallback.

    Escreve diretamente em stdout.buffer para evitar erros de encoding
    quando sys.stdout.encoding não suporta caracteres não-ASCII.
    """
    try:
        # Preferir escrever bytes diretamente no buffer (mais seguro)
        buf = getattr(sys.stdout, 'buffer', None)
        if buf is not None:
            buf.write((str(msg) + "\n").encode('utf-8', errors='replace'))
            buf.flush()
            return

        # Se não houver buffer (ambientes especiais), usar wrapper com UTF-8
        text_wrapper = io.TextIOWrapper(getattr(sys.stdout, 'buffer', sys.stdout), encoding='utf-8', errors='replace')
        text_wrapper.write(str(msg) + "\n")
        text_wrapper.flush()
        try:
            # Se criamos um wrapper novo, desmontar para não interferir
            if text_wrapper is not sys.stdout:
                text_wrapper.detach()
        except Exception:
            pass
    except Exception:
        # Como último recurso, ignora falhas de logging
        try:
            sys.stdout.write(str(msg) + "\n")
            sys.stdout.flush()
        except Exception:
            pass

class EmailService:
    """Serviço para envio de emails usando configurações SMTP da empresa"""

    @staticmethod
    def _create_smtp_connection(empresa: Empresa) -> smtplib.SMTP:
        """Cria conexão SMTP com as configurações da empresa"""
        if not all([empresa.smtp_server, empresa.smtp_port, empresa.smtp_user, empresa.smtp_password]):
            raise ValueError("Configurações SMTP incompletas")

        # Criar conexão SMTP
        if empresa.smtp_port == 465:
            # SMTP SSL
            server = smtplib.SMTP_SSL(empresa.smtp_server, empresa.smtp_port)
        else:
            # SMTP normal (pode usar STARTTLS)
            server = smtplib.SMTP(empresa.smtp_server, empresa.smtp_port)
            server.starttls()

        # Descriptografar senha SMTP
        smtp_password = decrypt_sensitive_data(empresa.smtp_password)
        # Log seguro do tamanho da senha descriptografada (não imprime o valor)
        _safe_print(f"DEBUG: _create_smtp_connection - decrypted_pwd_len={len(smtp_password) if smtp_password else 0}")
        if not smtp_password:
            raise ValueError("Falha ao descriptografar senha SMTP")

        # Login
        server.login(empresa.smtp_user, smtp_password)
        return server

    @staticmethod
    def send_email(
        empresa: Empresa,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = False,
        attachments: Optional[List[str]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Envia email usando as configurações SMTP da empresa

        Args:
            empresa: Instância da empresa com configurações SMTP
            to_email: Email do destinatário
            subject: Assunto do email
            body: Corpo do email
            is_html: Se o corpo é HTML
            attachments: Lista de caminhos para arquivos anexos
            cc: Lista de emails em cópia
            bcc: Lista de emails em cópia oculta

        Returns:
            bool: True se enviado com sucesso
        """
        try:
            # Criar mensagem
            msg = MIMEMultipart()
            msg['From'] = empresa.smtp_user
            msg['To'] = to_email
            msg['Subject'] = subject

            # Adicionar CC se fornecido
            if cc:
                msg['Cc'] = ', '.join(cc)

            # Corpo do email
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            # Anexos
            if attachments:
                for attachment_path in attachments:
                    if os.path.exists(attachment_path):
                        with open(attachment_path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            filename = Path(attachment_path).name
                            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                            msg.attach(part)

            # Lista completa de destinatários
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            # Enviar email
            with EmailService._create_smtp_connection(empresa) as server:
                server.sendmail(empresa.smtp_user, recipients, msg.as_string())

            return True

        except Exception as e:
            _safe_print(f"Erro ao enviar email: {_safe_exc_str(e)}")
            return False

    @staticmethod
    def send_nfcom_email(
        empresa: Empresa,
        cliente_email: str,
        nfcom_data: Dict[str, Any],
        pdf_path: Optional[str] = None
    ) -> bool:
        """
        Envia NFCom por email para o cliente

        Args:
            empresa: Empresa emissora
            cliente_email: Email do cliente
            nfcom_data: Dados da NFCom
            pdf_path: Caminho para o PDF da NFCom (opcional)

        Returns:
            bool: True se enviado com sucesso
        """
        subject = f"NFCom - {empresa.razao_social}"

        # Corpo do email
        # Nota: por motivo de privacidade e consistência, o corpo do email não
        # deve ser preenchido automaticamente com dados sensíveis da nota
        # (número, valores, etc). Usamos um corpo genérico e claro.
        body = f"""
Prezado cliente,

Segue em anexo o documento referente à sua operação com {empresa.razao_social}.

Caso necessite de informações adicionais, responda este e-mail informando os detalhes desejados.

Atenciosamente,
{empresa.razao_social}
{empresa.email}
        """.strip()

        # Anexos
        attachments = []
        if pdf_path and os.path.exists(pdf_path):
            attachments.append(pdf_path)

        return EmailService.send_email(
            empresa=empresa,
            to_email=cliente_email,
            subject=subject,
            body=body,
            attachments=attachments
        )

    @staticmethod
    def test_smtp_connection(empresa: Empresa) -> Dict[str, Any]:
        """
        Testa a conexão SMTP da empresa usando configuração salva (criptografada).

        Returns:
            Dict com status e mensagem
        """
        try:
            # Mostra informações mínimas (sem revelar senha) para depuração
            _safe_print(f"DEBUG: test_smtp_connection - server={empresa.smtp_server}, port={empresa.smtp_port}, user={empresa.smtp_user}, pwd_len={len(empresa.smtp_password) if empresa.smtp_password else 0}")

            with EmailService._create_smtp_connection(empresa) as server:
                # Ativar debug detalhado do smtplib (imprime diálogo SMTP no stdout)
                    # NÃO ativamos o debug do smtplib por padrão aqui, porque ele
                    # imprime bytes brutos que causaram UnicodeEncodeError em
                    # terminais Windows com encoding ASCII. Se for necessário ver o
                    # diálogo SMTP, execute o backend com UTF-8 (veja instruções).

                # Tentar enviar um email de teste para si mesmo
                test_subject = "Teste de configuração SMTP"
                test_body = "Este é um email de teste para verificar a configuração SMTP."

                server.sendmail(empresa.smtp_user, empresa.smtp_user, f"Subject: {test_subject}\n\n{test_body}")

            return {"success": True, "message": "Conexão SMTP testada com sucesso"}

        except smtplib.SMTPAuthenticationError as auth_err:
            # Mostrar código e resposta retornada pelo servidor para diagnóstico
            code = getattr(auth_err, 'smtp_code', None)
            resp = getattr(auth_err, 'smtp_error', None)
            resp_str = _safe_exc_str(resp)
            _safe_print(f"SMTPAuthenticationError code={code} resp={resp_str} exception={_safe_exc_str(auth_err)}")
            return {"success": False, "message": f"Erro na configuração SMTP (autenticação): {code} {resp_str}"}

        except Exception as e:
            _safe_print(f"Erro na configuração SMTP geral: {type(e).__name__}: {_safe_exc_str(e)}")
            return {"success": False, "message": f"Erro na configuração SMTP: {_safe_exc_str(e)}"}

    @staticmethod
    def test_smtp_connection_with_credentials(
        smtp_server: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str
    ) -> Dict[str, Any]:
        """
        Testa a conexão SMTP com credenciais fornecidas diretamente (não descriptografa).

        Returns:
            Dict com status e mensagem
        """
        try:
            # Depuração mínima (não imprimir a senha inteira)
            _safe_print(f"DEBUG: test_smtp_connection_with_credentials - server={smtp_server}, port={smtp_port}, user={smtp_user}, pwd_len={len(smtp_password) if smtp_password else 0}")

            # Criar conexão SMTP
            if smtp_port == 465:
                # SMTP SSL
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                # SMTP normal (pode usar STARTTLS)
                server = smtplib.SMTP(smtp_server, smtp_port)
                # Ativar debug do smtplib para registrar diálogo somente se stderr usar UTF-8
                try:
                    stderr_enc = (getattr(sys.stderr, 'encoding', None) or sys.getdefaultencoding() or '').lower()
                    if 'utf' in stderr_enc:
                        server.set_debuglevel(1)
                    else:
                        _safe_print(f"DEBUG: stdout/stderr encoding '{stderr_enc}' não UTF-8; pulando set_debuglevel() para evitar UnicodeEncodeError")
                except Exception:
                    pass

                server.ehlo()
                server.starttls()
                server.ehlo()

            # Login
            try:
                server.login(smtp_user, smtp_password)
                # Se o login foi bem-sucedido (retorno 235 do servidor), consideramos
                # a autenticação validada. Em alguns ambientes o diálogo SMTP ou
                # operações subsequentes podem gerar UnicodeEncodeError apenas
                # durante o logging do smtplib; para garantir que a UI receba
                # feedback correto, retornamos sucesso após login.
                return {"success": True, "message": "Conexão SMTP autenticada com sucesso"}
            except smtplib.SMTPAuthenticationError as auth_err:
                code = getattr(auth_err, 'smtp_code', None)
                resp = getattr(auth_err, 'smtp_error', None)
                resp_str = _safe_exc_str(resp)
                _safe_print(f"SMTPAuthenticationError code={code} resp={resp_str} exception={_safe_exc_str(auth_err)}")
                return {"success": False, "message": f"Erro na configuração SMTP (autenticação): {code} {resp_str}"}

            # Observação: envio de um email de teste foi removido do fluxo
            # principal porque a autenticação (login) já valida as credenciais
            # e em alguns ambientes o diálogo completo pode gerar problemas de
            # encoding nos logs. Se quiser, podemos reativar o envio de teste
            # controladamente atrás de uma flag.
            return {"success": True, "message": "Conexão SMTP autenticada com sucesso"}

        except Exception as e:
            _safe_print(f"Erro na configuração SMTP com credenciais: {type(e).__name__}: {_safe_exc_str(e)}")
            return {"success": False, "message": f"Erro na configuração SMTP: {_safe_exc_str(e)}"}

    @staticmethod
    def send_using_credentials(
        smtp_server: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = False,
        attachments: Optional[List[str]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """Envia email usando credenciais SMTP explícitas (sem precisar de Empresa)."""
        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = to_email
            msg['Subject'] = subject

            if cc:
                msg['Cc'] = ', '.join(cc)

            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            if attachments:
                for attachment_path in attachments:
                    if os.path.exists(attachment_path):
                        with open(attachment_path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            filename = Path(attachment_path).name
                            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                            msg.attach(part)

            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            # Conectar usando parâmetros
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, recipients, msg.as_string())
                server.quit()
            else:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, recipients, msg.as_string())
                server.quit()

            return True

        except Exception as e:
            _safe_print(f"Erro ao enviar email com credenciais: {_safe_exc_str(e)}")
            return False