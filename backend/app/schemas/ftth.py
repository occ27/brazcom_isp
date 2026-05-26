from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ===== OLT SCHEMAS =====

class OLTBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    ip: str = Field(..., max_length=45)
    porta_snmp: Optional[int] = 161
    community_read: Optional[str] = Field(None, max_length=100)
    community_write: Optional[str] = Field(None, max_length=100)
    fabricante: Optional[str] = None
    modelo: Optional[str] = Field(None, max_length=100)
    firmware: Optional[str] = Field(None, max_length=50)
    localizacao: Optional[str] = Field(None, max_length=255)
    descricao: Optional[str] = None
    is_active: bool = True


class OLTCreate(OLTBase):
    pass


class OLTUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    ip: Optional[str] = Field(None, max_length=45)
    porta_snmp: Optional[int] = None
    community_read: Optional[str] = None
    community_write: Optional[str] = None
    fabricante: Optional[str] = None
    modelo: Optional[str] = None
    firmware: Optional[str] = None
    localizacao: Optional[str] = None
    descricao: Optional[str] = None
    is_active: Optional[bool] = None


class OLT(OLTBase):
    id: int
    empresa_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ===== CTO SCHEMAS =====

class CTOBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    olt_id: Optional[int] = None
    porta_pon: Optional[str] = Field(None, max_length=30)
    splitter_ratio: Optional[str] = Field(None, max_length=20)
    capacidade: Optional[int] = None
    coordenadas_gps: Optional[str] = Field(None, max_length=50)
    endereco: Optional[str] = Field(None, max_length=255)
    descricao: Optional[str] = None
    is_active: bool = True


class CTOCreate(CTOBase):
    pass


class CTOUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    olt_id: Optional[int] = None
    porta_pon: Optional[str] = None
    splitter_ratio: Optional[str] = None
    capacidade: Optional[int] = None
    coordenadas_gps: Optional[str] = None
    endereco: Optional[str] = None
    descricao: Optional[str] = None
    is_active: Optional[bool] = None


class CTO(CTOBase):
    id: int
    empresa_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    olt_nome: Optional[str] = None
    distancia_metros: Optional[float] = None

    class Config:
        from_attributes = True


# ===== SNAPSHOT / STATUS SCHEMAS =====

class FTTHMonitorSnapshotOut(BaseModel):
    id: int
    contrato_id: int
    empresa_id: int
    status: str
    rx_power: Optional[float] = None
    tx_power: Optional[float] = None
    temperature: Optional[float] = None
    voltage: Optional[float] = None
    latencia_ms: Optional[float] = None
    is_reachable: Optional[bool] = None
    metodo_coleta: str
    detalhe_erro: Optional[str] = None
    ip_verificado: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class ONUStatus(BaseModel):
    """Status atual de uma ONU com dados do contrato."""
    contrato_id: int
    cliente_nome: str
    numero_contrato: Optional[str] = None
    endereco_instalacao: Optional[str] = None
    onu_serial: Optional[str] = None
    onu_modelo: Optional[str] = None
    olt_nome: Optional[str] = None
    olt_pon: Optional[str] = None
    cto_nome: Optional[str] = None
    cto_porta: Optional[str] = None
    assigned_ip: Optional[str] = None
    coordenadas_gps: Optional[str] = None
    vlan_id: Optional[int] = None
    tipo_conexao: Optional[str] = None

    # Status atual (do último snapshot)
    status: str = "DESCONHECIDO"
    latencia_ms: Optional[float] = None
    rx_power: Optional[float] = None
    tx_power: Optional[float] = None
    is_reachable: Optional[bool] = None
    ultima_verificacao: Optional[datetime] = None
    metodo_coleta: Optional[str] = None


class FTTHDashboard(BaseModel):
    """Dados de resumo para o dashboard de monitoramento FTTH."""
    total_onus: int
    onus_online: int
    onus_offline: int
    onus_degradado: int
    onus_desconhecido: int
    disponibilidade_percentual: float
    total_olts: int
    total_ctos: int
    ultima_atualizacao: Optional[datetime] = None


class PingResult(BaseModel):
    """Resultado de um ping manual."""
    contrato_id: int
    ip_testado: Optional[str] = None
    is_reachable: bool
    latencia_ms: Optional[float] = None
    status: str
    timestamp: datetime
