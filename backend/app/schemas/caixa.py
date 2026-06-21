from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class LocalPagamentoBase(BaseModel):
    nome: str
    is_active: bool = True

class LocalPagamentoCreate(LocalPagamentoBase):
    pass

class LocalPagamentoUpdate(BaseModel):
    nome: Optional[str] = None
    is_active: Optional[bool] = None

class LocalPagamentoResponse(LocalPagamentoBase):
    id: int
    empresa_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FormaPagamentoBase(BaseModel):
    nome: str
    is_active: bool = True

class FormaPagamentoCreate(FormaPagamentoBase):
    pass

class FormaPagamentoUpdate(BaseModel):
    nome: Optional[str] = None
    is_active: Optional[bool] = None

class FormaPagamentoResponse(FormaPagamentoBase):
    id: int
    empresa_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RecebimentoCaixaSplit(BaseModel):
    forma_pagamento_id: int
    amount: float

class RecebimentoCaixaResponse(BaseModel):
    id: int
    receivable_id: int
    local_pagamento_id: int
    forma_pagamento_id: int
    usuario_id: int
    amount: float
    paid_at: datetime

    # Additional fields if needed for UI, e.g. forma_pagamento nome
    forma_pagamento_nome: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CaixaSessaoAbrir(BaseModel):
    local_pagamento_id: int
    saldo_inicial: float = 0.0

class CaixaSessaoFechar(BaseModel):
    saldo_final_informado: float

class CaixaMovimentacaoCreate(BaseModel):
    tipo: str
    valor: float
    forma_pagamento_id: int
    descricao: Optional[str] = None

class CaixaSessaoResponse(BaseModel):
    id: int
    empresa_id: int
    usuario_id: int
    local_pagamento_id: int
    data_abertura: datetime
    data_fechamento: Optional[datetime] = None
    saldo_inicial: float
    saldo_final_informado: Optional[float] = None
    saldo_final_calculado: Optional[float] = None
    status: str
    
    usuario_nome: Optional[str] = None
    local_pagamento_nome: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CaixaMovimentacaoResponse(BaseModel):
    id: int
    sessao_id: int
    usuario_id: int
    forma_pagamento_id: Optional[int] = None
    recebimento_caixa_id: Optional[int] = None
    tipo: str
    valor: float
    descricao: Optional[str] = None
    created_at: datetime
    
    forma_pagamento_nome: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)