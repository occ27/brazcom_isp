from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Servico(Base):
    __tablename__ = "servicos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
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

    empresa = relationship("Empresa")
