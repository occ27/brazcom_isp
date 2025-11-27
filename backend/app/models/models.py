from sqlalchemy import (Column, Integer, String, Boolean, DateTime, Date, Float, ForeignKey, Text, Enum as SQLAlchemyEnum)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum
from .servico_model import Servico


class StatusContrato(str, enum.Enum):
    """Status possíveis para um contrato de serviço."""
    ATIVO = "ATIVO"
    SUSPENSO = "SUSPENSO"
    CANCELADO = "CANCELADO"
    PENDENTE_INSTALACAO = "PENDENTE_INSTALACAO"


class TipoConexao(str, enum.Enum):
    """Tipos de conexão disponíveis para ISPs."""
    FIBRA = "FIBRA"
    RADIO = "RADIO"
    CABO = "CABO"
    SATELITE = "SATELITE"
    ADSL = "ADSL"
    OUTRO = "OUTRO"


class MetodoAutenticacao(str, enum.Enum):
    """Métodos de autenticação para serviços de internet."""
    IP_MAC = "IP_MAC"
    PPPOE = "PPPOE"
    HOTSPOT = "HOTSPOT"
    RADIUS = "RADIUS"


class Usuario(Base):
    """Modelo de Usuário do sistema."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    # Empresa ativa selecionada pelo usuário (opcional)
    active_empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    empresas = relationship("UsuarioEmpresa", back_populates="usuario")

class PasswordResetToken(Base):
    """Token/código de redefinição de senha enviado por email."""
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    code = Column(String(20), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    usuario = relationship("Usuario")

class Empresa(Base):
    """Modelo de Empresa emissora de NFCom."""
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    razao_social = Column(String(255), nullable=False)
    nome_fantasia = Column(String(255))
    cnpj = Column(String(18), unique=True, index=True, nullable=False) # Formatado: XX.XXX.XXX/XXXX-XX
    inscricao_estadual = Column(String(20))
    endereco = Column(String(255), nullable=False)  # OBRIGATÓRIO para NFCom
    numero = Column(String(20), nullable=False)  # OBRIGATÓRIO para NFCom
    complemento = Column(String(100))
    bairro = Column(String(100), nullable=False)  # OBRIGATÓRIO para NFCom
    municipio = Column(String(100), nullable=False)  # OBRIGATÓRIO para NFCom
    uf = Column(String(2), nullable=False)  # OBRIGATÓRIO para NFCom
    codigo_ibge = Column(String(7), nullable=False)  # OBRIGATÓRIO para NFCom
    cep = Column(String(9), nullable=False)  # OBRIGATÓRIO para NFCom
    pais = Column(String(60), nullable=False, server_default='BRASIL')
    codigo_pais = Column(String(4), nullable=False, server_default='1058')
    telefone = Column(String(20))
    email = Column(String(255), nullable=False)  # OBRIGATÓRIO para NFCom
    regime_tributario = Column(String(50)) # Ex: Simples Nacional
    cnae_principal = Column(String(10)) # CNAE principal (opcional mas recomendado)
    
    # Novos campos para logo, certificado e email
    logo_url = Column(String(500)) # Caminho para o arquivo da logo
    certificado_path = Column(String(500)) # Caminho para o certificado digital
    certificado_senha = Column(String(500)) # Senha do certificado (criptografada)
    
    # Configurações SMTP para envio de emails
    smtp_server = Column(String(255))
    smtp_port = Column(Integer)
    smtp_user = Column(String(255))
    smtp_password = Column(String(500)) # Senha SMTP (criptografada)
    # Ambiente para transmissão de NFCom: 'producao' ou 'homologacao'
    # Valor padrão: 'producao' (compatível com comportamento anterior quando AMBIENTE_PRODUCAO=True)
    ambiente_nfcom = Column(String(20), nullable=False, server_default='producao')
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # Usuário que cadastrou a empresa
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    usuarios = relationship("UsuarioEmpresa", back_populates="empresa")
    clientes = relationship("Cliente", back_populates="empresa")
    # Associações empresa-cliente (endereços e metadados por empresa)
    empresa_clientes = relationship("EmpresaCliente", back_populates="empresa")
    nfcoms = relationship("NFCom", back_populates="empresa")
    servicos = relationship("Servico", back_populates="empresa", cascade="all, delete-orphan")
    servicos_contratados = relationship("ServicoContratado", back_populates="empresa", cascade="all, delete-orphan")
    routers = relationship("Router", back_populates="empresa", cascade="all, delete-orphan")
    radius_servers = relationship("RadiusServer", back_populates="empresa", cascade="all, delete-orphan")
    radius_users = relationship("RadiusUser", back_populates="empresa", cascade="all, delete-orphan")
    ip_classes = relationship("IPClass", back_populates="empresa", cascade="all, delete-orphan")

    # Relacionamentos com configurações PPPoE e DHCP
    ip_pools = relationship("IPPool", back_populates="empresa", cascade="all, delete-orphan")
    ppp_profiles = relationship("PPPProfile", back_populates="empresa", cascade="all, delete-orphan")
    pppoe_servers = relationship("PPPoEServer", back_populates="empresa", cascade="all, delete-orphan")
    dhcp_servers = relationship("DHCPServer", back_populates="empresa", cascade="all, delete-orphan")
    dhcp_networks = relationship("DHCPNetwork", back_populates="empresa", cascade="all, delete-orphan")

    # Especifica explicitamente que esta relação usa a coluna user_id como FK
    usuario_criador = relationship(
        "Usuario",
        backref="empresas_criadas",
        foreign_keys=[user_id]
    )

class UsuarioEmpresa(Base):
    """Tabela de associação entre Usuário e Empresa."""
    __tablename__ = "usuario_empresa"

    usuario_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), primary_key=True)
    is_admin = Column(Boolean, default=False) # Se o usuário é admin da empresa

    usuario = relationship("Usuario", back_populates="empresas")
    empresa = relationship("Empresa", back_populates="usuarios")

class EmpresaCliente(Base):
    """Associação entre Empresa e Cliente (dados por-empresa)."""
    __tablename__ = "empresa_clientes"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="empresa_clientes")
    cliente = relationship("Cliente", back_populates="empresa_associations")
    created_by = relationship("Usuario")
    enderecos = relationship("EmpresaClienteEndereco", back_populates="empresa_cliente", cascade="all, delete-orphan")

class EmpresaClienteEndereco(Base):
    """Endereços vinculados à associação EmpresaCliente (permitir endereços distintos por empresa)."""
    __tablename__ = "empresa_cliente_enderecos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_cliente_id = Column(Integer, ForeignKey("empresa_clientes.id"), nullable=False)
    descricao = Column(String(100))
    endereco = Column(String(255), nullable=False)
    numero = Column(String(20), nullable=False)
    complemento = Column(String(100))
    bairro = Column(String(100), nullable=False)
    municipio = Column(String(100), nullable=False)
    uf = Column(String(2), nullable=False)
    cep = Column(String(9), nullable=False)
    codigo_ibge = Column(String(7))
    is_principal = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    empresa_cliente = relationship("EmpresaCliente", back_populates="enderecos")

class TipoPessoa(str, enum.Enum):
    FISICA = "F"
    JURIDICA = "J"

class IndicadorIEDest(str, enum.Enum):
    CONTRIBUINTE_ICMS = "1"
    CONTRIBUINTE_ISENTO = "2"
    NAO_CONTRIBUINTE = "9"

class Cliente(Base):
    """Modelo de Cliente de uma Empresa."""
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    nome_razao_social = Column(String(255), nullable=False)
    cpf_cnpj = Column(String(18), index=True, nullable=True) # Nulo se idOutros for preenchido
    idOutros = Column(String(20), index=True, nullable=True) # Nulo se cpf_cnpj for preenchido
    tipo_pessoa = Column(SQLAlchemyEnum(TipoPessoa), nullable=False)
    ind_ie_dest = Column(SQLAlchemyEnum(IndicadorIEDest), nullable=False)
    inscricao_estadual = Column(String(20))
    email = Column(String(255))
    telefone = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Legacy: cliente podia apontar para uma única empresa (mantido para migração)
    empresa = relationship("Empresa", back_populates="clientes")
    # Associações com empresas (nova modelagem)
    empresa_associations = relationship("EmpresaCliente", back_populates="cliente")
    nfcoms = relationship("NFCom", back_populates="cliente")
    servicos_contratados = relationship("ServicoContratado", back_populates="cliente", cascade="all, delete-orphan")
    radius_user = relationship("RadiusUser", back_populates="cliente", uselist=False)

# relação inversa: EmpresaCliente.enderecos back_populates
EmpresaCliente.enderecos = relationship("EmpresaClienteEndereco", back_populates="empresa_cliente", cascade="all, delete-orphan")

class TipoEmissao(str, enum.Enum):
    NORMAL = "1"
    CONTINGENCIA = "2"

class FinalidadeEmissao(str, enum.Enum):
    NORMAL = "0"
    SUBSTITUICAO = "3"
    AJUSTE = "4"

class TipoFaturamento(str, enum.Enum):
    NORMAL = "0"
    CENTRALIZADO = "1"
    COFATURAMENTO = "2"

class NFCom(Base):
    """Modelo da Nota Fiscal de Comunicação (NFCom - Modelo 62)."""
    __tablename__ = "nfcom"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    
    # Endereço do destinatário (snapshot no momento da emissão)
    dest_endereco = Column(String(255))
    dest_numero = Column(String(20))
    dest_complemento = Column(String(100))
    dest_bairro = Column(String(100))
    dest_municipio = Column(String(100))
    dest_uf = Column(String(2))
    dest_cep = Column(String(9))
    dest_codigo_ibge = Column(String(7))

    numero_nf = Column(Integer, nullable=False)
    serie = Column(Integer, nullable=False)
    chave_acesso = Column(String(44), unique=True, index=True)
    protocolo_autorizacao = Column(String(50))
    data_autorizacao = Column(DateTime(timezone=True))
    
    cMunFG = Column(String(7), nullable=False) # Código do município de ocorrência do fato gerador
    data_emissao = Column(DateTime(timezone=True), server_default=func.now())
    tipo_emissao = Column(SQLAlchemyEnum(TipoEmissao), nullable=False, default=TipoEmissao.NORMAL)
    finalidade_emissao = Column(SQLAlchemyEnum(FinalidadeEmissao), nullable=False, default=FinalidadeEmissao.NORMAL)
    tpFat = Column(SQLAlchemyEnum(TipoFaturamento), nullable=False, default=TipoFaturamento.NORMAL)

    # Campos de contrato exigidos pelo leiaute quando tpFat = NORMAL (0) ou CENTRALIZADO (1)
    numero_contrato = Column(String(20), nullable=True)
    d_contrato_ini = Column(Date, nullable=True)
    d_contrato_fim = Column(Date, nullable=True)

    valor_total = Column(Float, nullable=False)
    valor_icms = Column(Float)
    valor_pis = Column(Float)
    valor_cofins = Column(Float)
    
    informacoes_adicionais = Column(Text)
    
    xml_gerado = Column(Text)
    pdf_url = Column(String(500))
    # Adicionando os campos para o XML que já existem no banco
    xml_gerado = Column(Text)
    xml_url = Column(String(500))

    empresa = relationship("Empresa", back_populates="nfcoms")
    cliente = relationship("Cliente", back_populates="nfcoms")
    itens = relationship("NFComItem", back_populates="nfcom", cascade="all, delete-orphan")
    faturas = relationship("NFComFatura", back_populates="nfcom", cascade="all, delete-orphan")

    # Email delivery status fields
    email_status = Column(String(30), nullable=True, server_default='pending')
    email_sent_at = Column(DateTime(timezone=True), nullable=True)
    email_error = Column(Text, nullable=True)
    # Email sending status for UI convenience
    email_status = Column(String(30), nullable=False, server_default='pending')
    email_sent_at = Column(DateTime(timezone=True))
    email_error = Column(Text)

class NFComEmailJob(Base):
    __tablename__ = 'nfcom_email_jobs'
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=False)
    created_by_user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    total = Column(Integer, nullable=False, default=0)
    processed = Column(Integer, nullable=False, default=0)
    successes = Column(Integer, nullable=False, default=0)
    failures = Column(Integer, nullable=False, default=0)
    status = Column(String(30), nullable=False, server_default='pending')

class NFComEmailStatus(Base):
    __tablename__ = 'nfcom_email_statuses'
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey('nfcom_email_jobs.id'), nullable=False)
    nfcom_id = Column(Integer, ForeignKey('nfcom.id'), nullable=False, index=True)
    status = Column(String(30), nullable=False, server_default='pending')
    error_message = Column(Text)
    sent_at = Column(DateTime(timezone=True))

class NFComItem(Base):
    """Modelo de Item da NFCom."""
    __tablename__ = "nfcom_itens"

    id = Column(Integer, primary_key=True, index=True)
    nfcom_id = Column(Integer, ForeignKey("nfcom.id"), nullable=False)
    servico_id = Column(Integer, ForeignKey("servicos.id"), nullable=True)
    
    cClass = Column(String(7), nullable=False) # Código de classificação do item
    codigo_servico = Column(String(60), nullable=False)
    descricao_servico = Column(String(120), nullable=False)
    quantidade = Column(Float, nullable=False)
    unidade_medida = Column(String(10), nullable=False)
    valor_unitario = Column(Float, nullable=False)
    valor_desconto = Column(Float, default=0.0)
    valor_outros = Column(Float, default=0.0)
    valor_total = Column(Float, nullable=False)
    
    cfop = Column(String(4))
    ncm = Column(String(8))
    
    base_calculo_icms = Column(Float)
    aliquota_icms = Column(Float)
    valor_icms = Column(Float)
    
    # Campos para PIS e COFINS
    base_calculo_pis = Column(Float)
    aliquota_pis = Column(Float)
    base_calculo_cofins = Column(Float)
    aliquota_cofins = Column(Float)

    nfcom = relationship("NFCom", back_populates="itens")
    servico = relationship("Servico")

class ServicoContratado(Base):
    """Serviços contratados por um cliente (para emissão recorrente/por contrato)."""
    __tablename__ = "servicos_contratados"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    servico_id = Column(Integer, ForeignKey("servicos.id"), nullable=False)

    # Contrato / vigência
    numero_contrato = Column(String(50), nullable=True)
    d_contrato_ini = Column(Date, nullable=True)
    d_contrato_fim = Column(Date, nullable=True)

    # Status do contrato (específico para ISPs)
    status = Column(SQLAlchemyEnum(StatusContrato), nullable=False, server_default=StatusContrato.PENDENTE_INSTALACAO.value)

    # Informações de instalação (específicas para ISPs)
    endereco_instalacao = Column(Text, nullable=True)  # Endereço onde o serviço é instalado (pode ser diferente do endereço do cliente)
    tipo_conexao = Column(SQLAlchemyEnum(TipoConexao), nullable=True)
    coordenadas_gps = Column(String(50), nullable=True)  # Latitude,Longitude para mapeamento
    data_instalacao = Column(Date, nullable=True)  # Quando foi instalado fisicamente
    responsavel_tecnico = Column(String(100), nullable=True)  # Nome do técnico responsável

    # Emissão e cobrança
    periodicidade = Column(String(20), nullable=False, server_default='MENSAL')  # Ex: MENSAL, BIMESTRAL, TRIMESTRAL, SEMESTRAL, ANUAL
    dia_emissao = Column(Integer, nullable=False)  # Dia do mês para emissão (1-28/30/31 conforme contrato)
    quantidade = Column(Float, nullable=False, default=1.0)
    valor_unitario = Column(Float, nullable=False)
    valor_total = Column(Float, nullable=True)
    # Novo campo: dia do mês para vencimento (1-31). Preferido para geração de faturas automáticas.
    dia_vencimento = Column(Integer, nullable=True)
    periodo_carencia = Column(Integer, nullable=True, default=0)  # Dias de carência após vencimento
    multa_atraso_percentual = Column(Float, nullable=True, default=0.0)  # % de multa por atraso

    # Taxas adicionais (comuns em ISPs)
    taxa_instalacao = Column(Float, nullable=True, default=0.0)  # Taxa única de instalação
    taxa_instalacao_paga = Column(Boolean, nullable=True, default=False)  # Se já foi cobrada

    # SLA e qualidade (específicos para ISPs)
    sla_garantido = Column(Float, nullable=True)  # SLA garantido em % (ex: 99.9)
    velocidade_garantida = Column(String(50), nullable=True)  # Velocidade garantida (ex: "10M/10M")

    # Controles de emissão automática
    auto_emit = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    last_emission = Column(DateTime(timezone=True), nullable=True)
    next_emission = Column(DateTime(timezone=True), nullable=True)

    # Relacionamento com subscription ativa (provisionamento)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)  # Link com ativação atual

    # Configuração de rede (provisionamento automático)
    router_id = Column(Integer, ForeignKey("routers.id"), nullable=True)  # Router onde será provisionado
    interface_id = Column(Integer, ForeignKey("router_interfaces.id"), nullable=True)  # Interface do router
    ip_class_id = Column(Integer, ForeignKey("ip_classes.id"), nullable=True)  # Classe IP para atribuição automática
    mac_address = Column(String(17), nullable=True)  # Endereço MAC do dispositivo do cliente
    assigned_ip = Column(String(15), nullable=True)  # IP atribuído automaticamente
    metodo_autenticacao = Column(SQLAlchemyEnum(MetodoAutenticacao), nullable=True)  # Método de autenticação

    # Campos específicos para autenticação PPPoE
    pppoe_username = Column(String(50), nullable=True)  # Username PPPoE do cliente
    pppoe_password = Column(String(50), nullable=True)  # Password PPPoE do cliente

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="servicos_contratados")
    cliente = relationship("Cliente", back_populates="servicos_contratados")
    servico = relationship("Servico")
    subscription = relationship("Subscription")
    router = relationship("Router")
    interface = relationship("RouterInterface")
    ip_class = relationship("IPClass")

class NFComFatura(Base):
    """Modelo de Fatura/Cobrança da NFCom."""
    __tablename__ = "nfcom_faturas"

    id = Column(Integer, primary_key=True, index=True)
    nfcom_id = Column(Integer, ForeignKey("nfcom.id"), nullable=False)
    
    numero_fatura = Column(String(50), nullable=False)
    data_vencimento = Column(DateTime(timezone=True), nullable=False)
    valor_fatura = Column(Float, nullable=False)
    codigo_barras = Column(String(48), nullable=True)  # Linha digitável do código de barras (1-48 dígitos)
    
    nfcom = relationship("NFCom", back_populates="faturas")

# Imports tardios para resolver dependências circulares
from .network import Router
from .access_control import Role, Permission
from .radius import RadiusServer, RadiusUser, RadiusSession

