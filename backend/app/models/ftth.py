import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Text, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class FabricanteOLT(str, enum.Enum):
    """Fabricantes de OLT suportados."""
    ZTE = "ZTE"
    HUAWEI = "HUAWEI"
    FIBERHOME = "FIBERHOME"
    PARKS = "PARKS"
    INTELBRAS = "INTELBRAS"
    DATACOM = "DATACOM"
    OUTRO = "OUTRO"


class StatusONU(str, enum.Enum):
    """Status de uma ONU/ONT no momento da última verificação."""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DEGRADADO = "DEGRADADO"   # Ping ok mas sinal fraco
    DESCONHECIDO = "DESCONHECIDO"


class OLT(Base):
    """Optical Line Terminal — equipamento principal da rede FTTH."""
    __tablename__ = "olts"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    ip = Column(String(45), nullable=False)                     # Suporta IPv4 e IPv6
    porta_snmp = Column(Integer, default=161)
    community_read = Column(String(100), nullable=True)         # Community SNMP de leitura
    community_write = Column(String(100), nullable=True)        # Community SNMP de escrita
    fabricante = Column(String(50), nullable=True)              # Fabricante (ZTE, Huawei, etc.)
    modelo = Column(String(100), nullable=True)                 # Modelo (C300, C600, MA5800, etc.)
    firmware = Column(String(50), nullable=True)                # Versão do firmware
    localizacao = Column(String(255), nullable=True)            # Localização física
    descricao = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)

    # Relacionamentos
    empresa = relationship("Empresa")
    ctos = relationship("CTO", back_populates="olt", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CTO(Base):
    """Caixa de Terminação Óptica — ponto de distribuição de fibra para os clientes."""
    __tablename__ = "ctos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False, index=True)
    olt_id = Column(Integer, ForeignKey("olts.id"), nullable=True)   # OLT à qual esta CTO está conectada
    porta_pon = Column(String(30), nullable=True)                    # Porta PON da OLT (ex: "0/1/0")
    splitter_ratio = Column(String(20), nullable=True)              # Relação do splitter (ex: "1:8", "1:16", "1:32")
    capacidade = Column(Integer, nullable=True)                     # Capacidade máxima de ONUs
    coordenadas_gps = Column(String(50), nullable=True)             # Lat,Lng (ex: "-23.1234,-46.5678")
    endereco = Column(String(255), nullable=True)                   # Endereço físico da CTO
    descricao = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)

    # Relacionamentos
    empresa = relationship("Empresa")
    olt = relationship("OLT", back_populates="ctos")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class FTTHMonitorSnapshot(Base):
    """Snapshot de monitoramento de uma ONU em um determinado momento.
    
    Armazena o histórico de status e parâmetros de cada ONU para
    geração de gráficos de sinal e análise de disponibilidade.
    """
    __tablename__ = "ftth_monitor_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    contrato_id = Column(Integer, ForeignKey("servicos_contratados.id"), nullable=False, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)

    # Status da ONU no momento da verificação
    status = Column(String(20), nullable=False, default="DESCONHECIDO")  # ONLINE, OFFLINE, DEGRADADO, DESCONHECIDO

    # Parâmetros ópticos (quando disponíveis via SNMP)
    rx_power = Column(Float, nullable=True)      # Potência óptica recebida em dBm
    tx_power = Column(Float, nullable=True)      # Potência óptica transmitida em dBm
    temperature = Column(Float, nullable=True)   # Temperatura do módulo óptico (°C)
    voltage = Column(Float, nullable=True)       # Tensão de alimentação (V)

    # Parâmetros de rede
    latencia_ms = Column(Float, nullable=True)   # Latência do ping em ms
    is_reachable = Column(Boolean, nullable=True) # Se o IP responde a ping

    # Metadados da coleta
    metodo_coleta = Column(String(20), default="PING")  # PING, SNMP, MANUAL
    detalhe_erro = Column(Text, nullable=True)   # Mensagem de erro caso a coleta falhe

    # Snapshot do IP no momento da coleta (pode mudar com DHCP)
    ip_verificado = Column(String(45), nullable=True)

    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relacionamentos
    contrato = relationship("ServicoContratado")
    empresa = relationship("Empresa")
