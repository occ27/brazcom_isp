from sqlalchemy.orm import Session
from sqlalchemy import or_
import unicodedata
import re
import json
from pathlib import Path
from fastapi import HTTPException
from app.models import models
from app.schemas import servico as servico_schema

# UX / safety constants
MAX_LIMIT = 200

# Load allowed CFOP and cClass lists for server-side validation (optional)
_DATA_DIR = Path(__file__).resolve().parents[1] / 'data'
_CFOP_FILE = _DATA_DIR / 'cfop.json'
_CCLASS_FILE = _DATA_DIR / 'cclass.json'
try:
    with open(_CFOP_FILE, 'r', encoding='utf-8') as f:
        _cfop_items = json.load(f)
        VALID_CFOP_CODES = set(str(i.get('code')).zfill(4) for i in _cfop_items if i.get('code'))
except Exception:
    VALID_CFOP_CODES = set()
try:
    with open(_CCLASS_FILE, 'r', encoding='utf-8') as f:
        _cclass_items = json.load(f)
        VALID_CCLASS_CODES = set(str(i.get('code')) for i in _cclass_items if i.get('code'))
except Exception:
    VALID_CCLASS_CODES = set()


def _normalize_text(value: str, max_len: int = None) -> str:
    """Normalize a text field for NFCOM:
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


def get_servico(db: Session, servico_id: int, empresa_id: int = None):
    q = db.query(models.Servico).filter(models.Servico.id == servico_id)
    if empresa_id is not None:
        q = q.filter(models.Servico.empresa_id == empresa_id)
    return q.first()


def get_servicos_by_empresa(db: Session, empresa_id: int = None, qstr: str = None, skip: int = 0, limit: int = 100):
    # enforce sane limits for pagination
    if limit is None:
        limit = 100
    limit = min(int(limit), MAX_LIMIT)
    skip = max(int(skip or 0), 0)

    q = db.query(models.Servico)
    if empresa_id is not None:
        q = q.filter(models.Servico.empresa_id == empresa_id)
    if qstr:
        pattern = f"%{qstr}%"
        q = q.filter(or_(models.Servico.codigo.ilike(pattern), models.Servico.descricao.ilike(pattern)))
    return q.offset(skip).limit(limit).all()


def count_servicos_by_empresa(db: Session, empresa_id: int = None, qstr: str = None) -> int:
    q = db.query(models.Servico)
    if empresa_id is not None:
        q = q.filter(models.Servico.empresa_id == empresa_id)
    if qstr:
        pattern = f"%{qstr}%"
        q = q.filter(or_(models.Servico.codigo.ilike(pattern), models.Servico.descricao.ilike(pattern)))
    return q.count()


def create_servico(db: Session, servico_in: servico_schema.ServicoCreate, empresa_id: int = None) -> models.Servico:
    data = servico_in.model_dump()
    if empresa_id is not None:
        data['empresa_id'] = empresa_id
    # normalize text fields according to NFCOM manual and schema limits
    if 'codigo' in data and data['codigo'] is not None:
        data['codigo'] = _normalize_text(data['codigo'], max_len=60)
    if 'descricao' in data and data['descricao'] is not None:
        data['descricao'] = _normalize_text(data['descricao'], max_len=120)
    if 'unidade_medida' in data and data['unidade_medida'] is not None:
        data['unidade_medida'] = _normalize_text(data['unidade_medida'], max_len=10)
    if 'cClass' in data and data['cClass'] is not None:
        data['cClass'] = _normalize_text(data['cClass'], max_len=7)
    if 'cfop' in data and data['cfop'] is not None:
        data['cfop'] = _normalize_text(data['cfop'], max_len=4)
    if 'ncm' in data and data['ncm'] is not None:
        data['ncm'] = _normalize_text(data['ncm'], max_len=8)
    # Validate cClass: must be 7-digit item code (not just the 3-digit group)
    if 'cClass' in data and data['cClass']:
        cclass_digits = re.sub(r"\D", "", str(data['cClass']))
        if len(cclass_digits) != 7:
            raise HTTPException(status_code=400, detail="cClass inválido: deve selecionar o código de item de 7 dígitos (não o grupo de 3 dígitos).")
        if VALID_CCLASS_CODES and cclass_digits not in VALID_CCLASS_CODES:
            raise HTTPException(status_code=400, detail=f"cClass '{data['cClass']}' não encontrado na tabela de classificação.")
        data['cClass'] = cclass_digits
    # Validate CFOP against whitelist if available
    if 'cfop' in data and data['cfop']:
        cfop_digits = re.sub(r"\D", "", str(data['cfop']))
        if len(cfop_digits) != 4:
            raise HTTPException(status_code=400, detail="CFOP inválido: deve conter 4 dígitos.")
        if VALID_CFOP_CODES and cfop_digits not in VALID_CFOP_CODES:
            raise HTTPException(status_code=400, detail=f"CFOP '{data['cfop']}' não permitido para NFCom.")
        data['cfop'] = cfop_digits
    # numeric defaults
    if 'base_calculo_icms_default' in data and data['base_calculo_icms_default'] is not None:
        try:
            data['base_calculo_icms_default'] = float(data['base_calculo_icms_default'])
        except Exception:
            data['base_calculo_icms_default'] = None
    if 'aliquota_icms_default' in data and data['aliquota_icms_default'] is not None:
        try:
            data['aliquota_icms_default'] = float(data['aliquota_icms_default'])
        except Exception:
            data['aliquota_icms_default'] = None
    if 'valor_desconto_default' in data:
        data['valor_desconto_default'] = float(data.get('valor_desconto_default') or 0)
    if 'valor_outros_default' in data:
        data['valor_outros_default'] = float(data.get('valor_outros_default') or 0)

    db_servico = models.Servico(**data)
    db.add(db_servico)
    db.commit()
    db.refresh(db_servico)
    return db_servico


def update_servico(db: Session, db_obj: models.Servico, obj_in: servico_schema.ServicoUpdate) -> models.Servico:
    update_data = obj_in.model_dump(exclude_unset=True)
    # normalize text fields when present
    if 'codigo' in update_data and update_data['codigo'] is not None:
        update_data['codigo'] = _normalize_text(update_data['codigo'], max_len=60)
    if 'descricao' in update_data and update_data['descricao'] is not None:
        update_data['descricao'] = _normalize_text(update_data['descricao'], max_len=120)
    if 'unidade_medida' in update_data and update_data['unidade_medida'] is not None:
        update_data['unidade_medida'] = _normalize_text(update_data['unidade_medida'], max_len=10)
    if 'cClass' in update_data and update_data['cClass'] is not None:
        update_data['cClass'] = _normalize_text(update_data['cClass'], max_len=7)
    if 'cfop' in update_data and update_data['cfop'] is not None:
        update_data['cfop'] = _normalize_text(update_data['cfop'], max_len=4)
    if 'ncm' in update_data and update_data['ncm'] is not None:
        update_data['ncm'] = _normalize_text(update_data['ncm'], max_len=8)
    # Validate cClass in updates
    if 'cClass' in update_data and update_data['cClass']:
        cclass_digits = re.sub(r"\D", "", str(update_data['cClass']))
        if len(cclass_digits) != 7:
            raise HTTPException(status_code=400, detail="cClass inválido: deve selecionar o código de item de 7 dígitos (não o grupo de 3 dígitos).")
        if VALID_CCLASS_CODES and cclass_digits not in VALID_CCLASS_CODES:
            raise HTTPException(status_code=400, detail=f"cClass '{update_data['cClass']}' não encontrado na tabela de classificação.")
        update_data['cClass'] = cclass_digits
    # Validate CFOP in updates
    if 'cfop' in update_data and update_data['cfop']:
        cfop_digits = re.sub(r"\D", "", str(update_data['cfop']))
        if len(cfop_digits) != 4:
            raise HTTPException(status_code=400, detail="CFOP inválido: deve conter 4 dígitos.")
        if VALID_CFOP_CODES and cfop_digits not in VALID_CFOP_CODES:
            raise HTTPException(status_code=400, detail=f"CFOP '{update_data['cfop']}' não permitido para NFCom.")
        update_data['cfop'] = cfop_digits
    if 'base_calculo_icms_default' in update_data and update_data['base_calculo_icms_default'] is not None:
        try:
            update_data['base_calculo_icms_default'] = float(update_data['base_calculo_icms_default'])
        except Exception:
            update_data['base_calculo_icms_default'] = None
    if 'aliquota_icms_default' in update_data and update_data['aliquota_icms_default'] is not None:
        try:
            update_data['aliquota_icms_default'] = float(update_data['aliquota_icms_default'])
        except Exception:
            update_data['aliquota_icms_default'] = None
    if 'valor_desconto_default' in update_data:
        update_data['valor_desconto_default'] = float(update_data.get('valor_desconto_default') or 0)
    if 'valor_outros_default' in update_data:
        update_data['valor_outros_default'] = float(update_data.get('valor_outros_default') or 0)

    for field in update_data:
        if hasattr(db_obj, field):
            setattr(db_obj, field, update_data[field])
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_servico(db: Session, db_obj: models.Servico):
    db.delete(db_obj)
    db.commit()
    return db_obj
