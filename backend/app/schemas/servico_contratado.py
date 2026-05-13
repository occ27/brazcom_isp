from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from datetime import date, datetime
from enum import Enum
import re
from app.models.models import StatusContrato, TipoConexao, MetodoAutenticacao

class ServicoContratadoBase(BaseModel):
    cliente_id: int
    servico_id: int
    numero_contrato: Optional[str] = Field(None, max_length=50)
    d_contrato_ini: Optional[date] = None
    d_contrato_fim: Optional[date] = None
    status: StatusContrato = StatusContrato.PENDENTE_INSTALACAO
    
    # Informações de instalação
    endereco_instalacao: Optional[str] = Field(None, max_length=500)
    tipo_conexao: Optional[TipoConexao] = None
    coordenadas_gps: Optional[str] = Field(None, max_length=50)
    data_instalacao: Optional[date] = None
    responsavel_tecnico: Optional[str] = Field(None, max_length=100)
    
    # Detalhes de faturamento
    dia_vencimento: Optional[int] = Field(None, ge=1, le=31, description="Dia do mês para vencimento (1-31)")
    periodicidade: str = Field("MENSAL", max_length=20)
    dia_emissao: int = Field(..., ge=1, le=31)
    quantidade: float = Field(1.0, gt=0)
    valor_unitario: float = Field(..., gt=0)
    valor_total: Optional[float] = None
    
    # Controles de faturamento e carência
    periodo_carencia: int = Field(0, ge=0)
    multa_atraso_percentual: float = Field(0.0, ge=0, le=100)
    
    # Relacionamento com conta bancária para cobrança
    bank_account_id: Optional[int] = Field(None, description="ID da conta bancária para cobrança deste contrato")

    # Taxas adicionais
    taxa_instalacao: float = Field(0.0, ge=0)
    taxa_instalacao_paga: bool = False
    
    # SLA e qualidade
    sla_garantido: Optional[float] = Field(None, ge=0, le=100)
    velocidade_garantida: Optional[str] = Field(None, max_length=50)

    auto_emit: bool = True
    is_active: bool = True
    
    # Relacionamento com subscription ativa
    subscription_id: Optional[int] = None

    # Configuração de rede (provisionamento automático)
    router_id: Optional[int] = None
    interface_id: Optional[int] = None
    ip_class_id: Optional[int] = None
    mac_address: Optional[str] = Field(None, max_length=17)
    assigned_ip: Optional[str] = Field(None, max_length=45)
    metodo_autenticacao: Optional[MetodoAutenticacao] = Field(None, description="Método de autenticação para o serviço")

    # Campos específicos para autenticação PPPoE
    pppoe_username: Optional[str] = Field(None, max_length=50, description="Username PPPoE do cliente")
    pppoe_password: Optional[str] = Field(None, max_length=50, description="Password PPPoE do cliente")

    # Documentação Jurídica
    contrato_anatel_url: Optional[str] = Field(None, max_length=500)
    
    # Método de pagamento preferencial
    payment_method: str = Field("BOLETO", max_length=30)

class ServicoContratadoCreate(ServicoContratadoBase):
    empresa_id: Optional[int] = None
    
    @field_validator('interface_id', mode='after')
    @classmethod
    def validate_interface_if_router(cls, v, info):
        if info.data.get('router_id') is not None and v is None:
            raise ValueError('interface_id é obrigatório quando router_id é preenchido')
        return v

    @field_validator('ip_class_id', mode='after')
    @classmethod
    def validate_ip_class_if_router(cls, v, info):
        if info.data.get('router_id') is not None and v is None:
            raise ValueError('ip_class_id é obrigatório quando router_id é preenchido')
        return v

    @field_validator('mac_address')
    @classmethod
    def validate_mac_format(cls, v):
        if v and v != '':
            v = v.upper()
            mac_pattern = r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$'
            if not re.match(mac_pattern, v):
                raise ValueError('mac_address deve estar no formato AA:BB:CC:DD:EE:FF')
        return v

    @field_validator('mac_address', mode='after')
    @classmethod
    def validate_mac_if_router(cls, v, info):
        if info.data.get('router_id') is not None and info.data.get('metodo_autenticacao') == 'IP_MAC':
            if v is None or v == '':
                raise ValueError('mac_address é obrigatório quando router_id é preenchido e método é IP_MAC')
        return v

    @field_validator('assigned_ip', mode='after')
    @classmethod
    def validate_assigned_ip_if_router(cls, v, info):
        if info.data.get('router_id') is not None and info.data.get('metodo_autenticacao') == 'IP_MAC':
            if v is None or v == '':
                raise ValueError('assigned_ip é obrigatório quando router_id é preenchido e método é IP_MAC')
        return v

    @model_validator(mode='after')
    def validate_router_requirements(self):
        if self.router_id is not None and self.metodo_autenticacao == 'IP_MAC':
            if not self.mac_address or self.mac_address == '':
                raise ValueError('mac_address é obrigatório quando router_id é preenchido e método é IP_MAC')
            if not self.assigned_ip or self.assigned_ip == '':
                raise ValueError('assigned_ip é obrigatório quando router_id é preenchido e método é IP_MAC')
        return self

    # Ativos vinculados
    ativos: Optional[List['AtivoContratoCreate']] = None

class ServicoContratadoUpdate(BaseModel):
    cliente_id: Optional[int] = None
    servico_id: Optional[int] = None
    numero_contrato: Optional[str] = Field(None, max_length=50)
    d_contrato_ini: Optional[date] = None
    d_contrato_fim: Optional[date] = None
    status: Optional[StatusContrato] = None
    endereco_instalacao: Optional[str] = Field(None, max_length=500)
    tipo_conexao: Optional[TipoConexao] = None
    coordenadas_gps: Optional[str] = Field(None, max_length=50)
    data_instalacao: Optional[date] = None
    responsavel_tecnico: Optional[str] = Field(None, max_length=100)
    dia_vencimento: Optional[int] = Field(None, ge=1, le=31)
    periodicidade: Optional[str] = Field(None, max_length=20)
    dia_emissao: Optional[int] = Field(None, ge=1, le=31)
    quantidade: Optional[float] = None
    valor_unitario: Optional[float] = None
    valor_total: Optional[float] = None
    periodo_carencia: Optional[int] = Field(None, ge=0)
    multa_atraso_percentual: Optional[float] = Field(None, ge=0, le=100)
    bank_account_id: Optional[int] = Field(None)
    taxa_instalacao: Optional[float] = Field(None, ge=0)
    taxa_instalacao_paga: Optional[bool] = None
    sla_garantido: Optional[float] = Field(None, ge=0, le=100)
    velocidade_garantida: Optional[str] = Field(None, max_length=50)
    auto_emit: Optional[bool] = None
    is_active: Optional[bool] = None
    subscription_id: Optional[int] = None
    router_id: Optional[int] = None
    interface_id: Optional[int] = None
    ip_class_id: Optional[int] = None
    mac_address: Optional[str] = Field(None, max_length=17)
    assigned_ip: Optional[str] = Field(None, max_length=45)
    metodo_autenticacao: Optional[MetodoAutenticacao] = None
    pppoe_username: Optional[str] = Field(None, max_length=50)
    pppoe_password: Optional[str] = Field(None, max_length=50)
    contrato_anatel_url: Optional[str] = Field(None, max_length=500)
    payment_method: Optional[str] = Field(None, max_length=30)
    
    # Ativos vinculados
    ativos: Optional[List['AtivoContratoCreate']] = None

    @field_validator('interface_id', mode='after')
    @classmethod
    def validate_interface_if_router(cls, v, info):
        if info.data.get('router_id') is not None and v is None:
            raise ValueError('interface_id é obrigatório quando router_id é preenchido')
        return v

    @field_validator('ip_class_id', mode='after')
    @classmethod
    def validate_ip_class_if_router(cls, v, info):
        if info.data.get('router_id') is not None and v is None:
            raise ValueError('ip_class_id é obrigatório quando router_id é preenchido')
        return v

    @field_validator('mac_address')
    @classmethod
    def validate_mac_format(cls, v):
        if v and v != '':
            v = v.upper()
            mac_pattern = r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$'
            if not re.match(mac_pattern, v):
                raise ValueError('mac_address deve estar no formato AA:BB:CC:DD:EE:FF')
        return v

class AtivoContratoBase(BaseModel):
    tipo_equipamento: str = Field(..., max_length=50)
    modelo: Optional[str] = Field(None, max_length=100)
    patrimonio: Optional[str] = Field(None, max_length=50)
    serial_number: Optional[str] = Field(None, max_length=100)
    login_acesso: Optional[str] = Field(None, max_length=100)
    senha_acesso: Optional[str] = Field(None, max_length=100)
    is_comodato: bool = True
    observacoes: Optional[str] = None

class AtivoContratoCreate(AtivoContratoBase):
    pass

class AtivoContratoUpdate(AtivoContratoBase):
    tipo_equipamento: Optional[str] = Field(None, max_length=50)

class AtivoContratoResponse(AtivoContratoBase):
    id: int
    contrato_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class ServicoContratadoResponse(ServicoContratadoBase):
    id: int
    empresa_id: int
    last_emission: Optional[datetime] = None
    next_emission: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime]
    created_by_user_id: Optional[int] = None
    
    cliente_nome: Optional[str] = None
    cliente_razao_social: Optional[str] = None
    cliente_cpf_cnpj: Optional[str] = None
    cliente_telefone: Optional[str] = None
    cliente_inscricao_estadual: Optional[str] = None
    cliente_endereco: Optional[str] = None
    cliente_numero: Optional[str] = None
    cliente_bairro: Optional[str] = None
    cliente_municipio: Optional[str] = None
    cliente_uf: Optional[str] = None
    servico_descricao: Optional[str] = None
    servico_codigo: Optional[str] = None
    
    bank_account_id: Optional[int] = None
    bank_account_bank: Optional[str] = None
    bank_account_agencia: Optional[str] = None
    bank_account_conta: Optional[str] = None

    ativos: List[AtivoContratoResponse] = []

    class Config:
        from_attributes = True
