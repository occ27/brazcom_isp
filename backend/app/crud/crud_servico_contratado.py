from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from fastapi import HTTPException, status
from datetime import datetime, date
from app.models import models
from app.schemas import servico_contratado as sc_schema
from app.crud import crud_servico
import unicodedata
import re


MAX_LIMIT = 200


def _normalize_text(value: str, max_len: int = None) -> str:
    """Normalize a text field following NFCom standards:
    - strip, collapse multiple spaces
    - remove accents
    - uppercase
    - truncate to max_len if provided
    """
    if value is None:
        return value
    # ensure str
    v = str(value).strip()
    # collapse whitespace
    v = re.sub(r"\s+", " ", v)
    # remove accents
    v = unicodedata.normalize('NFKD', v)
    v = ''.join([c for c in v if not unicodedata.combining(c)])
    # uppercase
    v = v.upper()
    if max_len is not None and len(v) > max_len:
        v = v[:max_len]
    return v


def get_servico_contratado(db: Session, contrato_id: int, empresa_id: int = None):
    q = db.query(models.ServicoContratado).filter(models.ServicoContratado.id == contrato_id)
    if empresa_id is not None:
        q = q.filter(models.ServicoContratado.empresa_id == empresa_id)
    return q.first()


def get_servicos_contratados_by_empresa(db: Session, empresa_id: int = None, qstr: str = None, skip: int = 0, limit: int = 100, dia_vencimento_min: int = None, dia_vencimento_max: int = None):
    if limit is None:
        limit = 100
    limit = min(int(limit), MAX_LIMIT)
    skip = max(int(skip or 0), 0)
    # Include client basic info plus the principal address (if available via EmpresaCliente -> EmpresaClienteEndereco)
    q = db.query(
        models.ServicoContratado,
        models.Cliente.nome_razao_social.label('cliente_nome'),
        models.Cliente.cpf_cnpj.label('cliente_cpf_cnpj'),
        models.Cliente.telefone.label('cliente_telefone'),
        models.Cliente.inscricao_estadual.label('cliente_inscricao_estadual'),
        models.Cliente.nome_razao_social.label('cliente_razao_social'),
        models.EmpresaClienteEndereco.endereco.label('cliente_endereco'),
        models.EmpresaClienteEndereco.numero.label('cliente_numero'),
        models.EmpresaClienteEndereco.bairro.label('cliente_bairro'),
        models.EmpresaClienteEndereco.municipio.label('cliente_municipio'),
        models.EmpresaClienteEndereco.uf.label('cliente_uf'),
        models.Servico.descricao.label('servico_descricao'),
        models.Servico.codigo.label('servico_codigo')
    ).join(
        models.Cliente, models.ServicoContratado.cliente_id == models.Cliente.id
    ).join(
        models.Servico, models.ServicoContratado.servico_id == models.Servico.id
    ).outerjoin(
        models.EmpresaCliente,
        and_(models.EmpresaCliente.cliente_id == models.Cliente.id,
             models.EmpresaCliente.empresa_id == models.ServicoContratado.empresa_id)
    ).outerjoin(
        models.EmpresaClienteEndereco,
        and_(models.EmpresaClienteEndereco.empresa_cliente_id == models.EmpresaCliente.id,
             models.EmpresaClienteEndereco.is_principal == True)
    )
    if empresa_id is not None:
        q = q.filter(models.ServicoContratado.empresa_id == empresa_id)
    if qstr:
        pattern = f"%{qstr}%"
        q = q.filter(or_(
            models.ServicoContratado.numero_contrato.ilike(pattern),
            models.Cliente.nome_razao_social.ilike(pattern),
            models.Servico.descricao.ilike(pattern),
            models.Servico.codigo.ilike(pattern),
            models.EmpresaClienteEndereco.municipio.ilike(pattern)  # Include city in search
        ))
    # Filter by dia_vencimento if provided (new field). If not present in rows, legacy 'vencimento' date can be used
    if dia_vencimento_min is not None:
        q = q.filter(models.ServicoContratado.dia_vencimento >= dia_vencimento_min)
    if dia_vencimento_max is not None:
        q = q.filter(models.ServicoContratado.dia_vencimento <= dia_vencimento_max)
    results = q.offset(skip).limit(limit).all()

    # Convert to dict format expected by Pydantic
    contratos = []
    for row in results:
        (
            contrato,
            cliente_nome,
            cliente_cpf_cnpj,
            cliente_telefone,
            cliente_inscricao_estadual,
            cliente_razao_social,
            cliente_endereco,
            cliente_numero,
            cliente_bairro,
            cliente_municipio,
            cliente_uf,
            servico_descricao,
            servico_codigo
        ) = row

        contrato_dict = {
            **{k: v for k, v in contrato.__dict__.items() if not k.startswith('_')},
            'cliente_nome': cliente_nome,
            'cliente_razao_social': cliente_razao_social,
            'cliente_cpf_cnpj': cliente_cpf_cnpj,
            'cliente_telefone': cliente_telefone,
            'cliente_inscricao_estadual': cliente_inscricao_estadual,
            'cliente_endereco': cliente_endereco,
            'cliente_numero': cliente_numero,
            'cliente_bairro': cliente_bairro,
            'cliente_municipio': cliente_municipio,
            'cliente_uf': cliente_uf,
            'servico_descricao': servico_descricao,
            'servico_codigo': servico_codigo
        }
        contratos.append(contrato_dict)

    return contratos


def count_servicos_contratados_by_empresa(db: Session, empresa_id: int = None, qstr: str = None, dia_vencimento_min: int = None, dia_vencimento_max: int = None) -> int:
    # Build a query similar to get_servicos_contratados_by_empresa to ensure counts match list filters
    q = db.query(models.ServicoContratado).join(
        models.Cliente, models.ServicoContratado.cliente_id == models.Cliente.id
    ).join(
        models.Servico, models.ServicoContratado.servico_id == models.Servico.id
    ).outerjoin(
        models.EmpresaCliente,
        and_(models.EmpresaCliente.cliente_id == models.Cliente.id,
             models.EmpresaCliente.empresa_id == models.ServicoContratado.empresa_id)
    ).outerjoin(
        models.EmpresaClienteEndereco,
        and_(models.EmpresaClienteEndereco.empresa_cliente_id == models.EmpresaCliente.id,
             models.EmpresaClienteEndereco.is_principal == True)
    )
    if empresa_id is not None:
        q = q.filter(models.ServicoContratado.empresa_id == empresa_id)
    if qstr:
        pattern = f"%{qstr}%"
        q = q.filter(or_(
            models.ServicoContratado.numero_contrato.ilike(pattern),
            models.Cliente.nome_razao_social.ilike(pattern),
            models.Cliente.cpf_cnpj.ilike(pattern),
            models.Servico.descricao.ilike(pattern),
            models.Servico.codigo.ilike(pattern),
            models.EmpresaClienteEndereco.municipio.ilike(pattern)  # Include city in search
        ))
    return q.count()


def create_servico_contratado(db: Session, contrato_in: sc_schema.ServicoContratadoCreate, empresa_id: int = None, created_by_user_id: int = None):
    data = contrato_in.model_dump()
    if empresa_id is not None:
        data['empresa_id'] = empresa_id
    
    # Validação: empresa_id obrigatório
    if not data.get('empresa_id'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="empresa_id é obrigatório."
        )
    
    # Validação: cliente_id obrigatório e existente
    if not data.get('cliente_id'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cliente_id é obrigatório."
        )
    db_cliente = db.query(models.Cliente).filter(models.Cliente.id == data['cliente_id']).first()
    if not db_cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cliente com ID {data['cliente_id']} não encontrado."
        )
    
    # Validação: servico_id obrigatório e existente
    if not data.get('servico_id'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="servico_id é obrigatório."
        )
    db_servico = db.query(models.Servico).filter(models.Servico.id == data['servico_id']).first()
    if not db_servico:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Serviço com ID {data['servico_id']} não encontrado."
        )
    
    # Validação: valor_unitario obrigatório e positivo
    if data.get('valor_unitario') is None or data['valor_unitario'] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="valor_unitario é obrigatório e deve ser maior que zero."
        )
    
    # Normalização: numero_contrato
    if 'numero_contrato' in data and data['numero_contrato'] is not None:
        data['numero_contrato'] = _normalize_text(str(data['numero_contrato']), max_len=50)
    
    # Normalização: periodicidade
    if 'periodicidade' in data and data['periodicidade'] is not None:
        data['periodicidade'] = _normalize_text(str(data['periodicidade']), max_len=20)
    
    # Validação: dia_emissao (se fornecido, deve estar entre 1 e 31)
    if data.get('dia_emissao') is not None:
        dia = int(data['dia_emissao'])
        if dia < 1 or dia > 31:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="dia_emissao deve estar entre 1 e 31."
            )
    
    # Validação: quantidade positiva
    if data.get('quantidade') is not None and data['quantidade'] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="quantidade deve ser maior que zero."
        )
    
    # Validação de datas: d_contrato_fim >= d_contrato_ini
    if data.get('d_contrato_ini') and data.get('d_contrato_fim'):
        try:
            # Convert strings to date if needed
            d_ini = data['d_contrato_ini'] if isinstance(data['d_contrato_ini'], date) else datetime.strptime(str(data['d_contrato_ini']), '%Y-%m-%d').date()
            d_fim = data['d_contrato_fim'] if isinstance(data['d_contrato_fim'], date) else datetime.strptime(str(data['d_contrato_fim']), '%Y-%m-%d').date()
            if d_fim < d_ini:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="d_contrato_fim deve ser maior ou igual a d_contrato_ini."
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato de data inválido: {str(e)}"
            )
    
    # Compute valor_total if not provided
    try:
        if data.get('valor_total') in (None, ''):
            qty = float(data.get('quantidade') or 1)
            vu = float(data.get('valor_unitario') or 0)
            data['valor_total'] = round(qty * vu, 2)
    except Exception:
        data['valor_total'] = None

    data['created_by_user_id'] = created_by_user_id

    db_obj = models.ServicoContratado(**data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_servico_contratado(db: Session, db_obj: models.ServicoContratado, obj_in: sc_schema.ServicoContratadoUpdate):
    update_data = obj_in.model_dump(exclude_unset=True)
    
    # Validação: cliente_id (se fornecido, deve existir)
    if 'cliente_id' in update_data and update_data['cliente_id'] is not None:
        db_cliente = db.query(models.Cliente).filter(models.Cliente.id == update_data['cliente_id']).first()
        if not db_cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente com ID {update_data['cliente_id']} não encontrado."
            )
    
    # Validação: servico_id (se fornecido, deve existir)
    if 'servico_id' in update_data and update_data['servico_id'] is not None:
        db_servico = db.query(models.Servico).filter(models.Servico.id == update_data['servico_id']).first()
        if not db_servico:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Serviço com ID {update_data['servico_id']} não encontrado."
            )
    
    # Validação: valor_unitario (se fornecido, deve ser positivo)
    if 'valor_unitario' in update_data and update_data['valor_unitario'] is not None and update_data['valor_unitario'] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="valor_unitario deve ser maior que zero."
        )
    
    # Normalização: numero_contrato
    if 'numero_contrato' in update_data and update_data['numero_contrato'] is not None:
        update_data['numero_contrato'] = _normalize_text(str(update_data['numero_contrato']), max_len=50)
    
    # Normalização: periodicidade
    if 'periodicidade' in update_data and update_data['periodicidade'] is not None:
        update_data['periodicidade'] = _normalize_text(str(update_data['periodicidade']), max_len=20)
    
    # Validação: dia_emissao (se fornecido, deve estar entre 1 e 31)
    if 'dia_emissao' in update_data and update_data['dia_emissao'] is not None:
        dia = int(update_data['dia_emissao'])
        if dia < 1 or dia > 31:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="dia_emissao deve estar entre 1 e 31."
            )
    
    # Validação: quantidade positiva
    if 'quantidade' in update_data and update_data['quantidade'] is not None and update_data['quantidade'] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="quantidade deve ser maior que zero."
        )
    
    # Validação de datas: d_contrato_fim >= d_contrato_ini
    # Determine current values (from db_obj) and override with updates
    d_ini = update_data.get('d_contrato_ini', db_obj.d_contrato_ini)
    d_fim = update_data.get('d_contrato_fim', db_obj.d_contrato_fim)
    if d_ini and d_fim:
        try:
            # Convert strings to date if needed
            if isinstance(d_ini, str):
                d_ini = datetime.strptime(d_ini, '%Y-%m-%d').date()
            if isinstance(d_fim, str):
                d_fim = datetime.strptime(d_fim, '%Y-%m-%d').date()
            if d_fim < d_ini:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="d_contrato_fim deve ser maior ou igual a d_contrato_ini."
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato de data inválido: {str(e)}"
            )
    
    for field, val in update_data.items():
        if hasattr(db_obj, field):
            setattr(db_obj, field, val)
    
    # Recalculate valor_total if qty or valor_unitario changed
    try:
        if ('valor_total' not in update_data) and (('quantidade' in update_data) or ('valor_unitario' in update_data)):
            qty = float(getattr(db_obj, 'quantidade') or 1)
            vu = float(getattr(db_obj, 'valor_unitario') or 0)
            db_obj.valor_total = round(qty * vu, 2)
    except Exception:
        pass

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_servico_contratado(db: Session, db_obj: models.ServicoContratado):
    db.delete(db_obj)
    db.commit()


def find_due_for_emission(db: Session, empresa_id: int = None, limit: int = 100):
    # returns contratos with next_emission <= now and auto_emit = True and is_active = True
    q = db.query(models.ServicoContratado).filter(models.ServicoContratado.auto_emit == True, models.ServicoContratado.is_active == True)
    q = q.filter(models.ServicoContratado.next_emission != None)
    q = q.filter(models.ServicoContratado.next_emission <= datetime.utcnow())
    if empresa_id is not None:
        q = q.filter(models.ServicoContratado.empresa_id == empresa_id)
    return q.limit(limit).all()


def get_servicos_contratados_by_cliente(db: Session, cliente_id: int, empresa_id: int = None, cidade: str = None):
    """Retorna os serviços contratados ativos para um cliente específico."""
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"CRUD: get_servicos_contratados_by_cliente chamado com cliente_id={cliente_id}, empresa_id={empresa_id}")

    q = db.query(
        models.ServicoContratado,
        models.Servico.descricao.label('servico_descricao'),
        models.Servico.codigo.label('servico_codigo'),
        models.Servico.unidade_medida.label('servico_unidade'),
        models.Servico.cfop.label('servico_cfop'),
        models.Servico.ncm.label('servico_ncm'),
        models.Servico.base_calculo_icms_default.label('servico_base_calculo_icms_default'),
        models.Servico.aliquota_icms_default.label('servico_aliquota_icms_default'),
        models.Servico.valor_desconto_default.label('servico_valor_desconto_default'),
        models.Servico.valor_outros_default.label('servico_valor_outros_default')
    ).join(
        models.Servico, models.ServicoContratado.servico_id == models.Servico.id
    ).filter(
        models.ServicoContratado.cliente_id == cliente_id,
        models.ServicoContratado.is_active == True
    )

    if empresa_id is not None:
        q = q.filter(models.ServicoContratado.empresa_id == empresa_id)

    # If filtering by city, join EmpresaCliente and EmpresaClienteEndereco to check principal address
    if cidade:
        q = q.join(
            models.EmpresaCliente,
            and_(models.EmpresaCliente.cliente_id == models.ServicoContratado.cliente_id,
                 models.EmpresaCliente.empresa_id == models.ServicoContratado.empresa_id)
        ).join(
            models.EmpresaClienteEndereco,
            and_(models.EmpresaClienteEndereco.empresa_cliente_id == models.EmpresaCliente.id,
                 models.EmpresaClienteEndereco.is_principal == True)
        )
        pattern_city = f"%{cidade}%"
        q = q.filter(models.EmpresaClienteEndereco.municipio.ilike(pattern_city))

    # Debug: print the SQL query
    logger.info(f"SQL Query: {q}")

    try:
        results = q.all()
        logger.info(f"Query executada com sucesso, {len(results)} resultados")

        if results:
            logger.info(f"Primeiro resultado tipo: {type(results[0])}")
            logger.info(f"Primeiro resultado: {results[0]}")
    except Exception as e:
        logger.error(f"Erro na execução da query: {e}", exc_info=True)
        raise

    # Convert to dict format with service details
    contratos = []
    for row in results:
        # Safely unpack the row - it should have 10 elements
        if len(row) != 10:
            logger.warning(f"Aviso: Esperado 10 elementos na linha, mas recebeu {len(row)}")
            continue

        contrato = row[0]
        servico_descricao = row[1]
        servico_codigo = row[2]
        servico_unidade = row[3]
        servico_cfop = row[4]
        servico_ncm = row[5]
        servico_base_calculo_icms_default = row[6]
        servico_aliquota_icms_default = row[7]
        servico_valor_desconto_default = row[8]
        servico_valor_outros_default = row[9]

        logger.debug(f"Processando contrato ID {contrato.id}, serviço {contrato.servico_id}")

        contrato_dict = {
            **{k: v for k, v in contrato.__dict__.items() if not k.startswith('_')},
            'servico_descricao': servico_descricao,
            'servico_codigo': servico_codigo,
            'servico_unidade': servico_unidade,
            'servico_cfop': servico_cfop,
            'servico_ncm': servico_ncm,
            'servico_base_calculo_icms_default': servico_base_calculo_icms_default,
            'servico_aliquota_icms_default': servico_aliquota_icms_default,
            'servico_valor_desconto_default': servico_valor_desconto_default,
            'servico_valor_outros_default': servico_valor_outros_default
        }
        contratos.append(contrato_dict)

    logger.info(f"Retornando {len(contratos)} contratos processados")
    return contratos
