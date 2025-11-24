from sqlalchemy.orm import Session
from datetime import datetime
from types import SimpleNamespace
from app.models.models import Empresa, UsuarioEmpresa, Cliente, NFCom
from app.schemas.empresa import EmpresaCreate, EmpresaUpdate, UsuarioEmpresaCreate
from app.core.security import encrypt_sensitive_data, decrypt_sensitive_data


def _decrypt_sensitive_fields(empresa: Empresa) -> SimpleNamespace:
    """Cria uma representação segura (SimpleNamespace) da empresa para retorno ao cliente.

    Não retorna valores sensíveis (como senha ou path). Em vez disso, inclui flags
    indicando se esses valores estão configurados.
    """
    ns = SimpleNamespace(
        id=empresa.id,
        razao_social=empresa.razao_social,
        nome_fantasia=empresa.nome_fantasia,
        cnpj=empresa.cnpj,
        inscricao_estadual=empresa.inscricao_estadual,
        endereco=empresa.endereco,
        numero=empresa.numero,
        complemento=empresa.complemento,
        bairro=empresa.bairro,
        municipio=empresa.municipio,
        uf=empresa.uf,
        codigo_ibge=empresa.codigo_ibge,
        cep=empresa.cep,
        pais=empresa.pais,
        codigo_pais=empresa.codigo_pais,
        telefone=empresa.telefone,
        email=empresa.email,
        regime_tributario=empresa.regime_tributario,
        cnae_principal=empresa.cnae_principal,
        logo_url=empresa.logo_url,
        # Campos SMTP (exceto senha por segurança)
        smtp_server=empresa.smtp_server,
        smtp_port=empresa.smtp_port,
        smtp_user=empresa.smtp_user,
        ambiente_nfcom=getattr(empresa, 'ambiente_nfcom', 'producao'),
        user_id=empresa.user_id,
        is_active=empresa.is_active,
        created_at=empresa.created_at,
        updated_at=empresa.updated_at,
        # Flags para indicar presença de configuração sensível (sem expor valores)
        certificado_configurado=bool(empresa.certificado_path),
        certificado_senha_configurada=bool(empresa.certificado_senha),
        smtp_configurado=bool(empresa.smtp_server),
        smtp_password_configurada=bool(empresa.smtp_password),
    )
    return ns


def get_empresa(db: Session, empresa_id: int):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if empresa:
        return _decrypt_sensitive_fields(empresa)
    return None


def get_empresa_raw(db: Session, empresa_id: int):
    """Busca uma empresa pelo ID sem qualquer transformação (ORM object)."""
    return db.query(Empresa).filter(Empresa.id == empresa_id).first()


def get_empresa_by_cnpj(db: Session, cnpj: str):
    empresa = db.query(Empresa).filter(Empresa.cnpj == cnpj).first()
    if empresa:
        return _decrypt_sensitive_fields(empresa)
    return None


def get_empresas(db: Session, skip: int = 0, limit: int = 100):
    empresas = db.query(Empresa).offset(skip).limit(limit).all()
    return [_decrypt_sensitive_fields(empresa) for empresa in empresas]

def create_empresa(db: Session, empresa: EmpresaCreate, user_id: int):
    # Criar a empresa com o user_id
    empresa_data = empresa.model_dump()
    empresa_data['user_id'] = user_id

    # Criptografar senhas sensíveis antes de salvar
    if empresa_data.get('certificado_senha'):
        empresa_data['certificado_senha'] = encrypt_sensitive_data(empresa_data['certificado_senha'])
    if empresa_data.get('smtp_password'):
        empresa_data['smtp_password'] = encrypt_sensitive_data(empresa_data['smtp_password'])

    db_empresa = Empresa(**empresa_data)
    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)

    # Criar automaticamente a associação UsuarioEmpresa com is_admin=True
    usuario_empresa = UsuarioEmpresa(
        usuario_id=user_id,
        empresa_id=db_empresa.id,
        is_admin=True
    )
    db.add(usuario_empresa)
    db.commit()

    return db_empresa

def update_empresa(db: Session, db_obj: Empresa, obj_in: EmpresaUpdate):
    update_data = obj_in.model_dump(exclude_unset=True)

    # Criptografar senhas sensíveis antes de atualizar
    # Only encrypt and set sensitive fields when a non-empty value is provided.
    # This prevents accidental clearing/overwriting when the client does not supply them.
    sensitive_fields = {'certificado_senha', 'smtp_password', 'certificado_path'}

    # Encrypt sensitive passwords if provided and non-empty
    if 'certificado_senha' in update_data and update_data.get('certificado_senha'):
        update_data['certificado_senha'] = encrypt_sensitive_data(update_data['certificado_senha'])
    if 'smtp_password' in update_data and update_data.get('smtp_password'):
        update_data['smtp_password'] = encrypt_sensitive_data(update_data['smtp_password'])

    for field, value in update_data.items():
        # Skip updating sensitive fields when value is None or empty string
        if field in sensitive_fields and (value is None or (isinstance(value, str) and value.strip() == '')):
            continue
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_empresas_by_usuario(db: Session, usuario_id: int, skip: int = 0, limit: int = 100):
    """Obtém empresas associadas a um usuário específico."""
    # Retorna empresas onde o usuário é associado via UsuarioEmpresa
    # ou onde ele é o dono/criador (Empresa.user_id)
    empresas = (
        db.query(Empresa)
        .outerjoin(UsuarioEmpresa, UsuarioEmpresa.empresa_id == Empresa.id)
        .filter((UsuarioEmpresa.usuario_id == usuario_id) | (Empresa.user_id == usuario_id))
        .offset(skip)
        .limit(limit)
        .all()
    )
    # REMOVIDO: Não descriptografar. O schema cuidará da exclusão.
    return empresas

def delete_empresa(db: Session, db_obj: Empresa):
    """Deleta uma empresa e suas entidades relacionadas de forma segura.

    Estratégia:
    - Deleta NFCom via ORM (para aproveitar cascade em itens e faturas).
    - Deleta Clientes via ORM (endereços têm cascade configurado no modelo).
    - Deleta associações em UsuarioEmpresa.
    - Deleta a própria Empresa.
    """
    empresa_id = db_obj.id

    # Deletar NFComs relacionados usando ORM para respeitar cascade em itens e faturas
    nfs = db.query(NFCom).filter(NFCom.empresa_id == empresa_id).all()
    for nf in nfs:
        db.delete(nf)

    # Deletar Clientes (endereços têm cascade "all, delete-orphan")
    clientes = db.query(Cliente).filter(Cliente.empresa_id == empresa_id).all()
    for cliente in clientes:
        db.delete(cliente)

    # Deletar associações usuário-empresa
    db.query(UsuarioEmpresa).filter(UsuarioEmpresa.empresa_id == empresa_id).delete(synchronize_session=False)

    # Finalmente deletar a empresa
    db.delete(db_obj)
    db.commit()


def associar_usuario(db: Session, associacao: UsuarioEmpresaCreate):
    """Cria uma associação entre usuário e empresa se ainda não existir."""
    # Verificar existência
    exists = db.query(UsuarioEmpresa).filter(
        UsuarioEmpresa.usuario_id == associacao.usuario_id,
        UsuarioEmpresa.empresa_id == associacao.empresa_id
    ).first()
    if exists:
        return exists

    usuario_empresa = UsuarioEmpresa(
        usuario_id=associacao.usuario_id,
        empresa_id=associacao.empresa_id,
        is_admin=getattr(associacao, 'is_admin', False)
    )
    db.add(usuario_empresa)
    db.commit()
    return usuario_empresa


def empresa_tem_certificado(db: Session, empresa_id: int) -> bool:
    """Verifica se uma empresa tem certificado digital configurado."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        return False
    return bool(empresa.certificado_path and empresa.certificado_path.strip())
