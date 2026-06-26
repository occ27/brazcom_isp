from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime, date

from app.core.database import get_db
from app.routes.auth import get_current_active_user
from app.api import deps
from app.models.models import BankAccount
from app.models.models import Usuario
from app.core.security import encrypt_sensitive_data, decrypt_sensitive_data
from app.models.access_control import Permission

router = APIRouter(prefix="/empresas/{empresa_id}/bank-accounts", tags=["Bank Accounts"])


class BankAccountResponse(BaseModel):
    id: int
    empresa_id: int
    name: Optional[str] = None
    bank: str
    codigo_banco: Optional[str] = None
    agencia: Optional[str] = None
    agencia_dv: Optional[str] = None
    conta: Optional[str] = None
    conta_dv: Optional[str] = None
    titular: Optional[str] = None
    cpf_cnpj_titular: Optional[str] = None
    carteira: Optional[str] = None
    carteira_variacao: Optional[str] = None
    convenio: Optional[str] = None
    cnab_version: Optional[str] = None
    instrucao1: Optional[str] = None
    instrucao2: Optional[str] = None
    dias_protesto: Optional[int] = 0
    dias_baixa: Optional[int] = 0
    nosso_numero_sequence: Optional[int] = None
    remittance_config: Optional[str] = None
    instructions: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = True
    gateway_credentials: Optional[str] = None
    sicoob_client_id: Optional[str] = None
    sicoob_access_token: Optional[str] = None
    sicredi_codigo_beneficiario: Optional[str] = None
    sicredi_posto: Optional[str] = None
    sicredi_byte_id: Optional[str] = None
    bb_client_id: Optional[str] = None
    bb_app_key: Optional[str] = None
    bb_sandbox: Optional[bool] = True
    multa_atraso_percentual: Optional[float] = None
    juros_atraso_percentual: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BankAccountCreate(BaseModel):
    name: Optional[str] = None
    bank: str
    codigo_banco: Optional[str] = None
    agencia: Optional[str] = None
    agencia_dv: Optional[str] = None
    conta: Optional[str] = None
    conta_dv: Optional[str] = None
    titular: Optional[str] = None
    cpf_cnpj_titular: Optional[str] = None
    carteira: Optional[str] = None
    carteira_variacao: Optional[str] = None
    convenio: Optional[str] = None
    cnab_version: Optional[str] = "240"
    instrucao1: Optional[str] = None
    instrucao2: Optional[str] = None
    dias_protesto: Optional[int] = 0
    dias_baixa: Optional[int] = 0
    remittance_config: Optional[str] = None
    instructions: Optional[str] = None
    is_default: Optional[bool] = False
    is_active: Optional[bool] = True
    gateway_credentials: Optional[str] = None
    sicoob_client_id: Optional[str] = None
    sicoob_access_token: Optional[str] = None
    sicredi_codigo_beneficiario: Optional[str] = None
    sicredi_posto: Optional[str] = Field(None, description="Posto de atendimento SICREDI (AA)")
    sicredi_byte_id: Optional[str] = Field(None, description="Byte de identificação SICREDI")
    bb_client_id: Optional[str] = None
    bb_client_secret: Optional[str] = None
    bb_app_key: Optional[str] = None
    bb_sandbox: Optional[bool] = True
    multa_atraso_percentual: Optional[float] = Field(2.0, ge=0, le=100, description="Percentual de multa por atraso (%)")
    juros_atraso_percentual: Optional[float] = Field(1.0, ge=0, le=100, description="Percentual de juros por dia de atraso (%)")


class BankAccountUpdate(BaseModel):
    name: Optional[str] = None
    bank: Optional[str] = None
    codigo_banco: Optional[str] = None
    agencia: Optional[str] = None
    agencia_dv: Optional[str] = None
    conta: Optional[str] = None
    conta_dv: Optional[str] = None
    titular: Optional[str] = None
    cpf_cnpj_titular: Optional[str] = None
    carteira: Optional[str] = None
    carteira_variacao: Optional[str] = None
    convenio: Optional[str] = None
    cnab_version: Optional[str] = None
    instrucao1: Optional[str] = None
    instrucao2: Optional[str] = None
    dias_protesto: Optional[int] = None
    dias_baixa: Optional[int] = None
    remittance_config: Optional[str] = None
    instructions: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    gateway_credentials: Optional[str] = None
    sicoob_client_id: Optional[str] = None
    sicoob_access_token: Optional[str] = None
    sicredi_codigo_beneficiario: Optional[str] = None
    sicredi_posto: Optional[str] = Field(None, description="Posto de atendimento SICREDI (AA)")
    sicredi_byte_id: Optional[str] = Field(None, description="Byte de identificação SICREDI")
    bb_client_id: Optional[str] = None
    bb_client_secret: Optional[str] = None
    bb_app_key: Optional[str] = None
    bb_sandbox: Optional[bool] = None
    multa_atraso_percentual: Optional[float] = Field(None, ge=0, le=100, description="Percentual de multa por atraso (%)")
    juros_atraso_percentual: Optional[float] = Field(None, ge=0, le=100, description="Percentual de juros por dia de atraso (%)")


def _serialize(bank_account: BankAccount, include_credentials: bool = False):
    out = {
        'id': bank_account.id,
        'empresa_id': bank_account.empresa_id,
        'name': bank_account.name,
        'bank': bank_account.bank,
        'codigo_banco': bank_account.codigo_banco,
        'agencia': bank_account.agencia,
        'agencia_dv': bank_account.agencia_dv,
        'conta': bank_account.conta,
        'conta_dv': bank_account.conta_dv,
        'titular': bank_account.titular,
        'cpf_cnpj_titular': bank_account.cpf_cnpj_titular,
        'carteira': bank_account.carteira,
        'carteira_variacao': bank_account.carteira_variacao,
        'convenio': bank_account.convenio,
        'cnab_version': bank_account.cnab_version,
        'instrucao1': bank_account.instrucao1,
        'instrucao2': bank_account.instrucao2,
        'dias_protesto': bank_account.dias_protesto,
        'dias_baixa': bank_account.dias_baixa,
        'nosso_numero_sequence': bank_account.nosso_numero_sequence,
        'remittance_config': bank_account.remittance_config,
        'instructions': bank_account.instructions,
        'is_default': bank_account.is_default,
        'is_active': bank_account.is_active,
        'multa_atraso_percentual': bank_account.multa_atraso_percentual,
        'juros_atraso_percentual': bank_account.juros_atraso_percentual,
        'created_at': bank_account.created_at,
        'updated_at': bank_account.updated_at,
        
        # Campos de identificação não sensíveis (sempre visíveis no get/list para quem pode ver a conta)
        'sicoob_client_id': bank_account.sicoob_client_id,
        'sicredi_codigo_beneficiario': bank_account.sicredi_codigo_beneficiario,
        'sicredi_posto': bank_account.sicredi_posto,
        'sicredi_byte_id': bank_account.sicredi_byte_id,
        'bb_client_id': bank_account.bb_client_id,
        'bb_app_key': bank_account.bb_app_key,
        'bb_sandbox': bank_account.bb_sandbox,
    }
    
    # Apenas retornar secrets decriptados se include_credentials for True (o que agora só acontece no endpoint de credentials)
    if include_credentials:
        try:
            out['gateway_credentials'] = decrypt_sensitive_data(bank_account.gateway_credentials) if bank_account.gateway_credentials else None
        except Exception:
            out['gateway_credentials'] = None
            
        try:
            out['bb_client_secret'] = decrypt_sensitive_data(bank_account.bb_client_secret) if bank_account.bb_client_secret else None
        except Exception:
            out['bb_client_secret'] = None
            
        out['sicoob_access_token'] = bank_account.sicoob_access_token
    else:
        out['gateway_credentials'] = None
        out['bb_client_secret'] = None
        out['sicoob_access_token'] = None
        
    return out


@router.get('/metadata/banks')
def list_supported_banks():
    return [
        {"code": "756", "name": "SICOOB"},
        {"code": "748", "name": "SICREDI"},
        {"code": "001", "name": "BANCO DO BRASIL"},
    ]


@router.post('/init-permissions', status_code=status.HTTP_201_CREATED)
def init_permissions(empresa_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    # Apenas superuser pode inicializar permissões (ou usuários com permission_manage)
    if not getattr(current_user, 'is_superuser', False):
        deps.permission_checker('permission_manage')(db=db, current_user=current_user)
    # Cria permissões se não existirem
    perms = ['bank_accounts_view', 'bank_accounts_manage', 'receivables_view', 'receivables_manage']
    created = []
    for p in perms:
        exists = db.query(Permission).filter(Permission.name == p).first()
        if not exists:
            perm = Permission(name=p, description=f'Permissão para {p}')
            db.add(perm)
            created.append(p)
    if created:
        db.commit()
    return {'created': created}


CREDENTIALS_FIELDS = {
    'gateway_credentials', 'sicoob_client_id', 'sicoob_access_token',
    'sicredi_codigo_beneficiario', 'sicredi_posto', 'sicredi_byte_id',
    'bb_client_id', 'bb_client_secret', 'bb_app_key', 'bb_sandbox'
}

class BankAccountCredentialsUpdate(BaseModel):
    gateway_credentials: Optional[str] = None
    sicoob_client_id: Optional[str] = None
    sicoob_access_token: Optional[str] = None
    sicredi_codigo_beneficiario: Optional[str] = None
    sicredi_posto: Optional[str] = None
    sicredi_byte_id: Optional[str] = None
    bb_client_id: Optional[str] = None
    bb_client_secret: Optional[str] = None
    bb_app_key: Optional[str] = None
    bb_sandbox: Optional[bool] = None


@router.get('/', response_model=List[BankAccountResponse])
def list_bank_accounts(empresa_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    # Checa se usuário tem permissão de visualização
    deps.permission_checker('bank_accounts_view')(db=db, current_user=current_user)
    items = db.query(BankAccount).filter(BankAccount.empresa_id == empresa_id).all()
    serialized = [_serialize(i, include_credentials=False) for i in items]
    return serialized
@router.post('/', status_code=status.HTTP_201_CREATED)
def create_bank_account(empresa_id: int, payload: BankAccountCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    deps.permission_checker('bank_accounts_manage')(db=db, current_user=current_user)
    ba = BankAccount(
        empresa_id=empresa_id,
        name=payload.name,
        bank=payload.bank,
        codigo_banco=payload.codigo_banco,
        agencia=payload.agencia,
        agencia_dv=payload.agencia_dv,
        conta=payload.conta,
        conta_dv=payload.conta_dv,
        titular=payload.titular,
        cpf_cnpj_titular=payload.cpf_cnpj_titular,
        carteira=payload.carteira,
        carteira_variacao=payload.carteira_variacao,
        convenio=payload.convenio,
        cnab_version=payload.cnab_version,
        instrucao1=payload.instrucao1,
        instrucao2=payload.instrucao2,
        dias_protesto=payload.dias_protesto,
        dias_baixa=payload.dias_baixa,
        remittance_config=payload.remittance_config,
        instructions=payload.instructions,
        is_default=payload.is_default,
        is_active=payload.is_active,
        multa_atraso_percentual=payload.multa_atraso_percentual,
        juros_atraso_percentual=payload.juros_atraso_percentual,
    )
    
    # Adiciona credenciais não sensíveis
    ba.sicoob_client_id = payload.sicoob_client_id
    ba.sicredi_codigo_beneficiario = payload.sicredi_codigo_beneficiario
    ba.sicredi_posto = payload.sicredi_posto
    ba.sicredi_byte_id = payload.sicredi_byte_id
    ba.bb_client_id = payload.bb_client_id
    ba.bb_app_key = payload.bb_app_key
    ba.bb_sandbox = payload.bb_sandbox
    
    # Apenas criptografa e salva segredos se forem enviados e não-vazios
    if payload.gateway_credentials and payload.gateway_credentials.strip() != "":
        ba.gateway_credentials = encrypt_sensitive_data(payload.gateway_credentials)
    if payload.bb_client_secret and payload.bb_client_secret.strip() != "":
        ba.bb_client_secret = encrypt_sensitive_data(payload.bb_client_secret)
    if payload.sicoob_access_token and payload.sicoob_access_token.strip() != "":
        ba.sicoob_access_token = payload.sicoob_access_token
        
    db.add(ba)
    db.commit()
    db.refresh(ba)
    return _serialize(ba, include_credentials=False)


@router.put('/{bank_account_id}', status_code=status.HTTP_200_OK)
def update_bank_account(empresa_id: int, bank_account_id: int, payload: BankAccountUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    deps.permission_checker('bank_accounts_manage')(db=db, current_user=current_user)
    ba = db.query(BankAccount).filter(BankAccount.id == bank_account_id, BankAccount.empresa_id == empresa_id).first()
    if not ba:
        raise HTTPException(status_code=404, detail='Bank account not found')
    
    update_data = payload.dict(exclude_unset=True)
    for field, val in update_data.items():
        if field in ['gateway_credentials', 'bb_client_secret']:
            # Só atualiza se o valor enviado não for vazio/nulo (para não sobrescrever o DB com os campos ocultados no frontend)
            if val is not None and str(val).strip() != "":
                setattr(ba, field, encrypt_sensitive_data(val))
        elif field == 'sicoob_access_token':
            # Só atualiza se preenchido
            if val is not None and str(val).strip() != "":
                setattr(ba, field, val)
        else:
            setattr(ba, field, val)
            
    ba.updated_at = datetime.now()
    db.commit()
    db.refresh(ba)
    return _serialize(ba, include_credentials=False)


@router.get('/{bank_account_id}/credentials')
def get_bank_account_credentials(empresa_id: int, bank_account_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(deps.get_current_superuser)):
    """Retorna as credenciais de uma conta bancária de forma segura/descriptografada (apenas para superadministradores/acesso interno)."""
    ba = db.query(BankAccount).filter(BankAccount.id == bank_account_id, BankAccount.empresa_id == empresa_id).first()
    if not ba:
        raise HTTPException(status_code=404, detail='Conta bancária não encontrada')
    
    try:
        gateway_creds = decrypt_sensitive_data(ba.gateway_credentials) if ba.gateway_credentials else None
    except Exception:
        gateway_creds = None

    try:
        bb_secret = decrypt_sensitive_data(ba.bb_client_secret) if ba.bb_client_secret else None
    except Exception:
        bb_secret = None

    return {
        'gateway_credentials': gateway_creds,
        'sicoob_client_id': ba.sicoob_client_id,
        'sicoob_access_token': ba.sicoob_access_token,
        'sicredi_codigo_beneficiario': ba.sicredi_codigo_beneficiario,
        'sicredi_posto': ba.sicredi_posto,
        'sicredi_byte_id': ba.sicredi_byte_id,
        'bb_client_id': ba.bb_client_id,
        'bb_app_key': ba.bb_app_key,
        'bb_sandbox': ba.bb_sandbox,
        'bb_client_secret': bb_secret,
    }


@router.put('/{bank_account_id}/credentials', status_code=status.HTTP_200_OK)
def update_bank_account_credentials(empresa_id: int, bank_account_id: int, payload: BankAccountCredentialsUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(deps.get_current_superuser)):
    """Atualiza as credenciais de uma conta bancária de forma segura (apenas para superadministradores/acesso interno)."""
    ba = db.query(BankAccount).filter(BankAccount.id == bank_account_id, BankAccount.empresa_id == empresa_id).first()
    if not ba:
        raise HTTPException(status_code=404, detail='Conta bancária não encontrada')
    
    update_data = payload.dict(exclude_unset=True)
    for field, val in update_data.items():
        if field in ['gateway_credentials', 'bb_client_secret']:
            # Se for enviado String vazia ou None, limpa a credencial no DB
            setattr(ba, field, encrypt_sensitive_data(val) if val else None)
        else:
            setattr(ba, field, val)
            
    ba.updated_at = datetime.now()
    db.commit()
    db.refresh(ba)
    return {'ok': True}


@router.get('/{bank_account_id}/boletos')
def list_boletos(
    empresa_id: int, 
    bank_account_id: int, 
    status: Optional[str] = None, 
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    date_type: str = "due_date",
    page: int = 1, 
    per_page: int = 25, 
    db: Session = Depends(get_db), 
    current_user: Usuario = Depends(get_current_active_user)
):
    deps.permission_checker('receivables_view')(db=db, current_user=current_user)
    from app.models.models import Receivable, Cliente
    
    query = db.query(Receivable, Cliente.nome_razao_social, Cliente.cpf_cnpj)\
        .join(Cliente, Receivable.cliente_id == Cliente.id)\
        .filter(Receivable.empresa_id == empresa_id, Receivable.bank_account_id == bank_account_id)\
        .filter(Receivable.tipo != 'MERCADO_PAGO')
    
    if status:
        query = query.filter(Receivable.status == status)
        
    filter_field = Receivable.issue_date if date_type == "issue_date" else Receivable.due_date
    
    if start_date:
        query = query.filter(filter_field >= start_date)
    if end_date:
        query = query.filter(filter_field <= end_date)
        
    total = query.count()
    items = query.order_by(Receivable.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    from app.routes.receivables import ReceivableResponse
    result = []
    for recv, cliente_nome, cliente_cpf_cnpj in items:
        response = ReceivableResponse.from_orm(recv)
        response.cliente_nome = cliente_nome
        response.cliente_cpf_cnpj = cliente_cpf_cnpj
        result.append(response)
        
    return {"data": result, "total": total}


@router.post('/{bank_account_id}/generate-boletos')
def generate_boletos(
    empresa_id: int,
    bank_account_id: int,
    receivable_ids: List[int],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Marca boletos para registro ou gera nosso número dependendo do banco."""
    deps.permission_checker('receivables_manage')(db=db, current_user=current_user)
    from app.models.models import Receivable
    from app.services.billing_service import BillingService
    import asyncio
    
    receivables = db.query(Receivable).filter(
        Receivable.id.in_(receivable_ids),
        Receivable.empresa_id == empresa_id
    ).all()
    
    results = []
    for r in receivables:
        r.bank_account_id = bank_account_id
        # Para Sicredi, o BillingService._register_sicredi apenas marca como pendente de remessa
        # Para Sicoob, ele tenta registrar via API
        # Como register_receivable_with_bank é assíncrono, precisamos rodar com loop
        try:
            # Simplificando para marcar apenas
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(BillingService.register_receivable_with_bank(db, r))
            loop.close()
            results.append({"id": r.id, "success": success})
        except Exception as e:
            results.append({"id": r.id, "success": False, "error": str(e)})
            
    db.commit()
    return {"results": results}


@router.post('/{bank_account_id}/generate-sicredi-remittance', status_code=status.HTTP_200_OK)
def generate_sicredi_remittance(
    empresa_id: int, 
    bank_account_id: int, 
    receivable_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db), 
    current_user: Usuario = Depends(get_current_active_user)
):
    deps.permission_checker('bank_accounts_manage')(db=db, current_user=current_user)
    from app.services.billing_service import BillingService
    
    ba = db.query(BankAccount).filter(BankAccount.id == bank_account_id, BankAccount.empresa_id == empresa_id).first()
    if not ba:
        raise HTTPException(status_code=404, detail='Conta bancária não encontrada')
    
    if ba.bank != "SICREDI":
        raise HTTPException(status_code=400, detail=f'Esta operação é apenas para contas SICREDI.')
    
    filepath = BillingService.generate_sicredi_remittance_file(db=db, empresa_id=empresa_id, bank_account_id=bank_account_id, receivable_ids=receivable_ids)
    if not filepath:
        raise HTTPException(status_code=400, detail='Não foi possível gerar o arquivo de remessa.')
    
    return {
        'status': 'success',
        'message': 'Arquivo de remessa SICREDI gerado com sucesso',
        'filepath': filepath,
        'download_url': f'/uploads/remessas/{filepath.split("/")[-1]}'
    }


@router.delete('/{bank_account_id}', status_code=status.HTTP_200_OK)
def delete_bank_account(empresa_id: int, bank_account_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    deps.permission_checker('bank_accounts_manage')(db=db, current_user=current_user)
    ba = db.query(BankAccount).filter(BankAccount.id == bank_account_id, BankAccount.empresa_id == empresa_id).first()
    if not ba:
        raise HTTPException(status_code=404, detail='Bank account not found')
    db.delete(ba)
    db.commit()
    return {'ok': True}

@router.post('/{bank_account_id}/retorno')
async def upload_retorno(
    empresa_id: int,
    bank_account_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    deps.permission_checker('receivables_manage')(db=db, current_user=current_user)
    # Aqui viria a lógica de processamento do arquivo de retorno
    # Por enquanto, apenas simulamos o sucesso
    filename = file.filename
    content = await file.read()
    
    # TODO: Implementar parser de CNAB 240/400 retorno
    
    return {
        "status": "success",
        "message": f"Arquivo {filename} recebido com sucesso. O processamento automático de retorno será implementado em breve.",
        "processed_count": 0
    }
@router.post('/{bank_account_id}/register-boletos-api')
async def register_boletos_api(
    empresa_id: int,
    bank_account_id: int,
    receivable_ids: List[int],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Registra boletos na API do Banco do Brasil."""
    deps.permission_checker('receivables_manage')(db=db, current_user=current_user)
    from app.models.models import Receivable
    from app.services.billing_service import BillingService
    
    ba = db.query(BankAccount).filter(BankAccount.id == bank_account_id, BankAccount.empresa_id == empresa_id).first()
    if not ba:
        raise HTTPException(status_code=404, detail='Conta bancária não encontrada')
        
    receivables = db.query(Receivable).filter(
        Receivable.id.in_(receivable_ids),
        Receivable.empresa_id == empresa_id
    ).all()
    
    results = []
    for r in receivables:
        try:
            success, error_msg = await BillingService._register_bb(db, r, ba)
            results.append({"id": r.id, "ok": success, "error": None if success else error_msg})
        except Exception as e:
            results.append({"id": r.id, "ok": False, "error": str(e)})
            
    return {"results": results}


@router.delete('/{bank_account_id}/boletos/{receivable_id}/api')
async def cancel_boleto_api(
    empresa_id: int,
    bank_account_id: int,
    receivable_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Solicita a baixa/cancelamento do boleto na API do Banco do Brasil."""
    deps.permission_checker('receivables_manage')(db=db, current_user=current_user)
    from app.models.models import Receivable
    from app.services.bb_api_service import solicitar_baixa
    
    ba = db.query(BankAccount).filter(BankAccount.id == bank_account_id, BankAccount.empresa_id == empresa_id).first()
    if not ba:
        raise HTTPException(status_code=404, detail='Conta bancária não encontrada')
        
    recv = db.query(Receivable).filter(Receivable.id == receivable_id, Receivable.empresa_id == empresa_id).first()
    if not recv:
        raise HTTPException(status_code=404, detail='Boleto não encontrado')
        
    bb_numero = recv.bb_boleto_numero or recv.nosso_numero
    if not bb_numero:
        raise HTTPException(status_code=400, detail='Boleto não possui número de registro para baixa')
        
    try:
        success = solicitar_baixa(ba, bb_numero)
        if success:
            recv.status = "CANCELLED"
            db.commit()
            return {"ok": True}
        else:
            raise HTTPException(status_code=400, detail='Falha ao solicitar baixa na API BB')
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
