import base64
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, String, text
from typing import Optional
from fastapi import HTTPException, status
import xml.etree.ElementTree as ET
from datetime import date
from app.core.security import decrypt_sensitive_data
from pathlib import Path
import tempfile
import traceback
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from app.core.config import settings
import random
import requests
import hashlib
import os
from lxml import etree
import io, gzip
from app.models import models
from types import SimpleNamespace
from app.schemas import nfcom as nfcom_schema
from app.crud import crud_servico, crud_empresa


# ==============================================================================
# CONFIGURAÇÃO DE URLs QR CODE POR AMBIENTE
# ==============================================================================
# IMPORTANTE: URLs de QR Code variam entre PRODUÇÃO e HOMOLOGAÇÃO
# 
# PROBLEMA CONHECIDO (cStat 464):
# - Ambiente de HOMOLOGAÇÃO rejeita TODAS as URLs testadas (dezembro 2025)
# - URLs testadas: www.sefaz.rs.gov.br, dfe-portal.svrs.rs.gov.br, www.fazenda.pr.gov.br
# - Documentação não fornece lista oficial atualizada
# - XMLs PRODUÇÃO autorizados usam: www.sefaz.rs.gov.br (RS) ou www.fazenda.pr.gov.br (PR)
# 
# SOLUÇÃO ATUALIZADA:
# - Configure settings.NFCOM_AMBIENTE no arquivo .env
# - "homologacao" para testes (padrão)
# - "producao" para emissão real
# ==============================================================================

# DEPRECATED: Use settings.NFCOM_AMBIENTE ao invés desta constante
# AMBIENTE_PRODUCAO = False  # Removido - use .env

def get_qrcode_url_base(uf_code: str, ambiente: Optional[str] = None) -> str:
    """
    Retorna a URL base do QR Code para a UF especificada.
    
    Args:
        uf_code: Código da UF (2 dígitos) extraído da chave de acesso
        
    Returns:
        URL base para o QR Code (sem parâmetros)
    """

    """ https://dfe-portal.svrs.rs.gov.br/NFCom/consulta
        https://dfe-portal.svrs.rs.gov.br/Nfcom/Servicos
        https://www.fazenda.pr.gov.br/NFCom/NFCom-QRCODE.aspx
        https://nfcom-homologacao.svrs.rs.gov.br/WS/NFComRecepcao/NFComRecepcao.asmx
        https://www.fazenda.pr.gov.br/nfcom/qrcode
        https://www.sefaz.pr.gov.br/nfcom/consulta
        https://www.fazenda.pr.gov.br/nfcom/qrcode
        https://dfe-portal.svrs.rs.gov.br/NFCom/consulta
        

        URL para consulta em MG: https://portalnfcom.fazenda.mg.gov.br/qrcode
        PR: A URL de consulta em PR é www.fazenda.pr.gov.br/nfce/qrcode?. 

        Exemplos de URLs de consulta por estado:
        Minas Gerais: https://portalnfcom.fazenda.mg.gov.br/qrcode
        Goiás (ambiente de produção): https://nfeweb.sefaz.go.gov.br/nfeweb/sites/nfce/danfeNFCe
        Paraná (produção e homologação): https://www.fazenda.pr.gov.br/nfce/qrcode

        protocolo de atendimento por telefone em 04/11/2025 15:00h = 1726144
    """

    # URLs para PRODUÇÃO
    # A SVRS atende múltiplos estados (incluindo PR). Quando se transmite para a SVRS,
    # a URL do QR Code DEVE ser a da SVRS, mesmo que a empresa seja de outro estado.
    qr_urls_producao = {
        # Mapeia todas as UFs que usam SVRS para a URL de produção da SVRS.
        "26": "https://dfe-portal.svrs.rs.gov.br/nfCom/qrCode",  # PE
        "29": "https://dfe-portal.svrs.rs.gov.br/nfCom/qrCode",  # BA
        # MG (Minas Gerais) - portal NFCom MG (consulta QR Code)
        "31": "https://portalnfcom.fazenda.mg.gov.br/qrcode",
        "41": "https://dfe-portal.svrs.rs.gov.br/nfCom/qrCode",  # PR via SVRS
        "43": "https://dfe-portal.svrs.rs.gov.br/nfCom/qrCode",  # RS
        
        # Adicione outras UFs atendidas pela SVRS aqui se necessário
    }
    
    # URLs TENTATIVA em HOMOLOGAÇÃO (não há documentação oficial)
    # ATENÇÃO: Estas URLs PODEM resultar em cStat 464
    # Recomenda-se contatar suporte SEFAZ/SVRS para URL correta
    qr_urls_homologacao = {
        # Para homologação, a URL correta da SVRS parece ser dfe-portal
        "26": "https://dfe-portal.svrs.rs.gov.br/nfCom/qrCode",  # PE
        "29": "https://dfe-portal.svrs.rs.gov.br/nfCom/qrCode",  # BA
        # MG homologação (tentativa) — confirmar com SEFAZ MG se houver URL distinta
        "31": "https://portalnfcom.fazenda.mg.gov.br/qrcode",
        "41": "https://dfe-portal.svrs.rs.gov.br/nfCom/qrCode", # PR via SVRS (Homologação)
        "43": "https://dfe-portal.svrs.rs.gov.br/nfCom/qrCode",  # RS - TENTATIVA
    }
    
    # Decide qual conjunto de URLs usar. Prefer explicit `ambiente` when provided
    # (values expected: 'producao' or 'homologacao'). Caso contrário, usa a flag global.
    if ambiente is not None:
        ambiente_norm = str(ambiente).strip().lower()
        urls = qr_urls_producao if ambiente_norm == 'producao' else qr_urls_homologacao
    else:
        # Usar configuração global se não especificado por empresa
        urls = qr_urls_producao if settings.NFCOM_AMBIENTE == "producao" else qr_urls_homologacao
    default_url = urls.get("43")  # Fallback para SVRS/RS
    
    return urls.get(uf_code, default_url)


def get_nfcom(db: Session, nfcom_id: int, empresa_id: int = None):
    """Busca uma NFCom específica."""
    q = db.query(models.NFCom).options(
        joinedload(models.NFCom.empresa),
        joinedload(models.NFCom.cliente).joinedload(models.Cliente.empresa_associations).joinedload(models.EmpresaCliente.enderecos)
    ).filter(models.NFCom.id == nfcom_id)
    if empresa_id is not None:
        q = q.filter(models.NFCom.empresa_id == empresa_id)
    nfcom = q.first()
    if nfcom and nfcom.xml_gerado:
        nfcom.xml_url = f"/empresas/{nfcom.empresa_id}/nfcom/{nfcom.id}/xml"
    # Define status dinamicamente: marca como 'cancelada' se houver retorno de evento com cStat=134/135/136
    try:
        nfcom_status = None
        if nfcom:
            info = (nfcom.informacoes_adicionais or '')
            # cStat 135=evento vinculado, 136=vinculação prejudicada, 134=NFCom em situação diferente
            if any(code in info for code in ['cStat=135', 'cStat=136', 'cStat=134']):
                nfcom_status = 'cancelada'
            else:
                nfcom_status = 'emitida' if nfcom.protocolo_autorizacao else 'pendente'
            # Atribui atributo dinâmico para consumo no frontend
            setattr(nfcom, 'status', nfcom_status)
    except Exception:
        pass
    return nfcom

def get_nfcoms_by_empresa(
    db: Session, 
    empresa_id: int, 
    skip: int = 0, 
    limit: int = 100,
    search: str = None,
    date_from: str = None,
    date_to: str = None,
    status: str = None,
    min_value: float = None,
    max_value: float = None
):
    """
    Lista as NFComs de uma empresa com filtros opcionais.
    """
    from datetime import datetime
    
    base_query = db.query(models.NFCom).filter(models.NFCom.empresa_id == empresa_id)
    
    # Aplicar filtros
    if search:
        search_term = f"%{search}%"
        base_query = base_query.join(models.Cliente, models.NFCom.cliente_id == models.Cliente.id).filter(
            or_(
                models.NFCom.numero_nf.cast(String).ilike(search_term),
                models.Cliente.nome_razao_social.ilike(search_term),
                models.Cliente.id.cast(String).ilike(search_term)
            )
        )
    
    # Verificar e corrigir datas se necessário
    if date_from and date_to:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            # Se data inicial for maior que data final, inverter
            if date_from_obj > date_to_obj:
                date_from, date_to = date_to, date_from
                date_from_obj, date_to_obj = date_to_obj, date_from_obj
        except ValueError:
            pass  # Ignora filtros inválidos
    
    if date_from:
        try:
            if 'date_from_obj' not in locals():
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            base_query = base_query.filter(models.NFCom.data_emissao >= date_from_obj)
        except ValueError:
            pass  # Ignora filtro inválido
    
    if date_to:
        try:
            if 'date_to_obj' not in locals():
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            # Incluir o dia todo
            from datetime import timedelta
            date_to_obj = date_to_obj + timedelta(days=1)
            base_query = base_query.filter(models.NFCom.data_emissao < date_to_obj)
        except ValueError:
            pass  # Ignora filtro inválido
    
    if status:
        if status == 'authorized':
            base_query = base_query.filter(models.NFCom.protocolo_autorizacao.isnot(None))
        elif status == 'pending':
            base_query = base_query.filter(models.NFCom.protocolo_autorizacao.is_(None))
        elif status == 'cancelled' or status == 'canceled':
            # Filtra notas cuja informacoes_adicionais indica evento de cancelamento (cStat 134/135/136)
            base_query = base_query.filter(
                or_(
                    models.NFCom.informacoes_adicionais.ilike('%cStat=134%'),
                    models.NFCom.informacoes_adicionais.ilike('%cStat=135%'),
                    models.NFCom.informacoes_adicionais.ilike('%cStat=136%')
                )
            )
    
    # Verificar e corrigir valores se necessário
    if min_value is not None and max_value is not None:
        if min_value > max_value:
            min_value, max_value = max_value, min_value
    
    if min_value is not None:
        base_query = base_query.filter(models.NFCom.valor_total >= min_value)
    
    if max_value is not None:
        base_query = base_query.filter(models.NFCom.valor_total <= max_value)
    
    # 1. Total de registros (após filtros)
    total = base_query.count()
    
    # 2. Soma do valor total (após filtros)
    total_geral_valor = base_query.with_entities(func.sum(models.NFCom.valor_total)).scalar() or 0.0
    
    # 3. Contagens por status (após filtros)
    total_autorizadas = base_query.filter(models.NFCom.protocolo_autorizacao.isnot(None)).count()
    total_pendentes = base_query.filter(models.NFCom.protocolo_autorizacao.is_(None)).count()
    total_canceladas = base_query.filter(
        or_(
            models.NFCom.informacoes_adicionais.like('%cStat=134%'),
            models.NFCom.informacoes_adicionais.like('%cStat=135%'),
            models.NFCom.informacoes_adicionais.like('%cStat=136%')
        )
    ).count()
    
    # 4. Registros paginados
    nfcoms = base_query.order_by(models.NFCom.numero_nf.desc()).offset(skip).limit(limit).options(
        joinedload(models.NFCom.cliente), 
        joinedload(models.NFCom.itens).options(joinedload(models.NFComItem.servico)),
        joinedload(models.NFCom.empresa)
    ).all()
    
    # Adiciona a URL do XML dinamicamente para cada NFCom
    for nfcom in nfcoms:
        if nfcom.xml_gerado:
            nfcom.xml_url = f"/empresas/{nfcom.empresa_id}/nfcom/{nfcom.id}/xml"
        # Atribui status dinâmico: 'cancelada' quando retorno de evento contém cStat=134/135/136
        try:
            info = (nfcom.informacoes_adicionais or '')
            # cStat 135=evento vinculado, 136=vinculação prejudicada, 134=NFCom em situação diferente
            if any(code in info for code in ['cStat=135', 'cStat=136', 'cStat=134']):
                setattr(nfcom, 'status', 'cancelada')
            else:
                setattr(nfcom, 'status', 'emitida' if nfcom.protocolo_autorizacao else 'pendente')
        except Exception:
            pass

    return {
        "total": total, 
        "nfcoms": nfcoms, 
        "total_geral_valor": total_geral_valor,
        "total_autorizadas": total_autorizadas,
        "total_pendentes": total_pendentes,
        "total_canceladas": total_canceladas
    }

def get_next_numero_nf(db: Session, empresa_id: int, serie: int = 1) -> int:
    """Calcula o próximo número sequencial para a NFCom."""
    last_nf = db.query(func.max(models.NFCom.numero_nf)).filter(
        models.NFCom.empresa_id == empresa_id,
        models.NFCom.serie == serie
    ).scalar()
    return (last_nf or 0) + 1

def _calculate_dv(key: str) -> str:
    """Calcula o Dígito Verificador (DV) para uma chave de 43 dígitos (Módulo 11)."""
    if len(key) != 43:
        raise ValueError("A chave para cálculo do DV deve ter 43 dígitos.")
    
    # Pesos aplicados da direita para a esquerda (2..9 repetidos)
    pesos = [2, 3, 4, 5, 6, 7, 8, 9]
    soma = 0
    for i, digito in enumerate(reversed(key)):
        soma += int(digito) * pesos[i % len(pesos)]

    resto = soma % 11
    dv = 11 - resto

    # Regra conforme implementação padrão do Mod11 para chave de acesso NF-e/NFC-e:
    # - se dv == 10 ou dv == 11 -> 0
    # - caso contrário -> dv
    if dv in (10, 11):
        return "0"
    return str(dv)

def generate_access_key(nfcom: models.NFCom, cNF_override: Optional[str] = None) -> str:
    """Gera a chave de acesso de 44 dígitos para a NFCom.

    Se `cNF_override` for fornecido, será usado (deve ter 8 dígitos). Caso contrário,
    um cNF aleatório de 8 dígitos será gerado como fallback.
    """
    cUF = str(nfcom.empresa.codigo_ibge)[:2].zfill(2)
    AAMM = nfcom.data_emissao.strftime('%y%m')
    CNPJ = nfcom.empresa.cnpj.replace('.', '').replace('/', '').replace('-', '').zfill(14)
    mod = "62"
    serie = str(nfcom.serie).zfill(3)
    nNF = str(nfcom.numero_nf).zfill(9)
    tpEmis = str(nfcom.tipo_emissao.value)  # Converte para string
    # IMPORTANTE:
    # - Na CHAVE DE ACESSO: cNF tem 8 dígitos (para totalizar 43 + DV = 44)
    # - No XML <cNF>: usa-se apenas 7 dígitos (conforme XSD pattern="[0-9]{7}")
    # A chave é: cUF(2)+AAMM(4)+CNPJ(14)+mod(2)+serie(3)+nNF(9)+tpEmis(1)+cNF(8)+cDV(1) = 44
    if cNF_override:
        cNF = str(cNF_override).zfill(8)
        if not cNF.isdigit() or len(cNF) != 8:
            raise ValueError("cNF_override deve ser uma string de 8 dígitos.")
    else:
        cNF = ''.join(random.choices('0123456789', k=8))

    key_sem_dv = f"{cUF}{AAMM}{CNPJ}{mod}{serie}{nNF}{tpEmis}{cNF}"
    dv = _calculate_dv(key_sem_dv)

    return key_sem_dv + dv
 
def sanitize_string(value) -> str:
    """Sanitiza uma string para garantir que seja válida em UTF-8."""
    if value is None:
        return ""
    if isinstance(value, str):
        # Remove caracteres de controle e substitui caracteres problemáticos
        return ''.join(c for c in value if ord(c) >= 32 or c in '\n\r\t')
    return str(value)


def _format_ind_ie_dest(value) -> str:
    """Garante que indIEDest seja um único caractere aceito ('1','2' ou '9').

    Aceita enums, ints ou strings longas (ex.: '1 - Contribuinte') e extrai o código.
    Se não conseguir determinar, retorna '9' (não contribuinte) como fallback seguro.
    """
    if value is None:
        return '9'
    # Enum-like with .value
    try:
        if hasattr(value, 'value'):
            v = value.value
        else:
            v = value
    except Exception:
        v = value

    s = str(v).strip()
    # Se já for um único caractere válido
    if s in ('1', '2', '9'):
        return s

    # Tenta extrair o primeiro dígito válido da string
    import re
    m = re.search(r"([129])", s)
    if m:
        return m.group(1)

    # Fallback
    return '9'


def _map_unidade_to_tumed(unidade) -> str:
    """Mapeia a unidade de medida da aplicação para o código TUMedItem do leiaute NFCom.

    TUMedItem (conforme leiaute):
    1 = Minuto
    2 = MB
    3 = GB
    4 = UN

    Aceita valores já numéricos ('1','2','3','4'), siglas comuns ('UN','MB','GB','MIN'),
    ou palavras como 'MINUTO', 'MEGABYTE', 'GIGABYTE', 'UNIDADE'.
    Retorna '4' (UN) como fallback seguro.
    """
    if unidade is None:
        return '4'
    try:
        u = str(unidade).strip().upper()
    except Exception:
        return '4'

    # Se já vem no formato esperado
    if u in ('1', '2', '3', '4'):
        return u

    # Mapas diretos
    if u in ('MIN', 'MINUTO', 'MINUTOS'):
        return '1'
    if u in ('MB', 'MEGABYTE', 'MEGABYTES'):
        return '2'
    if u in ('GB', 'GIGABYTE', 'GIGABYTES'):
        return '3'
    if u in ('UN', 'U', 'UNIDADE', 'UNIDADES', 'UND', 'UNID'):
        return '4'

    # Alguns sistemas usam descrições em PT-BR ou abreviações
    if 'MIN' in u:
        return '1'
    if 'MB' in u:
        return '2'
    if 'GB' in u:
        return '3'
    if 'UN' in u or 'UNID' in u or 'UNIDADE' in u:
        return '4'

    # Se não reconhecido, fallback para UN
    return '4'

def generate_nfcom_xml(nfcom: models.NFCom) -> str:
    """Gera o conteúdo XML para uma NFCom."""
    
    # Define o namespace obrigatório para a NFCom
    ns = {'': "http://www.portalfiscal.inf.br/nfcom"}
    ET.register_namespace('', ns[''])

    def E(tag, *args, **kwargs):
        """Helper para criar elementos com o namespace correto."""
        return ET.Element(f"{{{ns['']}}}{tag}", *args, **kwargs)

    def SE(parent, tag, *args, **kwargs):
        """Helper para criar sub-elementos com o namespace correto."""
        return ET.SubElement(parent, f"{{{ns['']}}}{tag}", *args, **kwargs)

    infNFCom = E("infNFCom", Id=f"NFCom{nfcom.chave_acesso}", versao="1.00")
    
    # Grupo <ide>
    ide = SE(infNFCom, "ide")
    SE(ide, "cUF").text = str(nfcom.empresa.codigo_ibge)[:2] if nfcom.empresa else ''
    # Permite que a empresa especificada no snapshot escolha o ambiente.
    empresa_ambiente = None
    try:
        empresa_ambiente = getattr(nfcom, 'empresa', None)
        empresa_ambiente = getattr(empresa_ambiente, 'ambiente_nfcom', None)
    except Exception:
        empresa_ambiente = None

    if empresa_ambiente in ('producao', 'producao'):
        tpAmb_value = "1"
    elif empresa_ambiente in ('homologacao', 'homologação', 'homolog'):
        tpAmb_value = "2"
    else:
        # Usar configuração global se não especificado por empresa
        tpAmb_value = "1" if settings.NFCOM_AMBIENTE == "producao" else "2"

    SE(ide, "tpAmb").text = tpAmb_value  # 1 = Produção, 2 = Homologação
    print(f"DEBUG: tpAmb no XML = {tpAmb_value} (empresa_ambiente={empresa_ambiente} settings.NFCOM_AMBIENTE={settings.NFCOM_AMBIENTE})")
    SE(ide, "mod").text = "62"
    SE(ide, "serie").text = str(nfcom.serie)
    SE(ide, "nNF").text = str(nfcom.numero_nf)
    # IMPORTANTE:
    # - A chave tem cNF com 8 dígitos (posições 35-42)
    # - O XML <cNF> exige apenas 7 dígitos (XSD: pattern="[0-9]{7}")
    # - Decisão: usar os 7 ÚLTIMOS dígitos do cNF8 para preencher o XML.
    #   Isso permite que o XML reflita os dígitos menos significativos do ID
    #   (por exemplo, extraídos do id do registro), reduzindo chance de
    #   duplicidade quando usamos o `id` como base para o cNF8.
    cNF_from_key = nfcom.chave_acesso[35:43]  # 8 dígitos da chave
    SE(ide, "cNF").text = cNF_from_key[-7:]  # 7 últimos dígitos para o XML
    SE(ide, "cDV").text = nfcom.chave_acesso[43]  # Posição 43 = último dígito (DV)
    if nfcom.data_emissao:
        # Formato AAAA-MM-DDTHH:MM:SSTZD (ex: 2023-10-26T10:00:00-03:00)
        # Se a data não tiver tzinfo, assumimos o fuso -03:00 (horário de Brasília) para homologação.
        try:
            dt = nfcom.data_emissao
            if getattr(dt, 'tzinfo', None) is None:
                SE(ide, "dhEmi").text = dt.strftime('%Y-%m-%dT%H:%M:%S-03:00')
            else:
                SE(ide, "dhEmi").text = dt.isoformat()
        except Exception:
            # Fallback simples
            SE(ide, "dhEmi").text = str(nfcom.data_emissao)
    SE(ide, "tpEmis").text = nfcom.tipo_emissao.value
    SE(ide, "nSiteAutoriz").text = "0" # Site único, conforme manual
    SE(ide, "cMunFG").text = nfcom.cMunFG # Agora na posição correta
    SE(ide, "finNFCom").text = nfcom.finalidade_emissao.value
    SE(ide, "tpFat").text = nfcom.tpFat.value
    SE(ide, "verProc").text = "1.00 - NT 2025.001" # Versão do aplicativo emissor

    # (contratos tratados dentro do bloco <assinante> conforme o leiaute)

    # Grupo <emit>
    emit = SE(infNFCom, "emit")
    if nfcom.empresa:
        SE(emit, "CNPJ").text = nfcom.empresa.cnpj.replace('.', '').replace('/', '').replace('-', '')
        
        # Limpa a Inscrição Estadual, removendo pontuação, mas mantendo "ISENTO"
        ie_raw = nfcom.empresa.inscricao_estadual or ""
        if "ISENTO" in ie_raw.upper():
            SE(emit, "IE").text = "ISENTO"
        else:
            SE(emit, "IE").text = ''.join(filter(str.isdigit, ie_raw))

        # Mapeia o regime tributário para o código numérico esperado
        crt_map = {
            "Simples Nacional": "1",
            "Simples Nacional, excesso sublimite de receita bruta": "2",
            "Regime Normal": "3"
        }
        crt_code = crt_map.get(nfcom.empresa.regime_tributario, "3") # Padrão para Regime Normal se não encontrado
        SE(emit, "CRT").text = crt_code

        SE(emit, "xNome").text = sanitize_string(nfcom.empresa.razao_social)
        enderEmit = SE(emit, "enderEmit")
        SE(enderEmit, "xLgr").text = sanitize_string(nfcom.empresa.endereco)
        SE(enderEmit, "nro").text = sanitize_string(nfcom.empresa.numero)
        SE(enderEmit, "xBairro").text = sanitize_string(nfcom.empresa.bairro)
        SE(enderEmit, "cMun").text = sanitize_string(nfcom.empresa.codigo_ibge)
        SE(enderEmit, "xMun").text = sanitize_string(nfcom.empresa.municipio)
        SE(enderEmit, "CEP").text = sanitize_string(nfcom.empresa.cep.replace('-', ''))
        SE(enderEmit, "UF").text = sanitize_string(nfcom.empresa.uf)

    # Grupo <dest>
    dest = SE(infNFCom, "dest")
    if nfcom.cliente:
        SE(dest, "xNome").text = sanitize_string(nfcom.cliente.nome_razao_social)
        # Se for pessoa jurídica, inclui CNPJ e processa IE normalmente.
        # Se for pessoa física (CPF), não devemos enviar a tag <IE> — em geral
        # o padrão aceito pelo leiaute para pessoa física é indIEDest='9'.
        if nfcom.cliente.tipo_pessoa == models.TipoPessoa.JURIDICA:
            SE(dest, "CNPJ").text = nfcom.cliente.cpf_cnpj.replace('.', '').replace('/', '').replace('-', '')
            # Adiciona indIEDest conforme informado (normalizado)
            ind_ie_dest_value = _format_ind_ie_dest(nfcom.cliente.ind_ie_dest) # Normaliza para '1','2' ou '9'
            SE(dest, "indIEDest").text = ind_ie_dest_value
            
            # Regra de envio da tag <IE>:
            # - indIEDest='1' (Contribuinte ICMS): envia IE com número
            # - indIEDest='2' (Contribuinte ISENTO): envia <IE>ISENTO</IE>
            # - indIEDest='9' (Não Contribuinte): NÃO envia tag <IE>
            if ind_ie_dest_value == '1':
                # Contribuinte ICMS - deve ter IE com número
                ie_raw = nfcom.cliente.inscricao_estadual or ""
                ie_clean = ''.join(filter(str.isdigit, ie_raw))
                if ie_clean:
                    SE(dest, "IE").text = ie_clean
            elif ind_ie_dest_value == '2':
                # Contribuinte ISENTO - envia literal "ISENTO"
                SE(dest, "IE").text = "ISENTO"
            # Se ind_ie_dest_value == '9': não adiciona tag <IE>
        else:
            # Pessoa física: envia CPF e força indIEDest='9' (não contribuinte).
            SE(dest, "CPF").text = nfcom.cliente.cpf_cnpj.replace('.', '').replace('-', '')
            SE(dest, "indIEDest").text = '9'

        enderDest = SE(dest, "enderDest") # Bloco de endereço agora na posição correta
        SE(enderDest, "xLgr").text = sanitize_string(nfcom.dest_endereco) 
        SE(enderDest, "nro").text = sanitize_string(nfcom.dest_numero)
        SE(enderDest, "xBairro").text = sanitize_string(nfcom.dest_bairro)
        SE(enderDest, "cMun").text = sanitize_string(nfcom.dest_codigo_ibge)
        SE(enderDest, "xMun").text = sanitize_string(nfcom.dest_municipio)
        SE(enderDest, "CEP").text = sanitize_string(nfcom.dest_cep.replace('-', ''))
        SE(enderDest, "UF").text = sanitize_string(nfcom.dest_uf)

    # NOTA: <assinante> será inserido APÓS todos os grupos opcionais (gSub, gCofat)
    # e ANTES do primeiro <det>, conforme exige o schema para PJ.
    # Criamos uma função helper para preencher o bloco quando for a hora certa.
    def _build_assinante_block(parent_elem):
        """Constrói o bloco <assinante> dentro do elemento pai fornecido."""
        assinante = SE(parent_elem, "assinante")
        # iCodAssinante: usamos o id do cliente ou o CPF/CNPJ como fallback
        icod = None
        if getattr(nfcom, 'cliente', None) is not None:
            icod = getattr(nfcom.cliente, 'id', None) or getattr(nfcom.cliente, 'cpf_cnpj', None)
        if not icod:
            icod = '1'
        SE(assinante, "iCodAssinante").text = str(icod)

        # tpAssinante: tipo do assinante (fallback para '1' - Comercial)
        tp_ass = getattr(nfcom.cliente, 'tipo_assinante', None) if getattr(nfcom, 'cliente', None) else None
        if not tp_ass:
            tp_ass = '1'
        SE(assinante, "tpAssinante").text = str(tp_ass)

        # tpServUtil: tipo de serviço utilizado (fallback '1' - Telefonia)
        tp_serv = getattr(nfcom, 'tpServUtil', None)
        if not tp_serv:
            tp_serv = '1'
        SE(assinante, "tpServUtil").text = str(tp_serv)
        # Campos de contrato: quando o tipo de faturamento exige contrato (Normal/Centralizado)
        try:
            tp_fat_val = str(nfcom.tpFat.value) if getattr(nfcom, 'tpFat', None) is not None else None
        except Exception:
            tp_fat_val = getattr(nfcom, 'tpFat', None)

        if tp_fat_val in ('0', '1', 'NORMAL', 'CENTRALIZADO'):
            nContrato = getattr(nfcom, 'numero_contrato', None)
            dContratoIni = getattr(nfcom, 'd_contrato_ini', None)
            dContratoFim = getattr(nfcom, 'd_contrato_fim', None)

            if not nContrato or not dContratoIni:
                raise HTTPException(status_code=400, detail="Tipo de faturamento exige dados de contrato: preencha 'numero_contrato' e 'd_contrato_ini' no registro antes de transmitir.")

            SE(assinante, "nContrato").text = str(nContrato)
            try:
                if hasattr(dContratoIni, 'strftime'):
                    SE(assinante, "dContratoIni").text = dContratoIni.strftime('%Y-%m-%d')
                else:
                    SE(assinante, "dContratoIni").text = str(dContratoIni)
            except Exception:
                SE(assinante, "dContratoIni").text = str(dContratoIni)

            if dContratoFim:
                try:
                    if hasattr(dContratoFim, 'strftime'):
                        SE(assinante, "dContratoFim").text = dContratoFim.strftime('%Y-%m-%d')
                    else:
                        SE(assinante, "dContratoFim").text = str(dContratoFim)
                except Exception:
                    SE(assinante, "dContratoFim").text = str(dContratoFim)

    # Grupos opcionais gSub e gCofat iriam aqui (não implementados ainda)
    # Por ora, pulamos direto para <assinante> antes dos itens.

    # Insere <assinante> ANTES do primeiro <det>, conforme exige o schema
    try:
        print(f"DEBUG: Inserindo <assinante> após <dest> e antes de <det>")
        _build_assinante_block(infNFCom)
        print(f"DEBUG: <assinante> inserido com sucesso")
    except HTTPException:
        # HTTPException deve ser propagada para o usuário (dados de contrato faltando)
        raise
    except Exception as e:
        # Outros erros: garante um bloco mínimo
        print(f"DEBUG: Exceção não-HTTPException ao criar assinante: {e}, usando fallback")
        assinante = SE(infNFCom, "assinante")
        SE(assinante, "iCodAssinante").text = "1"
        SE(assinante, "tpAssinante").text = "1"
        SE(assinante, "tpServUtil").text = "1"

    # Grupo <det> - Itens da NFCom
    for index, item in enumerate(nfcom.itens):
        det = SE(infNFCom, "det", nItem=str(index + 1))
        
        # Grupo <prod>
        prod = SE(det, "prod")
        SE(prod, "cProd").text = sanitize_string(item.codigo_servico)
        SE(prod, "xProd").text = sanitize_string(item.descricao_servico)
        SE(prod, "cClass").text = sanitize_string(item.cClass)
        if item.cfop:
            SE(prod, "CFOP").text = sanitize_string(item.cfop)
        # O schema NFCom espera um código TUMedItem com comprimento 1.
        # Fazemos o mapeamento das unidades da aplicação para os códigos esperados.
        SE(prod, "uMed").text = _map_unidade_to_tumed(item.unidade_medida)
        SE(prod, "qFaturada").text = f"{item.quantidade:.4f}"
        SE(prod, "vItem").text = f"{item.valor_unitario:.2f}"
        if item.valor_desconto > 0:
            SE(prod, "vDesc").text = f"{item.valor_desconto:.2f}"
        if item.valor_outros > 0:
            SE(prod, "vOutro").text = f"{item.valor_outros:.2f}"
        SE(prod, "vProd").text = f"{item.valor_total:.2f}"

        # Grupo <imposto>
        imposto = SE(det, "imposto")
        # Exemplo com ICMS00 (Tributação normal) - pode ser expandido para outros CSTs
        icms = SE(imposto, "ICMS00")
        SE(icms, "CST").text = "00" # Exemplo fixo
        SE(icms, "vBC").text = f"{item.base_calculo_icms:.2f}" if item.base_calculo_icms is not None else "0.00"
        SE(icms, "pICMS").text = f"{item.aliquota_icms:.2f}" if item.aliquota_icms is not None else "0.00"
        vICMS = (item.base_calculo_icms or 0) * ((item.aliquota_icms or 0) / 100)
        SE(icms, "vICMS").text = f"{vICMS:.2f}"
        
        # Grupo <PIS> - movido para dentro do loop de itens
        pis = SE(imposto, "PIS")
        SE(pis, "CST").text = "01"  # Exemplo: Operação Tributável com Alíquota Básica
        SE(pis, "vBC").text = f"{item.base_calculo_pis:.2f}" if item.base_calculo_pis is not None else "0.00"
        SE(pis, "pPIS").text = f"{item.aliquota_pis:.2f}" if item.aliquota_pis is not None else "0.00"
        vPIS = (item.base_calculo_pis or 0) * ((item.aliquota_pis or 0) / 100)
        SE(pis, "vPIS").text = f"{vPIS:.2f}"

        # Grupo <COFINS> - movido para dentro do loop de itens
        cofins = SE(imposto, "COFINS")
        SE(cofins, "CST").text = "01"  # Exemplo: Operação Tributável com Alíquota Básica
        SE(cofins, "vBC").text = f"{item.base_calculo_cofins:.2f}" if item.base_calculo_cofins is not None else "0.00"
        SE(cofins, "pCOFINS").text = f"{item.aliquota_cofins:.2f}" if item.aliquota_cofins is not None else "0.00"
        vCOFINS = (item.base_calculo_cofins or 0) * ((item.aliquota_cofins or 0) / 100)
        SE(cofins, "vCOFINS").text = f"{vCOFINS:.2f}"

    # Após gerar todos os itens, monta o bloco <total> conforme a ordem do schema
    total_vBC = sum(item.base_calculo_icms or 0.0 for item in nfcom.itens)
    total_vICMS = sum((item.base_calculo_icms or 0) * ((item.aliquota_icms or 0) / 100) for item in nfcom.itens)
    total_vPIS = sum((item.base_calculo_pis or 0) * ((item.aliquota_pis or 0) / 100) for item in nfcom.itens)
    total_vCOFINS = sum((item.base_calculo_cofins or 0) * ((item.aliquota_cofins or 0) / 100) for item in nfcom.itens)
    # O valor total dos produtos já é calculado e armazenado em nfcom.valor_total
    total_vProd = nfcom.valor_total

    # Grupo <total>
    total = SE(infNFCom, "total")
    SE(total, "vProd").text = f"{total_vProd:.2f}"
    icms_tot = SE(total, "ICMSTot")
    SE(icms_tot, "vBC").text = f"{total_vBC:.2f}"
    SE(icms_tot, "vICMS").text = f"{total_vICMS:.2f}"
    SE(icms_tot, "vICMSDeson").text = "0.00" # Campo obrigatório
    # O schema espera vFCP (Fundo de Combate à Pobreza) aqui, não vICMSOutro
    SE(icms_tot, "vFCP").text = "0.00" # Campo obrigatório conforme nfcomTiposBasico_v1.00.xsd
    # O XSD requer que vCOFINS venha antes de vPIS e que vários campos existam
    SE(total, "vCOFINS").text = f"{total_vCOFINS:.2f}" # Campo obrigatório, filho de <total>
    SE(total, "vPIS").text = f"{total_vPIS:.2f}" # Campo obrigatório, filho de <total>
    # Campos exigidos pelo schema, mesmo quando zero
    SE(total, "vFUNTTEL").text = "0.00"
    SE(total, "vFUST").text = "0.00"

    # vRetTribTot é um complexo que agrega retenções; preencher com zeros para compatibilidade
    vRetTribTot = SE(total, "vRetTribTot")
    SE(vRetTribTot, "vRetPIS").text = "0.00"
    SE(vRetTribTot, "vRetCofins").text = "0.00"
    SE(vRetTribTot, "vRetCSLL").text = "0.00"
    SE(vRetTribTot, "vIRRF").text = "0.00"

    SE(total, "vDesc").text = "0.00"
    SE(total, "vOutro").text = "0.00"
    SE(total, "vNF").text = f"{nfcom.valor_total:.2f}"

    # Grupo <gFat> - Informações de controle da Fatura (obrigatório quando tpFat = NORMAL)
    # Posição no XSD: após <total> e <gFidelidade> (se existir), antes de <autXML> e <infAdic>
    try:
        tp_fat_val = str(nfcom.tpFat.value) if getattr(nfcom, 'tpFat', None) is not None else None
        if tp_fat_val in ('0', 'NORMAL'):
            faturas = getattr(nfcom, 'faturas', None) or []
            if not faturas:
                raise HTTPException(status_code=400, detail="Tipo de faturamento NORMAL exige grupo gFat: adicione ao menos uma fatura.")
            
            # Usamos a primeira fatura como base para CompetFat, dVencFat e codBarras
            primeira_fat = faturas[0]
            gFat = SE(infNFCom, "gFat")
            
            # CompetFat: Ano e mês referência do faturamento (AAAAMM)
            # Derivamos da data_vencimento da primeira fatura
            try:
                venc = getattr(primeira_fat, 'data_vencimento', None)
                if venc and hasattr(venc, 'strftime'):
                    compet = venc.strftime('%Y%m')
                else:
                    # Fallback: usar data atual
                    from datetime import datetime
                    compet = datetime.now().strftime('%Y%m')
            except Exception:
                from datetime import datetime
                compet = datetime.now().strftime('%Y%m')
            SE(gFat, "CompetFat").text = compet
            
            # dVencFat: Data de vencimento da fatura (AAAA-MM-DD)
            try:
                venc = getattr(primeira_fat, 'data_vencimento', None)
                if venc and hasattr(venc, 'strftime'):
                    SE(gFat, "dVencFat").text = venc.strftime('%Y-%m-%d')
                else:
                    # Fallback: usar data atual
                    from datetime import datetime
                    SE(gFat, "dVencFat").text = datetime.now().strftime('%Y-%m-%d')
            except Exception:
                from datetime import datetime
                SE(gFat, "dVencFat").text = datetime.now().strftime('%Y-%m-%d')
            
            # codBarras: Linha digitável do código de barras (campo obrigatório, 1-48 dígitos)
            # Se não tivermos um código de barras real, geramos um placeholder válido
            try:
                cod_barras = getattr(primeira_fat, 'codigo_barras', None)
                if not cod_barras:
                    # Gera código numérico baseado no numero_fatura e valor
                    num_fat = str(getattr(primeira_fat, 'numero_fatura', '1')).replace('.', '').replace('-', '')[:10]
                    val_fat = int((getattr(primeira_fat, 'valor_fatura', 0) or 0) * 100)
                    cod_barras = f"{num_fat}{val_fat:010d}".zfill(48)[:48]  # Preenche com zeros até 48 dígitos
                SE(gFat, "codBarras").text = cod_barras
            except Exception:
                # Código de barras genérico de emergência
                SE(gFat, "codBarras").text = "000000000000000000000000000000000000000000000001"
    except HTTPException:
        raise
    except Exception as e:
        # Falha ao montar gFat - logar mas não interromper
        print(f"AVISO: Falha ao gerar grupo gFat: {e}")

    # Determina a URL do QR Code baseada na UF da chave de acesso
    # Os 2 primeiros dígitos da chave indicam o código da UF (IBGE)
    uf_code = nfcom.chave_acesso[:2] if nfcom.chave_acesso else "41"
    
    # Usa função helper para obter URL baseada no ambiente (ver início do arquivo).
    # Tenta preferir o ambiente definido na empresa associada à NFCom.
    try:
        empresa_ambiente = getattr(nfcom, 'empresa', None)
        empresa_ambiente = getattr(empresa_ambiente, 'ambiente_nfcom', None)
    except Exception:
        empresa_ambiente = None
    qr_code_base_url = get_qrcode_url_base(uf_code, ambiente=empresa_ambiente)
    
    # XSD exige parâmetro tpAmb=[1-2]: pattern obrigatório conforme nfcomTiposBasico_v1.00.xsd linha 1992
    # Nota: usar & simples pois lxml faz encoding automático para &amp;
    # tpAmb também deve refletir o ambiente da empresa quando disponível
    if empresa_ambiente in ('producao', 'producao'):
        tpAmb = "1"
    elif empresa_ambiente in ('homologacao', 'homologação', 'homolog'):
        tpAmb = "2"
    else:
        # Usar configuração global se não especificado por empresa
        tpAmb = "1" if settings.NFCOM_AMBIENTE == "producao" else "2"
    params = f"?chNFCom={nfcom.chave_acesso}&tpAmb={tpAmb}"
    try:
        if getattr(nfcom, 'tipo_emissao', None) == models.TipoEmissao.CONTINGENCIA:
            to_sign = nfcom.chave_acesso + settings.SECRET_KEY
            signature = hashlib.sha1(to_sign.encode('utf-8')).hexdigest()
            params += f"&sign={signature}"
    except Exception:
        pass
    qr_code_url = qr_code_base_url + params

    # Cria infAdic -> infCpl apenas com o QR Code (faturas agora estão estruturadas em gFat)
    # NOTA: não criamos `infNFComSupl` aqui dentro de <infNFCom>, pois o schema
    # espera `infNFComSupl` como elemento irmão de <infNFCom> (fora do bloco).
    try:
        if qr_code_url and str(qr_code_url).strip():
            infAdic = SE(infNFCom, "infAdic")
            qr_text = str(qr_code_url).strip().replace('\n', ' ').replace('\r', ' ')
            SE(infAdic, "infCpl").text = qr_text
    except Exception:
        # não bloquear a geração do XML por falha ao anexar QR
        pass

    # Converte a árvore XML para uma string formatada
    # ET.indent(infNFCom) # A biblioteca lxml já faz uma boa formatação
    xml_result = ET.tostring(infNFCom, encoding='unicode', method='xml')
    return xml_result

def _make_nfcom_snapshot(nfcom, empresa_snapshot, client_snapshot=None):
    """Cria um snapshot simples (plain object) de uma NFCom e sua empresa para gerar o XML
    sem anexar objetos ORM à sessão.
    """
    snap = SimpleNamespace()
    # Campos básicos
    snap.chave_acesso = getattr(nfcom, 'chave_acesso', None)
    snap.serie = getattr(nfcom, 'serie', None)
    snap.numero_nf = getattr(nfcom, 'numero_nf', None)
    snap.data_emissao = getattr(nfcom, 'data_emissao', None)
    snap.cMunFG = getattr(nfcom, 'cMunFG', '')
    snap.finalidade_emissao = getattr(nfcom, 'finalidade_emissao', None)
    snap.tpFat = getattr(nfcom, 'tpFat', None)
    snap.tipo_emissao = getattr(nfcom, 'tipo_emissao', None)
    snap.empresa = empresa_snapshot
    # Cliente
    if client_snapshot is not None:
        snap.cliente = client_snapshot
    else:
        # Se o objeto nfcom passado tem o relacionamento 'cliente' carregado, cria um snapshot simples
        cliente_obj = getattr(nfcom, 'cliente', None)
        if cliente_obj is not None:
            snap.cliente = SimpleNamespace(
                nome_razao_social=getattr(cliente_obj, 'nome_razao_social', ''),
                cpf_cnpj=getattr(cliente_obj, 'cpf_cnpj', ''),
                tipo_pessoa=getattr(cliente_obj, 'tipo_pessoa', None),
                ind_ie_dest=getattr(cliente_obj, 'ind_ie_dest', None),
                inscricao_estadual=getattr(cliente_obj, 'inscricao_estadual', '')
            )
        else:
            # Fallback para o objeto ORM se o snapshot não for fornecido (útil para create_nfcom)
            snap.cliente = None

    # Destino / endereço
    snap.dest_endereco = getattr(nfcom, 'dest_endereco', '')
    snap.dest_numero = getattr(nfcom, 'dest_numero', '')
    snap.dest_bairro = getattr(nfcom, 'dest_bairro', '')
    snap.dest_codigo_ibge = getattr(nfcom, 'dest_codigo_ibge', '')
    snap.dest_municipio = getattr(nfcom, 'dest_municipio', '')
    snap.dest_uf = getattr(nfcom, 'dest_uf', '')
    snap.dest_cep = getattr(nfcom, 'dest_cep', '')

    # Campos de contrato (preservar do banco para geração de XML)
    snap.numero_contrato = getattr(nfcom, 'numero_contrato', None)
    snap.d_contrato_ini = getattr(nfcom, 'd_contrato_ini', None)
    snap.d_contrato_fim = getattr(nfcom, 'd_contrato_fim', None)

    # Itens
    items = []
    for item in getattr(nfcom, 'itens', []) or []:
        it = SimpleNamespace(
            codigo_servico=getattr(item, 'codigo_servico', ''),
            descricao_servico=getattr(item, 'descricao_servico', ''),
            cClass=getattr(item, 'cClass', ''),
            cfop=getattr(item, 'cfop', None),
            unidade_medida=getattr(item, 'unidade_medida', ''),
            quantidade=getattr(item, 'quantidade', 0) or 0,
            valor_unitario=getattr(item, 'valor_unitario', 0) or 0,
            valor_desconto=getattr(item, 'valor_desconto', 0) or 0,
            valor_outros=getattr(item, 'valor_outros', 0) or 0,
            valor_total=getattr(item, 'valor_total', 0) or 0,
            base_calculo_icms=getattr(item, 'base_calculo_icms', 0) or 0,
            aliquota_icms=getattr(item, 'aliquota_icms', 0) or 0,
            base_calculo_pis=getattr(item, 'base_calculo_pis', 0) or 0,
            aliquota_pis=getattr(item, 'aliquota_pis', 0) or 0,
            base_calculo_cofins=getattr(item, 'base_calculo_cofins', 0) or 0,
            aliquota_cofins=getattr(item, 'aliquota_cofins', 0) or 0,
        )
        items.append(it)
    snap.itens = items
    # Faturas (cobranças) associadas à NFCom
    faturas = []
    for f in getattr(nfcom, 'faturas', []) or []:
        try:
            fv = SimpleNamespace(
                numero_fatura=getattr(f, 'numero_fatura', ''),
                data_vencimento=getattr(f, 'data_vencimento', None),
                valor_fatura=getattr(f, 'valor_fatura', 0) or 0,
            )
            faturas.append(fv)
        except Exception:
            continue
    snap.faturas = faturas

    snap.valor_total = getattr(nfcom, 'valor_total', 0) or 0
    return snap

def sign_nfcom_xml(xml_string: str, empresa, chave_acesso: str = None, tipo_emissao=None) -> str:
    """
    Assina o XML da NFCom com assinatura enveloped usando cryptography.
    Implementação corrigida baseada na análise de XMLs válidos.
    """
    import traceback

    try:
        import xmlsec
        from cryptography.hazmat.primitives.serialization import pkcs12
        from cryptography.hazmat.primitives import serialization
        import base64
        import traceback
        import traceback
        import re

        # Resolve caminho absoluto do certificado (aceita caminho absoluto ou relativo ao CERTIFICATES_DIR)
        cert_path_raw = empresa.certificado_path or ""
        cert_path_norm = cert_path_raw.replace("/secure/", "").replace("\\secure\\", "")
        cert_path_norm = cert_path_norm.lstrip('/\\')
        if Path(cert_path_raw).is_absolute():
            absolute_cert_path = Path(cert_path_raw)
        else:
            absolute_cert_path = Path(settings.CERTIFICATES_DIR) / cert_path_norm

        # Verifica existência e acessibilidade; fornecer mensagens claras ao cliente
        if not absolute_cert_path.exists():
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Arquivo de certificado não encontrado: {absolute_cert_path}")

        # Se for diretório, tenta encontrar automaticamente um .pfx/.p12 dentro dele
        try:
            if absolute_cert_path.is_dir():
                pfx_candidates = list(absolute_cert_path.glob('*.pfx')) + list(absolute_cert_path.glob('*.p12'))
                if pfx_candidates:
                    absolute_cert_path = pfx_candidates[0]
                else:
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=(
                        f"Caminho de certificado é um diretório mas não contém arquivos .pfx/.p12: {absolute_cert_path}. "
                        "Defina `empresa.certificado_path` apontando para o arquivo .pfx/.p12 ou coloque o arquivo no diretório especificado."))
        except PermissionError:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Permissão negada ao acessar o diretório do certificado: {absolute_cert_path}")

        # Verifica permissão de leitura
        if not os.access(str(absolute_cert_path), os.R_OK):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=(
                f"Permissão negada ao acessar o certificado: {absolute_cert_path}. Verifique as permissões do arquivo e o usuário do processo."))

        # Abre o arquivo PFX/P12 com tratamento de PermissionError para mensagens claras
        try:
            with open(absolute_cert_path, "rb") as f:
                pfx_data = f.read()
        except PermissionError:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=(
                f"Permissão negada ao abrir o certificado: {absolute_cert_path}. Verifique se o processo tem permissão de leitura."))

        # Descriptografa a senha se necessário
        certificado_senha = ""
        if hasattr(empresa, 'certificado_senha') and empresa.certificado_senha:
            print(f"DEBUG: certificado_senha raw = {empresa.certificado_senha[:20]}..." if len(empresa.certificado_senha) > 20 else f"DEBUG: certificado_senha raw = {empresa.certificado_senha}")
            print(f"DEBUG: certificado_senha começa com 'gAAAAA'? {empresa.certificado_senha.startswith('gAAAAA') if isinstance(empresa.certificado_senha, str) else 'N/A'}")
            
            if isinstance(empresa.certificado_senha, str) and len(empresa.certificado_senha) > 0 and not empresa.certificado_senha.startswith('gAAAAA'):
                # Senha em texto plano (compatibilidade com dados antigos)
                certificado_senha = empresa.certificado_senha
                print(f"DEBUG: Usando senha em TEXTO PLANO")
            else:
                # Senha criptografada (padrão)
                try:
                    certificado_senha = decrypt_sensitive_data(empresa.certificado_senha)
                    print(f"DEBUG: Senha DESCRIPTOGRAFADA com sucesso")
                except Exception as e:
                    print(f"DEBUG: ERRO ao descriptografar senha: {e}")
                    certificado_senha = None
        else:
            print(f"DEBUG: Empresa SEM certificado_senha definido")

        senha_bytes = certificado_senha.encode('utf-8') if certificado_senha else None
        print(f"DEBUG: senha_bytes = {'<bytes>' if senha_bytes else 'None'}, len={len(senha_bytes) if senha_bytes else 0}")
        
        try:
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(pfx_data, senha_bytes)
            print(f"DEBUG: Certificado carregado COM SUCESSO usando senha fornecida")
        except Exception as e1:
            print(f"DEBUG: FALHA ao carregar com senha: {e1}")
            try:
                private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(pfx_data, None)
                print(f"DEBUG: Certificado carregado SEM SENHA (certificado sem proteção)")
            except Exception as e2:
                print(f"DEBUG: FALHA ao carregar sem senha: {e2}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao assinar NFCom: {str(e1)}"
                )

        # Prepara árvore XML
        ns = "http://www.portalfiscal.inf.br/nfcom"
        # Parse original infNFCom and reserialize/parsing to remove incidental formatting
        # (minify) so there are no whitespace-only text/tails between tags that some
        # autorizadores consider 'caracteres de edição'. We minify BEFORE signing.
        root_inf = etree.fromstring(xml_string.encode('utf-8'))  # <infNFCom>
        try:
            minified = etree.tostring(root_inf, encoding='utf-8', method='xml', pretty_print=False)
            root_inf = etree.fromstring(minified)
        except Exception:
            # fallback: keep original tree if minify fails
            pass

        # Monta <NFCom> raiz e anexa infNFCom
        nfcom_root = etree.Element(f"{{{ns}}}NFCom", nsmap={None: ns})
        nfcom_root.append(root_inf)

        # Normaliza tails que contenham apenas espaços/quebras para evitar inserção de
        # caracteres de edição (CR/LF) entre as tags no XML serializado. Isso não
        # altera textos de elementos que contenham conteúdo real — remove apenas
        # tails que são puramente whitespace (indentação).
        def _remove_indentation_tails(elem):
            for child in elem:
                if child.tail is not None and child.tail.strip() == '':
                    child.tail = ''
                _remove_indentation_tails(child)
        _remove_indentation_tails(nfcom_root)

        # infNFComSupl com QR Code (URL baseada na UF)
        infNFComSupl = etree.SubElement(nfcom_root, f"{{{ns}}}infNFComSupl")
        qrCodNFCom = etree.SubElement(infNFComSupl, f"{{{ns}}}qrCodNFCom")
        
        # Determina URL do QR Code pela UF da chave usando função helper
        uf_code = chave_acesso[:2] if chave_acesso else "41"
        # Preferir o ambiente da empresa (parâmetro `empresa`) quando disponível
        try:
            empresa_ambiente = getattr(empresa, 'ambiente_nfcom', None)
        except Exception:
            empresa_ambiente = None
        qr_code_base_url = get_qrcode_url_base(uf_code, ambiente=empresa_ambiente)
        
        # XSD exige parâmetro tpAmb=[1-2]: pattern obrigatório conforme nfcomTiposBasico_v1.00.xsd linha 1992
        # Determinar tpAmb a partir do ambiente da empresa quando possível
        if empresa_ambiente in ('producao', 'producao'):
            tpAmb = "1"
        elif empresa_ambiente in ('homologacao', 'homologação', 'homolog'):
            tpAmb = "2"
        else:
            # Usar configuração global se não especificado por empresa
            tpAmb = "1" if settings.NFCOM_AMBIENTE == "producao" else "2"
        params = f"?chNFCom={chave_acesso}&tpAmb={tpAmb}"
        try:
            # Adiciona parâmetro sign APENAS quando for emissão em CONTINGÊNCIA
            if getattr(tipo_emissao, 'value', None) == getattr(models.TipoEmissao, 'CONTINGENCIA', None) or str(tipo_emissao) == str(models.TipoEmissao.CONTINGENCIA):
                if getattr(settings, 'SECRET_KEY', None):
                    to_sign = (chave_acesso or '') + settings.SECRET_KEY
                    signature = hashlib.sha1(to_sign.encode('utf-8')).hexdigest()
                    params += f"&sign={signature}"
        except Exception:
            pass
        qrCodNFCom.text = qr_code_base_url + params
        # Log adicional para garantir correção futura: mostra tpAmb usado no QR
        try:
            print(f"DEBUG: URL QR Code gerada: {qrCodNFCom.text} (tpAmb={tpAmb}, empresa_ambiente={empresa_ambiente}, settings.NFCOM_AMBIENTE={settings.NFCOM_AMBIENTE})")
        except Exception:
            # Não falhar por logging
            pass

        # Assinatura enveloped: referência ao Id do infNFCom
        inf_id = root_inf.get('Id')
        if not inf_id:
            raise HTTPException(status_code=500, detail="Elemento <infNFCom> sem atributo Id para assinatura")

        # Registrar atributos Id para que xmlsec reconheça as referências
        try:
            xmlsec.tree.add_ids(nfcom_root, ["Id"])
        except Exception:
            # se não for possível registrar, não fatal — tentaremos assinar mesmo assim
            pass

        # Cria template de assinatura (c14n inclusiva, rsa-sha1) como filho direto de <NFCom>
        # IMPORTANTE: a posição da assinatura deve ficar APÓS <infNFComSupl> para satisfazer o XSD
        # CRÍTICO: Para evitar "Uso de prefixo de namespace não permitido" (SEFAZ-MG),
        # criamos o elemento <ds:Signature> com nsmap explícito que NÃO inclui xmlns default do NFCom.
        # IMPORTANTE: SEFAZ-MG pode rejeitar o uso do PREFIXO "ds:". Vamos testar SEM prefixo.
        ds_ns = 'http://www.w3.org/2000/09/xmldsig#'
        
        # Cria um documento XML ISOLADO apenas para o Signature (sem namespace padrão herdado)
        # ESTRATÉGIA: Manter o Signature FORA do nfcom_root até APÓS a assinatura
        # CRÍTICO: Criar elementos SEM prefixo ds: (apenas com namespace no tag)
        isolated_root = etree.Element('temp')
        sign_node = etree.SubElement(isolated_root, '{%s}Signature' % ds_ns, nsmap={None: ds_ns})
        
        # Adiciona filhos manualmente (SignedInfo, SignatureValue, KeyInfo) SEM prefixo
        signed_info = etree.SubElement(sign_node, '{%s}SignedInfo' % ds_ns)
        c14n_method = etree.SubElement(signed_info, '{%s}CanonicalizationMethod' % ds_ns)
        c14n_method.set('Algorithm', 'http://www.w3.org/TR/2001/REC-xml-c14n-20010315')
        sig_method = etree.SubElement(signed_info, '{%s}SignatureMethod' % ds_ns)
        sig_method.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#rsa-sha1')
        
        etree.SubElement(sign_node, '{%s}SignatureValue' % ds_ns)
        key_info_elem = etree.SubElement(sign_node, '{%s}KeyInfo' % ds_ns)
        etree.SubElement(key_info_elem, '{%s}X509Data' % ds_ns)
        
        # adiciona referência com transforms (enveloped + c14n) diretamente no SignedInfo
        ref = etree.SubElement(signed_info, '{%s}Reference' % ds_ns)
        ref.set('URI', "#%s" % inf_id)
        transforms = etree.SubElement(ref, '{%s}Transforms' % ds_ns)
        tr1 = etree.SubElement(transforms, '{%s}Transform' % ds_ns)
        tr1.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#enveloped-signature')
        tr2 = etree.SubElement(transforms, '{%s}Transform' % ds_ns)
        tr2.set('Algorithm', 'http://www.w3.org/TR/2001/REC-xml-c14n-20010315')
        digest_method = etree.SubElement(ref, '{%s}DigestMethod' % ds_ns)
        digest_method.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#sha1')
        etree.SubElement(ref, '{%s}DigestValue' % ds_ns)

        # CRÍTICO: Remove TODOS os text/tail whitespace do template da assinatura ANTES de assinar
        # para evitar que o xmlsec calcule a assinatura COM os \n (que causam cStat=599)
        for elem in sign_node.iter():
            if elem.text and not elem.text.strip():
                elem.text = None
            if elem.tail and not elem.tail.strip():
                elem.tail = None

        pem_path = None
        try:
            try:
                pem_path = _convert_pfx_to_pem(pfx_data, certificado_senha)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Erro ao converter PFX para PEM: {e}")

            # Extrai o certificado em base64 do PEM gerado para garantir que X509Certificate seja preenchido
            cert_b64_from_pem = None
            try:
                if pem_path and os.path.exists(pem_path):
                    with open(pem_path, 'r', encoding='utf-8') as pf:
                        pem_text = pf.read()
                    m = re.search(r"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----", pem_text, re.S)
                    if m:
                        cert_b64_from_pem = ''.join(m.group(1).split())
            except Exception as e:
                print('DEBUG: falha ao extrair certificado do PEM logo após conversao:', e)

            ctx = xmlsec.SignatureContext()
            try:
                print(f"DEBUG: loading key from PEM path: {pem_path}")
                key = xmlsec.Key.from_file(pem_path, xmlsec.KeyFormat.PEM, None)
                ctx.key = key
                
                # CRÍTICO: Carregar o certificado no key para que xmlsec preencha X509Certificate automaticamente
                try:
                    # Carrega o certificado x509 no key object
                    key.load_cert_from_file(pem_path, xmlsec.KeyFormat.CERT_PEM)
                    print('DEBUG: Certificado carregado no key object com sucesso')
                except Exception as cert_err:
                    print(f'DEBUG: Falha ao carregar certificado no key: {cert_err}')
                    # Não é fatal - vamos preencher manualmente depois
                    
            except Exception as e:
                tb = traceback.format_exc()
                print('DEBUG: falha ao carregar chave PEM:', e, tb)
                raise HTTPException(status_code=500, detail=f"Erro ao carregar chave PEM para assinatura: {e}\n{tb}")

            # Assina
            try:
                # DEBUG: dump the signature template before signing to help diagnose failures
                try:
                    print('DEBUG: Signature template before sign:\n', etree.tostring(sign_node, encoding='unicode', pretty_print=True))
                except Exception:
                    pass

                # EXTRA DEBUG: mostrar nsmap do Signature e dos ancestrais para entender onde o xmlns padrao aparece
                try:
                    parent = sign_node.getparent()
                    def ancestors(elem):
                        cur = elem
                        outs = []
                        while cur is not None:
                            outs.append(cur)
                            cur = cur.getparent()
                        return outs

                    print('DEBUG: sign_node.nsmap=', getattr(sign_node, 'nsmap', None))
                    print('DEBUG: sign_node está isolado (parent é temp)?', parent.tag == 'temp' if parent is not None else 'No parent')
                except Exception as e:
                    print('DEBUG: erro ao coletar nsmap/debugs adicionais:', e)

                # ESTRATÉGIA NOVA: assinar ANTES de inserir no nfcom_root
                # Primeiro, insere temporariamente no nfcom_root para que xmlsec possa resolver a URI
                try:
                    inf_supl = nfcom_root.find('{%s}infNFComSupl' % ns)
                    if inf_supl is not None:
                        idx = list(nfcom_root).index(inf_supl)
                        nfcom_root.insert(idx + 1, sign_node)
                    else:
                        nfcom_root.append(sign_node)
                except Exception:
                    nfcom_root.append(sign_node)
                
                ctx.sign(sign_node)
                
                # CRÍTICO: xmlsec pode não preencher X509Certificate automaticamente.
                # Garantir que está preenchido ANTES de serializar
                try:
                    x509data = sign_node.find('.//{http://www.w3.org/2000/09/xmldsig#}X509Data')
                    if x509data is not None:
                        x509cert = x509data.find('.//{http://www.w3.org/2000/09/xmldsig#}X509Certificate')
                        if x509cert is None:
                            # Cria o elemento
                            x509cert = etree.SubElement(x509data, '{http://www.w3.org/2000/09/xmldsig#}X509Certificate')
                        
                        # Preenche se estiver vazio
                        if not x509cert.text or not x509cert.text.strip():
                            # Tenta obter certificado do objeto certificate carregado do PKCS12
                            if 'certificate' in locals() and certificate is not None:
                                cert_der = certificate.public_bytes(serialization.Encoding.DER)
                                x509cert.text = base64.b64encode(cert_der).decode('utf-8')
                                print('DEBUG: X509Certificate preenchido manualmente com certificado do PKCS12')
                            elif 'cert_b64_from_pem' in locals() and cert_b64_from_pem:
                                x509cert.text = cert_b64_from_pem
                                print('DEBUG: X509Certificate preenchido manualmente do PEM extraído')
                        else:
                            print(f'DEBUG: X509Certificate já preenchido pelo xmlsec (len={len(x509cert.text)})')
                except Exception as e:
                    print(f'DEBUG: Erro ao verificar/preencher X509Certificate: {e}')
                
                # APÓS assinar, remove o Signature assinado e serializa para string SEM namespace padrão
                signed_signature_xml = etree.tostring(sign_node, encoding='unicode')
                
                # DEBUG: Verificar se X509Certificate está presente após assinatura
                if 'X509Certificate' in signed_signature_xml:
                    # Extrair trecho do certificado
                    import re
                    cert_match = re.search(r'<(?:ds:)?X509Certificate>(.{0,100})', signed_signature_xml)
                    if cert_match:
                        print(f'DEBUG: X509Certificate PRESENTE após sign: {cert_match.group(0)[:150]}...')
                    else:
                        print('DEBUG: X509Certificate tag encontrada mas vazia')
                else:
                    print('DEBUG: AVISO - X509Certificate NÃO encontrado após xmlsec.sign()!')
                
                # Remove o Signature do nfcom_root
                nfcom_root.remove(sign_node)
                
                # Usa regex para remover xmlns padrão da string do Signature (se houver ds:)
                import re
                signed_signature_xml_clean = re.sub(
                    r'(<ds:Signature[^>]*?)\s+xmlns="http://www\.portalfiscal\.inf\.br/nfcom"',
                    r'\1',
                    signed_signature_xml
                )
                
                print(f'DEBUG: Signature assinado (antes limpeza): {signed_signature_xml[:200]}')
                print(f'DEBUG: Signature assinado (depois limpeza): {signed_signature_xml_clean[:200]}')
                
                # Reparsa o Signature limpo e insere novamente no nfcom_root
                clean_sign_node = etree.fromstring(signed_signature_xml_clean.encode('utf-8'))
                
                try:
                    inf_supl = nfcom_root.find('{%s}infNFComSupl' % ns)
                    if inf_supl is not None:
                        idx = list(nfcom_root).index(inf_supl)
                        nfcom_root.insert(idx + 1, clean_sign_node)
                    else:
                        nfcom_root.append(clean_sign_node)
                except Exception:
                    nfcom_root.append(clean_sign_node)
                
                print('DEBUG: Signature assinado e limpo reinserido no nfcom_root')

                    # Note: Não forçar modificações no SignedInfo/C14N após a assinatura.
                    # Modificar a CanonicalizationMethod após a assinatura invalida o valor de SignatureValue.
                    # A canonicalização inclusiva é especificada já na criação do template (xmlsec.Transform.C14N)
                    # e seu uso é suficiente para atender o XSD.
            except Exception as e:
                tb = traceback.format_exc()
                print('ERRO ao executar ctx.sign:', e, tb)
                raise

                # DEBUG: log estado do certificado e do conteúdo extraído do PEM
                try:
                    print('DEBUG: certificate is None?', certificate is None)
                except NameError:
                    print('DEBUG: certificate variable não definida')
                try:
                    print('DEBUG: cert_b64_from_pem present?', bool(cert_b64_from_pem))
                except NameError:
                    print('DEBUG: cert_b64_from_pem variable não definida')

                # Garantir que o X509Certificate esteja presente em KeyInfo (algumas versões do xmlsec
                # podem inserir apenas um contêiner X509Data vazio). Inserimos explicitamente o bloco base64.
                try:
                    sig_elem = nfcom_root.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature')
                    if sig_elem is not None:
                        ki = sig_elem.find('.//{http://www.w3.org/2000/09/xmldsig#}KeyInfo')
                        if ki is None:
                            ki = etree.SubElement(sig_elem, '{http://www.w3.org/2000/09/xmldsig#}KeyInfo')
                        x509data = ki.find('{http://www.w3.org/2000/09/xmldsig#}X509Data')
                        if x509data is None:
                            x509data = etree.SubElement(ki, '{http://www.w3.org/2000/09/xmldsig#}X509Data')
                        x509cert = x509data.find('{http://www.w3.org/2000/09/xmldsig#}X509Certificate')
                        if x509cert is None:
                            x509cert = etree.SubElement(x509data, '{http://www.w3.org/2000/09/xmldsig#}X509Certificate')
                        # Preencher o texto do certificado; prioriza objeto certificate, depois o PEM extraído
                        try:
                            if 'certificate' in locals() and certificate is not None:
                                cert_der = certificate.public_bytes(serialization.Encoding.DER)
                                x509cert.text = base64.b64encode(cert_der).decode('utf-8')
                            elif 'cert_b64_from_pem' in locals() and cert_b64_from_pem:
                                x509cert.text = cert_b64_from_pem
                            else:
                                # última tentativa: ler pem_path agora
                                try:
                                    with open(pem_path, 'r', encoding='utf-8') as pf:
                                        pem_text = pf.read()
                                    m = re.search(r"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----", pem_text, re.S)
                                    if m:
                                        cert_b64_late = ''.join(m.group(1).split())
                                        x509cert.text = cert_b64_late
                                except Exception as e:
                                    print('DEBUG: falha ao preencher X509Certificate na etapa final:', e)
                        except Exception as e:
                            print('DEBUG: erro ao serializar/preencher X509Certificate:', e)
                except Exception as e:
                    print('DEBUG: erro ao localizar/inserir KeyInfo/X509Certificate:', e)

            # Insere manualmente o certificado em KeyInfo caso esteja ausente
            try:
                ki = sign_node.find('.//{http://www.w3.org/2000/09/xmldsig#}KeyInfo')
                if ki is not None:
                    x509data = ki.find('.//{http://www.w3.org/2000/09/xmldsig#}X509Data')
                    if x509data is None:
                        x509data = etree.SubElement(ki, '{http://www.w3.org/2000/09/xmldsig#}X509Data')
                    x509cert = x509data.find('.//{http://www.w3.org/2000/09/xmldsig#}X509Certificate')
                    if x509cert is None:
                        x509cert = etree.SubElement(x509data, '{http://www.w3.org/2000/09/xmldsig#}X509Certificate')
                        try:
                            # Prefer certificate object loaded from PKCS12
                            if certificate is not None:
                                cert_der = certificate.public_bytes(serialization.Encoding.DER)
                                x509cert.text = base64.b64encode(cert_der).decode('utf-8')
                            elif cert_b64_from_pem is not None:
                                x509cert.text = cert_b64_from_pem
                            else:
                                # Last resort: try to read PEM file now
                                try:
                                    with open(pem_path, 'r', encoding='utf-8') as pf:
                                        pem_text = pf.read()
                                    m = re.search(r"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----", pem_text, re.S)
                                    if m:
                                        cert_b64 = ''.join(m.group(1).split())
                                        x509cert.text = cert_b64
                                except Exception as e:
                                    print('DEBUG: falha ao extrair certificado do PEM (fallback tardio):', e)
                        except Exception as e:
                            print('DEBUG: falha ao serializar certificado para DER:', e)
            except Exception:
                # Não bloquear o fluxo principal, mas registrar para depuração
                tb = traceback.format_exc()
                print('DEBUG: erro ao inserir X509Certificate no KeyInfo:', tb)

            # Remove TODOS os tail (texto após elemento) da árvore da assinatura
            # NÃO removemos .text porque isso invalida a assinatura (cStat=297)
            # A assinatura é calculada COM os \n no .text
            signature_node = nfcom_root.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature')
            if signature_node is not None:
                for elem in signature_node.iter():
                    # Remove tail (texto após </elemento>)
                    if elem.tail:
                        elem.tail = None
                # Remove tail da própria Signature também
                if signature_node.tail:
                    signature_node.tail = None

            # Serializa o NFCom assinado usando C14N para canonicalizar e remover whitespace
            # IMPORTANTE: C14N não aceita encoding='unicode', usa utf-8 e decodifica
            signed_xml_bytes = etree.tostring(nfcom_root, method='c14n')
            signed_xml = signed_xml_bytes.decode('utf-8')
            # Adiciona declaração XML conforme MOC pg11
            signed_xml = '<?xml version="1.0" encoding="UTF-8"?>' + signed_xml

            # Normaliza SignatureValue e X509Certificate para evitar quebras/char de edição
            # que podem causar rejeição 599 pela SEFAZ (remove quebras de linha dentro das tags).
            try:
                import re
                # Remove espaços e quebras de linha internas de SignatureValue
                def _collapse_tag(tag, xml_text):
                    pattern = fr"(<ds:{tag}[^>]*>)(.*?)(</ds:{tag}>)"
                    def repl(m):
                        inner = m.group(2)
                        collapsed = re.sub(r"\s+", "", inner)
                        return f"{m.group(1)}{collapsed}{m.group(3)}"
                    return re.sub(pattern, repl, xml_text, flags=re.S)

                signed_xml = _collapse_tag('SignatureValue', signed_xml)
                signed_xml = _collapse_tag('X509Certificate', signed_xml)
                
                # NÃO remover quebras entre tags da assinatura - isso invalida a assinatura!
                # A solução é garantir que tostring não adicione formatação (pretty_print=False)
                    
            except Exception as e:
                print('DEBUG: falha ao normalizar SignatureValue/X509Certificate:', e)
            # Garantir via manipulação de string que X509Certificate esteja presente
            try:
                cert_text_b64 = None
                if 'certificate' in locals() and certificate is not None:
                    try:
                        cert_der = certificate.public_bytes(serialization.Encoding.DER)
                        cert_text_b64 = base64.b64encode(cert_der).decode('utf-8')
                    except Exception:
                        cert_text_b64 = None
                if not cert_text_b64 and 'cert_b64_from_pem' in locals() and cert_b64_from_pem:
                    cert_text_b64 = cert_b64_from_pem

                if cert_text_b64:
                    if '<ds:X509Data/>' in signed_xml:
                        signed_xml = signed_xml.replace('<ds:X509Data/>', f'<ds:X509Data><ds:X509Certificate>{cert_text_b64}</ds:X509Certificate></ds:X509Data>')
                    elif '<ds:X509Data></ds:X509Data>' in signed_xml:
                        signed_xml = signed_xml.replace('<ds:X509Data></ds:X509Data>', f'<ds:X509Data><ds:X509Certificate>{cert_text_b64}</ds:X509Certificate></ds:X509Data>')
            except Exception as e:
                print('DEBUG: erro ao injetar X509Certificate na string assinada:', e)

            # NOTA: Não substituímos a URI de canonicalização depois da assinatura,
            # isso altera o SignedInfo e invalida SignatureValue. A canonicalização
            # correta deve ser definida antes da assinatura no template.
            
            # DEBUG FINAL: Verificar como está o Signature no XML completo antes de retornar
            try:
                import re
                # Busca com e sem prefixo ds:
                sig_match = re.search(r'<(?:ds:)?Signature[^>]*>', signed_xml)
                if sig_match:
                    print(f'DEBUG FINAL: Signature no XML completo: {sig_match.group(0)[:300]}')
                else:
                    print('DEBUG FINAL: Signature não encontrado no XML final')
                
                # Verifica se X509Certificate está presente
                if '<X509Certificate>' in signed_xml or '<ds:X509Certificate>' in signed_xml:
                    cert_match = re.search(r'<(?:ds:)?X509Certificate>(.{0,100})', signed_xml)
                    if cert_match:
                        print(f'DEBUG FINAL: X509Certificate encontrado: {cert_match.group(0)[:150]}...')
                else:
                    print('DEBUG FINAL: AVISO - X509Certificate NÃO encontrado no XML!')
            except Exception as e:
                print(f'DEBUG FINAL: Erro ao buscar Signature: {e}')
            
            return signed_xml
        finally:
            if pem_path and os.path.exists(pem_path):
                try:
                    os.remove(pem_path)
                except Exception:
                    pass

    except ImportError as ie:
        tb = traceback.format_exc()
        print("ERRO na assinatura NFCom (xmlsec não disponível):\n", tb)
        raise HTTPException(status_code=500, detail=f"xmlsec não disponível: {ie}")
    except HTTPException:
        # re-raise HTTPException sem empacotar
        raise
    except Exception as e:
        tb = traceback.format_exc()
        # Detect common xmlsec/libxml2 mismatch and provide actionable guidance
        err_text = str(e) + "\n" + tb
        print("ERRO na assinatura NFCom (cryptography/xmlsec):\n", err_text)
        if 'libxml2' in err_text or 'lxml & xmlsec' in err_text or type(e).__name__ == 'InternalError':
            detail = (
                "Erro interno do xmlsec: possível incompatibilidade entre as bibliotecas libxml2/libxslt usadas por lxml e xmlsec.\n"
                "Soluções sugeridas:\n"
                " 1) Reinstalar lxml e xmlsec com rodas binárias compatíveis (pip):\n"
                "    python -m pip uninstall lxml xmlsec -y; python -m pip install --upgrade pip wheel setuptools; python -m pip install lxml xmlsec --prefer-binary\n"
                " 2) Ou usar conda (recomendado se disponível):\n"
                "    conda install -c conda-forge libxml2 libxslt xmlsec python-lxml python-xmlsec\n"
                "3) Como alternativa temporária, execute a assinatura em uma máquina/container com xmlsec funcional e mova o arquivo gerado.\n\n"
                f"Detalhes técnicos: {str(e)}"
            )
            raise HTTPException(status_code=500, detail=detail)
        raise HTTPException(status_code=500, detail=f"Erro ao assinar NFCom: {str(e)}\nTraceback: {tb}")

def validate_xml_with_xsd(xml_string: str, xsd_path: str):
    """Valida uma string XML contra um arquivo de schema XSD."""
    try:
        # Parse o schema XSD
        xsd_doc = etree.parse(xsd_path)
        xsd_schema = etree.XMLSchema(xsd_doc)

        # Parse o XML que queremos validar
        xml_doc = etree.fromstring(xml_string.encode('utf-8'))

        # Valida o XML contra o schema
        xsd_schema.assertValid(xml_doc)
        print("INFO: XML validado com sucesso contra o schema XSD.")
        return True
    except etree.DocumentInvalid as e:
        print(f"ERRO de validação XSD: {e}")
        raise HTTPException(status_code=400, detail=f"XML inválido: {str(e)}")
    except Exception as e:
        print(f"ERRO inesperado na validação XSD: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar validação do XML: {str(e)}")


def _convert_pfx_to_pem(pfx_data: bytes, password: str | None) -> str:
    """Converte um arquivo PFX (PKCS#12) em um arquivo PEM temporário contendo
    a chave privada e o(s) certificados concatenados. Retorna o caminho para o PEM.

    Observação: o arquivo gerado deve ser removido pelo chamador quando não for mais necessário.
    """
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.hazmat.primitives import serialization as crypto_serialization
    import tempfile

    senha_bytes = password.encode('utf-8') if password else None
    try:
        private_key, cert, additional_certs = pkcs12.load_key_and_certificates(pfx_data, senha_bytes)
    except Exception:
        # Tenta carregar sem senha como fallback
        private_key, cert, additional_certs = pkcs12.load_key_and_certificates(pfx_data, None)

    if not private_key or not cert:
        raise Exception("PFX inválido: não foi possível extrair chave privada e/ou certificado.")

    # Serializa a chave privada em PEM
    private_pem = private_key.private_bytes(
        encoding=crypto_serialization.Encoding.PEM,
        format=crypto_serialization.PrivateFormat.PKCS8,
        encryption_algorithm=crypto_serialization.NoEncryption()
    )

    # Serializa o certificado principal
    cert_pem = cert.public_bytes(crypto_serialization.Encoding.PEM)

    # Serializa certificados adicionais, se houver
    extra_pems = b""
    if additional_certs:
        for ac in additional_certs:
            try:
                extra_pems += ac.public_bytes(crypto_serialization.Encoding.PEM)
            except Exception:
                continue

    # Escreve tudo em um arquivo temporário e retorna o caminho
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pem', prefix='cert_', dir=None)
    try:
        tmp.write(private_pem)
        tmp.write(cert_pem)
        if extra_pems:
            tmp.write(extra_pems)
        tmp.flush()
        tmp.close()
        return tmp.name
    except Exception:
        try:
            tmp.close()
        except Exception:
            pass
        raise

def create_nfcom(db: Session, nfcom_in: nfcom_schema.NFComCreate, empresa_id: int) -> models.NFCom:
    """Cria uma nova NFCom e seus itens, utilizando o endereço fornecido no input."""
    
    # 1. Prepara os dados da NFCom principal, excluindo os itens para processamento separado
    # Exclui itens e faturas do payload ao criar o objeto NFCom principal
    nfcom_data = nfcom_in.model_dump(exclude={"itens", "faturas"})

    # Garante que exista data_emissao ao criar uma nota nova (evita erro em generate_access_key)
    # Se o usuário não forneceu, usamos o horário atual (homologação costuma aceitar).
    from datetime import datetime
    if not nfcom_data.get('data_emissao'):
        nfcom_data['data_emissao'] = datetime.now()

    # 2. Define o número e a série da nota
    serie = 1 # Série fixa por enquanto
    numero_nf = get_next_numero_nf(db, empresa_id=empresa_id, serie=serie)

    # Pré-cria o objeto para ter acesso aos dados para gerar a chave
    # (sem adicionar ao DB ainda)
    temp_nfcom = models.NFCom(**nfcom_data, empresa_id=empresa_id, numero_nf=numero_nf, serie=serie)
    # Não carregar o objeto Empresa na sessão: buscamos apenas os campos necessários
    # Busca campos necessários para gerar o XML (emit)
    empresa_row = db.execute(text('''
        SELECT cnpj, codigo_ibge, inscricao_estadual, regime_tributario,
               razao_social, endereco, numero, bairro, municipio, cep, uf
        FROM empresas WHERE id = :empresa_id
    '''), {'empresa_id': empresa_id}).fetchone()
    if not empresa_row:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    # Monta um snapshot leve da empresa com todos os campos usados na geração do XML
    temp_empresa = SimpleNamespace(
        cnpj=empresa_row[0] or '',
        codigo_ibge=empresa_row[1] or '',
        inscricao_estadual=empresa_row[2] or '',
        regime_tributario=empresa_row[3] or '',
        razao_social=empresa_row[4] or '',
        endereco=empresa_row[5] or '',
        numero=empresa_row[6] or '',
        bairro=empresa_row[7] or '',
        municipio=empresa_row[8] or '',
        cep=empresa_row[9] or '',
        uf=empresa_row[10] or ''
    )
    # Não atribuímos temp_empresa à relação ORM (isso dispara eventos do SQLAlchemy).
    # Em vez disso, criamos um objeto temporário com os campos necessários para
    # gerar a chave de acesso e o passamos para a função.
    # Garante que tipo_emissao tenha um fallback legível por generate_access_key
    tipo_emissao_obj = getattr(temp_nfcom, 'tipo_emissao', None)
    if not tipo_emissao_obj:
        # cria um objeto simples com atributo `value` esperado pela função
        tipo_emissao_obj = SimpleNamespace(value='1')

    temp_for_key = SimpleNamespace(
        empresa=temp_empresa,
        data_emissao=temp_nfcom.data_emissao,
        serie=serie,
        numero_nf=numero_nf,
        tipo_emissao=tipo_emissao_obj
    )
    # NÃO geramos a chave aqui: vamos persistir o registro primeiro para obter o `id`
    # e usar esse `id` como base para o cNF (determinístico e único).
    
    # 3. Cria a instância do modelo NFCom com todos os dados, incluindo o endereço snapshotado
    db_nfcom = models.NFCom(
        **nfcom_data,
        empresa_id=empresa_id,
        numero_nf=numero_nf,
        serie=serie
    )
    db.add(db_nfcom)
    db.flush()  # Para obter o ID da NFCom
    
    # Grupo <det> - Itens da NFCom
    db.query(models.NFComItem).filter(models.NFComItem.nfcom_id == db_nfcom.id).delete()
    db.flush()

    for item_in in nfcom_in.itens:
        item_data = item_in.model_dump()
        # Normaliza valores que podem vir como strings (ex: '1.800,00')
        def _to_float_local(v):
            try:
                from decimal import Decimal
                if v is None:
                    return 0.0
                if isinstance(v, (int, float)):
                    return float(v)
                if isinstance(v, Decimal):
                    return float(v)
                if isinstance(v, str):
                    s = v.strip()
                    if s.count(',') == 1 and s.count('.') >= 1:
                        s = s.replace('.', '').replace(',', '.')
                    else:
                        s = s.replace(',', '.')
                    s = s.replace(' ', '')
                    return float(s)
            except Exception:
                return 0.0
        valor_total_item = (_to_float_local(item_data.get('quantidade', 0)) * _to_float_local(item_data.get('valor_unitario', 0))) - _to_float_local(item_data.get('valor_desconto', 0)) + _to_float_local(item_data.get('valor_outros', 0))
        db_item = models.NFComItem(**item_data, valor_total=valor_total_item, nfcom_id=db_nfcom.id)
        db.add(db_item)

    # Faturas (se fornecidas)
    if getattr(nfcom_in, 'faturas', None):
        for f in nfcom_in.faturas:
            f_data = f.model_dump()
            # data_vencimento é date -> armazenar como datetime sem hora
            from datetime import datetime
            venc = f_data.get('data_vencimento')
            if isinstance(venc, date):
                # converte para datetime no timezone do DB (sem hora)
                f_data['data_vencimento'] = datetime.combine(venc, datetime.min.time())
            db_fat = models.NFComFatura(**f_data, nfcom_id=db_nfcom.id)
            db.add(db_fat)

    # Commit preliminar para persistir itens e recalcular totais
    db.commit()
    # Commit e retorno: não geramos/chave nem XML aqui — será feito na transmissão
    db.commit()
    db.refresh(db_nfcom)
    return db_nfcom

def update_nfcom(db: Session, nfcom_id: int, nfcom_in: nfcom_schema.NFComUpdate) -> models.NFCom:
    """Atualiza uma NFCom existente e seus itens."""
    
    # 1. Busca a NFCom existente
    db_nfcom = db.query(models.NFCom).filter(models.NFCom.id == nfcom_id).first()
    if not db_nfcom:
        raise HTTPException(status_code=404, detail="NFCom não encontrada")
    
    # 2. Atualiza os dados da NFCom (exceto itens)
    # Excluir collections (itens, faturas) para evitar atribuir listas/dicts diretamente às relações ORM
    update_data = nfcom_in.model_dump(exclude={"itens", "faturas"}, exclude_unset=True)
    for field, value in update_data.items():
        # Não sobrescrever com None (atualização parcial preserva valores existentes)
        if value is None:
            continue
        setattr(db_nfcom, field, value)

    # 3. Remove os itens antigos apenas se o payload incluiu 'itens' (substituição)
    if getattr(nfcom_in, 'itens', None) is not None:
        db.query(models.NFComItem).filter(models.NFComItem.nfcom_id == nfcom_id).delete()

    # 4. Adiciona os novos itens (somente se foram enviados)
    if getattr(nfcom_in, 'itens', None):
        for item_in in nfcom_in.itens:
            item_data = item_in.model_dump()
            # safe parse numbers that might be strings
            def _to_float_local2(v):
                try:
                    from decimal import Decimal
                    if v is None:
                        return 0.0
                    if isinstance(v, (int, float)):
                        return float(v)
                    if isinstance(v, Decimal):
                        return float(v)
                    if isinstance(v, str):
                        s = v.strip()
                        if s.count(',') == 1 and s.count('.') >= 1:
                            s = s.replace('.', '').replace(',', '.')
                        else:
                            s = s.replace(',', '.')
                        s = s.replace(' ', '')
                        return float(s)
                except Exception:
                    return 0.0
            valor_total_item = (_to_float_local2(item_data.get('quantidade', 0)) * _to_float_local2(item_data.get('valor_unitario', 0))) - _to_float_local2(item_data.get('valor_desconto', 0)) + _to_float_local2(item_data.get('valor_outros', 0))
            db_item = models.NFComItem(**item_data, valor_total=valor_total_item, nfcom_id=nfcom_id)
            db.add(db_item)
    # Faturas: substituir as antigas apenas se o payload incluiu 'faturas'
    if getattr(nfcom_in, 'faturas', None) is not None:
        db.query(models.NFComFatura).filter(models.NFComFatura.nfcom_id == nfcom_id).delete()
        if getattr(nfcom_in, 'faturas', None):
            for f in nfcom_in.faturas:
                f_data = f.model_dump()
                from datetime import datetime
                venc = f_data.get('data_vencimento')
                if isinstance(venc, date):
                    f_data['data_vencimento'] = datetime.combine(venc, datetime.min.time())
                db_fat = models.NFComFatura(**f_data, nfcom_id=nfcom_id)
                db.add(db_fat)
    
    # 5. Commit e refresh
    db.commit()
    db.refresh(db_nfcom)
    return db_nfcom

def delete_nfcom(db: Session, nfcom_id: int, empresa_id: int) -> bool:
    """Exclui uma NFCom se ela não estiver autorizada."""
    
    # 1. Busca a NFCom e verifica se pertence à empresa
    db_nfcom = db.query(models.NFCom).filter(
        models.NFCom.id == nfcom_id,
        models.NFCom.empresa_id == empresa_id
    ).first()
    
    if not db_nfcom:
        raise HTTPException(status_code=404, detail="NFCom não encontrada nesta empresa")
    
    # 2. Verifica se a NFCom está autorizada
    # Também bloquear exclusão se a nota foi cancelada (informacoes_adicionais com cStat de evento)
    info = (db_nfcom.informacoes_adicionais or '')
    if any(code in info for code in ['cStat=135', 'cStat=136', 'cStat=134']):
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível excluir NFCom #{db_nfcom.numero_nf} - nota cancelada"
        )

    if db_nfcom.protocolo_autorizacao:
        raise HTTPException(
            status_code=400, 
            detail=f"Não é possível excluir NFCom #{db_nfcom.numero_nf} - nota já autorizada"
        )
    
    # 3. Exclui os itens relacionados primeiro (cascade delete)
    db.query(models.NFComItem).filter(models.NFComItem.nfcom_id == nfcom_id).delete()
    db.query(models.NFComFatura).filter(models.NFComFatura.nfcom_id == nfcom_id).delete()
    
    # 4. Exclui a NFCom
    db.delete(db_nfcom)
    db.commit()
    
    return True

def bulk_emit_nfcom_from_contracts(db: Session, contract_ids: list, empresa_id: int, execute: bool = False, transmit: bool = False) -> dict:
    """
    Emissão em massa (modo dry-run).

    Esta função valida cada contrato informado e retorna um relatório com os
    contratos que passaram nas validações (lista `successes`) e os que falharam
    (lista `failures` com mensagem). NÃO cria nem transmite NFComs — é um modo
    seguro para o frontend validar antes de executar a operação real.
    """
    from app.crud import crud_servico_contratado

    successes = []
    failures = []
    skipped = []

    if not contract_ids:
        return {"successes": successes, "failures": failures, "skipped": skipped}

    for cid in contract_ids:
        try:
            contrato = crud_servico_contratado.get_servico_contratado(db, contrato_id=cid, empresa_id=empresa_id)
            if not contrato:
                failures.append({"contract_id": cid, "error": "Contrato não encontrado ou não pertence à empresa"})
                continue

            # Valida itens mínimos necessários para emitir NFCom a partir de um contrato
            # - cliente_id
            # - servico_id
            # - valor_unitario > 0
            if not getattr(contrato, 'cliente_id', None):
                failures.append({"contract_id": cid, "error": "Contrato sem cliente associado"})
                continue
            if not getattr(contrato, 'servico_id', None):
                failures.append({"contract_id": cid, "error": "Contrato sem serviço associado"})
                continue
            # Normaliza/valida valor_unitario do contrato (aceita strings como '1.800,00')
            def _to_float_safe(v):
                try:
                    from decimal import Decimal
                    if v is None:
                        return 0.0
                    if isinstance(v, (int, float)):
                        return float(v)
                    if isinstance(v, Decimal):
                        return float(v)
                    if isinstance(v, str):
                        s = v.strip()
                        # Caso comuns PT-BR: '1.800,00' -> '1800.00'
                        if s.count(',') == 1 and s.count('.') >= 1:
                            s = s.replace('.', '').replace(',', '.')
                        else:
                            s = s.replace(',', '.')
                        s = s.replace(' ', '')
                        return float(s)
                    return 0.0
                except Exception:
                    return 0.0

            contrato_vu = _to_float_safe(getattr(contrato, 'valor_unitario', None))
            if contrato_vu in (None, 0, 0.0):
                failures.append({"contract_id": cid, "error": "Contrato com valor_unitario inválido"})
                continue

            # Se o tipo de faturamento exigir contrato (NORMAL/CENTRALIZADO), verificar datas
            tp_fat = getattr(contrato, 'tp_fat', None) or getattr(contrato, 'tipo_faturamento', None) or None
            # Normalizamos para string se for Enum-like
            try:
                tp_fat_val = str(tp_fat.value) if hasattr(tp_fat, 'value') else str(tp_fat)
            except Exception:
                tp_fat_val = str(tp_fat)

            if tp_fat_val and tp_fat_val.upper() in ('0', 'NORMAL', '1', 'CENTRALIZADO'):
                if not getattr(contrato, 'numero_contrato', None) or not getattr(contrato, 'd_contrato_ini', None):
                    failures.append({"contract_id": cid, "error": "Contrato sem número ou data inicial (obrigatório para tipo de faturamento)"})
                    continue

            # Caso passe em todas as validações, se execute==True cria a NFCom no banco
            if execute:
                try:
                    # Carrega dados da empresa para preencher cMunFG
                    empresa_row = crud_empresa.get_empresa_raw(db, empresa_id=empresa_id)
                    if not empresa_row:
                        raise Exception("Empresa não encontrada")

                    # Determina próximo número e série
                    serie = 1
                    numero_nf = get_next_numero_nf(db, empresa_id=empresa_id, serie=serie)

                    # Calcula valor total do contrato (normalizando possíveis strings formadas em PT-BR).
                    # Preferimos sempre o total derivado de quantidade * valor_unitario quando houver discrepância
                    raw_valor_total = getattr(contrato, 'valor_total', None)
                    parsed_raw_total = None
                    if raw_valor_total not in (None, ''):
                        parsed_raw_total = _to_float_safe(raw_valor_total)

                    qty = (getattr(contrato, 'quantidade', 1) or 1)
                    computed_total = qty * contrato_vu

                    # Se raw_total ausente ou diferente do computado (diferença > 1 centavo), usar o computado
                    if parsed_raw_total is None or abs(parsed_raw_total - computed_total) > 0.01:
                        valor_total = round(computed_total, 2)
                    else:
                        valor_total = round(parsed_raw_total, 2)

                    # Busca endereço do cliente associado à empresa (se existir)
                    cliente = None
                    try:
                        cliente = db.query(models.Cliente).options(
                            joinedload(models.Cliente.empresa_associations).joinedload(models.EmpresaCliente.enderecos)
                        ).filter(models.Cliente.id == contrato.cliente_id).first()
                    except Exception:
                        cliente = None

                    dest_kwargs = {}
                    try:
                        if cliente:
                            # procura associação específica para a empresa
                            assoc = None
                            for ea in getattr(cliente, 'empresa_associations', []) or []:
                                try:
                                    if getattr(ea, 'empresa_id', None) == empresa_id:
                                        assoc = ea
                                        break
                                except Exception:
                                    continue

                            if assoc and getattr(assoc, 'enderecos', None):
                                # prefere endereço principal
                                end = None
                                for e in assoc.enderecos:
                                    if getattr(e, 'is_principal', False):
                                        end = e
                                        break
                                if end is None:
                                    end = assoc.enderecos[0]

                                dest_kwargs.update({
                                    'dest_endereco': getattr(end, 'endereco', '') or '',
                                    'dest_numero': getattr(end, 'numero', '') or '',
                                    'dest_bairro': getattr(end, 'bairro', '') or '',
                                    'dest_municipio': getattr(end, 'municipio', '') or '',
                                    'dest_uf': getattr(end, 'uf', '') or '',
                                    'dest_cep': getattr(end, 'cep', '') or '',
                                    'dest_codigo_ibge': getattr(end, 'codigo_ibge', '') or ''
                                })
                    except Exception:
                        dest_kwargs = {}

                    # Evita emissão duplicada: priorizamos verificação pelo número do contrato
                    # quando disponível; caso contrário, caímos para verificação por
                    # cliente+serviço+dia. Isso evita gerar múltiplas NFComs quando o
                    # mesmo cliente tiver vários contratos distintos.
                    try:
                        import datetime as _dt
                        # Consideramos o dia da emissão como hoje (data sem hora)
                        today = _dt.date.today()
                        start_dt = _dt.datetime.combine(today, _dt.time.min)
                        end_dt = _dt.datetime.combine(today + _dt.timedelta(days=1), _dt.time.min)

                        numero_contrato = getattr(contrato, 'numero_contrato', None)
                        if numero_contrato:
                            # Primeiro, tentar encontrar por número do contrato (mais específico)
                            existing_nf = db.query(models.NFCom).filter(
                                models.NFCom.empresa_id == empresa_id,
                                models.NFCom.numero_contrato == numero_contrato,
                                models.NFCom.data_emissao >= start_dt,
                                models.NFCom.data_emissao < end_dt
                            ).order_by(models.NFCom.id.desc()).first()
                        else:
                            # Fallback: procurar NFCom existente juntando com NFComItem para comparar servico_id
                            existing_nf = db.query(models.NFCom).join(models.NFComItem).filter(
                                models.NFCom.empresa_id == empresa_id,
                                models.NFCom.cliente_id == getattr(contrato, 'cliente_id', None),
                                models.NFComItem.servico_id == getattr(contrato, 'servico_id', None),
                                models.NFCom.data_emissao >= start_dt,
                                models.NFCom.data_emissao < end_dt
                            ).order_by(models.NFCom.id.desc()).first()
                    except Exception:
                        existing_nf = None

                    if existing_nf:
                        # Não emitir novamente automaticamente; registrar como pulado
                        skipped.append({
                            "contract_id": cid,
                            "cliente_id": getattr(contrato, 'cliente_id', None),
                            "servico_id": getattr(contrato, 'servico_id', None),
                            "nfcom_id": getattr(existing_nf, 'id', None),
                            "numero_nf": getattr(existing_nf, 'numero_nf', None),
                            "serie": getattr(existing_nf, 'serie', None),
                            "valor_total": getattr(existing_nf, 'valor_total', None),
                            "reason": "already_emitted_same_client_service_day"
                        })
                        # pula para o próximo contrato
                        continue

                    # Cria o objeto NFCom mínimo
                    db_nf = models.NFCom(
                        empresa_id=empresa_id,
                        cliente_id=contrato.cliente_id,
                        numero_nf=numero_nf,
                        serie=serie,
                        cMunFG=str(empresa_row.codigo_ibge)[:7] if getattr(empresa_row, 'codigo_ibge', None) else '',
                        data_emissao=date.today(),
                        valor_total=valor_total,
                        numero_contrato=getattr(contrato, 'numero_contrato', None),
                        d_contrato_ini=getattr(contrato, 'd_contrato_ini', None),
                        d_contrato_fim=getattr(contrato, 'd_contrato_fim', None),
                        **dest_kwargs
                    )
                    db.add(db_nf)
                    db.flush()

                    # Verifica se há taxa de instalação pendente para incluir na NFCom
                    taxa_instalacao = getattr(contrato, 'taxa_instalacao', 0) or 0
                    taxa_paga = getattr(contrato, 'taxa_instalacao_paga', False) or False

                    # Calcula valor total incluindo taxa de instalação se aplicável
                    valor_total_plano = valor_total
                    valor_total_com_taxa = valor_total

                    if taxa_instalacao > 0 and not taxa_paga:
                        valor_total_com_taxa = valor_total + taxa_instalacao
                        # Atualiza o valor total da NFCom para incluir a taxa
                        valor_total = valor_total_com_taxa
                        db_nf.valor_total = valor_total

                    # Cria itens da NFCom (plano + taxa de instalação se aplicável)
                    itens_criados = []

                    # Item 1: Plano de assinatura (sempre presente)
                    serv = None
                    try:
                        serv = db.query(models.Servico).filter(models.Servico.id == contrato.servico_id).first()
                    except Exception:
                        serv = None

                    # Determina valor unitário final (prioriza valor do contrato, senão valor do serviço)
                    serv_vu = None
                    try:
                        serv_vu = float(getattr(serv, 'valor_unitario', 0) or 0)
                    except Exception:
                        serv_vu = 0.0

                    final_vu = contrato_vu if contrato_vu and contrato_vu > 0 else serv_vu

                    item_plano = models.NFComItem(
                        nfcom_id=db_nf.id,
                        servico_id=getattr(contrato, 'servico_id', None),
                        cClass=getattr(serv, 'cClass', '') if serv is not None else '',
                        codigo_servico=getattr(serv, 'codigo', '') if serv is not None else '',
                        descricao_servico=getattr(serv, 'descricao', '') if serv is not None else '',
                        quantidade=getattr(contrato, 'quantidade', 1) or 1,
                        unidade_medida=getattr(serv, 'unidade_medida', '4') if serv is not None else '4',
                        valor_unitario=final_vu,
                        # Preencher campos fiscais padrão do serviço/contrato
                        valor_desconto=(getattr(contrato, 'valor_desconto', None) if getattr(contrato, 'valor_desconto', None) is not None else getattr(serv, 'valor_desconto_default', 0)) or 0,
                        valor_outros=(getattr(contrato, 'valor_outros', None) if getattr(contrato, 'valor_outros', None) is not None else getattr(serv, 'valor_outros_default', 0)) or 0,
                        cfop=(getattr(contrato, 'servico_cfop', None) or (getattr(serv, 'cfop', None) if serv is not None else '') ) or '',
                        ncm=(getattr(contrato, 'servico_ncm', None) or (getattr(serv, 'ncm', None) if serv is not None else '')) or '',
                        base_calculo_icms=(getattr(contrato, 'servico_base_calculo_icms_default', None) if getattr(contrato, 'servico_base_calculo_icms_default', None) is not None else getattr(serv, 'base_calculo_icms_default', None)) or 0,
                        aliquota_icms=(getattr(contrato, 'servico_aliquota_icms_default', None) if getattr(contrato, 'servico_aliquota_icms_default', None) is not None else getattr(serv, 'aliquota_icms_default', None)) or 0,
                        base_calculo_pis=(getattr(contrato, 'servico_base_calculo_pis_default', None) if getattr(contrato, 'servico_base_calculo_pis_default', None) is not None else getattr(serv, 'base_calculo_pis_default', None)) or 0,
                        aliquota_pis=(getattr(contrato, 'servico_aliquota_pis_default', None) if getattr(contrato, 'servico_aliquota_pis_default', None) is not None else getattr(serv, 'aliquota_pis_default', None)) or 0,
                        base_calculo_cofins=(getattr(contrato, 'servico_base_calculo_cofins_default', None) if getattr(contrato, 'servico_base_calculo_cofins_default', None) is not None else getattr(serv, 'base_calculo_cofins_default', None)) or 0,
                        aliquota_cofins=(getattr(contrato, 'servico_aliquota_cofins_default', None) if getattr(contrato, 'servico_aliquota_cofins_default', None) is not None else getattr(serv, 'aliquota_cofins_default', None)) or 0,
                        valor_total=valor_total_plano
                    )
                    db.add(item_plano)
                    itens_criados.append(item_plano)

                    # Item 2: Taxa de instalação (se aplicável)
                    if taxa_instalacao > 0 and not taxa_paga:
                        # Cria um serviço específico para taxa de instalação ou usa um genérico
                        # Aqui assumimos que existe um serviço padrão para "Taxa de Instalação"
                        # ou podemos criar um item genérico
                        item_taxa = models.NFComItem(
                            nfcom_id=db_nf.id,
                            servico_id=None,  # Taxa não está ligada a um serviço específico
                            cClass='010101',  # Código genérico para serviços - pode ser configurado
                            codigo_servico='TAXA_INSTALACAO',
                            descricao_servico='Taxa de Instalação de Serviço de Telecomunicações',
                            quantidade=1,
                            unidade_medida='UN',
                            valor_unitario=taxa_instalacao,
                            valor_desconto=0,
                            valor_outros=0,
                            # Campos fiscais específicos para taxa de instalação
                            # Estes podem ser diferentes do plano de assinatura
                            cfop='5307',  # CFOP específico para serviços de instalação
                            ncm='',  # Taxa de instalação geralmente não tem NCM
                            base_calculo_icms=taxa_instalacao,  # Base de cálculo = valor da taxa
                            aliquota_icms=18.0,  # Alíquota padrão - pode ser configurada
                            base_calculo_pis=taxa_instalacao,
                            aliquota_pis=0.65,  # PIS para serviços
                            base_calculo_cofins=taxa_instalacao,
                            aliquota_cofins=3.0,  # COFINS para serviços
                            valor_total=taxa_instalacao
                        )
                        db.add(item_taxa)
                        itens_criados.append(item_taxa)

                        # Marca a taxa como paga no contrato
                        contrato.taxa_instalacao_paga = True
                        db.add(contrato)


                    # Cria fatura se houver vencimento/valor
                    try:
                        # Primeiro, preferir novo campo `dia_vencimento` (inteiro 1-31) se presente
                        import datetime as _dt
                        import calendar as _cal

                        def _build_by_day(day_num: int, base_date: _dt.date) -> _dt.date:
                            year = base_date.year
                            month = base_date.month
                            last_day = _cal.monthrange(year, month)[1]
                            use_day = min(int(day_num), last_day)
                            candidate = _dt.date(year, month, use_day)
                            if candidate <= base_date:
                                # avançar para próximo mês
                                if month == 12:
                                    year += 1
                                    month = 1
                                else:
                                    month += 1
                                last_day = _cal.monthrange(year, month)[1]
                                use_day = min(int(day_num), last_day)
                                candidate = _dt.date(year, month, use_day)
                            return candidate

                        today = _dt.date.today()

                        day_from_venc = None
                        # Prioriza dia_vencimento (novo campo)
                        if getattr(contrato, 'dia_vencimento', None) is not None:
                            try:
                                day_from_venc = int(getattr(contrato, 'dia_vencimento'))
                            except Exception:
                                day_from_venc = None
                        else:
                            # Fallback para legacy `vencimento` date (extrai dia se possível)
                            venc = getattr(contrato, 'vencimento', None)
                            if venc is not None:
                                try:
                                    # Se for string ISO, extrai dia
                                    if isinstance(venc, str):
                                        # aceita 'YYYY-MM-DD' ou 'YYYY-MM-DDTHH:MM:SS...'
                                        import re as _re
                                        m = _re.match(r"^(\d{4})-(\d{2})-(\d{2})", venc)
                                        if m:
                                            day_from_venc = int(m.group(3))
                                    elif isinstance(venc, (_dt.datetime, _dt.date)):
                                        day_from_venc = int(venc.day)
                                    elif isinstance(venc, (int, float)):
                                        # epoch millis/seconds? tentar converter
                                        try:
                                            candidate_dt = _dt.datetime.fromtimestamp(float(venc))
                                            day_from_venc = int(candidate_dt.day)
                                        except Exception:
                                            day_from_venc = None
                                except Exception:
                                    day_from_venc = None

                        if day_from_venc:
                            # Construir vencimento usando apenas o dia informado
                            venc = _build_by_day(day_from_venc, today)
                        else:
                            # Se não houver `vencimento` explícito utilizável, derivamos a partir do `dia_emissao`
                            dia = getattr(contrato, 'dia_emissao', None)
                            if dia:
                                venc = _build_by_day(int(dia), today)

                        # Como fallback, usa datas de contrato (fim/ini) se ainda sem vencimento
                        if venc is None:
                            venc = getattr(contrato, 'd_contrato_fim', None) or getattr(contrato, 'd_contrato_ini', None)

                        dv = None
                        if venc:
                            # Normaliza para datetime quando possível (suporta date, datetime e strings ISO)
                            import datetime as _dt
                            try:
                                if isinstance(venc, _dt.datetime):
                                    dv = venc
                                elif isinstance(venc, _dt.date):
                                    dv = _dt.datetime.combine(venc, _dt.datetime.min.time())
                                elif isinstance(venc, str):
                                    # tenta parse ISO primeiro, depois dateutil como fallback
                                    try:
                                        dv = _dt.datetime.fromisoformat(venc)
                                    except Exception:
                                        try:
                                            from dateutil import parser as _p
                                            dv = _p.parse(venc)
                                        except Exception:
                                            dv = None
                                else:
                                    dv = None
                            except Exception:
                                dv = None

                        if dv is not None:
                            nf_fat = models.NFComFatura(
                                nfcom_id=db_nf.id,
                                numero_fatura=str(getattr(contrato, 'numero_contrato', f'CT{cid}')),
                                data_vencimento=dv,
                                valor_fatura=valor_total or 0
                            )
                            db.add(nf_fat)
                            # Debug opcional para rastrear criação automática de faturas
                            try:
                                print(f"DEBUG: Fatura criada automaticamente para contrato {cid} com vencimento {dv}")
                            except Exception:
                                pass
                    except Exception:
                        # não bloquear criação por falha na fatura
                        pass

                    # Commit por contrato para persistir e evitar bloqueios
                    db.commit()
                    db.refresh(db_nf)

                    # Se solicitado, transmite a NFCom imediatamente
                    transmit_result = None
                    transmitted = False
                    if transmit:
                        try:
                            transmit_result = transmit_nfcom(db, nfcom_id=db_nf.id, empresa_id=empresa_id)
                            # Considera transmitida se cStat == '100'
                            if isinstance(transmit_result, dict) and str(transmit_result.get('cStat', '')).strip() == '100':
                                transmitted = True
                        except HTTPException as he:
                            # Transmissão falhou — registrar como falha
                            try:
                                db.rollback()
                            except Exception:
                                pass
                            failures.append({
                                "contract_id": cid,
                                "nfcom_id": getattr(db_nf, 'id', None),
                                "error": f"Transmissão falhou: {he.detail}"
                            })
                            # continuar para o próximo contrato
                            continue
                        except Exception as te:
                            try:
                                db.rollback()
                            except Exception:
                                pass
                            failures.append({"contract_id": cid, "nfcom_id": getattr(db_nf, 'id', None), "error": f"Erro na transmissão: {te}"})
                            continue

                    successes.append({
                        "contract_id": cid,
                        "nfcom_id": db_nf.id,
                        "numero_nf": db_nf.numero_nf,
                        "serie": db_nf.serie,
                        "valor_total": db_nf.valor_total,
                        "transmitted": transmitted,
                        "transmit_result": transmit_result
                    })
                except Exception as e:
                    try:
                        db.rollback()
                    except Exception:
                        pass
                    failures.append({"contract_id": cid, "error": f"Erro ao criar NFCom: {e}"})
            else:
                successes.append({
                    "contract_id": cid,
                    "cliente_id": contrato.cliente_id,
                    "servico_id": contrato.servico_id,
                    "numero_contrato": getattr(contrato, 'numero_contrato', None),
                    "d_contrato_ini": getattr(contrato, 'd_contrato_ini', None),
                    "d_contrato_fim": getattr(contrato, 'd_contrato_fim', None),
                    "valor_unitario": getattr(contrato, 'valor_unitario', None),
                    "valor_total": getattr(contrato, 'valor_total', None)
                })

        except HTTPException:
            # Repropaga erros HTTP já formatados
            raise
        except Exception as e:
            failures.append({"contract_id": cid, "error": f"Erro ao processar contrato: {e}"})

    return {"successes": successes, "failures": failures, "skipped": skipped}

def get_sefaz_url_by_uf(uf: str, ambiente: str, service: str = "recepcao") -> str:
    """Retorna a URL do webservice da SEFAZ com base na UF, ambiente e serviço solicitado.

    service: 'recepcao' | 'status' | 'consulta' | 'evento'
    """
    # Mapeamento de UFs para seus respectivos autorizadores
    uf_map = {
        "AC": "svrs", "AL": "svrs", "AM": "svrs", "AP": "svrs", "BA": "svrs",
        "CE": "svrs", "DF": "svrs", "ES": "svrs", "GO": "svrs", "MA": "svrs",
        # MG (Minas Gerais) possui webservice próprio — mapear para 'mg'
        "MG": "mg", "MS": "svrs", "MT": "svrs", "PA": "svrs", "PB": "svrs",
        "PE": "svrs", "PI": "svrs", "PR": "svrs", "RJ": "svrs", "RN": "svrs",
        "RO": "svrs", "RR": "svrs", "RS": "svrs", "SC": "svrs", "SE": "svrs",
        "SP": "svrs", "TO": "svrs"
    }

    autorizador = uf_map.get(uf.upper(), "svrs")

    # Mapas de URLs por autorizador e por serviço
    urls = {
        "svrs": {
            "recepcao": {
                "homologacao": "https://nfcom-homologacao.svrs.rs.gov.br/ws/NFComRecepcao/NFComRecepcao.asmx",
                "producao": "https://nfcom.svrs.rs.gov.br/ws/NFComRecepcao/NFComRecepcao.asmx"
            },
            "status": {
                "homologacao": "https://nfcom-homologacao.svrs.rs.gov.br/ws/NFComStatusServico/NFComStatusServico.asmx",
                "producao": "https://nfcom.svrs.rs.gov.br/ws/NFComStatusServico/NFComStatusServico.asmx"
            },
            "consulta": {
                "homologacao": "https://nfcom-homologacao.svrs.rs.gov.br/ws/NFComConsulta/NFComConsulta.asmx",
                "producao": "https://nfcom.svrs.rs.gov.br/ws/NFComConsulta/NFComConsulta.asmx"
            },
            "evento": {
                "homologacao": "https://nfcom-homologacao.svrs.rs.gov.br/ws/NFComRecepcaoEvento/NFComRecepcaoEvento.asmx",
                "producao": "https://nfcom.svrs.rs.gov.br/ws/NFComRecepcaoEvento/NFComRecepcaoEvento.asmx"
            }
        },
        "mg": {
            "recepcao": {
                "homologacao": "https://hnfcom.fazenda.mg.gov.br/nfcom/services/NFComRecepcao",
                "producao": "https://nfcom.fazenda.mg.gov.br/nfcom/services/NFComRecepcao"
            },
            "status": {
                "homologacao": "https://hnfcom.fazenda.mg.gov.br/nfcom/services/NFComStatusServico",
                "producao": "https://nfcom.fazenda.mg.gov.br/nfcom/services/NFComStatusServico"
            },
            "consulta": {
                "homologacao": "https://hnfcom.fazenda.mg.gov.br/nfcom/services/NFComConsulta",
                "producao": "https://nfcom.fazenda.mg.gov.br/nfcom/services/NFComConsulta"
            },
            "evento": {
                "homologacao": "https://hnfcom.fazenda.mg.gov.br/nfcom/services/NFComRecepcaoEvento",
                "producao": "https://nfcom.fazenda.mg.gov.br/nfcom/services/NFComRecepcaoEvento"
            }
        }
    }

    # Segurança: validar service
    svc = (service or "recepcao").strip().lower()
    if autorizador not in urls:
        autorizador = "svrs"
    if svc not in urls[autorizador]:
        svc = "recepcao"

    return urls[autorizador][svc][ambiente]


def sign_evento_nfcom_xml(inf_evento_xml: str, empresa) -> str:
    """
    Assina um XML de evento (infEvento) e retorna o XML completo do
    elemento <eventoNFCom> assinado pronto para envio.
    Esta função adapta a lógica de assinatura usada para NFComs para eventos.
    """
    try:
        import xmlsec
        from cryptography.hazmat.primitives.serialization import pkcs12
        from cryptography.hazmat.primitives import serialization
        import base64

        cert_path_raw = empresa.certificado_path or ""
        cert_path_norm = cert_path_raw.replace("/secure/", "").replace("\\secure\\", "")
        cert_path_norm = cert_path_norm.lstrip('/\\')
        if Path(cert_path_raw).is_absolute():
            absolute_cert_path = Path(cert_path_raw)
        else:
            absolute_cert_path = Path(settings.CERTIFICATES_DIR) / cert_path_norm

        if not absolute_cert_path.exists():
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Arquivo de certificado não encontrado: {absolute_cert_path}")

        with open(absolute_cert_path, "rb") as f:
            pfx_data = f.read()

        certificado_senha = ""
        if hasattr(empresa, 'certificado_senha') and empresa.certificado_senha:
            try:
                certificado_senha = decrypt_sensitive_data(empresa.certificado_senha)
            except Exception:
                certificado_senha = empresa.certificado_senha

        senha_bytes = certificado_senha.encode('utf-8') if certificado_senha else None
        try:
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(pfx_data, senha_bytes)
        except Exception:
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(pfx_data, None)

        ns = "http://www.portalfiscal.inf.br/nfcom"

        # Parse infEvento (espera-se uma string contendo <infEvento ...>...</infEvento>)
        inf_root = etree.fromstring(inf_evento_xml.encode('utf-8'))
        # Minify infEvento (remove formatação incidental) para evitar caracteres de edição
        try:
            minified_inf = etree.tostring(inf_root, encoding='utf-8', method='xml', pretty_print=False)
            inf_root = etree.fromstring(minified_inf)
        except Exception:
            # fallback: keep original
            pass

        # Monta <eventoNFCom> raiz com atributo versao obrigatório e anexa infEvento
        evento_root = etree.Element(f"{{{ns}}}eventoNFCom", nsmap={None: ns})
        evento_root.set('versao', '1.00')  # Atributo obrigatório conforme schema
        evento_root.append(inf_root)

        # Cria template de assinatura e referencia o Id do infEvento
        ds_ns = 'http://www.w3.org/2000/09/xmldsig#'
        isolated_root = etree.Element('temp')
        sign_node = etree.SubElement(isolated_root, '{%s}Signature' % ds_ns, nsmap={None: ds_ns})
        signed_info = etree.SubElement(sign_node, '{%s}SignedInfo' % ds_ns)
        c14n_method = etree.SubElement(signed_info, '{%s}CanonicalizationMethod' % ds_ns)
        c14n_method.set('Algorithm', 'http://www.w3.org/TR/2001/REC-xml-c14n-20010315')
        sig_method = etree.SubElement(signed_info, '{%s}SignatureMethod' % ds_ns)
        sig_method.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#rsa-sha1')
        etree.SubElement(sign_node, '{%s}SignatureValue' % ds_ns)
        key_info_elem = etree.SubElement(sign_node, '{%s}KeyInfo' % ds_ns)
        etree.SubElement(key_info_elem, '{%s}X509Data' % ds_ns)

        # Reference to Id of infEvento
        inf_id = inf_root.get('Id')
        if not inf_id:
            raise HTTPException(status_code=500, detail="Elemento <infEvento> sem atributo Id para assinatura")

        ref = etree.SubElement(signed_info, '{%s}Reference' % ds_ns)
        ref.set('URI', "#%s" % inf_id)
        transforms = etree.SubElement(ref, '{%s}Transforms' % ds_ns)
        tr1 = etree.SubElement(transforms, '{%s}Transform' % ds_ns)
        tr1.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#enveloped-signature')
        tr2 = etree.SubElement(transforms, '{%s}Transform' % ds_ns)
        tr2.set('Algorithm', 'http://www.w3.org/TR/2001/REC-xml-c14n-20010315')
        digest_method = etree.SubElement(ref, '{%s}DigestMethod' % ds_ns)
        digest_method.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#sha1')
        etree.SubElement(ref, '{%s}DigestValue' % ds_ns)

        # Remove tails whitespace
        def _remove_tails(elem):
            for child in elem:
                if child.tail is not None and child.tail.strip() == '':
                    child.tail = ''
                _remove_tails(child)
        _remove_tails(evento_root)

        # Registrar o Id para que xmlsec possa referenciar o infEvento
        try:
            xmlsec.tree.add_ids(evento_root, ["Id"])
        except Exception:
            # não fatal, apenas log
            print('DEBUG: falha ao registrar Ids para xmlsec (ignorado)')

            # Preparar PEM temporário e assinar usando o xmlsec contra o sign_node
        pem_path = None
        try:
            pem_path = _convert_pfx_to_pem(pfx_data, certificado_senha)
            # Inserir sign_node (criado manualmente mais acima) no documento logo após <infEvento>
            try:
                inf_supl = evento_root.find('{%s}infEvento' % ns)
                if inf_supl is not None:
                    idx = list(evento_root).index(inf_supl)
                    evento_root.insert(idx + 1, sign_node)
                else:
                    evento_root.append(sign_node)
            except Exception:
                evento_root.append(sign_node)

            ctx = xmlsec.SignatureContext()
            try:
                key = xmlsec.Key.from_file(pem_path, xmlsec.KeyFormat.PEM, None)
                ctx.key = key
                # Carrega certificado na chave para que seja incluído automaticamente
                try:
                    key.load_cert_from_file(pem_path, xmlsec.KeyFormat.CERT_PEM)
                except Exception as e:
                    print('DEBUG: falha ao carregar certificado PEM (continuando):', e)
            except Exception as e:
                print('DEBUG: falha ao carregar chave PEM:', e)
                raise

            try:
                # Limpar whitespace-only tails/texts do sign_node para evitar cStat 599

                # Limpar whitespace-only tails/texts do sign_node para evitar cStat 599
                for elem in sign_node.iter():
                    if elem.text and not elem.text.strip():
                        elem.text = None
                    if elem.tail and not elem.tail.strip():
                        elem.tail = None

                ctx.sign(sign_node)
                
                # IMPORTANTE: Após assinatura, garantir que o X509Certificate esteja em KeyInfo
                ds_ns = 'http://www.w3.org/2000/09/xmldsig#'
                x509_data_elem = sign_node.find('.//{%s}X509Data' % ds_ns)
                if x509_data_elem is not None:
                    # Verificar se já tem X509Certificate
                    x509_cert_elem = x509_data_elem.find('{%s}X509Certificate' % ds_ns)
                    if x509_cert_elem is None:
                        # Adicionar certificado manualmente
                        import base64
                        cert_base64 = base64.b64encode(certificate.public_bytes(serialization.Encoding.DER)).decode('ascii')
                        x509_cert_elem = etree.SubElement(x509_data_elem, '{%s}X509Certificate' % ds_ns)
                        x509_cert_elem.text = cert_base64
            except Exception as e:
                # Captura erro de assinatura com detalhes para debug
                tb = traceback.format_exc()
                print('ERRO xmlsec.sign:', e, tb)
                # salva o XML que tentou assinar para análise externa
                try:
                    tmpf = tempfile.NamedTemporaryFile(delete=False, suffix='.xml', prefix='event_to_sign_', dir=tempfile.gettempdir())
                    tmpf.write(etree.tostring(evento_root, encoding='utf-8'))
                    tmpf.flush()
                    tmpf.close()
                    print('DEBUG: evento a assinar salvo em:', tmpf.name)
                except Exception:
                    pass
                raise

            # Serializa em C14N sem caracteres de edição
            signed_xml_bytes = etree.tostring(evento_root, method='c14n')
            signed_xml = signed_xml_bytes.decode('utf-8')
            
            # Remove TODOS os caracteres de edição (line-feed, carriage return, tabs) conforme MOC
            # SEFAZ rejeita com cStat 599 se houver qualquer formatação/quebra de linha
            signed_xml = signed_xml.replace('\n', '').replace('\r', '').replace('\t', '')
            
            signed_xml = '<?xml version="1.0" encoding="UTF-8"?>' + signed_xml

            # Nota: Não modificamos a URI de CanonicalizationMethod depois da assinatura,
            # pois isso altera o SignedInfo e torna a assinatura inválida. A canonicalização
            # correta é garantida pela criação do template usando xmlsec.Transform.C14N.

            return signed_xml
        finally:
            if pem_path and os.path.exists(pem_path):
                try:
                    os.remove(pem_path)
                except Exception:
                    pass

    except ImportError as ie:
        tb = traceback.format_exc()
        print("ERRO na assinatura do evento (xmlsec não disponível):\n", tb)
        raise HTTPException(status_code=500, detail=f"xmlsec não disponível: {ie}")
    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        print("ERRO ao assinar evento:", tb)
        raise HTTPException(status_code=500, detail=f"Erro ao assinar evento: {str(e)}")


def transmit_evento_cancelamento(db: Session, nfcom_id: int, empresa_id: int, nProt: str, justificativa: str) -> dict:
    """
    Constrói, assina e transmite o evento de cancelamento (110111) para a SEFAZ.
    Retorna o dicionário com a resposta da SEFAZ (cStat, xMotivo, nProt, content...)
    """
    # Valida nota e empresa
    db_nfcom = get_nfcom(db, nfcom_id=nfcom_id, empresa_id=empresa_id)
    if not db_nfcom:
        raise HTTPException(status_code=404, detail="NFCom não encontrada")

    # Nota deve estar autorizada para ser cancelada
    if not db_nfcom.protocolo_autorizacao:
        raise HTTPException(status_code=400, detail="NFCom não está autorizada; não é possível cancelar")

    # Carrega dados da empresa para assinatura e cOrgao
    empresa_row = crud_empresa.get_empresa_raw(db, empresa_id=empresa_id)
    if not empresa_row:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    empresa_para_assinatura = SimpleNamespace(
        certificado_path=empresa_row.certificado_path,
        certificado_senha=empresa_row.certificado_senha,
        id=empresa_id,
        ambiente_nfcom=getattr(empresa_row, 'ambiente_nfcom', None)
    )

    # Monta infEvento
    from datetime import datetime, timezone
    tpEvento = '110111'
    nSeq = 1
    id_ref = f"ID{tpEvento}{db_nfcom.chave_acesso}{str(nSeq).zfill(3)}"

    # cOrgao: usa os dois primeiros dígitos do código IBGE da empresa
    cOrgao = str(getattr(empresa_row, 'codigo_ibge', '') or '')[:2] or '00'
    tpAmb = '1' if getattr(empresa_row, 'ambiente_nfcom', None) == 'producao' else ('2' if getattr(empresa_row, 'ambiente_nfcom', None) == 'homologacao' else ('1' if settings.NFCOM_AMBIENTE == 'producao' else '2'))
    cnpj = (getattr(empresa_row, 'cnpj', '') or '').replace('.', '').replace('/', '').replace('-', '')
    
    # Formata dhEvento conforme padrão TDateTimeUTC (AAAA-MM-DDTHH:MM:SS+/-HH:MM)
    # Remove microssegundos para evitar rejeição do schema SEFAZ
    dhEvento_dt = datetime.now(timezone.utc).astimezone()
    dhEvento = dhEvento_dt.strftime('%Y-%m-%dT%H:%M:%S') + dhEvento_dt.strftime('%z')
    # Formata timezone corretamente: de '-0300' para '-03:00'
    if len(dhEvento) >= 19 and dhEvento[-5] in ('+', '-'):
        dhEvento = dhEvento[:-2] + ':' + dhEvento[-2:]

    # Monta XML do evCancNFCom
    import html
    # IMPORTANTE: evCancNFCom SEM namespace (será herdado do detEvento/eventoNFCom)
    ev_xml = f"<evCancNFCom>"
    ev_xml += f"<descEvento>Cancelamento</descEvento>"
    ev_xml += f"<nProt>{nProt}</nProt>"
    ev_xml += f"<xJust>{html.escape(justificativa or '')}</xJust>"
    ev_xml += "</evCancNFCom>"

    # Monta infEvento completo com Id
    inf_evento = f"<infEvento Id=\"{id_ref}\">"
    inf_evento += f"<cOrgao>{cOrgao}</cOrgao>"
    inf_evento += f"<tpAmb>{tpAmb}</tpAmb>"
    inf_evento += f"<CNPJ>{cnpj}</CNPJ>"
    inf_evento += f"<chNFCom>{db_nfcom.chave_acesso}</chNFCom>"
    inf_evento += f"<dhEvento>{dhEvento}</dhEvento>"
    inf_evento += f"<tpEvento>{tpEvento}</tpEvento>"
    inf_evento += f"<nSeqEvento>{nSeq}</nSeqEvento>"
    inf_evento += f"<detEvento versaoEvento=\"1.00\">{ev_xml}</detEvento>"
    inf_evento += "</infEvento>"

    # Assina o evento e obtém o XML assinado do <eventoNFCom>
    signed_evento_xml = sign_evento_nfcom_xml(inf_evento, empresa_para_assinatura)
    
    # IMPORTANTE: Remove a declaração XML do evento assinado antes de inserir no SOAP
    # O envelope SOAP já tem sua própria declaração XML
    signed_evento_xml_limpo = signed_evento_xml.replace('<?xml version="1.0" encoding="UTF-8"?>', '').strip()

    # Prepara envio SOAP (sem compactação) para o serviço evento
    empresa_ambiente = getattr(empresa_row, 'ambiente_nfcom', None)
    ambiente = empresa_ambiente if empresa_ambiente in ('producao', 'homologacao') else settings.NFCOM_AMBIENTE
    sefaz_url = get_sefaz_url_by_uf(empresa_row.uf, ambiente, service='evento')

    soap_body = f"""<soap12:Envelope xmlns:soap12=\"http://www.w3.org/2003/05/soap-envelope\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\"><soap12:Body><nfcomDadosMsg xmlns=\"http://www.portalfiscal.inf.br/nfcom/wsdl/NFComRecepcaoEvento\">{signed_evento_xml_limpo}</nfcomDadosMsg></soap12:Body></soap12:Envelope>"""

    # Prepara certificado PEM
    cert_password = decrypt_sensitive_data(empresa_row.certificado_senha) if empresa_row.certificado_senha else None
    relative_cert_path = empresa_row.certificado_path.replace("/secure/", "", 1) if empresa_row.certificado_path else empresa_row.certificado_path
    absolute_cert_path = Path(settings.CERTIFICATES_DIR) / (relative_cert_path or '')
    if not absolute_cert_path.exists():
        raise HTTPException(status_code=500, detail=f"Arquivo de certificado não encontrado: {absolute_cert_path}")

    pem_file_path = None
    try:
        with open(absolute_cert_path, 'rb') as f:
            pfx_data = f.read()
        pem_file_path = _convert_pfx_to_pem(pfx_data, cert_password)

        headers = {'Content-Type': 'application/soap+xml'}
        
        print(f"\n{'='*80}")
        print(f"ENVIANDO EVENTO DE CANCELAMENTO PARA SEFAZ")
        print(f"{'='*80}")
        print(f"URL: {sefaz_url}")
        print(f"Headers: {headers}")
        print(f"Certificado PEM: {pem_file_path}")
        print(f"NFCom ID: {db_nfcom.id} | Número: {db_nfcom.numero_nf}")
        print(f"Chave: {db_nfcom.chave_acesso}")
        print(f"Protocolo NFCom: {db_nfcom.protocolo_autorizacao}")
        print(f"{'='*80}\n")
        
        response = requests.post(url=sefaz_url, data=soap_body.encode('utf-8'), headers=headers, cert=pem_file_path, verify=False, timeout=30)

        print(f"\n{'='*80}")
        print(f"RESPOSTA RECEBIDA DA SEFAZ")
        print(f"{'='*80}")
        print(f"Status Code: {response.status_code if response else 'None'}")
        print(f"Headers: {dict(response.headers) if response else 'None'}")
        print(f"Content Length: {len(response.content) if response and response.content else 0}")
        print(f"Content Type: {response.headers.get('content-type', 'N/A') if response else 'N/A'}")
        if response and response.content:
            print(f"Content Preview (first 500 chars): {response.content[:500]}")
        print(f"{'='*80}\n")

        if not response or not response.content:
            error_detail = {
                "status_code": response.status_code if response else None,
                "error": "Resposta vazia da SEFAZ",
                "headers": dict(response.headers) if response else None,
                "url": sefaz_url,
                "xml_enviado": soap_body
            }
            print(f"ERRO: SEFAZ retornou resposta vazia! Detalhes: {error_detail}")
            return error_detail

        # Salva resposta em arquivo temporário
        resp_file_path = None
        try:
            tmp_resp = tempfile.NamedTemporaryFile(delete=False, suffix='.xml', prefix=f'sefaz_event_resp_{db_nfcom.id}_', dir=tempfile.gettempdir())
            tmp_resp.write(response.content)
            tmp_resp.flush()
            resp_file_path = tmp_resp.name
            tmp_resp.close()
        except Exception:
            resp_file_path = None

        # Parse resposta
        try:
            parse_content = response.content
            root = ET.fromstring(parse_content)
            ns_soap = {'soap': 'http://www.w3.org/2003/05/soap-envelope'}
            ns_nfcom = {'nfcom': 'http://www.portalfiscal.inf.br/nfcom'}
            body = root.find('soap:Body', ns_soap)
            result_node = None
            if body is not None:
                result_node = body.find('.//nfcom:retEventoNFCom', ns_nfcom)

            if result_node is not None:
                cStat_elem = result_node.find('.//nfcom:cStat', ns_nfcom)
                xMotivo_elem = result_node.find('.//nfcom:xMotivo', ns_nfcom)
                nProt_elem = result_node.find('.//nfcom:nProt', ns_nfcom)

                cStat = cStat_elem.text if cStat_elem is not None else None
                xMotivo = xMotivo_elem.text if xMotivo_elem is not None else None
                nProt_event = nProt_elem.text if nProt_elem is not None else None

                # LOG DETALHADO para debug
                print(f"\n{'='*80}")
                print(f"RETORNO SEFAZ - CANCELAMENTO NFCom #{db_nfcom.numero_nf}")
                print(f"{'='*80}")
                print(f"cStat: {cStat}")
                print(f"xMotivo: {xMotivo}")
                print(f"nProt Evento: {nProt_event}")
                print(f"Chave NFCom: {db_nfcom.chave_acesso}")
                print(f"Arquivo resposta: {resp_file_path}")
                print(f"{'='*80}\n")

                # Persistir informação de retorno no campo informacoes_adicionais para auditoria
                note = f"Evento cancelamento enviado em {datetime.now(timezone.utc).isoformat()}: cStat={cStat} xMotivo={xMotivo} nProt={nProt_event}\nRespostaSEFAZ:\n{response.text}"
                try:
                    db_nfcom.informacoes_adicionais = (db_nfcom.informacoes_adicionais or '') + "\n" + note
                    db.commit()
                except Exception:
                    try:
                        db.rollback()
                    except Exception:
                        pass

                # cStat 218 = NFCom já está cancelada no SEFAZ
                if str(cStat).strip() == '218':
                    print(f"INFO: Detectado cStat=218 (NFCom já cancelada) para NFCom {db_nfcom.id}")
                    try:
                        # Extrai informações do cancelamento da mensagem de erro
                        note_218 = f"NFCom já cancelada no SEFAZ: cStat=218 {xMotivo}"
                        if 'cStat=135' not in (db_nfcom.informacoes_adicionais or ''):
                            db_nfcom.informacoes_adicionais = (db_nfcom.informacoes_adicionais or '').rstrip() + f"\n{note_218}\ncStat=135\n"
                            db.commit()
                            print(f"INFO: NFCom {db_nfcom.id} marcada como cancelada via cStat=218")
                    except Exception as e:
                        print(f"ERROR: Falha ao atualizar informacoes_adicionais após cStat=218: {e}")
                        try:
                            db.rollback()
                        except Exception:
                            pass

                # If SEFAZ returned duplication (cStat 631), we should query SEFAZ for the NFCom
                # status/events to determine whether there is a prior cancelamento event already
                # registered. If a prior cancel is found (cStat 135/136/134 inside procEventoNFCom),
                # record it in informacoes_adicionais so that get_nfcom() marks NFCom as 'cancelada'.
                if str(cStat).strip() == '631' and xMotivo and 'Duplicidade de evento' in xMotivo:
                    print(f"INFO: Detectado cStat=631 (duplicidade) para NFCom {db_nfcom.id}. Consultando SEFAZ...")
                    consulta_sucesso = False
                    try:
                        # function will perform consSitNFCom and update DB if found
                        consulta_sucesso = _check_and_mark_cancelado_from_consulta(db, db_nfcom, empresa_row)
                    except Exception as e:
                        # Non-fatal; continue returning the original result; log for debug
                        print(f"WARN: falha ao consultar eventos via NFComConsulta após cStat=631: {e}")
                    
                    # Se a consulta automática não encontrou/atualizou, marque manualmente baseado no cStat 631
                    if not consulta_sucesso:
                        try:
                            # cStat 631 indica que o evento JÁ EXISTE no SEFAZ, então marcamos como cancelada
                            note = f"Evento cancelamento detectado via cStat=631 (duplicidade): xMotivo={xMotivo}"
                            if note not in (db_nfcom.informacoes_adicionais or ''):
                                db_nfcom.informacoes_adicionais = (db_nfcom.informacoes_adicionais or '').rstrip() + f"\n{note}\ncStat=135\n"
                                db.commit()
                                print(f"INFO: NFCom {db_nfcom.id} marcada como cancelada via cStat=631")
                        except Exception as e:
                            print(f"ERROR: Falha ao atualizar informacoes_adicionais após cStat=631: {e}")
                            try:
                                db.rollback()
                            except Exception:
                                pass

                return {"status_code": response.status_code, "cStat": cStat, "xMotivo": xMotivo, "nProt": nProt_event, "content": response.text, "xml_enviado": soap_body, "soap_response_file": resp_file_path}

            # Estrutura inesperada
            return {"status_code": response.status_code, "error": "Resposta inesperada", "content": response.text, "xml_enviado": soap_body, "soap_response_file": resp_file_path}
        except Exception:
            return {"status_code": response.status_code, "content": response.text, "xml_enviado": soap_body, "soap_response_file": resp_file_path}

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Erro de comunicação com a SEFAZ: {e}")
    finally:
        if pem_file_path and os.path.exists(pem_file_path):
            try:
                os.remove(pem_file_path)
            except Exception:
                pass

def consultar_status_servico_sefaz(db: Session, empresa_id: int, ambiente: str):
    """Consulta o status do serviço NFCom na SEFAZ para uma empresa."""
    empresa = crud_empresa.get_empresa_raw(db, empresa_id=empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # Use explicit service 'status' to get the correct URL for status service
    sefaz_url = get_sefaz_url_by_uf(empresa.uf, ambiente, service="status")
    
    soap_body = f"""<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <soap12:Header>
            <nfcomCabecMsg xmlns="http://www.portalfiscal.inf.br/nfcom/wsdl/NFComStatusServico">
                <cUF>{str(empresa.codigo_ibge)[:2]}</cUF>
                <versaoDados>1.00</versaoDados>
            </nfcomCabecMsg>
        </soap12:Header>
        <soap12:Body>
            <nfcomDadosMsg xmlns="http://www.portalfiscal.inf.br/nfcom/wsdl/NFComStatusServico">
                <consStatServNFCom xmlns="http://www.portalfiscal.inf.br/nfcom" versao="1.00">
                    <tpAmb>{"2" if ambiente == "homologacao" else "1"}</tpAmb>
                    <xServ>STATUS</xServ>
                </consStatServNFCom>
            </nfcomDadosMsg>
        </soap12:Body>
    </soap12:Envelope>"""

    # Usar Content-Type simples (alguns endpoints rejeitam o parâmetro charset)
    headers = {'Content-Type': 'application/soap+xml'}
    
    try:
        # Tentar com verificação de certificado; alguns ambientes homologação usam
        # certificados que o ambiente local não confia. Em caso de falha SSL tentamos
        # novamente com verify=False como fallback (com log para auditoria).
        try:
            response = requests.post(sefaz_url, data=soap_body.encode('utf-8'), headers=headers, timeout=10)
        except requests.exceptions.SSLError as e:
            print(f"WARN: Falha SSL na consulta NFCom (tentando fallback verify=False): {e}")
            try:
                response = requests.post(sefaz_url, data=soap_body.encode('utf-8'), headers=headers, timeout=10, verify=False)
            except Exception as e2:
                print(f"ERROR: Falha ao executar NFComConsulta mesmo com verify=False: {e2}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Erro de comunicação em NFComConsulta: {e}")
            return False
        
        if response.status_code == 200 and response.content:
            root = etree.fromstring(response.content)
            ns = {'sefaz': 'http://www.portalfiscal.inf.br/nfcom'}
            cStat = root.find('.//sefaz:cStat', ns)
            xMotivo = root.find('.//sefaz:xMotivo', ns)
            tpAmb = root.find('.//sefaz:tpAmb', ns)
            dhRecbto = root.find('.//sefaz:dhRecbto', ns)
            tMed = root.find('.//sefaz:tMed', ns)
            
            return {
                "status_code": response.status_code,
                "cStat": cStat.text if cStat is not None else "N/A",
                "xMotivo": xMotivo.text if xMotivo is not None else "N/A",
                "ambiente": "Homologação" if tpAmb is not None and tpAmb.text == "2" else "Produção",
                "servico_disponivel": cStat is not None and cStat.text == "107",
                "dhRecbto": dhRecbto.text if dhRecbto is not None else None,
                "tMed": tMed.text if tMed is not None else None,
            }
        else:
            return {"status_code": response.status_code, "error": "Resposta vazia ou inválida da SEFAZ", "content": response.text}
    except requests.exceptions.RequestException as e:
        return {"status_code": 503, "error": f"Erro de comunicação com a SEFAZ: {e}"}
    except Exception as e:
        return {"status_code": 500, "error": f"Erro ao processar resposta da SEFAZ: {e}", "content": response.text if 'response' in locals() else ''}


def _check_and_mark_cancelado_from_consulta(db: Session, db_nfcom, empresa_row):
    """Consulta a situação da NFCom (consSitNFCom) e procura por eventos de cancelamento homologados.

    Se encontrar um evento 110111 com cStat em (135,136,134), atualiza
    `db_nfcom.informacoes_adicionais` com os detalhes do evento para que o
    método `get_nfcom()` marque a nota como cancelada.
    """
    try:
        tpAmb = '1' if getattr(empresa_row, 'ambiente_nfcom', None) == 'producao' else ('2' if getattr(empresa_row, 'ambiente_nfcom', None) == 'homologacao' else ('1' if settings.NFCOM_AMBIENTE == 'producao' else '2'))
        cOrgao = str(getattr(empresa_row, 'codigo_ibge', '') or '')[:2] or '00'
        empresa_ambiente = getattr(empresa_row, 'ambiente_nfcom', None)
        ambiente = empresa_ambiente if empresa_ambiente in ('producao', 'homologacao') else settings.NFCOM_AMBIENTE
        sefaz_url = get_sefaz_url_by_uf(empresa_row.uf, ambiente, service='consulta')

        # Monta corpo SOAP para consSitNFCom
        soap_body = f"""<soap12:Envelope xmlns:soap12=\"http://www.w3.org/2003/05/soap-envelope\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\"><soap12:Header><nfcomCabecMsg xmlns=\"http://www.portalfiscal.inf.br/nfcom/wsdl/NFComConsulta\"><cUF>{cOrgao}</cUF><versaoDados>1.00</versaoDados></nfcomCabecMsg></soap12:Header><soap12:Body><nfcomConsultaNF xmlns=\"http://www.portalfiscal.inf.br/nfcom/wsdl/NFComConsulta\"><consSitNFCom xmlns=\"http://www.portalfiscal.inf.br/nfcom\" versao=\"1.00\"><tpAmb>{tpAmb}</tpAmb><xServ>CONSULTAR</xServ><chNFCom>{db_nfcom.chave_acesso}</chNFCom></consSitNFCom></nfcomConsultaNF></soap12:Body></soap12:Envelope>"""

        headers = {'Content-Type': 'application/soap+xml'}
        
        # Tenta primeiro com verificação SSL, depois com verify=False se falhar
        response = None
        try:
            response = requests.post(sefaz_url, data=soap_body.encode('utf-8'), headers=headers, timeout=10)
            print(f"INFO: Consulta NFCom executada com SSL verificado. Status: {response.status_code if response else 'N/A'}")
        except requests.exceptions.SSLError as e:
            print(f"WARN: Falha SSL na consulta NFCom (tentando fallback verify=False): {e}")
            try:
                response = requests.post(sefaz_url, data=soap_body.encode('utf-8'), headers=headers, timeout=10, verify=False)
                print(f"INFO: Consulta NFCom executada com verify=False. Status: {response.status_code if response else 'N/A'}")
            except Exception as e2:
                print(f"ERROR: Falha ao executar NFComConsulta mesmo com verify=False: {e2}")
                return False
        
        if not response:
            print(f"ERROR: Objeto response é None para chave {db_nfcom.chave_acesso}")
            return False
            
        if not response.content:
            print(f"WARN: response.content está vazio. Status: {response.status_code}, Headers: {dict(response.headers)}")
            return False
        
        print(f"INFO: Resposta recebida. Tamanho: {len(response.content)} bytes")
        
        # Salva resposta em arquivo temporário para debug
        try:
            import tempfile
            tmp_resp = tempfile.NamedTemporaryFile(delete=False, suffix='.xml', prefix=f'consulta_resp_{db_nfcom.id}_', dir=tempfile.gettempdir())
            tmp_resp.write(response.content)
            tmp_resp.flush()
            resp_file_path = tmp_resp.name
            tmp_resp.close()
            print(f"INFO: Resposta da consulta salva em: {resp_file_path}")
        except Exception as e:
            print(f"WARN: Falha ao salvar resposta da consulta: {e}")

        root = etree.fromstring(response.content)
        ns = {'nfcom': 'http://www.portalfiscal.inf.br/nfcom'}

        # Verifica se procEventoNFCom existe e procura por eventos 110111 (cancelamento)
        proc_nodes = root.findall('.//nfcom:procEventoNFCom', ns)
        print(f"INFO: Consulta NFCom encontrou {len(proc_nodes)} procEventoNFCom para chave {db_nfcom.chave_acesso}")
        for proc in proc_nodes:
            # tpEvento está dentro do evento -> infEvento/tpEvento
            tpEvento_elem = proc.find('.//nfcom:tpEvento', ns)
            if tpEvento_elem is None or tpEvento_elem.text != '110111':
                continue

            cStat_elem = proc.find('.//nfcom:cStat', ns)
            if cStat_elem is None:
                continue
            code = str(cStat_elem.text).strip()
            if code in ('135', '136', '134'):
                xMotivo_elem = proc.find('.//nfcom:xMotivo', ns)
                nProt_elem = proc.find('.//nfcom:nProt', ns)
                # Anexa observação para que get_nfcom() reconheça cancelamento
                note = f"Evento cancelamento detectado via consulta: cStat={code} xMotivo={(xMotivo_elem.text if xMotivo_elem is not None else '')} nProt={(nProt_elem.text if nProt_elem is not None else '')}"
                try:
                    db_nfcom.informacoes_adicionais = (db_nfcom.informacoes_adicionais or '') + "\n" + note
                    db.commit()
                    print(f"INFO: Atualizado informacoes_adicionais para NFCom {db_nfcom.id} com evento de cancelamento: cStat={code}")
                except Exception:
                    try:
                        db.rollback()
                    except Exception:
                        pass
                return True

        return False
    except Exception as e:
        print(f"ERRO na consulta de eventos (consSitNFCom): {e}")
        return False

def transmit_nfcom(db: Session, nfcom_id: int, empresa_id: int) -> dict:
    """
    Transmite uma NFCom para o webservice da SEFAZ.
    SEMPRE gera e assina o XML na hora da transmissão para garantir formato correto.
    """
    # 1. Busca a NFCom e a Empresa
    db_nfcom = get_nfcom(db, nfcom_id=nfcom_id, empresa_id=empresa_id)
    if not db_nfcom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NFCom não encontrada")

    # 2. SEMPRE gera o XML na hora da transmissão para garantir formato correto
    # (sem quebras de linha, com declaração XML, minificado)
    print("DEBUG: Gerando XML fresco para transmissão...")
    try:
        # Busca dados da empresa para assinatura
        empresa_raw = crud_empresa.get_empresa_raw(db, empresa_id=empresa_id)
        if not empresa_raw:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        try:
            cert_password = decrypt_sensitive_data(empresa_raw.certificado_senha) if empresa_raw.certificado_senha else None
        except Exception:
            cert_password = None

        empresa_para_assinatura = SimpleNamespace(
            certificado_path=empresa_raw.certificado_path,
            certificado_senha=cert_password,
            id=empresa_id,
            ambiente_nfcom=getattr(empresa_raw, 'ambiente_nfcom', None)
        )

        # Sempre gera uma nova chave de acesso no momento da transmissão.
        # Usamos o id do registro para compor um cNF8 determinístico, garantindo
        # previsibilidade e evitando divergências entre criação e transmissão.
        try:
            cnf8_from_id = str(db_nfcom.id % 100000000).zfill(8)
        except Exception:
            cnf8_from_id = '00000000'
        db_nfcom.chave_acesso = generate_access_key(db_nfcom, cNF_override=cnf8_from_id)
        try:
            db.commit()
            db.refresh(db_nfcom)
        except Exception:
            db.rollback()
        # DEBUG: print composed chave and DV diagnostics
        try:
            chave_dbg = getattr(db_nfcom, 'chave_acesso', '') or ''
            print(f"DEBUG: chave gerada (len={len(chave_dbg)}): {chave_dbg}")
            if len(chave_dbg) >= 43 and chave_dbg.isdigit():
                key43_dbg = chave_dbg[:-1]
                appended_dv = chave_dbg[-1]
                # recompute soma/rest/dv for debug
                pesos = [2,3,4,5,6,7,8,9]
                soma = sum(int(d)*pesos[i%len(pesos)] for i,d in enumerate(reversed(key43_dbg)))
                resto = soma % 11
                dv_raw = 11 - resto
                print(f"DEBUG: DV diagnostic -> soma={soma} resto={resto} dv_raw={dv_raw} appended_dv={appended_dv} calc_dv={_calculate_dv(key43_dbg)}")
        except Exception:
            pass

        # Gera XML não assinado
        snapshot = _make_nfcom_snapshot(db_nfcom, db_nfcom.empresa)
        xml_nao_assinado = generate_nfcom_xml(snapshot)
        # Valida localmente o XML gerado contra o XSD disponibilizado no repositório.
        # Isso evita enviar XML rejeitado por problemas de posicionamento/ordem de elementos
        # e fornece diagnóstico imediato para correção.
        try:
            xsd_path = Path(__file__).resolve().parents[1] / 'schemas' / 'xsd' / 'nfcom_v1.00.xsd'
            # Se o arquivo XSD existir, valida; caso contrário, apenas loga e continua.
            if xsd_path.exists():
                try:
                    # O XSD espera o elemento raiz <NFCom> contendo <infNFCom> E <infNFComSupl>.
                    # `generate_nfcom_xml` retorna apenas o <infNFCom>, e a assinatura
                    # insere o <infNFComSupl> (QR) depois; para validação local precisamos
                    # incluir temporariamente o <infNFComSupl> com o QR aqui também.

                    # Determina URL do QR Code pela UF da chave usando função helper
                    uf_code = db_nfcom.chave_acesso[:2] if db_nfcom.chave_acesso else "41"
                    # Preferir o ambiente definido na empresa_raw quando disponível
                    empresa_ambiente = getattr(empresa_raw, 'ambiente_nfcom', None)
                    qr_code_base_url = get_qrcode_url_base(uf_code, ambiente=empresa_ambiente)

                    # XSD exige parâmetro tpAmb=[1-2]: pattern obrigatório conforme nfcomTiposBasico_v1.00.xsd linha 1992
                    # Permitir escolha por empresa (ambiente_nfcom). Caso não exista, usar configuração global
                    empresa_ambiente = getattr(empresa_raw, 'ambiente_nfcom', None)
                    if empresa_ambiente in ('producao', 'producao'):
                        tpAmb = "1"
                    elif empresa_ambiente in ('homologacao', 'homologação', 'homolog'):
                        tpAmb = "2"
                    else:
                        # Usar configuração global se não especificado por empresa
                        tpAmb = "1" if settings.NFCOM_AMBIENTE == "producao" else "2"

                    params = f"?chNFCom={db_nfcom.chave_acesso}&tpAmb={tpAmb}"
                    try:
                        if getattr(db_nfcom, 'tipo_emissao', None) == models.TipoEmissao.CONTINGENCIA:
                            to_sign = db_nfcom.chave_acesso + settings.SECRET_KEY
                            signature = hashlib.sha1(to_sign.encode('utf-8')).hexdigest()
                            params += f"&sign={signature}"
                    except Exception:
                        pass
                    # Nota: não podemos validar <infNFCom> isoladamente contra o XSD porque
                    # o XSD só define <NFCom> como raiz global (que exige <Signature>).
                    # A validação completa será feita pelo SEFAZ após assinatura e envio.
                    # Salvamos o XML não assinado para diagnóstico em caso de rejeição:
                    temp_unsigned = tempfile.NamedTemporaryFile(
                        mode='w', encoding='utf-8', suffix='.xml',
                        prefix=f'unsigned_nfcom_{db_nfcom.id}_', delete=False
                    )
                    temp_unsigned.write(xml_nao_assinado)
                    temp_unsigned.close()
                    print(f"DEBUG: XML não assinado salvo em: {temp_unsigned.name}")
                except HTTPException as ve:
                    # Salva o XML que falhou na validação em arquivo temporário para inspeção
                    try:
                        tmpf = tempfile.NamedTemporaryFile(delete=False, suffix='.xml', prefix=f'invalid_nfcom_{db_nfcom.id}_', dir=tempfile.gettempdir())
                        try:
                            tmpf.write(xml_nao_assinado.encode('utf-8'))
                            tmpf.flush()
                            invalid_path = tmpf.name
                        finally:
                            tmpf.close()
                    except Exception:
                        invalid_path = None
                    detail_msg = f"XML inválido segundo XSD local: {ve.detail}."
                    if invalid_path:
                        detail_msg += f" XML salvo em: {invalid_path}"
                    raise HTTPException(status_code=400, detail=detail_msg)
        except HTTPException:
            # Propaga HTTPException (validação falhou)
            raise
        except Exception:
            # Se algo der errado na validação local, não bloquear a transmissão;
            # apenas loga o problema e prossegue (a validação remota da SEFAZ poderá fornecer o erro real).
            print("WARN: Falha ao tentar validar XML localmente contra XSD:", traceback.format_exc())
        
        # Assina o XML (já inclui minificação interna)
        xml_assinado = sign_nfcom_xml(xml_nao_assinado, empresa_para_assinatura, db_nfcom.chave_acesso, getattr(db_nfcom, 'tipo_emissao', None))
        
        # Salva o XML assinado no banco IMEDIATAMENTE para garantir que o
        # conteúdo enviado à SEFAZ esteja sempre persistido, mesmo que a
        # SEFAZ retorne erro/rejeição. Isso facilita auditoria e reenvio.
        try:
            db_nfcom.xml_gerado = xml_assinado
            db.commit()
            db.refresh(db_nfcom)
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass

        print(f"DEBUG: XML gerado e assinado com {len(xml_assinado)} caracteres")
        
    except Exception as e:
        print(f"ERRO ao gerar XML para transmissão: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar XML para transmissão: {e}")

    # 3. Define a URL do Webservice da SEFAZ (permite preferência por empresa)
    empresa_ambiente = getattr(empresa_raw, 'ambiente_nfcom', None)
    if empresa_ambiente in ('producao', 'homologacao'):
        ambiente = empresa_ambiente
    else:
        # Usar configuração global se não especificado por empresa
        ambiente = settings.NFCOM_AMBIENTE
    sefaz_url = get_sefaz_url_by_uf(db_nfcom.empresa.uf, ambiente)
    print(f"DEBUG: Ambiente={ambiente}, WebService URL={sefaz_url}")

    # 4. Compacta o XML com GZIP e codifica em Base64, como esperado pela SEFAZ.
    xml_bytes = xml_assinado.encode('utf-8')
    gzip_buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=gzip_buffer, mode='wb', mtime=0) as gzip_file:
        gzip_file.write(xml_bytes)
    dados_comprimidos_base64 = base64.b64encode(gzip_buffer.getvalue()).decode('utf-8')

    # 5. Monta o envelope SOAP correto (SOAP 1.2, SEM Header, conforme MOC)
    # "A área referente ao SOAP Header não deverá ser informada."
    soap_body = f"""<soap12:Envelope xmlns:soap12=\"http://www.w3.org/2003/05/soap-envelope\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\"><soap12:Body><nfcomDadosMsg xmlns=\"http://www.portalfiscal.inf.br/nfcom/wsdl/NFComRecepcao\">{dados_comprimidos_base64}</nfcomDadosMsg></soap12:Body></soap12:Envelope>"""

    # Log do XML sendo enviado para debug
    print("=== XML sendo enviado para SEFAZ ===")
    print(soap_body)
    print("=== Fim do XML ===")

    # Salva o envelope SOAP em um arquivo temporário para debug externo (curl/openssl)
    soap_file_path = None
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.xml', prefix=f'soap_nfcom_{db_nfcom.id}_', dir=tempfile.gettempdir())
        try:
            tmp.write(soap_body.encode('utf-8'))
            tmp.flush()
            soap_file_path = tmp.name
        finally:
            tmp.close()
        print(f"DEBUG: SOAP salvo em: {soap_file_path}")
    except Exception:
        print("WARN: não foi possível salvar o SOAP em arquivo temporário:\n", traceback.format_exc())
        soap_file_path = None

    # 4. Define os cabeçalhos da requisição
    # Alguns endpoints rejeitam o parâmetro charset; usar Content-Type sem charset pode evitar rejeição 599
    headers = {'Content-Type': 'application/soap+xml'}
    
    # 5. Prepara o certificado digital para a requisição
    empresa_raw = crud_empresa.get_empresa_raw(db, empresa_id=empresa_id)
    if not empresa_raw or not empresa_raw.certificado_path or not empresa_raw.certificado_senha:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Certificado digital da empresa não configurado.")

    cert_password = decrypt_sensitive_data(empresa_raw.certificado_senha)
    relative_cert_path = empresa_raw.certificado_path.replace("/secure/", "", 1)
    absolute_cert_path = Path(settings.CERTIFICATES_DIR) / relative_cert_path

    if not absolute_cert_path.exists():
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Arquivo de certificado não encontrado: {absolute_cert_path}")

    pem_file_path = None
    response = None
    try:
        with open(absolute_cert_path, "rb") as f:
            pfx_data = f.read()
        
        pem_file_path = _convert_pfx_to_pem(pfx_data, cert_password)

        # 6. Envia a requisição SOAP para o SEFAZ
        response = requests.post(
            url=sefaz_url,
            data=soap_body.encode('utf-8'),
            headers=headers,
            cert=pem_file_path,
            verify=False,  # Homologação pode não ter certificado válido
            timeout=30
        )

        # 7. Processa a resposta da SEFAZ
        # Processa a resposta da SEFAZ e sempre retorna o conteúdo para facilitar debug
        if response is not None:
            # Se a resposta estiver vazia, evita parsear e retorna detalhes para debug
            content_len = len(response.content or b'')
            print(f"DEBUG: resposta SEFAZ status={response.status_code} headers={response.headers} content_len={content_len}")
            if content_len == 0:
                # Salva resposta vazia (se houver) para debug
                resp_tmp = None
                try:
                    tmp_resp = tempfile.NamedTemporaryFile(delete=False, suffix='.resp', prefix=f'sefaz_resp_{db_nfcom.id}_', dir=tempfile.gettempdir())
                    tmp_resp.write(response.content or b'')
                    tmp_resp.flush()
                    resp_tmp = tmp_resp.name
                    tmp_resp.close()
                except Exception:
                    resp_tmp = None

                return {"status_code": response.status_code, "error": "Resposta vazia da SEFAZ", "headers": dict(response.headers), "content_len": content_len, "content": response.text, "xml_enviado": soap_body, "soap_file": soap_file_path, "soap_response_file": resp_tmp}

            try:
                # Salva o conteúdo bruto da resposta em arquivo para análise offline
                resp_file_path = None
                try:
                    tmp_resp = tempfile.NamedTemporaryFile(delete=False, suffix='.xml', prefix=f'sefaz_resp_{db_nfcom.id}_', dir=tempfile.gettempdir())
                    tmp_resp.write(response.content or b'')
                    tmp_resp.flush()
                    resp_file_path = tmp_resp.name
                    tmp_resp.close()
                except Exception:
                    resp_file_path = None

                # Tenta descompactar se o header indicar gzip
                try:
                    encoding = response.headers.get('Content-Encoding', '')
                    if 'gzip' in encoding.lower():
                        try:
                            import gzip as _gzip
                            decompressed = _gzip.decompress(response.content)
                            # sobrescreve o arquivo salvo com a versão descomprimida para facilitar leitura
                            if resp_file_path:
                                with open(resp_file_path, 'wb') as f:
                                    f.write(decompressed)
                            parse_content = decompressed
                        except Exception:
                            parse_content = response.content
                    else:
                        parse_content = response.content
                except Exception:
                    parse_content = response.content

                root = ET.fromstring(parse_content)
                ns_soap = {'soap': 'http://www.w3.org/2003/05/soap-envelope'}
                ns_nfcom = {'nfcom': 'http://www.portalfiscal.inf.br/nfcom'}
                ns_wsdl = {'wsdl': 'http://www.portalfiscal.inf.br/nfcom/wsdl/NFComRecepcao'}
                
                body = root.find('soap:Body', ns_soap)
                
                # Tenta encontrar retNFCom (resposta com cStat) ou protNFCom (autorização)
                result_node = None
                if body is not None:
                    # Primeiro tenta retNFCom (rejeições, erros)
                    result_node = body.find('.//nfcom:retNFCom', ns_nfcom)
                    if result_node is None:
                        # Se não encontrou, tenta protNFCom (autorização)
                        result_node = body.find('.//nfcom:protNFCom', ns_nfcom)

                if result_node is not None:
                    # Busca cStat e xMotivo no namespace nfcom
                    cStat_elem = result_node.find('.//nfcom:cStat', ns_nfcom)
                    xMotivo_elem = result_node.find('.//nfcom:xMotivo', ns_nfcom)
                    nProt_elem = result_node.find('.//nfcom:nProt', ns_nfcom)
                    
                    cStat = cStat_elem.text if cStat_elem is not None else "N/A"
                    xMotivo = xMotivo_elem.text if xMotivo_elem is not None else "N/A"
                    nProt = nProt_elem.text if nProt_elem is not None else None

                    print(f"=== RESPOSTA SEFAZ ===")
                    print(f"cStat: {cStat}")
                    print(f"xMotivo: {xMotivo}")
                    print(f"nProt: {nProt}")
                    print(f"===================")

                    if cStat == "100":
                        # Autorizada! Salva protocolo e XML no banco
                        db_nfcom.protocolo_autorizacao = nProt
                        db_nfcom.xml_gerado = xml_assinado
                        db.commit()
                        print("✅ NFCom AUTORIZADA! Protocolo e XML salvos no banco.")

                    return {"status_code": response.status_code, "cStat": cStat, "xMotivo": xMotivo, "nProt": nProt, "content": response.text, "xml_enviado": soap_body, "headers": dict(response.headers), "soap_file": soap_file_path, "soap_response_file": resp_file_path}
                else:
                    # Retorna o corpo da resposta mesmo quando inesperado
                    print("=== RESPOSTA SEFAZ (estrutura inesperada) ===")
                    print(f"Conteúdo: {response.text[:1000]}")  # Primeiros 1000 caracteres
                    print("=" * 50)
                    return {"status_code": response.status_code, "error": "Resposta inesperada", "content": response.text, "xml_enviado": soap_body, "headers": dict(response.headers), "soap_file": soap_file_path, "soap_response_file": resp_file_path}
            except Exception:
                # Se não conseguiu parsear como XML SOAP, devolve o texto cru também
                print("ERRO ao processar resposta SEFAZ (parsing):\n", traceback.format_exc())
                return {"status_code": response.status_code, "content": response.text, "xml_enviado": soap_body, "headers": dict(response.headers), "soap_file": soap_file_path, "soap_response_file": resp_file_path}

        # Se por algum motivo não houve resposta, retorna erro genérico com o XML enviado
        return {"status_code": None, "error": "Sem resposta da SEFAZ", "xml_enviado": soap_body, "soap_file": soap_file_path}

    except requests.exceptions.RequestException as e:
        print("ERRO de comunicação com a SEFAZ:\n", traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Erro de comunicação com a SEFAZ: {str(e)}\nXML enviado: {soap_body}\nSOAP file: {soap_file_path}")
    except Exception as e:
        print("ERRO inesperado durante a transmissão:\n", traceback.format_exc())
        # Retorna um HTTPException com detalhe para debug local
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro inesperado durante a transmissão: {str(e)}. Veja logs no servidor para o traceback. XML enviado: {soap_body}\nSOAP file: {soap_file_path}")
    finally:
        # Garante que o arquivo PEM temporário seja excluído
        if pem_file_path and os.path.exists(pem_file_path):
            os.remove(pem_file_path)