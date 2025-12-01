from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.routes.auth import get_current_active_user
from app.models.models import Usuario
from app.services.receivable_service import generate_monthly_receivables_for_company
from app.models.models import Receivable

router = APIRouter(prefix="/receivables", tags=["Receivables"])

class ReceivableResponse(BaseModel):
    id: int
    empresa_id: int
    cliente_id: int
    servico_contratado_id: int = None
    nfcom_fatura_id: int = None
    tipo: str
    issue_date: str
    due_date: str
    amount: float
    discount: float = 0.0
    interest_percent: float = 0.0
    fine_percent: float = 0.0
    bank: str
    carteira: str = None
    agencia: str = None
    conta: str = None
    nosso_numero: str = None
    bank_registration_id: str = None
    codigo_barras: str = None
    linha_digitavel: str = None
    status: str
    registered_at: str = None
    printed_at: str = None
    sent_at: str = None
    paid_at: str = None
    registro_result: str = None
    pdf_url: str = None
    bank_account_id: int = None
    bank_account_snapshot: str = None
    bank_payload: str = None
    created_at: datetime
    updated_at: datetime = None

    class Config:
        from_attributes = True


@router.post("/empresa/{empresa_id}/generate", status_code=status.HTTP_201_CREATED, response_model=List[ReceivableResponse])
def generate_for_company(empresa_id: int, target_date: date = None, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    if target_date is None:
        target_date = date.today()
    # permission checks could be added here (empresa ownership)
    created = generate_monthly_receivables_for_company(db, empresa_id, target_date)
    return created


@router.post("/empresa/{empresa_id}/test-sicoob", status_code=status.HTTP_200_OK)
async def test_sicoob_integration(empresa_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    """
    Endpoint de teste para integração com Sicoob.
    Registra um boleto de teste no ambiente sandbox.
    """
    try:
        from app.services.sicoob_gateway import SicoobGateway
        from app.models.models import BankAccount

        # Buscar conta SICOB da empresa
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

        # Dados de teste para o sandbox
        test_boleto = {
            "numeroContrato": "123456",
            "modalidade": 1,
            "numeroContaCorrente": "123456789",
            "especieDocumento": "DM",
            "dataEmissao": "2025-11-30",
            "dataVencimento": "2025-12-15",
            "valor": 100.00,
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
            "multa": 2.0,
            "juros": 1.0,
            "desconto": 0.0
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
    # TODO: add permission checks
    items = db.query(Receivable).filter(Receivable.empresa_id == empresa_id).offset(skip).limit(limit).all()
    return items
