import sys
import os
from datetime import datetime, date
import traceback
import ipaddress

# Add backend directory to sys.path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# ─── Configuração do Banco de Dados ───────────────────────────────────────────
# Para importar direto para produção, defina IMPORT_DB_URL antes de rodar:
#   export IMPORT_DB_URL="mysql+pymysql://occ:Altavista740@192.168.18.4:3315/brazcom_db"
# Ou deixe em branco para usar o banco local configurado no .env
from app.core.config import settings
IMPORT_DB_URL = os.environ.get("IMPORT_DB_URL", settings.DATABASE_URL)

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
    StatusTicket, PrioridadeTicket, CategoriaTicket, StatusContrato, TipoConexao
)
from app.models.servico_model import Servico, TipoServico
from app.models.network import IPClass, InterfaceIPClassAssignment, RouterInterface

EMPRESA_ID = 6

def parse_pronect_csv(file_path):
    """
    Parses a CSV file from Pronect that might be missing row delimiters (newlines)
    using a robust character-by-character state machine.
    """
    print(f"Parsing {file_path}...")
    with open(file_path, "r", encoding="windows-1252") as f:
        content = f.read()
        
    rows = []
    current_row = []
    current_field = []
    
    state = 'outside'
    saw_delimiter = True
    
    i = 0
    n = len(content)
    
    while i < n:
        char = content[i]
        
        if state == 'outside':
            if char.isspace() and char not in ('\r', '\n'):
                i += 1
            elif char in ('\r', '\n'):
                i += 1
            elif char == ';':
                current_row.append("".join(current_field))
                current_field = []
                saw_delimiter = True
                i += 1
            elif char == '"':
                if not saw_delimiter:
                    # Row transition!
                    current_row.append("".join(current_field))
                    rows.append(current_row)
                    current_row = []
                    current_field = []
                state = 'in_quotes'
                saw_delimiter = False
                i += 1
            else:
                if not saw_delimiter:
                    # Row transition!
                    current_row.append("".join(current_field))
                    rows.append(current_row)
                    current_row = []
                    current_field = []
                current_field.append(char)
                state = 'in_unquotes'
                saw_delimiter = False
                i += 1
                
        elif state == 'in_quotes':
            # Check for escaped quote \"
            num_backslashes = 0
            k = i - 1
            while k >= 0 and content[k] == '\\':
                num_backslashes += 1
                k -= 1
            
            if char == '"' and num_backslashes % 2 == 0:
                state = 'outside'
            else:
                current_field.append(char)
            i += 1
            
        elif state == 'in_unquotes':
            if char == ';':
                current_row.append("".join(current_field))
                current_field = []
                state = 'outside'
                saw_delimiter = True
                i += 1
            elif char == '"':
                current_row.append("".join(current_field))
                rows.append(current_row)
                current_row = []
                current_field = []
                state = 'in_quotes'
                saw_delimiter = False
                i += 1
            elif char in ('\r', '\n'):
                current_row.append("".join(current_field))
                current_field = []
                state = 'outside'
                saw_delimiter = False
                i += 1
            else:
                current_field.append(char)
                i += 1
                
    if current_field or current_row:
        current_row.append("".join(current_field))
        rows.append(current_row)
        
    return rows

def parse_date_only(date_str):
    if not date_str or date_str in ('0000-00-00', '0000-00-00 00:00:00', '\\N', 'None', ''):
        return None
    date_str = date_str.split()[0].strip()
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        try:
            return datetime.strptime(date_str, "%d/%m/%Y").date()
        except Exception:
            return None

def parse_datetime_val(date_str):
    if not date_str or date_str in ('0000-00-00', '0000-00-00 00:00:00', '\\N', 'None', ''):
        return None
    date_str = date_str.strip()
    try:
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except Exception:
            try:
                return datetime.strptime(date_str, "%d/%m/%Y")
            except Exception:
                return None

def clean_val(val):
    if not val or val == "\\N" or val == "NULL":
        return None
    return val.strip()

def get_cliente_and_endereco_by_legacy_id(db, cod_cliente):
    if not cod_cliente:
        return None, None
        
    cod = cod_cliente.strip()
    
    # Try finding by address description (stores the legacy COD_CLIENTE)
    endereco = db.query(EmpresaClienteEndereco).join(EmpresaCliente).filter(
        EmpresaCliente.empresa_id == EMPRESA_ID,
        EmpresaClienteEndereco.descricao == cod
    ).first()
    
    if endereco:
        cliente = db.query(Cliente).filter(Cliente.id == endereco.empresa_cliente.cliente_id).first()
        return cliente, endereco
        
    # Fallback to Cliente.idOutros
    cliente = db.query(Cliente).filter(
        Cliente.empresa_id == EMPRESA_ID,
        Cliente.idOutros == cod
    ).first()
    
    if cliente:
        # Try to find principal address
        emp_cli = db.query(EmpresaCliente).filter(
            EmpresaCliente.empresa_id == EMPRESA_ID,
            EmpresaCliente.cliente_id == cliente.id
        ).first()
        if emp_cli:
            addr = db.query(EmpresaClienteEndereco).filter(
                EmpresaClienteEndereco.empresa_cliente_id == emp_cli.id,
                EmpresaClienteEndereco.is_principal == True
            ).first()
            return cliente, addr
        return cliente, None
        
    return None, None

def process_clientes(db, file_path, dry_run=True):
    print("\n--- Processando Clientes ---")
    rows = parse_pronect_csv(file_path)
    if not rows or len(rows) < 2:
        print("Nenhum dado de cliente encontrado.")
        return 0
        
    headers = rows[0]
    header_map = {name: idx for idx, name in enumerate(headers)}
    
    count = 0
    for r_idx, r in enumerate(rows[1:], start=1):
        if len(r) != len(headers):
            print(f"Linha {r_idx} ignorada (colunas {len(r)} != esperado {len(headers)}).")
            continue
            
        row_dict = {name: r[idx] for name, idx in header_map.items()}
        cod_cliente = clean_val(row_dict.get('COD_CLIENTE'))
        if not cod_cliente:
            continue
            
        try:
            cpf_cnpj = clean_val(row_dict.get('CPF'))
            if cpf_cnpj:
                cpf_cnpj = ''.join(filter(str.isdigit, cpf_cnpj))
                if not cpf_cnpj:
                    cpf_cnpj = None
                    
            cliente = None
            if cpf_cnpj:
                cliente = db.query(Cliente).filter(
                    Cliente.empresa_id == EMPRESA_ID,
                    Cliente.cpf_cnpj == cpf_cnpj
                ).first()
                
            if not cliente:
                cliente = db.query(Cliente).filter(
                    Cliente.empresa_id == EMPRESA_ID,
                    Cliente.idOutros == cod_cliente
                ).first()
                
            # Determina tipo de pessoa
            tipo_p = clean_val(row_dict.get('TIPO_CLIENTE'))
            tipo_pessoa = TipoPessoa.JURIDICA if tipo_p == 'J' else TipoPessoa.FISICA
            if cpf_cnpj and len(cpf_cnpj) > 11:
                tipo_pessoa = TipoPessoa.JURIDICA
                
            data_nasc = parse_date_only(clean_val(row_dict.get('DATA_NASCIMENTO')))
            is_active = (clean_val(row_dict.get('ATIVO')) == 'S')
            
            nome = clean_val(row_dict.get('NOME')) or 'Sem Nome'
            identidade = clean_val(row_dict.get('IDENTIDADE')) or ''
            email = clean_val(row_dict.get('EMAIL1')) or ''
            tel = clean_val(row_dict.get('TELEFONE_CELULAR1')) or clean_val(row_dict.get('TELEFONE_RESIDENCIAL')) or ''
            
            if not cliente:
                if not dry_run:
                    cliente = Cliente(
                        empresa_id=EMPRESA_ID,
                        nome_razao_social=nome[:255],
                        cpf_cnpj=cpf_cnpj,
                        idOutros=cod_cliente,
                        tipo_pessoa=tipo_pessoa,
                        ind_ie_dest=IndicadorIEDest.NAO_CONTRIBUINTE,
                        inscricao_estadual=identidade[:20],
                        email=email[:255],
                        telefone=tel[:20],
                        data_nascimento=data_nasc,
                        is_active=is_active
                    )
                    db.add(cliente)
                    db.flush()
                count += 1
            else:
                # Update attributes if needed
                if not dry_run:
                    cliente.nome_razao_social = nome[:255]
                    cliente.idOutros = cod_cliente
                    cliente.email = email[:255]
                    cliente.telefone = tel[:20]
                    cliente.is_active = is_active
                    db.flush()
                count += 1
                
            # Create/update association
            if not dry_run:
                emp_cli = db.query(EmpresaCliente).filter(
                    EmpresaCliente.empresa_id == EMPRESA_ID,
                    EmpresaCliente.cliente_id == cliente.id
                ).first()
                if not emp_cli:
                    emp_cli = EmpresaCliente(
                        empresa_id=EMPRESA_ID,
                        cliente_id=cliente.id,
                        is_active=is_active
                    )
                    db.add(emp_cli)
                    db.flush()
                else:
                    emp_cli.is_active = is_active
                    db.flush()
                    
                # Create Address
                endereco_exists = db.query(EmpresaClienteEndereco).filter(
                    EmpresaClienteEndereco.empresa_cliente_id == emp_cli.id,
                    EmpresaClienteEndereco.descricao == cod_cliente
                ).first()
                
                logradouro = clean_val(row_dict.get('LOGRADOURO')) or ''
                end = clean_val(row_dict.get('ENDERECO')) or ''
                logradouro_end = f"{logradouro} {end}".strip()[:255] or 'Sem Endereço'
                
                numero = clean_val(row_dict.get('COMPLEMENTO')) or 'S/N'
                bairro = clean_val(row_dict.get('BAIRRO')) or 'Centro'
                municipio = clean_val(row_dict.get('CIDADE')) or 'Cidade'
                uf = clean_val(row_dict.get('ESTADO')) or 'MG'
                cep = clean_val(row_dict.get('CEP')) or '00000000'
                cep = ''.join(filter(str.isdigit, cep))[:9]
                
                if not endereco_exists:
                    endereco = EmpresaClienteEndereco(
                        empresa_cliente_id=emp_cli.id,
                        descricao=cod_cliente,
                        endereco=logradouro_end,
                        numero=numero[:20],
                        bairro=bairro[:100],
                        municipio=municipio[:100],
                        uf=uf[:2],
                        cep=cep,
                        is_principal=True
                    )
                    db.add(endereco)
                    db.flush()
                else:
                    endereco_exists.endereco = logradouro_end
                    endereco_exists.numero = numero[:20]
                    endereco_exists.bairro = bairro[:100]
                    endereco_exists.municipio = municipio[:100]
                    endereco_exists.uf = uf[:2]
                    endereco_exists.cep = cep
                    db.flush()
                    
            if not dry_run and count % 500 == 0:
                db.commit()
                
        except Exception as e:
            if not dry_run:
                db.rollback()
            print(f"Erro ao processar cliente {cod_cliente}: {e}")
            traceback.print_exc()
            
    if not dry_run:
        db.commit()
    print(f"Clientes processados: {count} (Modo Dry-Run: {dry_run})")
    return count

def process_logins(db, file_path, dry_run=True):
    print("\n--- Processando Logins (ServicoContratado) ---")
    rows = parse_pronect_csv(file_path)
    if not rows or len(rows) < 2:
        print("Nenhum dado de login encontrado.")
        return 0
        
    headers = rows[0]
    header_map = {name: idx for idx, name in enumerate(headers)}
    
    # 1. Pré-carrega associações de rede para roteadores da EMPRESA_ID
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
                
    print(f"Carregadas {len(networks_map)} associações de rede.")
    
    count = 0
    for r_idx, r in enumerate(rows[1:], start=1):
        if len(r) != len(headers):
            continue
            
        row_dict = {name: r[idx] for name, idx in header_map.items()}
        cod_cliente = clean_val(row_dict.get('COD_CLIENTE'))
        try:
            cliente, endereco = get_cliente_and_endereco_by_legacy_id(db, cod_cliente)
            if not cliente:
                continue
                
            cod_plano = clean_val(row_dict.get('COD_PLANO'))
            if not cod_plano:
                continue
                
            valor_str = clean_val(row_dict.get('VALOR_MENSALIDADE'))
            try:
                valor_mensal = float(valor_str) if valor_str else 0.0
            except:
                valor_mensal = 0.0
                
            # Verifica / cria plano
            servico = db.query(Servico).filter(
                Servico.empresa_id == EMPRESA_ID,
                Servico.codigo == cod_plano
            ).first()
            
            if not servico:
                if not dry_run:
                    servico = Servico(
                        empresa_id=EMPRESA_ID,
                        tipo=TipoServico.PLANO_INTERNET.value,
                        codigo=cod_plano,
                        descricao=f"Plano {cod_plano}",
                        cClass='99',
                        unidade_medida='UN',
                        valor_unitario=valor_mensal,
                        is_active=True,
                        download_speed=0.0,
                        upload_speed=0.0
                    )
                    db.add(servico)
                    db.flush()
                    print(f"Criado plano dinamicamente: Plano {cod_plano}")
                else:
                    print(f"Necessário criar plano dinamicamente: Plano {cod_plano}")
                    
            assigned_ip = clean_val(row_dict.get('IP'))
            router_id = None
            interface_id = None
            ip_class_id = None
            
            if assigned_ip:
                try:
                    ip_obj = ipaddress.IPv4Address(assigned_ip)
                    for net_map in networks_map:
                        if ip_obj in net_map['network']:
                            router_id = net_map['router_id']
                            interface_id = net_map['interface_id']
                            ip_class_id = net_map['ip_class_id']
                            break
                except:
                    pass
                    
            # Verifica se já existe o serviço contratado
            exists = db.query(ServicoContratado).filter(
                ServicoContratado.empresa_id == EMPRESA_ID,
                ServicoContratado.cliente_id == cliente.id,
                ServicoContratado.servico_id == (servico.id if servico else 1)
            ).first()
            
            dia_venc_str = clean_val(row_dict.get('DIA_VENCIMENTO'))
            dia_venc = 10
            if dia_venc_str:
                try:
                    dia_venc = int(float(dia_venc_str))
                except:
                    pass
                    
            contrato_num = clean_val(row_dict.get('CODIGO'))
            data_inst = parse_date_only(clean_val(row_dict.get('DATA_INSTALACAO')))
            
            mac = clean_val(row_dict.get('MAC'))
            login = clean_val(row_dict.get('LOGIN'))
            senha = clean_val(row_dict.get('SENHA'))
            
            # Método de autenticação
            # If the password is an IP address or username looks like an IP, it's IP_MAC
            is_ip_mac = False
            import re
            if senha and re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', senha.strip()):
                is_ip_mac = True
            elif login and re.match(r'^\d+\.\d+\.\d+\.\d+\.\d+$', login.strip()):
                is_ip_mac = True
                
            metodo = 'IP_MAC' if is_ip_mac else ('PPPOE' if login and senha else 'IP_MAC')
            
            if exists:
                if not dry_run:
                    exists.numero_contrato = contrato_num
                    exists.assigned_ip = assigned_ip
                    exists.mac_address = mac
                    exists.pppoe_username = login
                    exists.pppoe_password = senha
                    exists.metodo_autenticacao = metodo
                    exists.dia_vencimento = dia_venc
                    exists.dia_emissao = dia_venc
                    exists.bank_account_id = 6
                    exists.valor_unitario = valor_mensal
                    exists.tipo_conexao = TipoConexao.FIBRA
                    if data_inst:
                        exists.data_instalacao = data_inst
                        exists.d_contrato_ini = data_inst
                        exists.data_inicio_cobranca = data_inst
                        
                    if router_id:
                        exists.router_id = router_id
                        exists.interface_id = interface_id
                        exists.ip_class_id = ip_class_id
                    db.flush()
                count += 1
            else:
                if not dry_run:
                    servico_contratado = ServicoContratado(
                        empresa_id=EMPRESA_ID,
                        cliente_id=cliente.id,
                        servico_id=servico.id if servico else 1,
                        endereco_id=endereco.id if endereco else None,
                        router_id=router_id,
                        interface_id=interface_id,
                        ip_class_id=ip_class_id,
                        numero_contrato=contrato_num,
                        d_contrato_ini=data_inst,
                        data_instalacao=data_inst,
                        data_inicio_cobranca=data_inst,
                        valor_unitario=valor_mensal,
                        dia_emissao=dia_venc,
                        dia_vencimento=dia_venc,
                        metodo_autenticacao=metodo,
                        assigned_ip=assigned_ip,
                        mac_address=mac,
                        pppoe_username=login,
                        pppoe_password=senha,
                        bank_account_id=6,
                        tipo_conexao=TipoConexao.FIBRA,
                        auto_emit=True,
                        is_active=True,
                        status=StatusContrato.ATIVO
                    )
                    db.add(servico_contratado)
                    db.flush()
                count += 1
                
            if not dry_run and count % 500 == 0:
                db.commit()
                
        except Exception as e:
            if not dry_run:
                db.rollback()
            print(f"Erro ao processar login {cod_cliente}: {e}")
            traceback.print_exc()
            
    if not dry_run:
        db.commit()
    print(f"Logins processados: {count} (Modo Dry-Run: {dry_run})")
    return count

def process_financeiro(db, file_path, dry_run=True):
    print("\n--- Processando Financeiro ---")
    rows = parse_pronect_csv(file_path)
    if not rows or len(rows) < 2:
        print("Nenhum dado financeiro encontrado.")
        return 0
        
    headers = rows[0]
    header_map = {name: idx for idx, name in enumerate(headers)}
    
    count = 0
    for r_idx, r in enumerate(rows[1:], start=1):
        if len(r) != len(headers):
            continue
            
        row_dict = {name: r[idx] for name, idx in header_map.items()}
        cod_cliente = clean_val(row_dict.get('COD_CLIENTE'))
        cod_areceber = clean_val(row_dict.get('COD_ARECEBER'))
        
        if not cod_cliente or not cod_areceber:
            continue
            
        try:
            cliente, _ = get_cliente_and_endereco_by_legacy_id(db, cod_cliente)
            if not cliente:
                continue
                
            # Verifica se já existe Receivable
            exists = db.query(Receivable).filter(
                Receivable.empresa_id == EMPRESA_ID,
                Receivable.nosso_numero == cod_areceber
            ).first()
            
            if not exists:
                due_date = parse_datetime_val(clean_val(row_dict.get('DATA_VENCIMENTO')))
                if not due_date:
                    continue
                    
                issue_date = parse_datetime_val(clean_val(row_dict.get('DATA_ENTRADA'))) or datetime.now()
                paid_at = parse_datetime_val(clean_val(row_dict.get('DATA_PAGAMENTO')))
                
                amount = float(clean_val(row_dict.get('VALOR')) or 0.0)
                discount = float(clean_val(row_dict.get('DESCONTO')) or 0.0)
                paid_amount = float(clean_val(row_dict.get('VALOR_PAGO')) or 0.0) if paid_at else None
                
                # Bank Cobrança
                bc = clean_val(row_dict.get('BANCO_COBRANCA'))
                bank_name = 'SICOB'
                if bc == '001':
                    bank_name = 'BANCO_DO_BRASIL'
                elif bc == '756':
                    bank_name = 'SICOB'
                else:
                    bank_name = 'OUTRO'
                    
                status = 'PAID' if paid_at else 'PENDING'
                
                obs = clean_val(row_dict.get('OBS')) or ''
                
                # Try to map to ServicoContratado
                contrato = db.query(ServicoContratado).filter(
                    ServicoContratado.empresa_id == EMPRESA_ID,
                    ServicoContratado.cliente_id == cliente.id
                ).first()
                
                if not dry_run:
                    receivable = Receivable(
                        empresa_id=EMPRESA_ID,
                        cliente_id=cliente.id,
                        servico_contratado_id=contrato.id if contrato else None,
                        nosso_numero=cod_areceber,
                        issue_date=issue_date,
                        due_date=due_date,
                        amount=amount,
                        discount=discount,
                        paid_amount=paid_amount,
                        paid_at=paid_at,
                        status=status,
                        bank=bank_name,
                        tipo='BOLETO'
                    )
                    db.add(receivable)
                    db.flush()
                count += 1
                
            if not dry_run and count % 1000 == 0:
                db.commit()
                
        except Exception as e:
            if not dry_run:
                db.rollback()
            print(f"Erro ao processar financeiro {cod_areceber}: {e}")
            traceback.print_exc()
            
    if not dry_run:
        db.commit()
    print(f"Receivables processados: {count} (Modo Dry-Run: {dry_run})")
    return count

def process_os(db, file_path, dry_run=True):
    print("\n--- Processando OS ---")
    rows = parse_pronect_csv(file_path)
    if not rows or len(rows) < 2:
        print("Nenhum dado de OS encontrado.")
        return 0
        
    headers = rows[0]
    header_map = {name: idx for idx, name in enumerate(headers)}
    
    count = 0
    for r_idx, r in enumerate(rows[1:], start=1):
        if len(r) != len(headers):
            continue
            
        row_dict = {name: r[idx] for name, idx in header_map.items()}
        cod_cliente = clean_val(row_dict.get('COD_CLIENTE'))
        id_os = clean_val(row_dict.get('ID_OS'))
        
        if not cod_cliente or not id_os:
            continue
            
        try:
            cliente, _ = get_cliente_and_endereco_by_legacy_id(db, cod_cliente)
            if not cliente:
                continue
                
            data_cad = parse_datetime_val(clean_val(row_dict.get('DATA_CADASTRO')))
            if not data_cad:
                continue
                
            tipo_servico = clean_val(row_dict.get('TIPO_SERVICO')) or 'Geral'
            titulo = f"OS {id_os} - {tipo_servico}"
            
            # Check if OS already exists
            exists = db.query(Ticket).filter(
                Ticket.empresa_id == EMPRESA_ID,
                Ticket.cliente_id == cliente.id,
                Ticket.titulo == titulo
            ).first()
            
            if not exists:
                obs = clean_val(row_dict.get('OBS')) or 'Sem descrição'
                obs_conclusao = clean_val(row_dict.get('OBS_CONCLUSAO')) or ''
                
                data_conclusao = parse_datetime_val(clean_val(row_dict.get('DATA_CONCLUSAO')))
                status = StatusTicket.FECHADO if data_conclusao else StatusTicket.ABERTO
                
                # Get client's contract link if any
                contrato = db.query(ServicoContratado).filter(
                    ServicoContratado.empresa_id == EMPRESA_ID,
                    ServicoContratado.cliente_id == cliente.id
                ).first()
                
                if not dry_run:
                    ticket = Ticket(
                        empresa_id=EMPRESA_ID,
                        cliente_id=cliente.id,
                        contrato_id=contrato.id if contrato else None,
                        criado_por_id=1,  # Default User ID
                        titulo=titulo[:255],
                        descricao=obs,
                        status=status,
                        resolucao=obs_conclusao,
                        resolvido_em=data_conclusao,
                        prioridade=PrioridadeTicket.NORMAL,
                        categoria=CategoriaTicket.SUPORTE,
                        created_at=data_cad
                    )
                    db.add(ticket)
                    db.flush()
                count += 1
                
            if not dry_run and count % 500 == 0:
                db.commit()
                
        except Exception as e:
            if not dry_run:
                db.rollback()
            print(f"Erro ao processar OS {id_os}: {e}")
            traceback.print_exc()
            
    if not dry_run:
        db.commit()
    print(f"OS processadas: {count} (Modo Dry-Run: {dry_run})")
    return count

def main():
    db = SessionLocal()
    try:
        # Check if company ID 6 exists
        empresa = db.query(Empresa).filter(Empresa.id == EMPRESA_ID).first()
        if not empresa:
            print(f"Empresa ID {EMPRESA_ID} não encontrada no banco. Crie a empresa no painel antes de rodar.")
            sys.exit(1)
            
        dry_run = "--commit" not in sys.argv
        if dry_run:
            print("\n🚨 RUNNING IN DRY-RUN MODE - NO DATABASE WRITES WILL BE COMMITTED. Run with --commit to apply changes.\n")
        else:
            print("\n💾 RUNNING IN COMMIT MODE - WRITES WILL BE PERMANENTLY SAVED TO THE DATABASE.\n")
            
        base_dir = "/Users/orlando/Downloads/Pronect"
        
        # Process order: Clientes -> Logins -> Financeiro -> OS
        process_clientes(db, f"{base_dir}/Clientes.csv", dry_run)
        process_logins(db, f"{base_dir}/Logins.csv", dry_run)
        process_financeiro(db, f"{base_dir}/Financeiro.csv", dry_run)
        process_os(db, f"{base_dir}/OS.csv", dry_run)
        
        print("\nImportação concluída com sucesso!")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
