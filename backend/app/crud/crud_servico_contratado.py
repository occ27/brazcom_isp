from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from fastapi import HTTPException, status
from datetime import datetime, date
from typing import Optional
from app.models import models
from app.models.ftth import OLT, CTO
from app.schemas import servico_contratado as sc_schema
from app.crud import crud_servico
import unicodedata
import re
import logging

logger = logging.getLogger(__name__)


def _resolve_ftth_fks(db: Session, data: dict) -> dict:
    """
    Se olt_id ou cto_id foram informados, resolve os registros cadastrados
    e auto-preenche olt_nome, olt_pon, cto_nome e cto_porta a partir deles.
    Isso garante que o monitoramento FTTH encontre o contrato pelo registro FK.
    """
    if data.get('olt_id'):
        olt = db.query(OLT).filter(OLT.id == data['olt_id']).first()
        if not olt:
            raise HTTPException(status_code=404, detail=f"OLT id={data['olt_id']} n\u00e3o encontrada.")
        # Auto-preenche o campo texto para compat. legada (relatórios, display)
        data['olt_nome'] = olt.nome
    elif data.get('olt_id') is None and 'olt_id' in data:
        # olt_id explicitamente enviado como None → limpar FK mas manter texto se preenchido
        pass

    if data.get('cto_id'):
        cto = db.query(CTO).filter(CTO.id == data['cto_id']).first()
        if not cto:
            raise HTTPException(status_code=404, detail=f"CTO id={data['cto_id']} n\u00e3o encontrada.")
        # Auto-preenche campos texto a partir do registro CTO
        data['cto_nome'] = cto.nome
        # Se a CTO tiver porta PON definida e olt_pon não foi preenchido manualmente
        if cto.porta_pon and not data.get('olt_pon'):
            data['olt_pon'] = cto.porta_pon
        # Se a CTO estiver vinculada a uma OLT e olt_id ainda não foi definido
        if cto.olt_id and not data.get('olt_id'):
            data['olt_id'] = cto.olt_id
            olt = db.query(OLT).filter(OLT.id == cto.olt_id).first()
            if olt:
                data['olt_nome'] = olt.nome
    elif data.get('cto_id') is None and 'cto_id' in data:
        pass

    return data


def _sync_radius(contrato: models.ServicoContratado, radius_db, action: str = "sync") -> None:
    """
    Sincroniza o contrato com o FreeRadius, se for um contrato PPPoE
    e se o Router do contrato tiver metodo_autenticacao_padrao = RADIUS.
    """
    if not radius_db:
        return
    if not contrato.pppoe_username:
        return

    if contrato.router_id:
        try:
            from app.core.database import SessionLocal
            from app.crud import crud_router
            _db = SessionLocal()
            try:
                router_db = crud_router.get_router(_db, router_id=contrato.router_id, empresa_id=contrato.empresa_id)
                if router_db and router_db.metodo_autenticacao_padrao and router_db.metodo_autenticacao_padrao != "RADIUS":
                    logger.info(
                        f"[RadiusSync] Contrato {contrato.id}: Router '{router_db.nome}' usa "
                        f"'{router_db.metodo_autenticacao_padrao}' (não RADIUS) — sync ignorado."
                    )
                    return
            finally:
                _db.close()
        except Exception as e:
            logger.warning(f"[RadiusSync] Não foi possível verificar método do router para contrato {contrato.id}: {e}")

    try:
        from app.services.radius_sync_service import RadiusSyncService
        sync = RadiusSyncService(radius_db)

        if action == "delete":
            sync.delete_user(contrato.pppoe_username)
            logger.info(f"[RadiusSync] Contrato {contrato.id}: usuário '{contrato.pppoe_username}' removido do FreeRadius.")
            _kick_mikrotik_session(contrato)

        elif action == "disable":
            sync.disable_user(contrato.pppoe_username)
            logger.info(f"[RadiusSync] Contrato {contrato.id}: usuário '{contrato.pppoe_username}' BLOQUEADO no FreeRadius.")
            _kick_mikrotik_session(contrato)

        else:  # sync
            rate_limit = None
            if contrato.velocidade_garantida:
                rate_limit = contrato.velocidade_garantida

            sync.sync_user(
                username=contrato.pppoe_username,
                password=contrato.pppoe_password or "",
                rate_limit=rate_limit,
                ip_fixo=contrato.assigned_ip,
            )
            logger.info(f"[RadiusSync] Contrato {contrato.id}: usuário '{contrato.pppoe_username}' sincronizado.")

    except Exception as e:
        logger.error(f"[RadiusSync] Erro ao sincronizar contrato {contrato.id} com FreeRadius: {e}")


def _kick_mikrotik_session(contrato: models.ServicoContratado) -> None:
    if not contrato.router_id:
        return
    try:
        from app.core.database import SessionLocal
        from app.crud import crud_router
        from app.mikrotik.controller import MikrotikController
        from app.core.security import decrypt_password

        db = SessionLocal()
        try:
            router_db = crud_router.get_router(db, router_id=contrato.router_id, empresa_id=contrato.empresa_id)
            if not router_db: return
            try:
                password = decrypt_password(router_db.senha) if router_db.senha else ""
            except Exception:
                password = router_db.senha or ""

            mk = MikrotikController(host=router_db.ip, username=router_db.usuario, password=password, port=router_db.porta or 8728)
            mk.disconnect_pppoe_active(contrato.pppoe_username)
            try: mk.close()
            except Exception: pass
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[KickSession] Erro ao encerrar sessão Mikrotik: {e}")


def _normalize_text(value: str, max_len: int = None) -> str:
    if value is None: return value
    v = str(value).strip()
    v = re.sub(r"\s+", " ", v)
    v = unicodedata.normalize('NFKD', v)
    v = ''.join([c for c in v if not unicodedata.combining(c)])
    v = v.upper()
    if max_len is not None and len(v) > max_len: v = v[:max_len]
    return v


def get_servico_contratado(db: Session, contrato_id: int, empresa_id: int = None):
    q = db.query(models.ServicoContratado).options(joinedload(models.ServicoContratado.ativos)).filter(models.ServicoContratado.id == contrato_id)
    if empresa_id is not None:
        q = q.filter(models.ServicoContratado.empresa_id == empresa_id)
    return q.first()


def get_servico_contratado_with_relations(db: Session, contrato_id: int, empresa_id: int = None):
    """Get a single servico contratado with related data and assets."""
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
        models.Servico.codigo.label('servico_codigo'),
        models.BankAccount.id.label('bank_account_id'),
        models.BankAccount.bank.label('bank_account_bank'),
        models.BankAccount.agencia.label('bank_account_agencia'),
        models.BankAccount.conta.label('bank_account_conta')
    ).options(joinedload(models.ServicoContratado.ativos)).join(
        models.Cliente, models.ServicoContratado.cliente_id == models.Cliente.id
    ).join(
        models.Servico, models.ServicoContratado.servico_id == models.Servico.id
    ).outerjoin(
        models.EmpresaCliente,
        and_(models.EmpresaCliente.cliente_id == models.Cliente.id,
             models.EmpresaCliente.empresa_id == models.ServicoContratado.empresa_id)
    ).outerjoin(
        models.EmpresaClienteEndereco,
        or_(
            models.EmpresaClienteEndereco.id == models.ServicoContratado.endereco_id,
            and_(
                models.ServicoContratado.endereco_id.is_(None),
                models.EmpresaClienteEndereco.empresa_cliente_id == models.EmpresaCliente.id,
                models.EmpresaClienteEndereco.is_principal == True
            )
        )
    ).outerjoin(
        models.BankAccount, models.ServicoContratado.bank_account_id == models.BankAccount.id
    ).filter(models.ServicoContratado.id == contrato_id)
    
    if empresa_id is not None:
        q = q.filter(models.ServicoContratado.empresa_id == empresa_id)
    
    row = q.first()
    if not row: return None
        
    contrato = row[0]
    
    contrato_dict = {
        **{k: v for k, v in contrato.__dict__.items() if not k.startswith('_')},
        'cliente_nome': row.cliente_nome,
        'cliente_razao_social': row.cliente_razao_social,
        'cliente_cpf_cnpj': row.cliente_cpf_cnpj,
        'cliente_telefone': row.cliente_telefone,
        'cliente_inscricao_estadual': row.cliente_inscricao_estadual,
        'cliente_endereco': row.cliente_endereco,
        'cliente_numero': row.cliente_numero,
        'cliente_bairro': row.cliente_bairro,
        'cliente_municipio': row.cliente_municipio,
        'cliente_uf': row.cliente_uf,
        'servico_descricao': row.servico_descricao,
        'servico_codigo': row.servico_codigo,
        'bank_account_id': row.bank_account_id,
        'bank_account_bank': row.bank_account_bank,
        'bank_account_agencia': row.bank_account_agencia,
        'bank_account_conta': row.bank_account_conta,
        'ativos': [
            {k: v for k, v in ativo.__dict__.items() if not k.startswith('_')}
            for ativo in (contrato.ativos or [])
        ]
    }
    
    return contrato_dict


def get_servicos_contratados_by_empresa(db: Session, empresa_id: int = None, qstr: str = None, skip: int = 0, limit: int = 100, dia_vencimento_min: int = None, dia_vencimento_max: int = None):
    MAX_LIMIT = 200
    limit = min(int(limit or 100), MAX_LIMIT)
    skip = max(int(skip or 0), 0)
    
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
        models.Servico.codigo.label('servico_codigo'),
        models.BankAccount.id.label('bank_account_id'),
        models.BankAccount.bank.label('bank_account_bank'),
        models.BankAccount.agencia.label('bank_account_agencia'),
        models.BankAccount.conta.label('bank_account_conta')
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
        or_(
            models.EmpresaClienteEndereco.id == models.ServicoContratado.endereco_id,
            and_(
                models.ServicoContratado.endereco_id.is_(None),
                models.EmpresaClienteEndereco.empresa_cliente_id == models.EmpresaCliente.id,
                models.EmpresaClienteEndereco.is_principal == True
            )
        )
    ).outerjoin(
        models.BankAccount, models.ServicoContratado.bank_account_id == models.BankAccount.id
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
            models.EmpresaClienteEndereco.municipio.ilike(pattern)
        ))
    if dia_vencimento_min is not None:
        q = q.filter(models.ServicoContratado.dia_vencimento >= dia_vencimento_min)
    if dia_vencimento_max is not None:
        q = q.filter(models.ServicoContratado.dia_vencimento <= dia_vencimento_max)
        
    results = q.offset(skip).limit(limit).all()
    contratos = []
    for row in results:
        contrato = row[0]
        contrato_dict = {
            **{k: v for k, v in contrato.__dict__.items() if not k.startswith('_')},
            'cliente_nome': row.cliente_nome,
            'cliente_razao_social': row.cliente_razao_social,
            'cliente_cpf_cnpj': row.cliente_cpf_cnpj,
            'cliente_telefone': row.cliente_telefone,
            'cliente_inscricao_estadual': row.cliente_inscricao_estadual,
            'cliente_endereco': row.cliente_endereco,
            'cliente_numero': row.cliente_numero,
            'cliente_bairro': row.cliente_bairro,
            'cliente_municipio': row.cliente_municipio,
            'cliente_uf': row.cliente_uf,
            'servico_descricao': row.servico_descricao,
            'servico_codigo': row.servico_codigo,
            'bank_account_id': row.bank_account_id,
            'bank_account_bank': row.bank_account_bank,
            'bank_account_agencia': row.bank_account_agencia,
            'bank_account_conta': row.bank_account_conta
        }
        contratos.append(contrato_dict)
    return contratos


def count_servicos_contratados_by_empresa(db: Session, empresa_id: int = None, qstr: str = None, dia_vencimento_min: int = None, dia_vencimento_max: int = None) -> int:
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
        or_(
            models.EmpresaClienteEndereco.id == models.ServicoContratado.endereco_id,
            and_(
                models.ServicoContratado.endereco_id.is_(None),
                models.EmpresaClienteEndereco.empresa_cliente_id == models.EmpresaCliente.id,
                models.EmpresaClienteEndereco.is_principal == True
            )
        )
    )
    if empresa_id is not None: q = q.filter(models.ServicoContratado.empresa_id == empresa_id)
    if qstr:
        pattern = f"%{qstr}%"
        q = q.filter(or_(
            models.ServicoContratado.numero_contrato.ilike(pattern),
            models.Cliente.nome_razao_social.ilike(pattern),
            models.Cliente.cpf_cnpj.ilike(pattern),
            models.Servico.descricao.ilike(pattern),
            models.Servico.codigo.ilike(pattern),
            models.EmpresaClienteEndereco.municipio.ilike(pattern)
        ))
    return q.count()


def create_servico_contratado(db: Session, contrato_in: sc_schema.ServicoContratadoCreate, empresa_id: int = None, created_by_user_id: int = None, radius_db=None):
    data = contrato_in.model_dump()
    if empresa_id is not None: data['empresa_id'] = empresa_id
    
    if not data.get('empresa_id'): raise HTTPException(status_code=400, detail="empresa_id é obrigatório.")
    if not data.get('cliente_id'): raise HTTPException(status_code=400, detail="cliente_id é obrigatório.")
    if not data.get('servico_id'): raise HTTPException(status_code=400, detail="servico_id é obrigatório.")
    
    if data.get('valor_unitario') is None or data['valor_unitario'] <= 0:
        raise HTTPException(status_code=400, detail="valor_unitario deve ser maior que zero.")
    
    # Resolver FKs de OLT e CTO (auto-preenche campos texto)
    data = _resolve_ftth_fks(db, data)
    
    # Normalização e Cálculo
    if 'numero_contrato' in data and data['numero_contrato']:
        data['numero_contrato'] = _normalize_text(str(data['numero_contrato']), 50) or None
    if 'periodicidade' in data: data['periodicidade'] = _normalize_text(str(data['periodicidade']), 20)
    
    if not data.get('data_inicio_cobranca') and data.get('d_contrato_ini'):
        data['data_inicio_cobranca'] = data['d_contrato_ini']
    
    try:
        if data.get('valor_total') in (None, ''):
            data['valor_total'] = round(float(data.get('quantidade') or 1) * float(data.get('valor_unitario') or 0), 2)
    except Exception: pass

    data['created_by_user_id'] = created_by_user_id
    ativos_data = data.pop('ativos', []) or []

    db_obj = models.ServicoContratado(**data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    # Se numero_contrato não foi informado, gerar automaticamente com o ID do contrato criado
    if not db_obj.numero_contrato or db_obj.numero_contrato.strip() == '':
        db_obj.numero_contrato = str(db_obj.id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

    for ativo_in in ativos_data:
        ativo_dict = ativo_in if isinstance(ativo_in, dict) else ativo_in.model_dump()
        db_ativo = models.AtivoContrato(**ativo_dict, contrato_id=db_obj.id)
        db.add(db_ativo)
    
    if ativos_data:
        db.commit()
        db.refresh(db_obj)

    if db_obj.status == models.StatusContrato.ATIVO: _sync_radius(db_obj, radius_db, "sync")
    return db_obj


def update_servico_contratado(db: Session, db_obj: models.ServicoContratado, obj_in: sc_schema.ServicoContratadoUpdate, radius_db=None):
    update_data = obj_in.model_dump(exclude_unset=True)
    
    # Resolver FKs de OLT e CTO se foram enviados no update
    if 'olt_id' in update_data or 'cto_id' in update_data:
        update_data = _resolve_ftth_fks(db, update_data)
    
    for field, val in update_data.items():
        if field != 'ativos' and hasattr(db_obj, field):
            setattr(db_obj, field, val)
    
    # Recalculate valor_total
    try:
        if ('valor_total' not in update_data) and (('quantidade' in update_data) or ('valor_unitario' in update_data)):
            db_obj.valor_total = round(float(db_obj.quantidade or 1) * float(db_obj.valor_unitario or 0), 2)
    except Exception: pass

    if 'ativos' in update_data:
        ativos_data = update_data.pop('ativos') or []
        # Limpar a coleção atual para evitar InvalidRequestError
        db_obj.ativos = []
        db.flush()
        for ativo_in in ativos_data:
            ativo_dict = ativo_in if isinstance(ativo_in, dict) else ativo_in.model_dump()
            ativo_dict.pop('id', None)
            db_ativo = models.AtivoContrato(**ativo_dict, contrato_id=db_obj.id)
            db.add(db_ativo)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    novo_status = getattr(db_obj, 'status', None)
    if novo_status in (models.StatusContrato.SUSPENSO, models.StatusContrato.CANCELADO): _sync_radius(db_obj, radius_db, "disable")
    elif novo_status == models.StatusContrato.ATIVO: _sync_radius(db_obj, radius_db, "sync")

    return db_obj


def delete_servico_contratado(db: Session, db_obj: models.ServicoContratado, radius_db=None):
    _sync_radius(db_obj, radius_db, "delete")
    db.delete(db_obj)
    db.commit()


def find_due_for_emission(db: Session, empresa_id: int = None, limit: int = 100):
    q = db.query(models.ServicoContratado).filter(models.ServicoContratado.auto_emit == True, models.ServicoContratado.is_active == True)
    q = q.filter(models.ServicoContratado.next_emission != None, models.ServicoContratado.next_emission <= datetime.utcnow())
    if empresa_id is not None: q = q.filter(models.ServicoContratado.empresa_id == empresa_id)
    return q.limit(limit).all()


def get_servicos_contratados_by_cliente(db: Session, cliente_id: int, empresa_id: int = None, cidade: str = None):
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
    ).join(models.Servico, models.ServicoContratado.servico_id == models.Servico.id).filter(
        models.ServicoContratado.cliente_id == cliente_id, models.ServicoContratado.is_active == True
    )

    if empresa_id is not None: q = q.filter(models.ServicoContratado.empresa_id == empresa_id)
    if cidade:
        q = q.join(models.EmpresaCliente, and_(models.EmpresaCliente.cliente_id == models.ServicoContratado.cliente_id, models.EmpresaCliente.empresa_id == models.ServicoContratado.empresa_id)).join(
            models.EmpresaClienteEndereco, and_(models.EmpresaClienteEndereco.empresa_cliente_id == models.EmpresaCliente.id, models.EmpresaClienteEndereco.is_principal == True)
        ).filter(models.EmpresaClienteEndereco.municipio.ilike(f"%{cidade}%"))

    results = q.all()
    contratos = []
    for row in results:
        contrato = row[0]
        contratos.append({
            **{k: v for k, v in contrato.__dict__.items() if not k.startswith('_')},
            'servico_descricao': row.servico_descricao, 'servico_codigo': row.servico_codigo,
            'servico_unidade': row.servico_unidade, 'servico_cfop': row.servico_cfop,
            'servico_ncm': row.servico_ncm, 'servico_base_calculo_icms_default': row.servico_base_calculo_icms_default,
            'servico_aliquota_icms_default': row.servico_aliquota_icms_default,
            'servico_valor_desconto_default': row.servico_valor_desconto_default,
            'servico_valor_outros_default': row.servico_valor_outros_default
        })
    return contratos
