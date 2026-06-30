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
from app.models.models import Usuario, Receivable, BankAccount, Empresa, CaixaSessao, CaixaMovimentacao
from app.services import isp_service
from app.schemas import caixa as schema_caixa
from app.crud import crud_caixa
from app.services.receivable_service import generate_receivables_for_company, generate_receivables_for_company_range, build_boleto_context
from app.services.boleto_generator import generate_boleto_pdf
from app.services.email_service import EmailService
import tempfile
import os
from app.core.config import settings

router = APIRouter(prefix="/receivables", tags=["Receivables"])

class SettlePayload(BaseModel):
    paid_amount: Optional[float] = None
    splits: List[schema_caixa.RecebimentoCaixaSplit]

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

    # Campos de status de desbloqueio para settle response
    unblock_attempted: Optional[bool] = None
    unblock_success: Optional[bool] = None
    unblock_message: Optional[str] = None
    local_pagamento_nome: Optional[str] = None

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



@router.post("/empresa/{empresa_id}/reconcile-bb", status_code=status.HTTP_200_OK)
def reconcile_bb_payments(
    empresa_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """
    Reconcilia pagamentos do Banco do Brasil para boletos selecionados.
    Consulta a API do BB para os boletos informados e atualiza o status no sistema.
    """
    is_admin = current_user.is_superuser or any(
        assoc.empresa_id == empresa_id and assoc.is_admin
        for assoc in current_user.empresas
    )
    if not is_admin:
        raise HTTPException(status_code=403, detail="Apenas administradores podem executar a reconciliação.")

    receivable_ids = payload.get("receivable_ids", [])
    if not receivable_ids:
        return {"checked": 0, "updated": 0, "errors": 0, "message": "Nenhum boleto selecionado para reconciliação."}

    from app.models.models import BankAccount
    from app.services import bb_api_service

    total_checked = 0
    total_updated = 0
    total_errors = 0
    details = []

    # Busca apenas os boletos selecionados (que sejam PENDING ou REGISTERED e do BB)
    receivables = db.query(Receivable).filter(
        Receivable.empresa_id == empresa_id,
        Receivable.id.in_(receivable_ids),
        Receivable.status.in_(['PENDING', 'REGISTERED'])
    ).all()

    if not receivables:
        return {"checked": 0, "updated": 0, "errors": 0, "message": "Nenhum dos boletos selecionados é elegível para reconciliação BB (devem estar Pendentes ou Registrados)."}
        return {"checked": 0, "updated": 0, "errors": 0, "message": "Nenhum boleto BB pendente encontrado."}

    # Agrupa por bank_account_id para reutilizar tokens
    by_bank = {}
    for r in receivables:
        by_bank.setdefault(r.bank_account_id, []).append(r)

    for ba_id, recv_list in by_bank.items():
        bank_account = None
        if ba_id is not None:
            bank_account = db.query(BankAccount).filter_by(id=ba_id).first()

        # Fallback: usa a conta BB padrão da empresa
        if bank_account is None:
            bank_account = db.query(BankAccount).filter(
                BankAccount.empresa_id == empresa_id,
                BankAccount.bank.in_(['BANCO DO BRASIL', 'BB', 'BANCO_DO_BRASIL']),
                BankAccount.bb_client_id != None,
                BankAccount.is_active == True,
            ).first()

        if bank_account is None or not bank_account.bb_client_id:
            total_errors += len(recv_list)
            continue

        convenio_digits = ''.join(filter(str.isdigit, bank_account.convenio or ''))

        def get_bb_numero(r):
            if r.bb_boleto_numero:
                return r.bb_boleto_numero
            seq = ''.join(filter(str.isdigit, r.nosso_numero or ''))
            return '000' + convenio_digits.zfill(7) + seq.zfill(10)

        for r in recv_list:
            total_checked += 1
            bb_numero = get_bb_numero(r)
            try:
                dados = bb_api_service.consultar_boleto(bank_account, bb_numero)
                if dados is None:
                    continue

                codigo_sit = str(dados.get('codigoEstadoTituloCobranca', '') or '').strip()
                new_status = bb_api_service.situacao_para_status(codigo_sit) if codigo_sit else None

                if new_status and new_status != r.status:
                    old_status = r.status
                    r.status = new_status

                    if not r.bb_boleto_numero:
                        r.bb_boleto_numero = bb_numero

                    if new_status == 'PAID':
                        if not r.paid_at:
                            r.paid_at = datetime.now()
                        valor_pago = dados.get('valorPagoSacado') or dados.get('valorPago')
                        if valor_pago is not None:
                            try:
                                r.paid_amount = float(valor_pago)
                            except (ValueError, TypeError):
                                pass
                        if r.servico_contratado_id:
                            try:
                                isp_service.process_unblock_if_needed(db, r.servico_contratado_id)
                            except Exception as e:
                                logger.error(f"Reconcile: erro desbloqueio contrato {r.servico_contratado_id}: {e}")

                    db.add(r)
                    total_updated += 1
                    details.append({"id": r.id, "nosso_numero": r.nosso_numero, "old": old_status, "new": new_status})

            except Exception as e:
                total_errors += 1
                logger.error(f"Reconcile BB: erro no boleto {bb_numero} (ID={r.id}): {e}")

    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Reconcile BB: erro ao salvar no banco")
        raise HTTPException(status_code=500, detail="Erro ao salvar alterações no banco de dados.")

    return {
        "checked": total_checked,
        "updated": total_updated,
        "errors": total_errors,
        "details": details,
        "message": f"Reconciliação concluída: {total_updated} boleto(s) atualizado(s) de {total_checked} verificados.",
    }


@router.post("/empresa/{empresa_id}/generate", status_code=status.HTTP_201_CREATED, response_model=List[ReceivableResponse])
def generate_for_company(
    empresa_id: int,
    target_date: Optional[date] = None,
    start_due_date: Optional[date] = None,
    end_due_date: Optional[date] = None,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    deps.permission_checker('receivables_manage')(db=db, current_user=current_user)
    
    if start_due_date and end_due_date:
        created_receivables = generate_receivables_for_company_range(
            db, empresa_id, start_due_date, end_due_date, cliente_id
        )
    else:
        if target_date is None:
            from datetime import timezone, timedelta
            tz_br = timezone(timedelta(hours=-3))
            target_date = datetime.now(tz_br).date()
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
    items = query.order_by(Receivable.paid_at.desc(), Receivable.due_date.desc())\
        .offset((page - 1) * per_page)\
        .limit(per_page)\
        .all()
    
    from app.models.models import CaixaMovimentacao, CaixaSessao, LocalPagamento
    result = []
    for recv, cliente_nome, cliente_cpf_cnpj in items:
        response = ReceivableResponse.from_orm(recv).dict()
        response['cliente_nome'] = cliente_nome
        response['cliente_cpf_cnpj'] = cliente_cpf_cnpj
        
        if recv.status == 'PAID' and recv.bank == 'CAIXA':
            mov = db.query(CaixaMovimentacao).filter(CaixaMovimentacao.recebimento_caixa_id == recv.id).first()
            if mov:
                sessao = db.query(CaixaSessao).filter(CaixaSessao.id == mov.sessao_id).first()
                if sessao:
                    local = db.query(LocalPagamento).filter(LocalPagamento.id == sessao.local_pagamento_id).first()
                    if local:
                        response['local_pagamento_nome'] = local.nome
                        
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

@router.post("/{receivable_id}/settle", status_code=status.HTTP_200_OK, response_model=ReceivableResponse)
def settle_receivable(receivable_id: int, payload: SettlePayload = Body(...), db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    # 1. Verifica sessão de caixa do usuário
    sessao = crud_caixa.get_sessao_atual(db, current_user.active_empresa_id, current_user.id)
    if not sessao:
        raise HTTPException(status_code=400, detail="Você não possui um caixa aberto. Abra um caixa para receber pagamentos.")

    receivable = db.query(Receivable).filter(Receivable.id == receivable_id).first()
    if not receivable:
        raise HTTPException(status_code=404, detail="Receivable not found")

    deps.permission_checker('receivables_manage')(db=db, current_user=current_user)

    if receivable.status == 'PAID':
        raise HTTPException(status_code=400, detail="Receivable is already paid")

    # 2. Executa a baixa
    receivable.status = 'PAID'
    receivable.paid_amount = payload.paid_amount if payload.paid_amount is not None else receivable.amount
    
    from datetime import timezone, timedelta
    tz_br = timezone(timedelta(hours=-3))
    receivable.paid_at = datetime.now(tz_br)

    # 3. Lançar movimentações no caixa para cada split
    # Como não temos uma tabela de recebimento específica, criamos uma movimentação de "RECEBIMENTO"
    # para cada forma de pagamento do split, e deixamos recebimento_caixa_id como None
    from app.models.models import Cliente
    cliente = db.query(Cliente).filter(Cliente.id == receivable.cliente_id).first()
    cliente_nome = cliente.nome_razao_social if cliente else "Desconhecido"

    for split in payload.splits:
        mov = CaixaMovimentacao(
            sessao_id=sessao.id,
            usuario_id=current_user.id,
            forma_pagamento_id=split.forma_pagamento_id,
            recebimento_caixa_id=receivable.id,
            tipo="RECEBIMENTO",
            valor=split.amount,
            descricao=f"Baixa Manual #{receivable.id} - {cliente_nome}"
        )
        db.add(mov)

    # Se for boleto BB registrado, solicita a baixa (cancelamento) no banco
    if receivable.bank == 'BANCO_DO_BRASIL' and receivable.bb_boleto_numero:
        try:
            from app.services import bb_api_service
            bank_account = db.query(BankAccount).filter(BankAccount.id == receivable.bank_account_id).first()
            if bank_account:
                bb_api_service.solicitar_baixa(bank_account, receivable.bb_boleto_numero)
                logger.info(f"Baixa solicitada no BB para boleto {receivable.bb_boleto_numero} devido a pagamento manual")
        except Exception as e:
            logger.error(f"Erro ao solicitar baixa no BB para boleto {receivable.bb_boleto_numero}: {e}")

    # Se a cobrança estiver vinculada a um contrato ISP, realiza o desbloqueio automático
    unblock_attempted = False
    unblock_success = False
    unblock_message = None

    if receivable.servico_contratado_id:
        unblock_attempted = True
        try:
            # Sincroniza com o router e passa raise_on_error=True para obtermos a resposta precisa
            success = isp_service.process_unblock_if_needed(db, receivable.servico_contratado_id, raise_on_error=True)
            if success:
                unblock_success = True
                unblock_message = f"Contrato #{receivable.servico_contratado_id} reativado com absoluto sucesso no Router/Radius!"
            else:
                from app.models.models import ServicoContratado, StatusContrato
                contrato = db.query(ServicoContratado).filter(ServicoContratado.id == receivable.servico_contratado_id).first()
                if contrato and contrato.status == StatusContrato.ATIVO:
                    unblock_success = True
                    unblock_message = "O contrato associado já estava ativo."
                else:
                    unblock_success = False
                    unblock_message = "O contrato associado não exige desbloqueio no momento."
        except Exception as e:
            unblock_success = False
            unblock_message = f"Falha de comunicação com o Router/Radius: {str(e)}"
            logger.error(f"Erro ao processar desbloqueio automático ISP para contrato {receivable.servico_contratado_id}: {e}")

    db.commit()
    db.refresh(receivable)
    
    response_obj = ReceivableResponse.from_orm(receivable)
    response_obj.unblock_attempted = unblock_attempted
    response_obj.unblock_success = unblock_success
    response_obj.unblock_message = unblock_message
    
    return response_obj

@router.put("/{receivable_id}/refund", response_model=ReceivableResponse)
def refund_receivable(receivable_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    """Estorna um pagamento, alterando o status para PENDING e limpando informações de pagamento."""
    deps.permission_checker('receivables_manage')(db=db, current_user=current_user)
    recv = db.query(Receivable).filter(Receivable.id == receivable_id).first()
    if not recv:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")
    
    # Apenas administradores ou superusuários podem estornar
    is_admin = current_user.is_superuser or any(assoc.empresa_id == recv.empresa_id and assoc.is_admin for assoc in current_user.empresas)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Apenas administradores podem estornar pagamentos.")
    
    if recv.status != 'PAID':
        raise HTTPException(status_code=400, detail="Apenas cobranças pagas podem ser estornadas.")
    
    # Remover movimentações do caixa se foi pago pelo caixa
    from app.models.models import CaixaMovimentacao
    movimentacoes = db.query(CaixaMovimentacao).filter(CaixaMovimentacao.recebimento_caixa_id == recv.id).all()
    for mov in movimentacoes:
        db.delete(mov)

    recv.status = 'PENDING'
    recv.paid_at = None
    recv.paid_amount = None
    
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
        issue_date=datetime.now(),
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
    from app.models.models import Empresa
    from app.core.config import settings
    import os

    context = build_boleto_context(db, recv)
    logo_path = None
    empresa = db.query(Empresa).filter(Empresa.id == recv.empresa_id).first()
    if empresa and empresa.logo_url:
        if empresa.logo_url.startswith("/files/"):
            relative_part = empresa.logo_url[len("/files/"):]
            logo_path = os.path.abspath(os.path.join(settings.UPLOAD_DIR, relative_part))
            if not os.path.exists(logo_path):
                logo_path = None

    pdf_bytes = generate_boleto_pdf(context, logo_path=logo_path)
    
    recv.printed_at = datetime.now()
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
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
    # Carregar empresa raw para pegar senha SMTP descriptografada se necessário pelo serviço
    from app.crud import crud_empresa
    empresa_raw = crud_empresa.get_empresa_raw(db, empresa_id=recv.empresa_id)
    
    pdf_path = None
    try:
        # Se NÃO for Mercado Pago e não tiver link, gerar o PDF do boleto
        if not recv.payment_url:
            logo_path = None
            if empresa and empresa.logo_url:
                if empresa.logo_url.startswith("/files/"):
                    relative_part = empresa.logo_url[len("/files/"):]
                    import os
                    logo_path = os.path.abspath(os.path.join(settings.UPLOAD_DIR, relative_part))
                    if not os.path.exists(logo_path):
                        logo_path = None
            context = build_boleto_context(db, recv)
            pdf_bytes = generate_boleto_pdf(context, logo_path=logo_path)
            
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
                receivable_data=receivable_data,
                pdf_path=pdf_path
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

        recv.sent_at = datetime.now()
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
    """Exclui permanentemente uma cobrança se não estiver paga."""
    deps.permission_checker('receivables_manage')(db=db, current_user=current_user)
    recv = db.query(Receivable).filter(Receivable.id == receivable_id).first()
    if not recv:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")
    
    if recv.status == 'PAID':
        raise HTTPException(status_code=400, detail="Não é possível excluir uma cobrança já paga. Estorne o pagamento primeiro se necessário.")
    
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


class CarnetRequest(BaseModel):
    receivable_ids: List[int]


@router.post("/print-carnet")
def print_carnet_route(req: CarnetRequest, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    """Gera um PDF único com múltiplos boletos (Carnê) e retorna para download."""
    deps.permission_checker('receivables_view')(db=db, current_user=current_user)
    
    if not req.receivable_ids:
        raise HTTPException(status_code=400, detail="Nenhuma cobrança selecionada.")

    receivables = db.query(Receivable).filter(Receivable.id.in_(req.receivable_ids)).all()
    if len(receivables) != len(req.receivable_ids):
        raise HTTPException(status_code=404, detail="Algumas cobranças não foram encontradas.")

    # Validar se todas pertencem à mesma empresa e mesmo cliente
    empresa_id = receivables[0].empresa_id
    cliente_id = receivables[0].cliente_id
    
    for r in receivables:
        if r.empresa_id != empresa_id:
            raise HTTPException(status_code=400, detail="Cobranças pertencem a empresas diferentes.")
        if r.cliente_id != cliente_id:
            raise HTTPException(status_code=400, detail="Cobranças pertencem a clientes diferentes.")
            
    deps.check_empresa_access(db, empresa_id, current_user)
    
    from app.models.models import Empresa
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    
    from app.services.receivable_service import build_boleto_context
    from app.services.boleto_generator import generate_boletos_pdf
    from fastapi.responses import Response
    import os
    
    contexts = []
    for r in receivables:
        contexts.append(build_boleto_context(db, r))
        # Marcar como impresso
        r.printed_at = datetime.now()
        
    db.commit()
        
    logo_path = None
    if empresa and empresa.logo_url and empresa.logo_url.startswith("/files/"):
        relative_part = empresa.logo_url[len("/files/"):]
        from app.core.config import settings
        logo_path = os.path.abspath(os.path.join(settings.UPLOAD_DIR, relative_part))
        if not os.path.exists(logo_path):
            logo_path = None

    pdf_bytes = generate_boletos_pdf(contexts, logo_path=logo_path)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=carne.pdf"}
    )

@router.post("/send-carnet")
def send_carnet_route(req: CarnetRequest, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    """Gera um PDF único com múltiplos boletos (Carnê) e envia por E-mail/WhatsApp."""
    deps.permission_checker('receivables_edit')(db=db, current_user=current_user)
    
    if not req.receivable_ids:
        raise HTTPException(status_code=400, detail="Nenhuma cobrança selecionada.")

    receivables = db.query(Receivable).filter(Receivable.id.in_(req.receivable_ids)).all()
    if len(receivables) != len(req.receivable_ids):
        raise HTTPException(status_code=404, detail="Algumas cobranças não foram encontradas.")

    # Validar se todas pertencem à mesma empresa e mesmo cliente
    empresa_id = receivables[0].empresa_id
    cliente_id = receivables[0].cliente_id
    
    for r in receivables:
        if r.empresa_id != empresa_id:
            raise HTTPException(status_code=400, detail="Cobranças pertencem a empresas diferentes.")
        if r.cliente_id != cliente_id:
            raise HTTPException(status_code=400, detail="Cobranças pertencem a clientes diferentes.")
            
    deps.check_empresa_access(db, empresa_id, current_user)
    
    from app.models.models import Empresa, Cliente
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    
    from app.services.receivable_service import build_boleto_context
    from app.services.boleto_generator import generate_boletos_pdf
    from app.services.email_service import EmailService
    import tempfile
    import os
    
    contexts = []
    amount_total = 0.0
    for r in receivables:
        contexts.append(build_boleto_context(db, r))
        amount_total += float(r.amount)
        
    logo_path = None
    if empresa.logo_url and empresa.logo_url.startswith("/files/"):
        relative_part = empresa.logo_url[len("/files/"):]
        from app.core.config import settings
        l_path = os.path.abspath(os.path.join(settings.UPLOAD_DIR, relative_part))
        if os.path.exists(l_path):
            logo_path = l_path

    pdf_bytes = generate_boletos_pdf(contexts, logo_path=logo_path)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        pdf_path = tmp.name

    send_email = getattr(empresa, "send_method_email", True)
    send_whatsapp = getattr(empresa, "send_method_whatsapp", False)
    
    if not send_email and not send_whatsapp:
        send_email = True

    success_email = False
    success_whatsapp = False
    channels_sent = []

    if send_email:
        if not cliente.email:
            raise HTTPException(status_code=400, detail="Cliente não possui email cadastrado para receber por e-mail")
        success_email = EmailService.send_carnet_email(
            empresa=empresa,
            cliente_email=cliente.email,
            amount_total=amount_total,
            boletos_count=len(receivables),
            pdf_path=pdf_path
        )
        if success_email:
            channels_sent.append("E-mail")

    if send_whatsapp:
        if not cliente.telefone:
            raise HTTPException(status_code=400, detail="Cliente não possui telefone cadastrado para receber por WhatsApp")
        from app.services.whatsapp_service import WhatsAppService
        success_whatsapp = WhatsAppService.send_carnet_message(
            empresa=empresa,
            cliente_nome=cliente.nome_razao_social,
            cliente_phone=cliente.telefone,
            amount_total=amount_total,
            boletos_count=len(receivables),
            pdf_path=pdf_path
        )
        if success_whatsapp:
            channels_sent.append("WhatsApp")

    if (send_email and not success_email) or (send_whatsapp and not success_whatsapp):
        failed_channels = []
        if send_email and not success_email: failed_channels.append("E-mail")
        if send_whatsapp and not success_whatsapp: failed_channels.append("WhatsApp")
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao enviar por: {', '.join(failed_channels)}. Verifique as configurações."
        )

    for r in receivables:
        r.sent_at = datetime.now()
        db.add(r)
    db.commit()

    return {"message": f"Carnê enviado com sucesso via {', '.join(channels_sent)}!"}
