from pydantic import BaseModel, Field, validator, model_validator
from typing import Optional, List
from datetime import datetime
import re

from .empresa import EmpresaResponse
from app.models.models import TipoPessoa, IndicadorIEDest

# Schemas para Endereço do Cliente (EmpresaClienteEndereco)

class ClienteEnderecoBase(BaseModel):
    descricao: Optional[str] = Field(None, max_length=100)
    endereco: str = Field(..., max_length=255)
    numero: str = Field(..., max_length=20)
    complemento: Optional[str] = Field(None, max_length=100)
    bairro: str = Field(..., max_length=100)
    municipio: str = Field(..., max_length=100)
    uf: str = Field(..., max_length=2)
    cep: str = Field(..., max_length=9)
    codigo_ibge: Optional[str] = Field(None, max_length=7)
    is_principal: bool = True

    def format_cep(cls, v):
        if v:
            cep_clean = re.sub(r'[^0-9]', '', v)
            if len(cep_clean) != 8:
                raise ValueError('CEP deve ter 8 dígitos')
            return cep_clean
        return v

    def validate_codigo_ibge(cls, v, values):
        if v:
            from app.core.validators import validate_codigo_ibge
            uf = values.get('uf')
            if uf and not validate_codigo_ibge(v, uf):
                raise ValueError('Código IBGE inválido ou incompatível com a UF')
        return v

# Schemas para Cliente

class ClienteBase(BaseModel):
    nome_razao_social: str = Field(..., max_length=255)
    cpf_cnpj: str = Field(..., max_length=18)
    tipo_pessoa: TipoPessoa
    ind_ie_dest: IndicadorIEDest = Field(..., description="Indicador de Inscrição Estadual do Destinatário")
    inscricao_estadual: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    telefone: Optional[str] = Field(None, max_length=20)
    # Campos de autenticação
    password_hash: Optional[str] = Field(None, description="Hash da senha para autenticação no portal")
    reset_token: Optional[str] = Field(None, description="Token para reset de senha")
    reset_token_expires: Optional[datetime] = Field(None, description="Data de expiração do token de reset")
    email_verified: Optional[bool] = Field(False, description="Se o email foi verificado")
    last_login: Optional[datetime] = Field(None, description="Último login do cliente")

    def format_cpf_cnpj(cls, v):
        if v:
            cpf_cnpj_clean = re.sub(r'[^0-9]', '', v)
            return cpf_cnpj_clean
        return v

class ClienteCreate(ClienteBase):
    enderecos: List[ClienteEnderecoBase] = []
    # Campos opcionais para criação com senha
    password: Optional[str] = Field(None, min_length=6, description="Senha para autenticação no portal")

    def clean_and_upper_name(cls, v):
        """Remover espaços duplos, strip e converter nome/razão social para maiúsculas."""
        if isinstance(v, str):
            from app.core.validators import clean_string
            cleaned = clean_string(v)
            return cleaned.upper()
        return v

    def clean_string_fields(cls, v):
        if isinstance(v, str):
            from app.core.validators import clean_string
            return clean_string(v)
        return v

    def validate_and_format_telefone(cls, v):
        """Remove caracteres não numéricos e valida comprimento mínimo para telefone."""
        if not v:
            return v
        import re
        telefone_clean = re.sub(r'[^0-9]', '', v)
        if len(telefone_clean) < 8:
            raise ValueError('Telefone inválido')
        return telefone_clean

    def validate_cpf_cnpj(cls, v):
        if not v:
            raise ValueError('CPF/CNPJ é obrigatório')
        from app.core.validators import clean_string
        v = clean_string(v)
        cpf_cnpj_clean = re.sub(r'[^0-9]', '', v)

        if len(cpf_cnpj_clean) not in [11, 14]:
            raise ValueError('CPF deve ter 11 dígitos ou CNPJ deve ter 14 dígitos')

        if len(cpf_cnpj_clean) == 11:
            if not cls._validate_cpf(cpf_cnpj_clean):
                raise ValueError('CPF inválido')
        elif len(cpf_cnpj_clean) == 14:
            from app.core.validators import validate_cnpj
            if not validate_cnpj(cpf_cnpj_clean):
                raise ValueError('CNPJ inválido')

        return cpf_cnpj_clean

    def validate_tipo_pessoa(cls, v, values):
        cpf_cnpj = values.get('cpf_cnpj')
        if cpf_cnpj:
            cpf_cnpj_clean = re.sub(r'[^0-9]', '', cpf_cnpj)
            if len(cpf_cnpj_clean) == 11 and v != TipoPessoa.FISICA:
                raise ValueError('Para CPF, tipo pessoa deve ser Física')
            elif len(cpf_cnpj_clean) == 14 and v != TipoPessoa.JURIDICA:
                raise ValueError('Para CNPJ, tipo pessoa deve ser Jurídica')
        return v

    def check_inscricao_estadual_logic(cls, v, values):
        """Valida a Inscrição Estadual com base no Indicador de IE (ind_ie_dest)."""
        ind_ie = values.get('ind_ie_dest')
        uf = None
        
        # Pega a UF do primeiro endereço para validar a regra do 'ISENTO'
        enderecos = values.get('enderecos')
        if enderecos and len(enderecos) > 0:
            first = enderecos[0]
            try:
                uf = first.uf if hasattr(first, 'uf') else first.get('uf')
            except Exception:
                uf = None

        # Regra G27: Não Contribuinte
        if ind_ie == IndicadorIEDest.NAO_CONTRIBUINTE:
            if v:
                raise ValueError("Inscrição Estadual não deve ser preenchida para 'Não Contribuinte'.")
            return None

        # Regra G26: Contribuinte Isento
        if ind_ie == IndicadorIEDest.CONTRIBUINTE_ISENTO:
            if not v or v.upper() != 'ISENTO':
                raise ValueError("Inscrição Estadual deve ser 'ISENTO' para 'Contribuinte Isento'.")
            
            from app.core.validators import validate_inscricao_estadual
            if not validate_inscricao_estadual(v, uf):
                 raise ValueError(f"A UF '{uf}' não permite Inscrição Estadual 'ISENTO'.")
            return 'ISENTO'

        # Regra G25: Contribuinte ICMS
        if ind_ie == IndicadorIEDest.CONTRIBUINTE_ICMS:
            if not v or v.upper() == 'ISENTO':
                raise ValueError("Inscrição Estadual é obrigatória e não pode ser 'ISENTO' para 'Contribuinte ICMS'.")
            
            from app.core.validators import validate_inscricao_estadual
            if not validate_inscricao_estadual(v, uf):
                raise ValueError(f"Inscrição Estadual '{v}' inválida para a UF '{uf}'.")
            return v
        
        return v

    def validate_email(cls, v):
        if v:
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
                raise ValueError('Email inválido')
        return v

    def validate_enderecos(cls, v, values):
        """Para NFCom, pessoa jurídica deve ter pelo menos um endereço completo"""
        tipo_pessoa = values.get('tipo_pessoa')
        if tipo_pessoa == TipoPessoa.JURIDICA and len(v) == 0:
            raise ValueError('Pessoa jurídica deve ter pelo menos um endereço cadastrado')
        
        from app.core.validators import validate_codigo_ibge
        for addr in v:
            try:
                codigo = addr.codigo_ibge if hasattr(addr, 'codigo_ibge') else addr.get('codigo_ibge')
                uf = addr.uf if hasattr(addr, 'uf') else addr.get('uf')
            except Exception:
                codigo = None
                uf = None
            
            if codigo and uf:
                if not validate_codigo_ibge(codigo, uf):
                    raise ValueError(f"Código IBGE '{codigo}' inválido para a UF '{uf}' em um dos endereços.")
        return v

    def _validate_cpf(cpf):
        """Validação básica de CPF"""
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            return False
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        resto = (soma * 10) % 11
        if resto == 10: resto = 0
        if resto != int(cpf[9]): return False
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        resto = (soma * 10) % 11
        if resto == 10: resto = 0
        if resto != int(cpf[10]): return False
        return True

class ClienteUpdate(BaseModel):
    nome_razao_social: Optional[str] = Field(None, max_length=255)
    cpf_cnpj: Optional[str] = Field(None, max_length=18)
    tipo_pessoa: Optional[TipoPessoa] = None
    ind_ie_dest: Optional[IndicadorIEDest] = None
    inscricao_estadual: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    telefone: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    # Campos de autenticação opcionais para update
    password: Optional[str] = Field(None, min_length=6, description="Nova senha para autenticação no portal")
    email_verified: Optional[bool] = Field(None, description="Se o email foi verificado")

    def clean_string_fields(cls, v):
        if isinstance(v, str):
            from app.core.validators import clean_string
            return clean_string(v)
        return v

    def validate_email(cls, v):
        if v:
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
                raise ValueError('Email inválido')
        return v

# NEW Schemas for the "new model"
class EmpresaClienteEnderecoResponse(ClienteEnderecoBase):
    id: int
    class Config:
        from_attributes = True

class EmpresaClienteResponse(BaseModel):
    id: int
    empresa_id: int
    enderecos: List[EmpresaClienteEnderecoResponse] = []
    class Config:
        from_attributes = True


class ClienteResponse(ClienteBase):
    id: int
    empresa_id: int
    ind_ie_dest: str  # Alterado de IndicadorIEDest para str para evitar problemas de serialização
    is_active: Optional[bool] = True  # Opcional para suportar clientes sem esse campo
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # This will be populated from the legacy relationship, but we will overwrite it
    enderecos: List[EmpresaClienteEnderecoResponse] = []
    
    # This will be populated from the NEW relationship and then used by the validator
    empresa_associations: List[EmpresaClienteResponse] = Field([])

    @validator('ind_ie_dest', pre=True)
    def convert_ind_ie_dest_to_value(cls, v):
        if hasattr(v, 'value'):
            return v.value
        return str(v)

    @model_validator(mode='after')
    def use_new_address_model_if_available(self):
        # Use new address model if available, otherwise use legacy addresses
        if self.enderecos:
            return self

        # Otherwise, populate from the new association model
        all_enderecos = []
        for assoc in self.empresa_associations:
            all_enderecos.extend(assoc.enderecos)
        self.enderecos = all_enderecos
        return self

    class Config:
        from_attributes = True


class ClienteListResponse(BaseModel):
    total: int
    clientes: List[ClienteResponse]

    class Config:
        from_attributes = True


# Schema para autocomplete de clientes
class ClienteAutocomplete(BaseModel):
    id: int
    nome_razao_social: str
    cpf_cnpj: Optional[str] = None
    idOutros: Optional[str] = None
    tipo_pessoa: TipoPessoa
    email: Optional[str] = None
    telefone: Optional[str] = None

    class Config:
        from_attributes = True


# Schemas para autenticação de clientes no portal

class ClienteLogin(BaseModel):
    cpf_cnpj: str = Field(..., description="CPF ou CNPJ do cliente")
    password: str = Field(..., description="Senha do cliente")
    empresa_id: Optional[int] = Field(None, description="ID da empresa (opcional se houver apenas uma)")

class ClienteAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    cliente: dict  # Dados básicos do cliente
    empresa: dict  # Dados básicos da empresa

class ClienteForgotPassword(BaseModel):
    cpf_cnpj: str = Field(..., description="CPF ou CNPJ do cliente")
    email: str = Field(..., description="Email do cliente para validação")
    empresa_id: Optional[int] = Field(None, description="ID da empresa")

class ClienteResetPassword(BaseModel):
    cpf_cnpj: str = Field(..., description="CPF ou CNPJ do cliente")
    reset_code: str = Field(..., description="Código de reset enviado por email")
    new_password: str = Field(..., min_length=6, description="Nova senha")
    empresa_id: Optional[int] = Field(None, description="ID da empresa")

class ClienteSetPassword(BaseModel):
    password: str = Field(..., min_length=6, description="Nova senha")
    confirm_password: str = Field(..., min_length=6, description="Confirmação da senha")

    @model_validator(mode='after')
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError('As senhas não coincidem')
        return self