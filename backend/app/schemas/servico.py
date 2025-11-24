from pydantic import BaseModel, Field
from typing import Optional


class ServicoBase(BaseModel):
    empresa_id: Optional[int] = None
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


class ServicoCreate(ServicoBase):
    pass


class ServicoUpdate(BaseModel):
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


class ServicoResponse(ServicoBase):
    id: int
    empresa_id: int

    class Config:
        from_attributes = True
