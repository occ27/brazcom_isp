from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import re

from .usuario import UsuarioResponse
from app.core.validators import clean_string, validate_cnpj, validate_inscricao_estadual

# Schemas para Empresa

class EmpresaBase(BaseModel):
    razao_social: str = Field(..., max_length=255)
    nome_fantasia: Optional[str] = Field(None, max_length=255)
    cnpj: str = Field(..., max_length=18)
    inscricao_estadual: Optional[str] = Field(None, max_length=20)
    endereco: str = Field(..., max_length=255)
    numero: str = Field(..., max_length=20)
    complemento: Optional[str] = Field(None, max_length=100)
    bairro: str = Field(..., max_length=100)
    municipio: str = Field(..., max_length=100)
    uf: str = Field(..., max_length=2)
    codigo_ibge: str = Field(..., max_length=7)
    cep: str = Field(..., max_length=9)
    pais: str = Field('BRASIL', max_length=60)
    codigo_pais: str = Field('1058', max_length=4)
    telefone: Optional[str] = Field(None, max_length=20)
    email: str = Field(..., max_length=255)
    regime_tributario: Optional[str] = Field(None, max_length=50)
    cnae_principal: Optional[str] = Field(None, max_length=10)
    
    # Configuração de cobrança: conta bancária padrão (opcional)
    default_bank_account_id: Optional[int] = Field(None, description="ID da conta bancária padrão para cobranças")
    
    # Novos campos
    logo_url: Optional[str] = Field(None, max_length=500)
    # Campos sensíveis (não expostos por padrão nas respostas)
    # NOTA: certificado_path, certificado_senha e smtp_password foram removidos daqui
    # para evitar que apareçam no `EmpresaResponse`. Eles são declarados em
    # `EmpresaCreate` e `EmpresaUpdate` (para entrada/atualização) apenas.

    @validator('razao_social', 'nome_fantasia', 'endereco', 'numero', 'complemento', 'bairro', 'municipio', 'uf', 'cep', 'telefone', 'email', 'regime_tributario', 'pais', 'codigo_pais', pre=True)
    def clean_string_fields(cls, v):
        if isinstance(v, str):
            return clean_string(v)
        return v

    @validator('cnpj', pre=True)
    def validate_and_format_cnpj(cls, v):
        if not v:
            raise ValueError('CNPJ é obrigatório')
        # Limpa espaços primeiro
        v = clean_string(v)
        # Remove formatação para validação
        cnpj_clean = re.sub(r'[^0-9]', '', v)
        if len(cnpj_clean) != 14:
            raise ValueError('CNPJ deve ter 14 dígitos')
        if not validate_cnpj(cnpj_clean):
            raise ValueError('CNPJ inválido')
        return cnpj_clean

    @validator('inscricao_estadual', pre=True)
    def validate_inscricao_estadual_field(cls, v):
        if v:
            v = clean_string(v)
            # Para NFCom, IE pode ser ISENTO ou válido
            if v.upper() == 'ISENTO':
                return v.upper()
            if not validate_inscricao_estadual(v):
                raise ValueError('Inscrição estadual inválida')
        return v

    @validator('cep', pre=True)
    def format_cep(cls, v):
        if v:
            v = clean_string(v)
            cep_clean = re.sub(r'[^0-9]', '', v)
            if len(cep_clean) != 8:
                raise ValueError('CEP deve ter 8 dígitos')
            return cep_clean
        return v

    @validator('uf')
    def validate_uf(cls, v):
        if v:
            v = v.upper()
            ufs_validas = [
                'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
                'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
            ]
            if v not in ufs_validas:
                raise ValueError('UF inválida')
            return v
        return v

    @validator('codigo_ibge')
    def validate_codigo_ibge(cls, v):
        if v:
            if not re.match(r'^\d{7}$', v):
                raise ValueError('Código IBGE deve ter 7 dígitos')
        return v

    @validator('email')
    def validate_email(cls, v):
        if v:
            # Validação básica de email
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
                raise ValueError('Email inválido')
        return v

    @validator('cnae_principal')
    def validate_cnae(cls, v):
        if v:
            # CNAE deve ter 7 dígitos
            cnae_clean = re.sub(r'[^0-9]', '', v)
            if len(cnae_clean) != 7:
                raise ValueError('CNAE deve ter 7 dígitos')
        return v

class EmpresaCreate(EmpresaBase):
    user_id: int = Field(..., description="ID do usuário que cadastrou a empresa")
    # Campos sensíveis necessários apenas para criação/atualização
    certificado_path: Optional[str] = Field(None, max_length=500)
    certificado_senha: Optional[str] = Field(None, max_length=500)
    smtp_server: Optional[str] = Field(None, max_length=255)
    smtp_port: Optional[int] = Field(None, ge=1, le=65535)
    smtp_user: Optional[str] = Field(None, max_length=255)
    smtp_password: Optional[str] = Field(None, max_length=500)
    # Ambiente desejado para transmissão desta empresa. Valores permitidos: 'producao' ou 'homologacao'
    ambiente_nfcom: Optional[str] = Field('producao', max_length=20)

class EmpresaResponse(BaseModel):
    # Campos de EmpresaBase
    razao_social: str = Field(..., max_length=255)
    nome_fantasia: Optional[str] = Field(None, max_length=255)
    cnpj: str = Field(..., max_length=18)
    inscricao_estadual: Optional[str] = Field(None, max_length=20)
    endereco: str = Field(..., max_length=255)
    numero: str = Field(..., max_length=20)
    complemento: Optional[str] = Field(None, max_length=100)
    bairro: str = Field(..., max_length=100)
    municipio: str = Field(..., max_length=100)
    uf: str = Field(..., max_length=2)
    codigo_ibge: str = Field(..., max_length=7)
    cep: str = Field(..., max_length=9)
    pais: str = Field('BRASIL', max_length=60)
    codigo_pais: str = Field('1058', max_length=4)
    telefone: Optional[str] = Field(None, max_length=20)
    email: str = Field(..., max_length=255)
    regime_tributario: Optional[str] = Field(None, max_length=50)
    cnae_principal: Optional[str] = Field(None, max_length=10)
    
    # Configuração de cobrança: conta bancária padrão (opcional)
    default_bank_account_id: Optional[int] = Field(None, description="ID da conta bancária padrão para cobranças")
    
    # Novos campos
    logo_url: Optional[str] = Field(None, max_length=500)
    
    # Campos específicos de EmpresaResponse
    id: int
    ambiente_nfcom: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Campos SMTP (exceto senha por segurança)
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    
    class Config:
        from_attributes = True

# Schema para associação de usuário a empresa

class UsuarioEmpresaBase(BaseModel):
    usuario_id: int
    empresa_id: int
    is_admin: bool = False

class UsuarioEmpresaCreate(UsuarioEmpresaBase):
    pass

class UsuarioEmpresaResponse(BaseModel):
    usuario: UsuarioResponse
    empresa: EmpresaResponse
    is_admin: bool

    class Config:
        from_attributes = True

class EmpresaUpdate(BaseModel):
    razao_social: Optional[str] = Field(None, max_length=255)
    nome_fantasia: Optional[str] = Field(None, max_length=255)
    cnpj: Optional[str] = Field(None, max_length=18)
    inscricao_estadual: Optional[str] = Field(None, max_length=20)
    endereco: Optional[str] = Field(None, max_length=255)
    numero: Optional[str] = Field(None, max_length=20)
    complemento: Optional[str] = Field(None, max_length=100)
    bairro: Optional[str] = Field(None, max_length=100)
    municipio: Optional[str] = Field(None, max_length=100)
    uf: Optional[str] = Field(None, max_length=2)
    codigo_ibge: Optional[str] = Field(None, max_length=7)
    cep: Optional[str] = Field(None, max_length=9)
    pais: Optional[str] = Field(None, max_length=60)
    codigo_pais: Optional[str] = Field(None, max_length=4)
    telefone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    regime_tributario: Optional[str] = Field(None, max_length=50)
    cnae_principal: Optional[str] = Field(None, max_length=10)
    
    # Configuração de cobrança: conta bancária padrão (opcional)
    default_bank_account_id: Optional[int] = Field(None, description="ID da conta bancária padrão para cobranças")
    
    # Novos campos
    logo_url: Optional[str] = Field(None, max_length=500)
    certificado_path: Optional[str] = Field(None, max_length=500)
    certificado_senha: Optional[str] = Field(None, max_length=500)
    smtp_server: Optional[str] = Field(None, max_length=255)
    smtp_port: Optional[int] = Field(None, ge=1, le=65535)
    smtp_user: Optional[str] = Field(None, max_length=255)
    smtp_password: Optional[str] = Field(None, max_length=500)
    
    is_active: Optional[bool] = None
    ambiente_nfcom: Optional[str] = Field(None, max_length=20)

    @validator('razao_social', 'nome_fantasia', 'endereco', 'numero', 'complemento', 'bairro', 'municipio', 'uf', 'cep', 'telefone', 'email', 'regime_tributario', 'pais', 'codigo_pais', pre=True)
    def clean_string_fields(cls, v):
        if isinstance(v, str):
            return clean_string(v)
        return v

    @validator('cnpj', pre=True)
    def validate_and_format_cnpj(cls, v):
        if v:
            # Limpa espaços primeiro
            v = clean_string(v)
            # Remove formatação para validação
            cnpj_clean = re.sub(r'[^0-9]', '', v)
            if len(cnpj_clean) != 14:
                raise ValueError('CNPJ deve ter 14 dígitos')
            if not validate_cnpj(cnpj_clean):
                raise ValueError('CNPJ inválido')
            return cnpj_clean
        return v

    @validator('inscricao_estadual', pre=True)
    def validate_inscricao_estadual_field(cls, v):
        if v:
            v = clean_string(v)
            # Para NFCom, IE pode ser ISENTO ou válido
            if v.upper() == 'ISENTO':
                return v.upper()
            if not validate_inscricao_estadual(v):
                raise ValueError('Inscrição estadual inválida')
        return v

    @validator('cep', pre=True)
    def format_cep(cls, v):
        if v:
            v = clean_string(v)
            cep_clean = re.sub(r'[^0-9]', '', v)
            if len(cep_clean) != 8:
                raise ValueError('CEP deve ter 8 dígitos')
            return cep_clean
        return v

    @validator('uf')
    def validate_uf(cls, v):
        if v:
            v = v.upper()
            ufs_validas = [
                'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
                'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
            ]
            if v not in ufs_validas:
                raise ValueError('UF inválida')
            return v
        return v

    @validator('codigo_ibge')
    def validate_codigo_ibge(cls, v):
        if v:
            if not re.match(r'^\d{7}$', v):
                raise ValueError('Código IBGE deve ter 7 dígitos')
        return v

    @validator('email')
    def validate_email(cls, v):
        if v:
            # Validação básica de email
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
                raise ValueError('Email inválido')
        return v

    @validator('cnae_principal')
    def validate_cnae(cls, v):
        if v:
            # CNAE deve ter 7 dígitos
            cnae_clean = re.sub(r'[^0-9]', '', v)
            if len(cnae_clean) != 7:
                raise ValueError('CNAE deve ter 7 dígitos')
        return v


    @validator('ambiente_nfcom')
    def validate_ambiente_nfcom(cls, v):
        if v is None:
            return v
        if v not in ('producao', 'homologacao'):
            raise ValueError("'ambiente_nfcom' deve ser 'producao' ou 'homologacao'")
        return v


# Schema de entrada usado pela API (não exige `user_id` no body). O servidor
# irá atribuir `user_id` com base no usuário autenticado (quando aplicável).
class EmpresaIn(EmpresaBase):
    certificado_path: Optional[str] = Field(None, max_length=500)
    certificado_senha: Optional[str] = Field(None, max_length=500)
    smtp_server: Optional[str] = Field(None, max_length=255)
    smtp_port: Optional[int] = Field(None, ge=1, le=65535)
    smtp_user: Optional[str] = Field(None, max_length=255)
    smtp_password: Optional[str] = Field(None, max_length=500)
    ambiente_nfcom: Optional[str] = Field('producao', max_length=20)

# Schema para teste SMTP com credenciais não salvas
class SMTPTest(BaseModel):
    smtp_server: str
    smtp_port: int
    smtp_user: str
    smtp_password: str

# Schema para associação de usuário a empresa

class UsuarioEmpresaBase(BaseModel):
    usuario_id: int
    empresa_id: int
    is_admin: bool = False

class UsuarioEmpresaCreate(UsuarioEmpresaBase):
    pass

class UsuarioEmpresaResponse(BaseModel):
    usuario: UsuarioResponse
    empresa: EmpresaResponse
    is_admin: bool

    class Config:
        from_attributes = True