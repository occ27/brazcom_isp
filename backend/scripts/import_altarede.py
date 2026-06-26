import sys
import os
from datetime import datetime
import traceback
import ipaddress

# Add backend directory to sys.path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# ─── Configuração do Banco de Dados ───────────────────────────────────────────
# Para importar direto para produção, defina IMPORT_DB_URL antes de rodar:
#   export IMPORT_DB_URL="mysql+pymysql://occ:Altavista740@192.168.18.4:3315/brazcom_db"
# Ou deixe em branco para usar o banco local configurado no .env
IMPORT_DB_URL = os.environ.get(
    "IMPORT_DB_URL",
    "mysql+pymysql://occ:Altavista740@192.168.18.4:3315/brazcom_db"
)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if IMPORT_DB_URL:
    print(f"🔗 Conectando ao banco: {IMPORT_DB_URL.split('@')[1]}")  # oculta senha no log
    _engine = create_engine(IMPORT_DB_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
else:
    from app.core.database import SessionLocal
# ──────────────────────────────────────────────────────────────────────────────

from app.models.models import (
    Empresa, Cliente, EmpresaCliente, EmpresaClienteEndereco, 
    Receivable, Ticket, ServicoContratado, TipoPessoa, IndicadorIEDest, 
    StatusTicket, PrioridadeTicket, CategoriaTicket
)
from app.models.servico_model import Servico, TipoServico
from app.models.network import IPClass, InterfaceIPClassAssignment, RouterInterface

EMPRESA_ID = int(os.environ.get("EMPRESA_ID", "6"))

def parse_single_line_csv(file_path, encoding='latin1'):
    """
    Parses a single-line semicolon separated CSV with potential duplicate headers.
    """
    print(f"Parsing CSV {file_path}...")
    if not os.path.exists(file_path):
        print(f"  Warning: File {file_path} does not exist. Skipping.")
        return []
    
    with open(file_path, 'r', encoding=encoding) as f:
        content = f.read()

    # Find the first quote indicating the start of data
    first_quote_idx = content.find('"')
    if first_quote_idx == -1:
        header_part = content
        value_part = ""
    else:
        header_part = content[:first_quote_idx]
        value_part = content[first_quote_idx:]

    # Parse headers and make duplicate names unique
    header_raw = [h.strip() for h in header_part.split(';') if h.strip()]
    header = []
    seen = {}
    for h in header_raw:
        if h in seen:
            seen[h] += 1
            header.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            header.append(h)

    num_cols = len(header)
    if num_cols == 0:
        return []
        
    print(f"  Found headers ({num_cols}): {header[:10]}...")

    tokens = []
    n = len(value_part)
    i = 0
    while i < n:
        if value_part[i] == '"':
            # Quoted token
            start = i + 1
            i += 1
            while i < n:
                if value_part[i] == '\\':
                    i += 2  # skip escape and escaped char
                elif value_part[i] == '"':
                    break
                else:
                    i += 1
            token = value_part[start:i]
            tokens.append(token)
            i += 1 # move past closing quote
            if i < n and value_part[i] == ';':
                i += 1 # move past semicolon
        else:
            # Unquoted token
            start = i
            while i < n and value_part[i] != ';' and value_part[i] != '"':
                i += 1
            token = value_part[start:i]
            if token == '\\N':
                token = None
            tokens.append(token)
            if i < n and value_part[i] == ';':
                i += 1 # move past semicolon

    rows = []
    for idx in range(0, len(tokens), num_cols):
        row_tokens = tokens[idx:idx+num_cols]
        if len(row_tokens) == num_cols:
            row_dict = {header[c]: row_tokens[c] for c in range(num_cols)}
            rows.append(row_dict)
            
    print(f"  Parsed {len(rows)} rows.")
    return rows

def normalize_cod(cod):
    """
    Normaliza COD_CLIENTE/COD_ARECEBER removendo separadores de milhar (ponto)
    que o Altarede usa em campos numéricos (ex: '1.152' -> '1152').
    """
    if not cod:
        return cod
    cleaned = cod.strip()
    parts = cleaned.split('.')
    if len(parts) > 1 and all(p.isdigit() for p in parts):
        return ''.join(parts)
    return cleaned

def get_cached_cliente_and_endereco(cod_cliente_raw, clients_by_id_outros, clients_by_id, emp_clis, enderecos_by_desc):
    if not cod_cliente_raw:
        return None, None

    variants = list(dict.fromkeys([cod_cliente_raw, normalize_cod(cod_cliente_raw)]))

    for cod in variants:
        endereco = enderecos_by_desc.get(cod)
        if endereco:
            emp_cli = emp_clis.get(endereco.empresa_cliente_id)
            if emp_cli:
                cliente = clients_by_id.get(emp_cli.cliente_id)
                if cliente:
                    return cliente, endereco

        cliente = clients_by_id_outros.get(cod)
        if cliente:
            return cliente, None

    return None, None

def process_planos(db, file_path):
    print("\n--- Processando Planos ---")
    count = 0
    # Preload existing plans for EMPRESA_ID
    existing_planos = {
        s.codigo: s for s in db.query(Servico).filter(Servico.empresa_id == EMPRESA_ID).all()
    }
    
    for row in parse_single_line_csv(file_path):
        cod_plano = row.get('COD_PLANO')
        if not cod_plano:
            continue
            
        try:
            servico = existing_planos.get(cod_plano)
            if not servico:
                servico = Servico(
                    empresa_id=EMPRESA_ID,
                    tipo=TipoServico.PLANO_INTERNET.value,
                    codigo=cod_plano,
                    descricao=row.get('NOME', f'Plano {cod_plano}'),
                    cClass='99',
                    unidade_medida='UN',
                    valor_unitario=float(row.get('VALOR_MENSAL', 0.0) or 0.0),
                    is_active=True,
                    download_speed=float(row.get('DOWNLOAD', 0.0) or 0.0) / 1024.0,
                    upload_speed=float(row.get('UPLOAD', 0.0) or 0.0) / 1024.0
                )
                db.add(servico)
                existing_planos[cod_plano] = servico
                count += 1
        except Exception as e:
            db.rollback()
            print(f"Error row Plano {cod_plano}: {e}")
            
    db.commit()
    print(f"Planos importados: {count}")

def process_clientes(db, file_path):
    print("\n--- Processando Clientes ---")
    count = 0
    
    # Preload existing clients
    existing_by_cpf = {}
    existing_by_id_outros = {}
    
    clis = db.query(Cliente).filter(Cliente.empresa_id == EMPRESA_ID).all()
    for c in clis:
        if c.cpf_cnpj:
            existing_by_cpf[c.cpf_cnpj] = c
        if c.idOutros:
            existing_by_id_outros[c.idOutros] = c
            
    # Preload existing EmpresaCliente relations
    existing_emp_clis = {
        ec.cliente_id: ec for ec in db.query(EmpresaCliente).filter(EmpresaCliente.empresa_id == EMPRESA_ID).all()
    }
    
    # Preload existing EmpresaClienteEndereco relations
    existing_enderecos = {
        (ece.empresa_cliente_id, ece.descricao): ece
        for ece in db.query(EmpresaClienteEndereco)
        .join(EmpresaCliente, EmpresaClienteEndereco.empresa_cliente_id == EmpresaCliente.id)
        .filter(EmpresaCliente.empresa_id == EMPRESA_ID).all()
    }
    
    for row in parse_single_line_csv(file_path):
        cod_cliente = row.get('COD_CLIENTE')
        if not cod_cliente:
            continue
            
        try:
            cliente = None
            cpf_cnpj = row.get('CPF') or row.get('CNPJ')
            if cpf_cnpj:
                cpf_cnpj = ''.join(filter(str.isdigit, cpf_cnpj))
                if not cpf_cnpj:
                    cpf_cnpj = None
                    
            if cpf_cnpj:
                cliente = existing_by_cpf.get(cpf_cnpj)
                
            if not cliente:
                cliente = existing_by_id_outros.get(cod_cliente)
                
            if not cliente:
                # TIPO_CLIENTE (index 6) holds person type like 'F' or 'J'
                tipo_pessoa = TipoPessoa.FISICA if row.get('TIPO_CLIENTE') == 'F' else TipoPessoa.JURIDICA
                data_nasc_str = row.get('DATA_NASCIMENTO')
                data_nasc = None
                if data_nasc_str and data_nasc_str != '0000-00-00':
                    try:
                        data_nasc = datetime.strptime(data_nasc_str[:10], '%Y-%m-%d').date()
                    except:
                        pass
                        
                cliente = Cliente(
                    empresa_id=EMPRESA_ID,
                    nome_razao_social=row.get('NOME', 'Sem Nome')[:255],
                    cpf_cnpj=cpf_cnpj,
                    idOutros=cod_cliente,
                    tipo_pessoa=tipo_pessoa,
                    ind_ie_dest=IndicadorIEDest.NAO_CONTRIBUINTE,
                    inscricao_estadual=row.get('IDENTIDADE', '')[:20],
                    email=row.get('EMAIL1', '')[:255],
                    telefone=(row.get('TELEFONE_CELULAR1', '') or row.get('TELEFONE_RESIDENCIAL', ''))[:20],
                    data_nascimento=data_nasc,
                    is_active=True if row.get('ATIVO') == 'S' else False
                )
                db.add(cliente)
                db.flush() # get cliente.id
                
                if cpf_cnpj:
                    existing_by_cpf[cpf_cnpj] = cliente
                existing_by_id_outros[cod_cliente] = cliente
                
            emp_cli = existing_emp_clis.get(cliente.id)
            if not emp_cli:
                emp_cli = EmpresaCliente(
                    empresa_id=EMPRESA_ID,
                    cliente_id=cliente.id,
                    is_active=cliente.is_active
                )
                db.add(emp_cli)
                db.flush() # get emp_cli.id
                existing_emp_clis[cliente.id] = emp_cli
                
            # Verifica se já importou este endereço/cod_cliente
            addr_key = (emp_cli.id, cod_cliente)
            endereco_exists = existing_enderecos.get(addr_key)
            
            if not endereco_exists:
                endereco = EmpresaClienteEndereco(
                    empresa_cliente_id=emp_cli.id,
                    descricao=cod_cliente,
                    endereco=f"{row.get('LOGRADOURO', '')} {row.get('ENDERECO', '')}".strip()[:255] or 'Sem Endereço',
                    numero=row.get('COMPLEMENTO', 'S/N')[:20] or 'S/N',
                    bairro=row.get('BAIRRO', 'Centro')[:100] or 'Centro',
                    municipio=row.get('CIDADE', 'Cidade')[:100] or 'Cidade',
                    uf=row.get('ESTADO', 'MG')[:2] or 'MG',
                    cep=''.join(filter(str.isdigit, row.get('CEP', '00000000')))[:9] or '00000000',
                    is_principal=True
                )
                db.add(endereco)
                db.flush() # get endereco.id
                existing_enderecos[addr_key] = endereco
                count += 1
                
            if count % 1000 == 0:
                db.commit()
                
        except Exception as e:
            db.rollback()
            print(f"Error row Cliente {cod_cliente}: {e}")
            
    db.commit()
    print(f"Clientes/Endereços importados: {count}")

def process_logins(db, logins_file_path, endereco_logins_file_path):
    print("\n--- Processando Logins (ServicoContratado) ---")
    
    # 1. Preload clients and address caches
    clients_by_id_outros = {c.idOutros: c for c in db.query(Cliente).filter(Cliente.empresa_id == EMPRESA_ID).all() if c.idOutros}
    clients_by_id = {c.id: c for c in db.query(Cliente).filter(Cliente.empresa_id == EMPRESA_ID).all()}
    
    emp_clis = {
        ec.cliente_id: ec for ec in db.query(EmpresaCliente).filter(EmpresaCliente.empresa_id == EMPRESA_ID).all()
    }
    emp_clis_by_id = {ec.id: ec for ec in emp_clis.values()}
    
    enderecos_by_desc = {
        ece.descricao: ece 
        for ece in db.query(EmpresaClienteEndereco)
        .join(EmpresaCliente, EmpresaClienteEndereco.empresa_cliente_id == EmpresaCliente.id)
        .filter(EmpresaCliente.empresa_id == EMPRESA_ID).all()
    }
    
    # 2. Load Endereco_Logins.csv mapping
    login_address_map = {}
    if os.path.exists(endereco_logins_file_path):
        for row in parse_single_line_csv(endereco_logins_file_path):
            login_val = row.get('LOGIN')
            if login_val:
                login_address_map[login_val.strip()] = row
                
    # 3. Preload Router interfaces and IP classes
    networks_map = []
    from app.models.network import Router as RouterModel
    
    assignments = (
        db.query(InterfaceIPClassAssignment)
        .join(RouterInterface, InterfaceIPClassAssignment.interface_id == RouterInterface.id)
        .join(RouterModel, RouterInterface.router_id == RouterModel.id)
        .filter(RouterModel.empresa_id == EMPRESA_ID)
        .all()
    )
    
    for asgmnt in assignments:
        ip_class = db.query(IPClass).filter(IPClass.id == asgmnt.ip_class_id).first()
        interface = db.query(RouterInterface).filter(RouterInterface.id == asgmnt.interface_id).first()
        if ip_class and interface:
            try:
                net = ipaddress.IPv4Network(ip_class.rede, strict=False)
                networks_map.append({
                    'network': net,
                    'ip_class_id': ip_class.id,
                    'interface_id': interface.id,
                    'router_id': interface.router_id
                })
            except Exception as e:
                print(f"Erro ao parsear rede {ip_class.rede}: {e}")
                
    print(f"Carregadas {len(networks_map)} associações de rede para roteadores (apenas empresa {EMPRESA_ID}).")

    # 4. Preload existing plans
    existing_planos = {
        s.codigo: s for s in db.query(Servico).filter(Servico.empresa_id == EMPRESA_ID).all()
    }
    
    # 5. Preload existing contracts (ServicoContratado)
    existing_contratos = {
        (sc.cliente_id, sc.servico_id, sc.endereco_id): sc
        for sc in db.query(ServicoContratado).filter(ServicoContratado.empresa_id == EMPRESA_ID).all()
    }

    count = 0
    for row in parse_single_line_csv(logins_file_path):
        cod_cliente = row.get('COD_CLIENTE')
        try:
            cliente, endereco = get_cached_cliente_and_endereco(
                cod_cliente, clients_by_id_outros, clients_by_id, emp_clis_by_id, enderecos_by_desc
            )
            if not cliente:
                continue
                
            cod_plano = row.get('COD_PLANO')
            servico = None
            if cod_plano:
                servico = existing_planos.get(cod_plano)
                
            if not servico:
                continue
                
            # Check if this login has a custom address in Endereco_Logins.csv
            login_key = row.get('LOGIN', '').strip()
            custom_addr = login_address_map.get(login_key)
            if custom_addr:
                emp_cli = emp_clis.get(cliente.id)
                if emp_cli:
                    addr_desc = f"{cod_cliente}_login_{login_key}"
                    custom_endereco = enderecos_by_desc.get(addr_desc)
                    if not custom_endereco:
                        # Create secondary address
                        custom_endereco = EmpresaClienteEndereco(
                            empresa_cliente_id=emp_cli.id,
                            descricao=addr_desc,
                            endereco=f"{custom_addr.get('LOGRADOURO', '')} {custom_addr.get('ENDERECO', '')}".strip()[:255] or 'Sem Endereço',
                            numero=custom_addr.get('COMPLEMENTO', 'S/N')[:20] or 'S/N',
                            bairro=custom_addr.get('BAIRRO', 'Centro')[:100] or 'Centro',
                            municipio=custom_addr.get('CIDADE', 'Cidade')[:100] or 'Cidade',
                            uf=custom_addr.get('ESTADO', 'MG')[:2] or 'MG',
                            cep=''.join(filter(str.isdigit, custom_addr.get('CEP', '00000000')))[:9] or '00000000',
                            is_principal=False
                        )
                        db.add(custom_endereco)
                        db.flush() # get id
                        enderecos_by_desc[addr_desc] = custom_endereco
                    endereco = custom_endereco

            assigned_ip = row.get('IP')
            router_id = None
            interface_id = None
            ip_class_id = None
            
            if assigned_ip:
                try:
                    ip_obj = ipaddress.IPv4Address(assigned_ip.strip())
                    for net_map in networks_map:
                        if ip_obj in net_map['network']:
                            router_id = net_map['router_id']
                            interface_id = net_map['interface_id']
                            ip_class_id = net_map['ip_class_id']
                            break
                except:
                    pass
            
            addr_id = endereco.id if endereco else None
            exists = existing_contratos.get((cliente.id, servico.id, addr_id))
            
            if exists:
                # Update existing
                exists.metodo_autenticacao = 'IP_MAC'
                exists.assigned_ip = assigned_ip
                exists.mac_address = row.get('MAC')
                exists.pppoe_username = None
                exists.pppoe_password = None

                codigo_legado = row.get('CODIGO', '').strip()
                if codigo_legado and not exists.numero_contrato:
                    exists.numero_contrato = codigo_legado

                data_inst_str = row.get('DATA_INSTALACAO', '').strip()
                if data_inst_str and data_inst_str != '0000-00-00':
                    try:
                        data_inst = datetime.strptime(data_inst_str[:10], '%Y-%m-%d')
                        if not exists.d_contrato_ini:
                            exists.d_contrato_ini = data_inst
                        if not exists.data_instalacao:
                            exists.data_instalacao = data_inst
                        if not exists.data_inicio_cobranca:
                            exists.data_inicio_cobranca = data_inst
                    except:
                        pass

                if router_id:
                    exists.router_id = router_id
                    exists.interface_id = interface_id
                    exists.ip_class_id = ip_class_id

                count += 1
                if count % 1000 == 0:
                    db.commit()
            else:
                dia_venc_str = row.get('DIA_VENCIMENTO')
                dia_venc = 10
                try:
                    if dia_venc_str:
                        dia_venc = int(float(dia_venc_str))
                except:
                    pass

                codigo_legado = normalize_cod(row.get('CODIGO', '').strip()) or None

                data_inst = None
                data_inst_str = row.get('DATA_INSTALACAO', '').strip()
                if data_inst_str and data_inst_str not in ('0000-00-00', ''):
                    try:
                        data_inst = datetime.strptime(data_inst_str[:10], '%Y-%m-%d')
                    except:
                        pass

                servico_contratado = ServicoContratado(
                    empresa_id=EMPRESA_ID,
                    cliente_id=cliente.id,
                    servico_id=servico.id,
                    endereco_id=addr_id,
                    router_id=router_id,
                    interface_id=interface_id,
                    ip_class_id=ip_class_id,
                    numero_contrato=codigo_legado,
                    d_contrato_ini=data_inst,
                    data_instalacao=data_inst,
                    data_inicio_cobranca=data_inst,
                    valor_unitario=servico.valor_unitario,
                    dia_emissao=dia_venc,
                    dia_vencimento=dia_venc,
                    metodo_autenticacao='IP_MAC',
                    assigned_ip=assigned_ip,
                    mac_address=row.get('MAC'),
                    pppoe_username=None,
                    pppoe_password=None,
                    auto_emit=True,
                    is_active=True
                )
                db.add(servico_contratado)
                existing_contratos[(cliente.id, servico.id, addr_id)] = servico_contratado
                count += 1

                if count % 1000 == 0:
                    db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error row Login {cod_cliente}: {e}")
            
    db.commit()
    print(f"Logins importados: {count}")

def process_financeiro(db, file_path):
    print(f"\n--- Processando Financeiro ({file_path}) ---")
    
    # Preload clients for lookup
    clients_by_id_outros = {c.idOutros: c for c in db.query(Cliente).filter(Cliente.empresa_id == EMPRESA_ID).all() if c.idOutros}
    clients_by_id = {c.id: c for c in db.query(Cliente).filter(Cliente.empresa_id == EMPRESA_ID).all()}
    
    emp_clis = {
        ec.cliente_id: ec for ec in db.query(EmpresaCliente).filter(EmpresaCliente.empresa_id == EMPRESA_ID).all()
    }
    emp_clis_by_id = {ec.id: ec for ec in emp_clis.values()}
    
    enderecos_by_desc = {
        ece.descricao: ece 
        for ece in db.query(EmpresaClienteEndereco)
        .join(EmpresaCliente, EmpresaClienteEndereco.empresa_cliente_id == EmpresaCliente.id)
        .filter(EmpresaCliente.empresa_id == EMPRESA_ID).all()
    }
    
    # Preload existing receivables
    existing_receivables = set(
        r[0] for r in db.query(Receivable.nosso_numero).filter(Receivable.empresa_id == EMPRESA_ID).all() if r[0]
    )
    
    count = 0
    for row in parse_single_line_csv(file_path):
        cod_cliente = row.get('COD_CLIENTE')
        try:
            cliente, _ = get_cached_cliente_and_endereco(
                cod_cliente, clients_by_id_outros, clients_by_id, emp_clis_by_id, enderecos_by_desc
            )
            if not cliente:
                continue
                
            cod_areceber = row.get('COD_ARECEBER')
            if not cod_areceber:
                continue
                
            if cod_areceber in existing_receivables:
                continue
                
            due_date_str = row.get('DATA_VENCIMENTO')
            if not due_date_str or due_date_str == '0000-00-00':
                continue
            due_date = datetime.strptime(due_date_str[:10], '%Y-%m-%d')
            
            amount = float(row.get('VALOR', 0.0) or 0.0)
            paid_amount_str = row.get('VALOR_PAGO', 0.0)
            paid_amount = float(paid_amount_str) if paid_amount_str else None
            
            paid_at = None
            status = 'PENDING'
            data_pagamento_str = row.get('DATA_PAGAMENTO')
            if data_pagamento_str and data_pagamento_str != '0000-00-00':
                try:
                    paid_at = datetime.strptime(data_pagamento_str[:10], '%Y-%m-%d')
                    status = 'PAID'
                except:
                    pass
                
            receivable = Receivable(
                empresa_id=EMPRESA_ID,
                cliente_id=cliente.id,
                nosso_numero=cod_areceber,
                due_date=due_date,
                amount=amount,
                paid_amount=paid_amount,
                paid_at=paid_at,
                status=status,
                bank='OUTRO'
            )
            db.add(receivable)
            existing_receivables.add(cod_areceber)
            count += 1
            
            if count % 1000 == 0:
                db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error row Financeiro {cod_cliente}: {e}")
            
    db.commit()
    print(f"Registros financeiros importados: {count}")

def process_os(db, file_path):
    print("\n--- Processando OS ---")
    
    # Preload clients
    clients_by_id_outros = {c.idOutros: c for c in db.query(Cliente).filter(Cliente.empresa_id == EMPRESA_ID).all() if c.idOutros}
    clients_by_id = {c.id: c for c in db.query(Cliente).filter(Cliente.empresa_id == EMPRESA_ID).all()}
    
    emp_clis = {
        ec.cliente_id: ec for ec in db.query(EmpresaCliente).filter(EmpresaCliente.empresa_id == EMPRESA_ID).all()
    }
    emp_clis_by_id = {ec.id: ec for ec in emp_clis.values()}
    
    enderecos_by_desc = {
        ece.descricao: ece 
        for ece in db.query(EmpresaClienteEndereco)
        .join(EmpresaCliente, EmpresaClienteEndereco.empresa_cliente_id == EmpresaCliente.id)
        .filter(EmpresaCliente.empresa_id == EMPRESA_ID).all()
    }
    
    # Preload existing ticket titles for the client
    existing_tickets = set(
        (t.cliente_id, t.titulo)
        for t in db.query(Ticket).filter(Ticket.empresa_id == EMPRESA_ID).all()
    )
    
    count = 0
    for row in parse_single_line_csv(file_path):
        cod_cliente = row.get('COD_CLIENTE')
        try:
            cliente, _ = get_cached_cliente_and_endereco(
                cod_cliente, clients_by_id_outros, clients_by_id, emp_clis_by_id, enderecos_by_desc
            )
            if not cliente:
                continue
                
            id_os = row.get('ID_OS')
            if not id_os:
                continue
                
            data_cadastro_str = row.get('DATA_CADASTRO')
            if not data_cadastro_str or data_cadastro_str == '0000-00-00':
                continue
            data_cadastro = datetime.strptime(data_cadastro_str[:10], '%Y-%m-%d')
            
            status = StatusTicket.ABERTO
            resolvido_em = None
            
            data_conclusao_str = row.get('DATA_CONCLUSAO')
            if data_conclusao_str and data_conclusao_str != '0000-00-00':
                try:
                    resolvido_em = datetime.strptime(data_conclusao_str[:10], '%Y-%m-%d')
                    status = StatusTicket.FECHADO
                except:
                    pass
                
            obs = row.get('OBS', 'Sem descrição')
            obs_conclusao = row.get('OBS_CONCLUSAO', '')
            user_id = 1 
            
            titulo_os = f"OS {id_os} - {row.get('TIPO_SERVICO', 'Geral')}"
            
            if (cliente.id, titulo_os) in existing_tickets:
                continue
                
            ticket = Ticket(
                empresa_id=EMPRESA_ID,
                cliente_id=cliente.id,
                criado_por_id=user_id,
                titulo=titulo_os,
                descricao=obs,
                status=status,
                resolucao=obs_conclusao,
                resolvido_em=resolvido_em,
                prioridade=PrioridadeTicket.NORMAL,
                categoria=CategoriaTicket.SUPORTE
            )
            db.add(ticket)
            existing_tickets.add((cliente.id, titulo_os))
            count += 1
            
            if count % 1000 == 0:
                db.commit()
                
        except Exception as e:
            db.rollback()
            print(f"Error row OS {cod_cliente}: {e}")
            
    db.commit()
    print(f"OS importadas: {count}")


def main():
    db = SessionLocal()
    try:
        # Check if empresa exists
        empresa = db.query(Empresa).filter(Empresa.id == EMPRESA_ID).first()
        if not empresa:
            print(f"Empresa ID {EMPRESA_ID} não encontrada. Criando empresa padrão.")
            empresa = Empresa(
                id=EMPRESA_ID, 
                razao_social="Empresa Migrada", 
                cnpj="00000000000000", 
                endereco="Rua A", 
                numero="1", 
                bairro="Centro", 
                municipio="BH", 
                uf="MG", 
                codigo_ibge="0000000", 
                cep="00000000", 
                email="contato@empresa.com", 
                user_id=1
            )
            db.add(empresa)
            db.commit()

        base_dir = "/Users/orlando/python/FastAPI/brazcom_isp/Pronect"
        
        process_planos(db, f"{base_dir}/Planos.csv")
        process_clientes(db, f"{base_dir}/Clientes.csv")
        process_logins(db, f"{base_dir}/Logins.csv", f"{base_dir}/Endereco_Logins.csv")
        process_financeiro(db, f"{base_dir}/Financeiro.csv")
        process_os(db, f"{base_dir}/OS.csv")

        print("Importação concluída com sucesso!")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
