from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, String
from app.models.models import Cliente, EmpresaCliente, EmpresaClienteEndereco
from app.schemas.cliente import ClienteCreate, ClienteUpdate
from app.core.validators import clean_string

def get_cliente(db: Session, cliente_id: int):
    return db.query(Cliente).filter(Cliente.id == cliente_id).first()

def get_clientes_by_empresa(db: Session, empresa_id: int, q: str = None, skip: int = 0, limit: int = 100):
    # Retorna clientes associados à empresa via empresa_clientes OU clientes legacy (empresa_id)
    from sqlalchemy import select
    # Use scalar_subquery() to produce a scalar SELECT usable inside IN() without coercion warnings
    subquery = select(EmpresaCliente.cliente_id).where(EmpresaCliente.empresa_id == empresa_id).scalar_subquery()

    query = (
        db.query(Cliente)
        .filter(
            or_(
                # Clientes com associações EmpresaCliente
                Cliente.id.in_(subquery),
                # Clientes legacy (diretamente associados via empresa_id)
                Cliente.empresa_id == empresa_id
            )
        )
    )

    if q:
        query = query.filter(
            or_(
                Cliente.nome_razao_social.ilike(f"%{q}%"),
                Cliente.cpf_cnpj.ilike(f"%{q}%"),
                Cliente.id.cast(String).ilike(f"%{q}%"),
                Cliente.email.ilike(f"%{q}%"),
                Cliente.telefone.ilike(f"%{q}%")
            )
        )

    return query.offset(skip).limit(limit).all()

def create_cliente(db: Session, cliente: ClienteCreate, empresa_id: int, created_by_user_id: int = None):
    """Cria um Cliente global se não existir e cria/garante a associação EmpresaCliente.

    Também cria os endereços em EmpresaClienteEndereco vinculados à associação.
    """
    # DEBUG: log received enderecos for troubleshooting
    try:
        print(f"DEBUG crud.create_cliente: received enderecos={getattr(cliente, 'enderecos', None)}")
    except Exception:
        pass
    cliente_data = cliente.model_dump(exclude={"enderecos"})

    # Procurar cliente global por CPF/CNPJ
    cpf_cnpj = cliente_data.get('cpf_cnpj')
    db_cliente = None
    if cpf_cnpj:
        db_cliente = db.query(Cliente).filter(Cliente.cpf_cnpj == cpf_cnpj).first()

    # Se não existir, criar Cliente (legacy: define empresa_id como a empresa que está criando)
    if not db_cliente:
        db_cliente = Cliente(**cliente_data, empresa_id=empresa_id)
        db.add(db_cliente)
        db.flush()  # garante que db_cliente.id exista

    # Garantir que exista uma associação empresa_cliente
    empresa_cliente = (
        db.query(EmpresaCliente)
        .filter(EmpresaCliente.empresa_id == empresa_id, EmpresaCliente.cliente_id == db_cliente.id)
        .first()
    )
    if not empresa_cliente:
        empresa_cliente = EmpresaCliente(
            empresa_id=empresa_id,
            cliente_id=db_cliente.id,
            created_by_user_id=created_by_user_id,
            is_active=True,
        )
        db.add(empresa_cliente)
        db.flush()

    # Criar endereços como EmpresaClienteEndereco vinculados à associação
    for endereco_data in cliente.enderecos:
        e_data = endereco_data.model_dump()
        # reuse helper to ensure sanitization/normalization
        try:
            create_endereco_for_empresa_cliente(db, empresa_id=empresa_id, cliente_id=db_cliente.id, endereco_data=e_data)
        except Exception:
            # fallback: attempt raw insert (keeps previous behavior if helper fails)
            e_data['empresa_cliente_id'] = empresa_cliente.id
            e = EmpresaClienteEndereco(**e_data)
            db.add(e)

    db.commit()
    db.refresh(db_cliente)
    return db_cliente

def update_cliente(db: Session, db_obj: Cliente, obj_in: ClienteUpdate):
    update_data = obj_in.model_dump(exclude_unset=True)
    for field in update_data:
        setattr(db_obj, field, update_data[field])
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete_cliente(db: Session, db_obj: Cliente):
    db.delete(db_obj)
    db.commit()
    return db_obj


def get_empresa_cliente(db: Session, empresa_id: int, cliente_id: int):
    return (
        db.query(EmpresaCliente)
        .filter(EmpresaCliente.empresa_id == empresa_id, EmpresaCliente.cliente_id == cliente_id)
        .first()
    )


def get_empresa_cliente_by_id(db: Session, empresa_cliente_id: int):
    return db.query(EmpresaCliente).filter(EmpresaCliente.id == empresa_cliente_id).first()


def get_enderecos_by_empresa_cliente(db: Session, empresa_cliente_id: int):
    return (
        db.query(EmpresaClienteEndereco)
        .filter(EmpresaClienteEndereco.empresa_cliente_id == empresa_cliente_id)
        .all()
    )


def create_endereco_for_empresa_cliente(db: Session, empresa_id: int, cliente_id: int, endereco_data: dict):
    """Cria um endereco vinculado à associação empresa_cliente.

    endereco_data deve ser um dict compatível com EmpresaClienteEndereco columns.
    """
    empresa_cliente = get_empresa_cliente(db, empresa_id, cliente_id)
    if not empresa_cliente:
        raise ValueError("Associação empresa-cliente não encontrada")
    # sanitize and normalize some fields
    endereco_data['empresa_cliente_id'] = empresa_cliente.id
    try:
        if 'cep' in endereco_data and endereco_data['cep']:
            endereco_data['cep'] = ''.join([c for c in str(endereco_data['cep']) if c.isdigit()])
        if 'uf' in endereco_data and endereco_data['uf']:
            endereco_data['uf'] = str(endereco_data['uf']).upper()
        if 'codigo_ibge' in endereco_data and endereco_data['codigo_ibge']:
            endereco_data['codigo_ibge'] = ''.join([c for c in str(endereco_data['codigo_ibge']) if c.isdigit()])
        # normalize textual address fields: endereco, complemento, bairro -> trimmed, single spaces, UPPER
        if 'endereco' in endereco_data and endereco_data.get('endereco'):
            try:
                endereco_data['endereco'] = clean_string(str(endereco_data['endereco'])).upper()
            except Exception:
                pass
        if 'complemento' in endereco_data and endereco_data.get('complemento'):
            try:
                endereco_data['complemento'] = clean_string(str(endereco_data['complemento'])).upper()
            except Exception:
                pass
        if 'bairro' in endereco_data and endereco_data.get('bairro'):
            try:
                endereco_data['bairro'] = clean_string(str(endereco_data['bairro'])).upper()
            except Exception:
                pass
    except Exception:
        pass

    # DEBUG log
    try:
        print(f"DEBUG crud.create_endereco_for_empresa_cliente: empresa_id={empresa_id} cliente_id={cliente_id} data={endereco_data}")
    except Exception:
        pass

    e = EmpresaClienteEndereco(**endereco_data)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def update_endereco_for_empresa_cliente(db: Session, endereco_id: int, empresa_id: int, cliente_id: int, update_data: dict):
    # garantir que o endereco pertence à associação pedida
    endereco = db.query(EmpresaClienteEndereco).filter(EmpresaClienteEndereco.id == endereco_id).first()
    if not endereco:
        return None
    empresa_cliente = get_empresa_cliente(db, empresa_id, cliente_id)
    if not empresa_cliente or endereco.empresa_cliente_id != empresa_cliente.id:
        raise ValueError('Endereço não pertence à associação especificada')
    # sanitize input and only update allowed fields
    allowed = {'descricao', 'endereco', 'numero', 'complemento', 'bairro', 'municipio', 'uf', 'cep', 'codigo_ibge', 'is_principal'}
    sanitized: dict = {}
    for k, v in (update_data or {}).items():
        if k in allowed:
            sanitized[k] = v

    # normalize common fields
    if 'cep' in sanitized and sanitized['cep'] is not None:
        try:
            sanitized['cep'] = ''.join([c for c in str(sanitized['cep']) if c.isdigit()])
        except Exception:
            pass
    if 'uf' in sanitized and sanitized['uf'] is not None:
        try:
            sanitized['uf'] = str(sanitized['uf']).upper()
        except Exception:
            pass
    if 'codigo_ibge' in sanitized and sanitized['codigo_ibge'] is not None:
        try:
            sanitized['codigo_ibge'] = ''.join([c for c in str(sanitized['codigo_ibge']) if c.isdigit()])
        except Exception:
            pass
    # normalize textual address fields: endereco, complemento, bairro -> trimmed, single spaces, UPPER
    if 'endereco' in sanitized and sanitized.get('endereco') is not None:
        try:
            sanitized['endereco'] = clean_string(str(sanitized['endereco'])).upper()
        except Exception:
            pass
    if 'complemento' in sanitized and sanitized.get('complemento') is not None:
        try:
            sanitized['complemento'] = clean_string(str(sanitized['complemento'])).upper()
        except Exception:
            pass
    if 'bairro' in sanitized and sanitized.get('bairro') is not None:
        try:
            sanitized['bairro'] = clean_string(str(sanitized['bairro'])).upper()
        except Exception:
            pass

    # DEBUG log before update
    try:
        print(f"DEBUG crud.update_endereco_for_empresa_cliente: endereco_id={endereco_id} empresa_id={empresa_id} cliente_id={cliente_id} update={sanitized}")
    except Exception:
        pass

    for k, v in sanitized.items():
        setattr(endereco, k, v)
    db.add(endereco)
    db.commit()
    db.refresh(endereco)
    try:
        print(f"DEBUG crud.update_endereco_for_empresa_cliente: updated endereco id={endereco.id}")
    except Exception:
        pass
    return endereco


def delete_endereco_for_empresa_cliente(db: Session, endereco_id: int, empresa_id: int, cliente_id: int):
    endereco = db.query(EmpresaClienteEndereco).filter(EmpresaClienteEndereco.id == endereco_id).first()
    if not endereco:
        return None
    empresa_cliente = get_empresa_cliente(db, empresa_id, cliente_id)
    if not empresa_cliente or endereco.empresa_cliente_id != empresa_cliente.id:
        raise ValueError('Endereço não pertence à associação especificada')
    db.delete(endereco)
    db.commit()
    return endereco


def delete_empresa_cliente(db: Session, empresa_id: int, cliente_id: int, remove_orphan_cliente: bool = False):
    empresa_cliente = get_empresa_cliente(db, empresa_id, cliente_id)
    if not empresa_cliente:
        return None
    # deletar endereços vinculados
    db.query(EmpresaClienteEndereco).filter(EmpresaClienteEndereco.empresa_cliente_id == empresa_cliente.id).delete()
    db.delete(empresa_cliente)
    db.commit()
    if remove_orphan_cliente:
        # se não houver outras associações, deletar cliente global
        remaining = db.query(EmpresaCliente).filter(EmpresaCliente.cliente_id == cliente_id).count()
        if remaining == 0:
            cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
            if cliente:
                db.delete(cliente)
                db.commit()
    return True


def get_cliente_by_cpf_cnpj_and_empresa(db: Session, cpf_cnpj: str, empresa_id: int):
    """Busca cliente por CPF/CNPJ e empresa (considerando a constraint única)."""
    # Primeiro tenta buscar exatamente como fornecido
    cliente = db.query(Cliente).filter(
        Cliente.empresa_id == empresa_id,
        Cliente.cpf_cnpj == cpf_cnpj
    ).first()

    if cliente:
        return cliente

    # Se não encontrou, tenta com a versão limpa (somente dígitos)
    cpf_cnpj_clean = ''.join(filter(str.isdigit, cpf_cnpj))
    if cpf_cnpj_clean != cpf_cnpj:  # Só busca se for diferente
        cliente = db.query(Cliente).filter(
            Cliente.empresa_id == empresa_id,
            Cliente.cpf_cnpj == cpf_cnpj_clean
        ).first()
        if cliente:
            return cliente

    # Se ainda não encontrou, tenta buscar por versões formatadas
    # (para casos onde o CPF está armazenado formatado mas a entrada não está)
    if len(cpf_cnpj_clean) == 11:  # CPF
        cpf_formatado = f"{cpf_cnpj_clean[:3]}.{cpf_cnpj_clean[3:6]}.{cpf_cnpj_clean[6:9]}-{cpf_cnpj_clean[9:]}"
        cliente = db.query(Cliente).filter(
            Cliente.empresa_id == empresa_id,
            Cliente.cpf_cnpj == cpf_formatado
        ).first()

    return cliente
