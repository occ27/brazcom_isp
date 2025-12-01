from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

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
    bank: str
    codigo_banco: Optional[str] = None
    agencia: Optional[str] = None
    agencia_dv: Optional[str] = None
    conta: Optional[str] = None
    conta_dv: Optional[str] = None
    titular: Optional[str] = None
    cpf_cnpj_titular: Optional[str] = None
    carteira: Optional[str] = None
    convenio: Optional[str] = None
    nosso_numero_sequence: Optional[int] = None
    remittance_config: Optional[str] = None
    instructions: Optional[str] = None
    is_default: Optional[bool] = None
    gateway_credentials: Optional[str] = None
    sicoob_client_id: Optional[str] = None
    sicoob_access_token: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BankAccountCreate(BaseModel):
    bank: str
    codigo_banco: Optional[str] = None
    agencia: Optional[str] = None
    agencia_dv: Optional[str] = None
    conta: Optional[str] = None
    conta_dv: Optional[str] = None
    titular: Optional[str] = None
    cpf_cnpj_titular: Optional[str] = None
    carteira: Optional[str] = None
    convenio: Optional[str] = None
    remittance_config: Optional[str] = None
    instructions: Optional[str] = None
    is_default: Optional[bool] = False
    gateway_credentials: Optional[str] = None
    sicoob_client_id: Optional[str] = None
    sicoob_access_token: Optional[str] = None


class BankAccountUpdate(BaseModel):
    bank: Optional[str] = None
    codigo_banco: Optional[str] = None
    agencia: Optional[str] = None
    agencia_dv: Optional[str] = None
    conta: Optional[str] = None
    conta_dv: Optional[str] = None
    titular: Optional[str] = None
    cpf_cnpj_titular: Optional[str] = None
    carteira: Optional[str] = None
    convenio: Optional[str] = None
    remittance_config: Optional[str] = None
    instructions: Optional[str] = None
    is_default: Optional[bool] = None
    gateway_credentials: Optional[str] = None
    sicoob_client_id: Optional[str] = None
    sicoob_access_token: Optional[str] = None


def _serialize(bank_account: BankAccount, include_credentials: bool = False):
    out = {
        'id': bank_account.id,
        'empresa_id': bank_account.empresa_id,
        'bank': bank_account.bank,
        'codigo_banco': bank_account.codigo_banco,
        'agencia': bank_account.agencia,
        'agencia_dv': bank_account.agencia_dv,
        'conta': bank_account.conta,
        'conta_dv': bank_account.conta_dv,
        'titular': bank_account.titular,
        'cpf_cnpj_titular': bank_account.cpf_cnpj_titular,
        'carteira': bank_account.carteira,
        'convenio': bank_account.convenio,
        'nosso_numero_sequence': bank_account.nosso_numero_sequence,
        'remittance_config': bank_account.remittance_config,
        'instructions': bank_account.instructions,
        'is_default': bank_account.is_default,
        'created_at': bank_account.created_at,
        'updated_at': bank_account.updated_at,
    }
    if include_credentials and bank_account.gateway_credentials:
        try:
            out['gateway_credentials'] = decrypt_sensitive_data(bank_account.gateway_credentials)
        except Exception:
            out['gateway_credentials'] = None
    else:
        out['gateway_credentials'] = None
    
    # Sempre incluir credenciais do Sicoob quando solicitadas
    if include_credentials:
        out['sicoob_client_id'] = bank_account.sicoob_client_id
        out['sicoob_access_token'] = bank_account.sicoob_access_token
    else:
        out['sicoob_client_id'] = None
        out['sicoob_access_token'] = None
    
    return out


@router.post('/init-permissions', status_code=status.HTTP_201_CREATED)
def init_permissions(empresa_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    # Apenas superuser pode inicializar permissões (ou usuários com permission_manage)
    if not getattr(current_user, 'is_superuser', False):
        deps.permission_checker('permission_manage')(db=db, current_user=current_user)
    # Cria permissões se não existirem
    perms = ['billing_view', 'billing_manage']
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


@router.get('/', response_model=List[BankAccountResponse])
def list_bank_accounts(empresa_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    # Checa se usuário tem permissão de visualização
    deps.permission_checker('billing_view')(db=db, current_user=current_user)
    items = db.query(BankAccount).filter(BankAccount.empresa_id == empresa_id).all()
    serialized = [_serialize(i, include_credentials=getattr(current_user, 'is_superuser', False)) for i in items]
    return serialized


@router.post('/', status_code=status.HTTP_201_CREATED)
def create_bank_account(empresa_id: int, payload: BankAccountCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    deps.permission_checker('billing_manage')(db=db, current_user=current_user)
    ba = BankAccount(
        empresa_id=empresa_id,
        bank=payload.bank,
        codigo_banco=payload.codigo_banco,
        agencia=payload.agencia,
        agencia_dv=payload.agencia_dv,
        conta=payload.conta,
        conta_dv=payload.conta_dv,
        titular=payload.titular,
        cpf_cnpj_titular=payload.cpf_cnpj_titular,
        carteira=payload.carteira,
        convenio=payload.convenio,
        remittance_config=payload.remittance_config,
        instructions=payload.instructions,
        is_default=payload.is_default,
    )
    if payload.gateway_credentials:
        ba.gateway_credentials = encrypt_sensitive_data(payload.gateway_credentials)
    
    # Credenciais do Sicoob (não criptografadas pois são tokens de API)
    ba.sicoob_client_id = payload.sicoob_client_id
    ba.sicoob_access_token = payload.sicoob_access_token
    
    db.add(ba)
    db.commit()
    db.refresh(ba)
    return _serialize(ba, include_credentials=getattr(current_user, 'is_superuser', False))


@router.put('/{bank_account_id}', status_code=status.HTTP_200_OK)
def update_bank_account(empresa_id: int, bank_account_id: int, payload: BankAccountUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    deps.permission_checker('billing_manage')(db=db, current_user=current_user)
    ba = db.query(BankAccount).filter(BankAccount.id == bank_account_id, BankAccount.empresa_id == empresa_id).first()
    if not ba:
        raise HTTPException(status_code=404, detail='Bank account not found')
    for field in payload.__fields__:
        val = getattr(payload, field)
        if val is None:
            continue
        if field == 'gateway_credentials':
            ba.gateway_credentials = encrypt_sensitive_data(val)
        elif field in ['sicoob_client_id', 'sicoob_access_token']:
            # Campos do Sicoob não são criptografados
            setattr(ba, field, val)
        else:
            setattr(ba, field, val)
    ba.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ba)
    return _serialize(ba, include_credentials=getattr(current_user, 'is_superuser', False))


@router.delete('/{bank_account_id}', status_code=status.HTTP_200_OK)
def delete_bank_account(empresa_id: int, bank_account_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    deps.permission_checker('billing_manage')(db=db, current_user=current_user)
    ba = db.query(BankAccount).filter(BankAccount.id == bank_account_id, BankAccount.empresa_id == empresa_id).first()
    if not ba:
        raise HTTPException(status_code=404, detail='Bank account not found')
    db.delete(ba)
    db.commit()
    return {'status': 'ok'}
