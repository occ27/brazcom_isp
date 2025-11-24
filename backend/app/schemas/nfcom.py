from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import date, datetime, timezone, timedelta

from app.models.models import FinalidadeEmissao, TipoFaturamento, TipoEmissao
from .cliente import ClienteResponse

# Schemas for NFComItem

class NFComItemBase(BaseModel):
    cClass: str = Field(..., max_length=7, description="Código de Classificação do Item")
    servico_id: Optional[int] = None
    codigo_servico: str = Field(..., max_length=60, description="Código do produto ou serviço")
    descricao_servico: str = Field(..., max_length=120, description="Descrição do produto ou serviço")
    quantidade: float = Field(..., gt=0)
    unidade_medida: str = Field(..., max_length=10)
    valor_unitario: float = Field(..., gt=0)
    valor_desconto: float = Field(0, ge=0)
    valor_outros: float = Field(0, ge=0)
    cfop: Optional[str] = Field(None, max_length=4, description="Código Fiscal de Operações e Prestações")
    ncm: Optional[str] = Field(None, max_length=8, description="Nomenclatura Comum do Mercosul")
    base_calculo_icms: Optional[float] = Field(None, ge=0, description="Base de cálculo do ICMS")
    aliquota_icms: Optional[float] = Field(None, ge=0, description="Alíquota do ICMS")
    # Adicionando campos de PIS/COFINS
    base_calculo_pis: Optional[float] = Field(None, ge=0, description="Base de cálculo do PIS")
    aliquota_pis: Optional[float] = Field(None, ge=0, description="Alíquota do PIS")
    base_calculo_cofins: Optional[float] = Field(None, ge=0, description="Base de cálculo do COFINS")
    aliquota_cofins: Optional[float] = Field(None, ge=0, description="Alíquota do COFINS")

class NFComItemCreate(NFComItemBase):
    pass


class NFComFaturaBase(BaseModel):
    numero_fatura: str
    data_vencimento: date
    valor_fatura: float
    codigo_barras: Optional[str] = None


class NFComFaturaCreate(NFComFaturaBase):
    pass


class NFComFaturaResponse(NFComFaturaBase):
    id: int

    class Config:
        from_attributes = True

class NFComItemResponse(NFComItemBase):
    id: int
    valor_total: float
    valor_icms: Optional[float] = None

    class Config:
        from_attributes = True

# Schemas for NFCom

class NFComBase(BaseModel):
    cliente_id: int
    cMunFG: str = Field(..., max_length=7, description="Código do Município de Ocorrência do Fato Gerador")
    finalidade_emissao: FinalidadeEmissao
    tpFat: TipoFaturamento
    data_emissao: datetime
    valor_total: float = Field(..., ge=0)
    informacoes_adicionais: Optional[str] = None

    @validator('data_emissao', pre=True, always=True)
    def combine_date_with_current_time(cls, v):
        """
        Combina a data recebida do frontend com a hora atual e fuso horário -03:00
        para criar um objeto datetime completo, conforme exigido pela SEFAZ.
        """
        if isinstance(v, str):
            v = date.fromisoformat(v)
        
        # Pega a hora atual com fuso horário
        now_with_tz = datetime.now(timezone(timedelta(hours=-3)))
        # Combina a data do formulário com a hora atual, mas sem os microssegundos
        full_datetime = datetime.combine(v, now_with_tz.time()).replace(microsecond=0)
        # Reatribui o fuso horário correto
        return full_datetime.replace(tzinfo=now_with_tz.tzinfo)

class NFComCreate(NFComBase):
    itens: List[NFComItemCreate]
    faturas: Optional[List[NFComFaturaCreate]] = None

    # Endereço do destinatário (snapshot no momento da emissão)
    dest_endereco: str
    dest_numero: str
    dest_complemento: Optional[str] = None
    dest_bairro: str
    dest_municipio: str
    dest_uf: str
    dest_cep: str
    dest_codigo_ibge: str
    # Campos de contrato (requeridos dependendo de tpFat)
    numero_contrato: Optional[str] = None
    d_contrato_ini: Optional[date] = None
    d_contrato_fim: Optional[date] = None

    def check_itens_not_empty(cls, v):
        if not v:
            raise ValueError('A NFCom deve ter pelo menos um item')
        return v

class NFComResponse(NFComBase):
    id: int
    empresa_id: int
    numero_nf: int
    serie: int
    chave_acesso: Optional[str] = None
    # Status calculado dinamicamente no backend: 'cancelada', 'emitida' or 'pendente'
    status: Optional[str] = None
    protocolo_autorizacao: Optional[str] = None
    data_autorizacao: Optional[date] = None
    numero_contrato: Optional[str] = None
    d_contrato_ini: Optional[date] = None
    d_contrato_fim: Optional[date] = None
    
    xml_url: Optional[str] = None
    informacoes_adicionais: Optional[str] = None
    # Endereço do destinatário que foi snapshotado
    dest_endereco: Optional[str] = None
    dest_numero: Optional[str] = None
    dest_complemento: Optional[str] = None
    dest_bairro: Optional[str] = None
    dest_municipio: Optional[str] = None
    dest_uf: Optional[str] = None
    dest_cep: Optional[str] = None
    dest_codigo_ibge: Optional[str] = None

    itens: List[NFComItemResponse] = []
    faturas: List[NFComFaturaResponse] = []
    cliente: Optional[ClienteResponse] = None
    # Campos de status de email (persistidos no modelo NFCom)
    email_status: Optional[str] = None
    email_sent_at: Optional[datetime] = None
    email_error: Optional[str] = None

    class Config:
        from_attributes = True

class NFComUpdate(BaseModel):
    # Campos opcionais para atualização
    data_emissao: Optional[datetime] = None
    tipo_emissao: Optional[TipoEmissao] = None
    tipo_faturamento: Optional[TipoFaturamento] = None
    serie: Optional[int] = None
    numero_nf: Optional[int] = None
    
    # Dados do cliente
    cliente_nome: Optional[str] = None
    cliente_cpf_cnpj: Optional[str] = None
    cliente_inscricao_estadual: Optional[str] = None
    cliente_telefone: Optional[str] = None
    cliente_email: Optional[str] = None
    
    # Endereço do destinatário
    dest_endereco: Optional[str] = None
    dest_numero: Optional[str] = None
    dest_complemento: Optional[str] = None
    dest_bairro: Optional[str] = None
    dest_municipio: Optional[str] = None
    dest_uf: Optional[str] = None
    dest_cep: Optional[str] = None
    dest_codigo_ibge: Optional[str] = None
    
    # Campos de contrato
    numero_contrato: Optional[str] = None
    d_contrato_ini: Optional[date] = None
    d_contrato_fim: Optional[date] = None
    
    # Informações adicionais
    informacoes_adicionais: Optional[str] = None
    
    # Itens (opcional para atualização)
    itens: Optional[List[NFComItemCreate]] = None
    # Faturas (opcional para atualização)
    faturas: Optional[List[NFComFaturaCreate]] = None

class NFComListResponse(BaseModel):
    total: int
    nfcoms: List[NFComResponse]
    total_geral_valor: float
    total_autorizadas: int
    total_pendentes: int
    total_canceladas: int


class BulkEmitNFComRequest(BaseModel):
    """Schema para requisição de emissão em massa de NFCom baseada em contratos."""
    contract_ids: List[int] = Field(..., description="Lista de IDs dos contratos para emissão")
    execute: Optional[bool] = Field(False, description="Se True, cria as NFComs no banco (modo apply). Se False, apenas valida (dry-run).")
    transmit: Optional[bool] = Field(False, description="Se True, após criar cada NFCom chamará transmissão (transmit_nfcom). Requer certificados configurados.")


class BulkEmitNFComResponse(BaseModel):
    """Schema para resposta da emissão em massa de NFCom."""
    successes: List[dict] = Field(..., description="Lista de emissões bem-sucedidas")
    failures: List[dict] = Field(..., description="Lista de falhas na emissão")
    total_processed: int = Field(..., description="Total de contratos processados")
    total_success: int = Field(..., description="Total de emissões bem-sucedidas")
    total_failed: int = Field(..., description="Total de falhas")