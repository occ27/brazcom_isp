from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from enum import Enum


class TipoServico(str, Enum):
    SERVICO = "SERVICO"
    PLANO_INTERNET = "PLANO_INTERNET"


class ServicoBase(BaseModel):
    empresa_id: Optional[int] = None
    tipo: TipoServico = Field(TipoServico.SERVICO, description="Tipo do serviço")
    codigo: str = Field(..., max_length=60, description="Código interno do serviço/produto")
    descricao: str = Field(..., max_length=120, description="Descrição do serviço/produto")
    cClass: str = Field(..., max_length=7, description="Código de Classificação do Item da NFCom")
    unidade_medida: str = Field("UN", max_length=10)
    valor_unitario: float = Field(..., ge=0)
    is_active: Optional[bool] = True
    cfop: Optional[str] = Field(None, max_length=4)
    ncm: Optional[str] = Field(None, max_length=8)
    base_calculo_icms_default: Optional[float] = None
    aliquota_icms_default: Optional[float] = None
    valor_desconto_default: Optional[float] = None
    valor_outros_default: Optional[float] = None
    # Novos campos para planos de acesso
    upload_speed: Optional[float] = Field(None, ge=0, description="Velocidade de upload em Mbps")
    download_speed: Optional[float] = Field(None, ge=0, description="Velocidade de download em Mbps")
    max_limit: Optional[str] = Field(None, max_length=50, description="Limite para queue no RouterOS (ex: '10M/10M'). Se não informado, será gerado automaticamente baseado nas velocidades.")
    fidelity_months: Optional[int] = Field(None, ge=0, description="Fidelidade em meses")
    billing_cycle: Optional[str] = Field("MENSAL", max_length=20, description="Ciclo de cobrança")
    notes: Optional[str] = Field(None, max_length=500, description="Observações adicionais")
    # Campos para promoções
    promotional_price: Optional[float] = Field(None, ge=0, description="Preço promocional")
    promotional_months: Optional[int] = Field(None, ge=1, description="Meses com preço promocional")
    promotional_active: Optional[bool] = Field(False, description="Se promoção está ativa")

    # Configuração de rede para planos de internet
    ppp_profile_id: Optional[int] = Field(None, description="Profile PPPoE para planos de internet")


class ServicoCreate(ServicoBase):
    @field_validator('max_limit')
    @classmethod
    def normalize_max_limit(cls, v):
        if v is None:
            return v
        # Remove espaços e converte para maiúsculo
        normalized = str(v).strip().upper()
        # Remove caracteres inválidos, permite apenas números, /, M, K, G, T, P
        import re
        normalized = re.sub(r'[^0-9/MKGTP]', '', normalized)
        return normalized or None

    @model_validator(mode='after')
    def generate_max_limit_if_missing(self):
        # Se max_limit não foi fornecido, gerar automaticamente baseado nas velocidades
        if not self.max_limit and self.upload_speed is not None and self.download_speed is not None:
            self.max_limit = f"{int(self.upload_speed)}M/{int(self.download_speed)}M"
        return self


class ServicoUpdate(BaseModel):
    tipo: Optional[TipoServico] = None
    codigo: Optional[str] = Field(None, max_length=60)
    descricao: Optional[str] = Field(None, max_length=120)
    cClass: Optional[str] = Field(None, max_length=7)
    unidade_medida: Optional[str] = Field(None, max_length=10)
    valor_unitario: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None
    # Allow updates to CFOP/NCM and NFCom defaults
    cfop: Optional[str] = Field(None, max_length=4)
    ncm: Optional[str] = Field(None, max_length=8)
    base_calculo_icms_default: Optional[float] = None
    aliquota_icms_default: Optional[float] = None
    valor_desconto_default: Optional[float] = None
    valor_outros_default: Optional[float] = None
    # Novos campos para planos de acesso
    upload_speed: Optional[float] = Field(None, ge=0)
    download_speed: Optional[float] = Field(None, ge=0)
    max_limit: Optional[str] = Field(None, max_length=50)
    fidelity_months: Optional[int] = Field(None, ge=0)
    billing_cycle: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = Field(None, max_length=500)
    # Campos para promoções
    promotional_price: Optional[float] = Field(None, ge=0)
    promotional_months: Optional[int] = Field(None, ge=1)
    promotional_active: Optional[bool] = None

    # Configuração de rede para planos de internet
    ppp_profile_id: Optional[int] = Field(None, description="Profile PPPoE para planos de internet")

    @field_validator('max_limit')
    @classmethod
    def normalize_max_limit(cls, v):
        if v is None:
            return v
        # Remove espaços e converte para maiúsculo
        normalized = str(v).strip().upper()
        # Remove caracteres inválidos, permite apenas números, /, M, K, G, T, P
        import re
        normalized = re.sub(r'[^0-9/MKGTP]', '', normalized)
        return normalized or None

    @model_validator(mode='after')
    def generate_max_limit_if_missing(self):
        # Se max_limit não foi fornecido, gerar automaticamente baseado nas velocidades
        if not self.max_limit and self.upload_speed is not None and self.download_speed is not None:
            self.max_limit = f"{int(self.upload_speed)}M/{int(self.download_speed)}M"
        return self


class ServicoResponse(ServicoBase):
    id: int
    empresa_id: int

    class Config:
        from_attributes = True
