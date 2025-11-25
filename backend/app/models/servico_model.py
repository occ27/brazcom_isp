from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class TipoServico(str, enum.Enum):
    SERVICO = "SERVICO"  # Serviço geral de cobrança
    PLANO_INTERNET = "PLANO_INTERNET"  # Plano de acesso à internet


class Servico(Base):
    __tablename__ = "servicos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    tipo = Column(String(20), nullable=False, default=TipoServico.SERVICO.value)  # Tipo do serviço
    codigo = Column(String(60), nullable=False)
    descricao = Column(String(120), nullable=False)
    cClass = Column(String(7), nullable=False)
    unidade_medida = Column(String(10), nullable=False)
    valor_unitario = Column(Float, nullable=False)
    is_active = Column(Boolean, nullable=True)
    # Fields to help pre-fill NFCom items
    cfop = Column(String(4), nullable=True)
    ncm = Column(String(8), nullable=True)
    base_calculo_icms_default = Column(Float, nullable=True)
    aliquota_icms_default = Column(Float, nullable=True)
    valor_desconto_default = Column(Float, nullable=True, default=0.0)
    valor_outros_default = Column(Float, nullable=True, default=0.0)

    # Novos campos para planos de acesso (opcionais)
    upload_speed = Column(Float, nullable=True)  # Velocidade de upload em Mbps
    download_speed = Column(Float, nullable=True)  # Velocidade de download em Mbps
    max_limit = Column(String(50), nullable=True)  # Limite para queue no RouterOS (ex: "10M/10M")
    fidelity_months = Column(Integer, nullable=True)  # Fidelidade em meses
    billing_cycle = Column(String(20), nullable=True, default='MENSAL')  # Ciclo de cobrança: MENSAL, TRIMESTRAL, etc.
    notes = Column(String(500), nullable=True)  # Observações adicionais

    # Campos para promoções
    promotional_price = Column(Float, nullable=True)  # Preço promocional
    promotional_months = Column(Integer, nullable=True)  # Meses com preço promocional
    promotional_active = Column(Boolean, nullable=True, default=False)  # Se promoção está ativa

    empresa = relationship("Empresa")
