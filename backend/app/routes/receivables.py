from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.routes.auth import get_current_active_user
from app.api import deps
from app.models.models import Usuario
from app.services.receivable_service import generate_monthly_receivables_for_company
from app.models.models import Receivable

router = APIRouter(prefix="/receivables", tags=["Receivables"])

class ReceivableResponse(BaseModel):
    id: int
    empresa_id: int
    cliente_id: int
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
    bank_account_id: Optional[int] = None
    bank_account_snapshot: Optional[str] = None
    bank_payload: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

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
        return cls(**data)


@router.post("/empresa/{empresa_id}/generate", status_code=status.HTTP_201_CREATED, response_model=List[ReceivableResponse])
def generate_for_company(empresa_id: int, target_date: date = None, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    deps.permission_checker('receivables_manage')(db=db, current_user=current_user)
    if target_date is None:
        target_date = date.today()
    # permission checks could be added here (empresa ownership)
    created_receivables = generate_monthly_receivables_for_company(db, empresa_id, target_date)
    # Converte os objetos Receivable para ReceivableResponse usando o método customizado
    return [ReceivableResponse.from_orm(r) for r in created_receivables]


@router.post("/empresa/{empresa_id}/test-sicoob", status_code=status.HTTP_200_OK)
async def test_sicoob_integration(empresa_id: int, bank_account_id: Optional[int] = None, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
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


@router.get("/empresa/{empresa_id}", response_model=List[ReceivableResponse])
def list_receivables(empresa_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    deps.permission_checker('receivables_view')(db=db, current_user=current_user)
    items = db.query(Receivable).filter(Receivable.empresa_id == empresa_id).offset(skip).limit(limit).all()
    return [ReceivableResponse.from_orm(r) for r in items]
