from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import date, datetime
from enum import Enum
import re


class StatusContrato(str, Enum):
    ATIVO = "ATIVO"
    SUSPENSO = "SUSPENSO"
    CANCELADO = "CANCELADO"
    PENDENTE_INSTALACAO = "PENDENTE_INSTALACAO"


class TipoConexao(str, Enum):
    FIBRA = "FIBRA"
    RADIO = "RADIO"
    CABO = "CABO"
    SATELITE = "SATELITE"
    ADSL = "ADSL"
    OUTRO = "OUTRO"


class MetodoAutenticacao(str, Enum):
    IP_MAC = "IP_MAC"
    PPPOE = "PPPOE"
    HOTSPOT = "HOTSPOT"
    RADIUS = "RADIUS"


class ServicoContratadoBase(BaseModel):
    empresa_id: Optional[int] = None
    cliente_id: int
    servico_id: int

    numero_contrato: Optional[str] = Field(None, max_length=50)
    d_contrato_ini: Optional[date] = None
    d_contrato_fim: Optional[date] = None

    # Status do contrato (específico para ISPs)
    status: Optional[StatusContrato] = Field(StatusContrato.PENDENTE_INSTALACAO, description="Status: ATIVO, SUSPENSO, CANCELADO, PENDENTE_INSTALACAO")

    # Informações de instalação (específicas para ISPs)
    endereco_instalacao: str = Field(..., max_length=500, description="Endereço onde o serviço é instalado")
    tipo_conexao: TipoConexao = Field(..., description="Tipo: FIBRA, RADIO, CABO, SATELITE, ADSL, OUTRO")
    coordenadas_gps: Optional[str] = Field(None, max_length=50, description="Coordenadas GPS: latitude,longitude")
    data_instalacao: Optional[date] = None
    responsavel_tecnico: str = Field(..., max_length=100, description="Nome do técnico responsável pela instalação")

    # Dia do mês de vencimento do serviço/contrato (opcional). Preferido para geração de faturas.
    dia_vencimento: Optional[int] = Field(None, ge=1, le=31, description="Dia do mês para vencimento (1-31)")

    periodicidade: Optional[str] = Field('MENSAL', max_length=20, description="Periodicidade: MENSAL, BIMESTRAL, TRIMESTRAL, SEMESTRAL, ANUAL")
    dia_emissao: int = Field(..., ge=1, le=31, description="Dia do mês para emissão (1-31)")
    quantidade: Optional[float] = 1.0
    valor_unitario: float
    valor_total: Optional[float] = None

    # Campos de cobrança adicionais
    periodo_carencia: Optional[int] = Field(0, ge=0, description="Dias de carência após vencimento")
    multa_atraso_percentual: Optional[float] = Field(0.0, ge=0, le=100, description="Percentual de multa por atraso (%)")

    # Taxas adicionais
    taxa_instalacao: Optional[float] = Field(0.0, ge=0, description="Taxa única de instalação")
    taxa_instalacao_paga: Optional[bool] = Field(False, description="Se a taxa de instalação já foi cobrada")

    # SLA e qualidade (específicos para ISPs)
    sla_garantido: Optional[float] = Field(None, ge=0, le=100, description="SLA garantido em % (ex: 99.9)")
    velocidade_garantida: Optional[str] = Field(None, max_length=50, description="Velocidade garantida (ex: '10M/10M')")

    auto_emit: Optional[bool] = True
    is_active: Optional[bool] = True

    # Relacionamento com subscription ativa
    subscription_id: Optional[int] = None

    # Configuração de rede (provisionamento automático)
    router_id: Optional[int] = None
    interface_id: Optional[int] = None
    ip_class_id: Optional[int] = None
    mac_address: Optional[str] = Field(None, max_length=17, description="Endereço MAC do dispositivo do cliente")
    assigned_ip: Optional[str] = Field(None, max_length=15, description="IP atribuído automaticamente")
    metodo_autenticacao: Optional[MetodoAutenticacao] = Field(None, description="Método de autenticação para o serviço")


class ServicoContratadoCreate(ServicoContratadoBase):
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
            # Convert to uppercase first
            v = v.upper()
            # Check if MAC address is in format AA:BB:CC:DD:EE:FF
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


class ServicoContratadoUpdate(BaseModel):
    cliente_id: Optional[int] = None
    servico_id: Optional[int] = None
    numero_contrato: Optional[str] = Field(None, max_length=50)
    d_contrato_ini: Optional[date] = None
    d_contrato_fim: Optional[date] = None

    # Status do contrato
    status: Optional[StatusContrato] = None

    # Informações de instalação
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

    # Campos de cobrança adicionais
    periodo_carencia: Optional[int] = Field(None, ge=0)
    multa_atraso_percentual: Optional[float] = Field(None, ge=0, le=100)

    # Taxas adicionais
    taxa_instalacao: Optional[float] = Field(None, ge=0)
    taxa_instalacao_paga: Optional[bool] = None

    # SLA e qualidade
    sla_garantido: Optional[float] = Field(None, ge=0, le=100)
    velocidade_garantida: Optional[str] = Field(None, max_length=50)

    auto_emit: Optional[bool] = None
    is_active: Optional[bool] = None

    # Relacionamento com subscription ativa
    subscription_id: Optional[int] = None

    # Configuração de rede (provisionamento automático)
    router_id: Optional[int] = None
    interface_id: Optional[int] = None
    ip_class_id: Optional[int] = None
    mac_address: Optional[str] = Field(None, max_length=17)
    assigned_ip: Optional[str] = Field(None, max_length=15)
    metodo_autenticacao: Optional[MetodoAutenticacao] = Field(None, description="Método de autenticação para o serviço")

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
            # Convert to uppercase first
            v = v.upper()
            # Check if MAC address is in format AA:BB:CC:DD:EE:FF
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


class ServicoContratadoResponse(ServicoContratadoBase):
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    # Related data
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

    class Config:
        from_attributes = True
