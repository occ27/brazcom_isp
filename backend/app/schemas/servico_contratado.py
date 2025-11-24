from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


class ServicoContratadoBase(BaseModel):
    empresa_id: Optional[int] = None
    cliente_id: int
    servico_id: int

    numero_contrato: Optional[str] = Field(None, max_length=50)
    d_contrato_ini: Optional[date] = None
    d_contrato_fim: Optional[date] = None
    # Dia do mês de vencimento do serviço/contrato (opcional). Preferido para geração de faturas.
    dia_vencimento: Optional[int] = None

    periodicidade: Optional[str] = Field('MENSAL', max_length=20)
    dia_emissao: int = Field(..., ge=1, le=31, description="Dia do mês para emissão (1-31)")
    quantidade: Optional[float] = 1.0
    valor_unitario: float
    valor_total: Optional[float] = None

    auto_emit: Optional[bool] = True
    is_active: Optional[bool] = True


class ServicoContratadoCreate(ServicoContratadoBase):
    pass


class ServicoContratadoUpdate(BaseModel):
    cliente_id: Optional[int] = None
    servico_id: Optional[int] = None
    numero_contrato: Optional[str] = Field(None, max_length=50)
    d_contrato_ini: Optional[date]
    d_contrato_fim: Optional[date]
    dia_vencimento: Optional[int]
    periodicidade: Optional[str] = Field(None, max_length=20)
    dia_emissao: Optional[int] = Field(None, ge=1, le=31, description="Dia do mês para emissão (1-31)")
    quantidade: Optional[float] = None
    valor_unitario: Optional[float] = None
    valor_total: Optional[float] = None
    auto_emit: Optional[bool] = None
    is_active: Optional[bool] = None


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
