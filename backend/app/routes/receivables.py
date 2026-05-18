from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session, object_session
from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel

import logging
logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.routes.auth import get_current_active_user
from app.api import deps
from app.models.models import Usuario, Receivable, BankAccount, Empresa
from app.services import isp_service
from app.services.receivable_service import generate_receivables_for_company, build_boleto_context
from app.services.boleto_generator import generate_boleto_pdf
from app.services.email_service import EmailService
import tempfile
import os
from app.core.config import settings

router = APIRouter(prefix="/receivables", tags=["Receivables"])

class SettlePayload(BaseModel):
    paid_amount: Optional[float] = None

class ReceivableResponse(BaseModel):
    id: int
    empresa_id: int
    cliente_id: int
    cliente_nome: Optional[str] = None
    cliente_cpf_cnpj: Optional[str] = None
    servico_contratado_id: Optional[int] = None
    nfcom_fatura_id: Optional[int] = None
    tipo: str
    issue_date: str
    due_date: str
    amount: float
    discount: float = 0.0
    interest_percent: float = 0.0
    fine_percent: float = 0.0
    bank: str
    carteira: Optional[str] = None
    agencia: Optional[str] = None
    conta: Optional[str] = None
    paid_amount: Optional[float] = None
    nosso_numero: Optional[str] = None
    bank_registration_id: Optional[str] = None
    codigo_barras: Optional[str] = None
    linha_digitavel: Optional[str] = None
    status: str
    registered_at: Optional[str] = None
    printed_at: Optional[str] = None
    sent_at: Optional[str] = None
    paid_at: Optional[str] = None
    registro_result: Optional[str] = None
    pdf_url: Optional[str] = None
    bb_boleto_numero: Optional[str] = None
    bb_boleto_url: Optional[str] = None
    bb_pix_qrcode: Optional[str] = None
    bb_pix_txid: Optional[str] = None
    payment_token: Optional[str] = None
    payment_url: Optional[str] = None
    
    # Mercado Pago específicos
    mp_payment_id: Optional[str] = None
    mp_payment_status: Optional[str] = None
    mp_payment_method: Optional[str] = None
    mp_preference_id: Optional[str] = None

    bank_account_id: Optional[int] = None
    bank_account_snapshot: Optional[str] = None
    bank_payload: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Adicionado para suportar filtros de pagamento no checkout
    mp_settings: Optional[dict] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        """Converte um objeto Receivable do banco para ReceivableResponse."""
        data = {}
        for field in cls.__fields__:
            value = getattr(obj, field, None)
            if field in ['issue_date', 'due_date', 'registered_at', 'printed_at', 'sent_at', 'paid_at', 'created_at', 'updated_at']:
                if value is not None:
                    if isinstance(value, datetime):
                        data[field] = value.isoformat()
                    else:
                        data[field] = str(value)
                else:
                    data[field] = None
            else:
                data[field] = value
        
        # Injetar mp_settings se disponível na empresa
        try:
            from app.models.models import Empresa
            db = object_session(obj)
            if db:
                empresa = db.query(Empresa).filter(Empresa.id == obj.empresa_id).first()
                if empresa:
                    data['mp_settings'] = {
                        "allow_boleto": empresa.mp_allow_boleto,
                        "allow_pix": empresa.mp_allow_pix,
                        "allow_credit_card": empresa.mp_allow_credit_card
                    }
        except Exception:
            pass

        return cls(**data)


@router.post("/empresa/{empresa_id}/generate", status_code=status.HTTP_201_CREATED, response_model=List[ReceivableResponse])
def generate_for_company(empresa_id: int, target_date: date = None, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    deps.permission_checker('receivables_manage')(db=db, current_user=current_user)
    if target_date is None:
        target_date = date.today()
    # permission checks could be added here (empresa ownership)
    created_receivables = generate_receivables_for_company(db, empresa_id, target_date)
    db.commit()  # Commit explicitamente as mudanças
    # Converte os objetos Receivable para ReceivableResponse usando o método customizado
    return [ReceivableResponse.from_orm(r) for r in created_receivables]


@router.post("/empresa/{empresa_id}/test-sicoob", status_code=status.HTTP_200_OK)
async def test_sicoob_integration(empresa_id: int, bank_account_id: Optional[int] = None, bank_account_data: Optional[dict] = Body(None), db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    deps.permission_checker('receivables_manage')(db=db, current_user=current_user)
    """
    Endpoint de teste para integração com Sicoob.
    Registra um boleto de teste no ambiente sandbox.
    """
    try:
        from app.services.sicoob_gateway import SicoobGateway
        from app.models.models import BankAccount

        # Buscar conta SICOB da empresa; se fornecido bank_account_id, buscar conta específica
        if bank_account_id is not None:
            sicoob_account = db.query(BankAccount).filter(
                BankAccount.id == bank_account_id,
                BankAccount.empresa_id == empresa_id,
                BankAccount.bank == "SICOB"
            ).first()
        else:
            sicoob_account = db.query(BankAccount).filter(
                BankAccount.empresa_id == empresa_id,
                BankAccount.bank == "SICOB"
            ).first()

        # Se dados enviados no corpo, priorizar para teste antes de salvar
        if bank_account_data:
            client_id = bank_account_data.get('sicoob_client_id')
            access_token = bank_account_data.get('sicoob_access_token')
            gateway = SicoobGateway(client_id=client_id, access_token=access_token) if (client_id and access_token) else SicoobGateway()
            using_custom_credentials = bool(client_id and access_token)
        else:
            # Criar gateway com credenciais da conta ou usar padrão do sandbox
            if sicoob_account and sicoob_account.sicoob_client_id and sicoob_account.sicoob_access_token:
                gateway = SicoobGateway(
                    client_id=sicoob_account.sicoob_client_id,
                    access_token=sicoob_account.sicoob_access_token
                )
                using_custom_credentials = True
            else:
                gateway = SicoobGateway()  # Usa credenciais padrão do sandbox
                using_custom_credentials = False

        # Verificar se temos dados reais da conta SICOB (não fictícios)
        def is_fictitious_data(value):
            if not value:
                return True
            # Detectar padrões fictícios comuns
            value_str = str(value).strip()
            if len(value_str) < 4:  # Valores muito curtos
                return True
            if value_str in ['123456', '123456789', '0703', '34256']:  # Valores conhecidos como fictícios
                return True
            return False
        
        # Validar se os dados reais existem: priorizar dados enviados no body (antes de salvar), senão usar conta do DB
        if bank_account_data:
            conta_val = bank_account_data.get('conta')
            agencia_val = bank_account_data.get('agencia')
            convenio_val = bank_account_data.get('convenio')
            has_real_data = (conta_val and not is_fictitious_data(conta_val) and agencia_val and not is_fictitious_data(agencia_val) and convenio_val and not is_fictitious_data(convenio_val))
        else:
            has_real_data = (sicoob_account and 
                            sicoob_account.conta and not is_fictitious_data(sicoob_account.conta) and
                            sicoob_account.agencia and not is_fictitious_data(sicoob_account.agencia) and
                            sicoob_account.convenio and not is_fictitious_data(sicoob_account.convenio))
        
        if not has_real_data:
            return {
                "status": "warning",
                "message": "Teste do Sicoob não pode ser executado: dados bancários fictícios detectados. Configure uma conta SICOB com dados reais para testar a integração.",
                "details": "Para testar a integração com Sicoob, é necessário configurar uma conta bancária com dados reais (agência, conta e convênio válidos)."
            }

        # Buscar dados da conta SICOB para usar valores reais
        # Obter valores reais preferencialmente do body se fornecido
        if bank_account_data:
            numero_contrato = bank_account_data.get('convenio')
            conta_corrente = bank_account_data.get('conta')
        else:
            numero_contrato = sicoob_account.convenio
            conta_corrente = sicoob_account.conta

        # Dados de teste para o sandbox
        test_boleto = {
            "numeroContrato": numero_contrato,
            "modalidade": 1,
            "numeroContaCorrente": conta_corrente,
            "especieDocumento": "DM",
            "dataEmissao": "2025-11-30",
            "dataVencimento": "2025-12-15",
            "valor": "100.00",
            "pagador": {
                "numeroCpfCnpj": "12345678901",
                "nome": "Cliente Teste Sandbox",
                "endereco": "Rua Teste, 123",
                "bairro": "Centro",
                "cidade": "São Paulo",
                "cep": "01234567",
                "uf": "SP"
            },
            "beneficiario": {
                "numeroCpfCnpj": "98765432100",
                "nome": "Empresa Teste Sandbox Ltda"
            },
            "instrucoes": ["Boleto de teste - Sandbox Sicoob"],
            "multa": "2.0",
            "juros": "1.0",
            "desconto": "0.0"
        }

        # Tentar registrar o boleto
        response = await gateway.registrar_boleto(test_boleto)

        credentials_info = "usando credenciais da conta bancária" if using_custom_credentials else "usando credenciais padrão do sandbox"

        return {
            "status": "success",
            "message": f"Boleto de teste registrado com sucesso no Sicoob ({credentials_info})",
            "response": response,
            "credentials_used": "custom" if using_custom_credentials else "default"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Erro no teste do Sicoob: {str(e)}",
            "details": "Verifique as credenciais e conectividade com o sandbox"
        }


@router.get("/empresa/{empresa_id}")
def list_receivables(
    empresa_id: int, 
    page: int = 1,
    per_page: int = 25,
    status: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    date_type: str = "due_date",
    db: Session = Depends(get_db), 
    current_user: Usuario = Depends(get_current_active_user)
):
    deps.permission_checker('receivables_view')(db=db, current_user=current_user)
    from app.models.models import Cliente
    from sqlalchemy import or_, String
    
    query = db.query(Receivable, Cliente.nome_razao_social, Cliente.cpf_cnpj)\
        .join(Cliente, Receivable.cliente_id == Cliente.id)\
        .filter(Receivable.empresa_id == empresa_id)
    
    if status:
        query = query.filter(Receivable.status == status)
        
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Cliente.nome_razao_social.ilike(search_term),
                Cliente.cpf_cnpj.ilike(search_term),
                Receivable.nosso_numero.ilike(search_term),
                Receivable.id.cast(String).ilike(search_term)
            )
        )
    
    filter_field = Receivable.issue_date if date_type == "issue_date" else Receivable.due_date
    
    if start_date:
        query = query.filter(filter_field >= start_date)
    if end_date:
        query = query.filter(filter_field <= end_date)
        
    total = query.count()
    items = query.order_by(Receivable.id.desc())\
        .offset((page - 1) * per_page)\
        .limit(per_page)\
        .all()
    
    result = []
    for recv, cliente_nome, cliente_cpf_cnpj in items:
        response = ReceivableResponse.from_orm(recv).dict()
        response['cliente_nome'] = cliente_nome
        response['cliente_cpf_cnpj'] = cliente_cpf_cnpj
        result.append(response)
    
    return {"data": result, "total": total}
    
@router.get("/cliente/{cliente_id}", response_model=List[ReceivableResponse])
def list_receivables_by_client(cliente_id: int, empresa_id: Optional[int] = None, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    """Lista todas as cobranças de um cliente específico."""
    deps.permission_checker('receivables_view')(db=db, current_user=current_user)
    
    query = db.query(Receivable).filter(Receivable.cliente_id == cliente_id)
    
    if empresa_id:
        query = query.filter(Receivable.empresa_id == empresa_id)
        
    items = query.order_by(Receivable.due_date.desc()).all()
    return [ReceivableResponse.from_orm(r) for r in items]
@router.put("/{receivable_id}/settle", response_model=ReceivableResponse)
def settle_receivable(receivable_id: int, payload: SettlePayload = Body(...), db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    """Marca uma cobrança como paga manualmente."""
    deps.permission_checker('receivables_manage')(db=db, current_user=current_user)
    recv = db.query(Receivable).filter(Receivable.id == receivable_id).first()
    if not recv:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")
    
    recv.status = 'PAID'
    recv.paid_at = datetime.utcnow()
    recv.paid_amount = payload.paid_amount if payload.paid_amount is not None else recv.amount
    
    # Se for boleto BB registrado, solicita a baixa (cancelamento) no banco
    if recv.bank == 'BANCO_DO_BRASIL' and recv.bb_boleto_numero:
        try:
            from app.services import bb_api_service
            bank_account = db.query(BankAccount).filter(BankAccount.id == recv.bank_account_id).first()
            if bank_account:
                bb_api_service.solicitar_baixa(bank_account, recv.bb_boleto_numero)
                logger.info(f"Baixa solicitada no BB para boleto {recv.bb_boleto_numero} devido a pagamento manual")
        except Exception as e:
            logger.error(f"Erro ao solicitar baixa no BB para boleto {recv.bb_boleto_numero}: {e}")

    # Se a cobrança estiver vinculada a um contrato ISP, realiza o desbloqueio automático
    if recv.servico_contratado_id:
        try:
            isp_service.process_unblock_if_needed(db, recv.servico_contratado_id)
        except Exception as e:
            logger.error(f"Erro ao processar desbloqueio automático ISP para contrato {recv.servico_contratado_id}: {e}")

    db.commit()
    db.refresh(recv)
    return ReceivableResponse.from_orm(recv)

class ReceivableCreate(BaseModel):
    empresa_id: int
    cliente_id: int
    due_date: date
    amount: float
    tipo: str = 'BOLETO'
    servico_contratado_id: Optional[int] = None
    bank_account_id: Optional[int] = None
    fine_percent: float = 0.0
    interest_percent: float = 0.0

@router.post("/", response_model=ReceivableResponse)
def create_manual_receivable(
    payload: ReceivableCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Cria uma cobrança manual para um cliente."""
    deps.permission_checker('receivables_manage')(db=db, current_user=current_user)
    from app.models.models import BankAccount, Bank
    import json

    # Validar se o usuário tem acesso a esta empresa
    user_empresas_ids = [e.empresa_id for e in current_user.empresas]
    if payload.empresa_id not in user_empresas_ids and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Usuário não tem acesso a esta empresa")

    recv = Receivable(
        empresa_id=payload.empresa_id,
        cliente_id=payload.cliente_id,
        servico_contratado_id=payload.servico_contratado_id,
        issue_date=datetime.utcnow(),
        due_date=datetime.combine(payload.due_date, datetime.min.time()),
        amount=payload.amount,
        fine_percent=payload.fine_percent,
        interest_percent=payload.interest_percent,
        status='PENDING',
        tipo=payload.tipo
    )

    if payload.bank_account_id:
        ba = db.query(BankAccount).filter(BankAccount.id == payload.bank_account_id).first()
        if ba:
            recv.bank_account_id = ba.id
            recv.bank = ba.bank
            snapshot = {
                "id": ba.id, "bank": ba.bank, "codigo_banco": ba.codigo_banco,
                "agencia": ba.agencia, "agencia_dv": ba.agencia_dv,
                "conta": ba.conta, "conta_dv": ba.conta_dv,
                "carteira": ba.carteira, "convenio": ba.convenio
            }
            recv.bank_account_snapshot = json.dumps(snapshot, default=str)
    
    # Se for Mercado Pago, gerar token de pagamento único
    if recv.tipo == 'MERCADO_PAGO':
        import uuid
        from app.core.config import settings
        recv.payment_token = str(uuid.uuid4())
        base_url = settings.FRONTEND_URL.rstrip("/")
        recv.payment_url = f"{base_url}/checkout?token={recv.payment_token}"
        recv.bank = 'MERCADO_PAGO'

    db.add(recv)
    db.commit()
    db.refresh(recv)
    return ReceivableResponse.from_orm(recv)


@router.get("/{receivable_id}/print")
def print_receivable(receivable_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    """Gera o PDF do boleto com layout Agrobraz."""
    deps.permission_checker('receivables_view')(db=db, current_user=current_user)
    recv = db.query(Receivable).filter(Receivable.id == receivable_id).first()
    if not recv:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")
    
    from app.services.receivable_service import build_boleto_context
    from app.services.boleto_generator import generate_boleto_pdf
    from fastapi.responses import Response

    context = build_boleto_context(db, recv)
    pdf_bytes = generate_boleto_pdf(context)
    
    recv.printed_at = datetime.utcnow()
    db.commit()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=boleto_{receivable_id}.pdf"}
    )


@router.get("/{receivable_id}", response_model=ReceivableResponse)
def get_receivable(receivable_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    """Busca detalhes de uma cobrança por ID."""
    # Nota: Acesso privado requer permissão de visualização
    deps.permission_checker('receivables_view')(db=db, current_user=current_user)
    
    recv = db.query(Receivable).filter(Receivable.id == receivable_id).first()
    if not recv:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")
    
    return ReceivableResponse.from_orm(recv)


@router.post("/{receivable_id}/send-email")
def send_receivable_email_route(receivable_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    """Envia a cobrança por email (Link Mercado Pago ou PDF Boleto)."""
    deps.permission_checker('receivables_manage')(db=db, current_user=current_user)
    
    recv = db.query(Receivable).filter(Receivable.id == receivable_id).first()
    if not recv:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")
    
    from app.models.models import Empresa, Cliente
    empresa = db.query(Empresa).filter(Empresa.id == recv.empresa_id).first()
    cliente = db.query(Cliente).filter(Cliente.id == recv.cliente_id).first()
    
    if not cliente or not cliente.email:
        raise HTTPException(status_code=400, detail="Cliente não possui email cadastrado")
        
    # Carregar empresa raw para pegar senha SMTP descriptografada se necessário pelo serviço
    from app.crud import crud_empresa
    empresa_raw = crud_empresa.get_empresa_raw(db, empresa_id=recv.empresa_id)
    
    pdf_path = None
    try:
        # Se NÃO for Mercado Pago e não tiver link, gerar o PDF do boleto
        if not recv.payment_url:
            context = build_boleto_context(db, recv)
            pdf_bytes = generate_boleto_pdf(context)
            
            # Salvar em arquivo temporário para anexo
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            tmp.write(pdf_bytes)
            tmp.close()
            pdf_path = tmp.name
            
        # Garantir que a URL de pagamento use a URL base atual do sistema
        payment_url = recv.payment_url
        if recv.payment_token:
            base_url = settings.FRONTEND_URL.rstrip("/")
            payment_url = f"{base_url}/checkout?token={recv.payment_token}"
            # Sincronizar no banco se houver divergência
            if recv.payment_url != payment_url:
                recv.payment_url = payment_url
                db.add(recv)
                db.commit()

        # Preparar dados para o serviço de email
        receivable_data = {
            "amount": recv.amount,
            "due_date": recv.due_date,
            "payment_url": payment_url
        }
        
        send_email = getattr(empresa, "send_method_email", True)
        send_whatsapp = getattr(empresa, "send_method_whatsapp", False)
        
        # Fallback caso nenhum esteja marcado
        if not send_email and not send_whatsapp:
            send_email = True

        success_email = False
        success_whatsapp = False
        channels_sent = []

        if send_email:
            if not cliente.email:
                raise HTTPException(status_code=400, detail="Cliente não possui email cadastrado para receber por e-mail")
            success_email = EmailService.send_receivable_email(
                empresa=empresa_raw,
                cliente_email=cliente.email,
                receivable_data=receivable_data,
                pdf_path=pdf_path
            )
            if success_email:
                channels_sent.append("E-mail")

        if send_whatsapp:
            if not cliente.telefone:
                raise HTTPException(status_code=400, detail="Cliente não possui telefone cadastrado para receber por WhatsApp")
            from app.services.whatsapp_service import WhatsAppService
            success_whatsapp = WhatsAppService.send_receivable_message(
                empresa=empresa_raw,
                cliente_nome=cliente.nome_razao_social,
                cliente_phone=cliente.telefone,
                receivable_data=receivable_data
            )
            if success_whatsapp:
                channels_sent.append("WhatsApp")

        if (send_email and not success_email) or (send_whatsapp and not success_whatsapp):
            failed_channels = []
            if send_email and not success_email:
                failed_channels.append("E-mail")
            if send_whatsapp and not success_whatsapp:
                failed_channels.append("WhatsApp")
            raise HTTPException(
                status_code=500,
                detail=f"Falha ao enviar por: {', '.join(failed_channels)}. Verifique as configurações."
            )

        recv.sent_at = datetime.utcnow()
        db.commit()
        return {"message": f"Cobrança enviada com sucesso via {', '.join(channels_sent)}!"}
            
    finally:
        # Limpar arquivo temporário
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.unlink(pdf_path)
            except:
                pass


@router.delete("/{receivable_id}")
def delete_receivable(receivable_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    """Exclui permanentemente uma cobrança se não estiver paga (ou se o usuário for administrador)."""
    deps.permission_checker('receivables_manage')(db=db, current_user=current_user)
    recv = db.query(Receivable).filter(Receivable.id == receivable_id).first()
    if not recv:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")
    
    if recv.status == 'PAID':
        is_admin = current_user.is_superuser or any(assoc.empresa_id == recv.empresa_id and assoc.is_admin for assoc in current_user.empresas)
        if not is_admin:
            raise HTTPException(status_code=400, detail="Não é possível excluir uma cobrança já paga. Apenas administradores podem realizar esta ação.")
    
    # Solicitar baixa no banco associado se estiver registrado
    if recv.status == 'REGISTERED':
        # Banco do Brasil
        if recv.bank in ['BANCO DO BRASIL', 'BANCO_DO_BRASIL']:
            from app.services.bb_api_service import solicitar_baixa
            from app.models.models import BankAccount
            ba = db.query(BankAccount).filter(BankAccount.id == recv.bank_account_id).first()
            if ba and recv.bb_boleto_numero:
                try:
                    solicitar_baixa(ba, recv.bb_boleto_numero)
                    logger.info(f"Baixa solicitada no BB para fatura {recv.id}")
                except Exception as e:
                    logger.error(f"Erro ao solicitar baixa no BB antes da exclusão (fatura {recv.id}): {e}")
        
        # Sicoob
        elif recv.bank == 'SICOB':
            try:
                from app.services.sicoob_gateway import SicoobGateway
                from app.models.models import BankAccount
                ba = db.query(BankAccount).filter(BankAccount.id == recv.bank_account_id).first()
                if ba and recv.nosso_numero:
                    # Inicializar gateway com credenciais da conta
                    gateway = SicoobGateway(
                        client_id=ba.sicoob_client_id,
                        access_token=ba.sicoob_access_token
                    )
                    # Sicoob API é async, mas a rota é sync. Usamos run_sync se necessário ou transformamos a rota.
                    # Como a maioria das rotas aqui são sync, vamos tentar rodar o async de forma segura.
                    import asyncio
                    try:
                        asyncio.run(gateway.baixar_boleto(recv.nosso_numero))
                        logger.info(f"Baixa solicitada no Sicoob para fatura {recv.id}")
                    except Exception as async_e:
                        # Fallback se já houver um loop rodando (comum em environments async como FastAPI)
                        logger.warning(f"Falha ao usar asyncio.run, tentando loop atual: {async_e}")
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                loop.create_task(gateway.baixar_boleto(recv.nosso_numero))
                            else:
                                loop.run_until_complete(gateway.baixar_boleto(recv.nosso_numero))
                        except Exception as loop_e:
                            logger.error(f"Erro definitivo ao solicitar baixa no Sicoob: {loop_e}")
            except Exception as e:
                logger.error(f"Erro ao processar baixa no Sicoob (fatura {recv.id}): {e}")
        
        # Mercado Pago
        elif recv.mp_payment_id and recv.status != 'PAID':
            try:
                import mercadopago
                empresa = db.query(Empresa).filter(Empresa.id == recv.empresa_id).first()
                if empresa and empresa.mp_access_token:
                    sdk = mercadopago.SDK(empresa.mp_access_token)
                    # No Mercado Pago, cancelar um pagamento pendente muda o status para 'cancelled'
                    cancel_res = sdk.payment().update(int(recv.mp_payment_id), {"status": "cancelled"})
                    if cancel_res["status"] in [200, 201]:
                        logger.info(f"Pagamento MP {recv.mp_payment_id} cancelado com sucesso")
                    else:
                        logger.warning(f"Falha ao cancelar pagamento MP {recv.mp_payment_id}: {cancel_res['response']}")
            except Exception as e:
                logger.error(f"Erro ao cancelar pagamento no Mercado Pago (fatura {recv.id}): {e}")

    # Exclusão física do banco
    db.delete(recv)
    db.commit()
    return {"message": "Cobrança excluída permanentemente"}
