import sys
import os
import xml.etree.ElementTree as ET
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

EMPRESA_ID = 5
NAMESPACES = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}

def parse_xml_spreadsheet(file_path):
    """
    Parses an XML Spreadsheet 2003 and yields rows as lists of strings.
    """
    print(f"Parsing {file_path}...")
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Find all Worksheets
        for worksheet in root.findall('ss:Worksheet', NAMESPACES):
            table = worksheet.find('ss:Table', NAMESPACES)
            if table is None:
                continue
            
            rows = table.findall('ss:Row', NAMESPACES)
            if not rows:
                continue
            
            # Read header
            header_cells = rows[0].findall('ss:Cell', NAMESPACES)
            headers = []
            for cell in header_cells:
                data = cell.find('ss:Data', NAMESPACES)
                headers.append(data.text if data is not None else "")
                
            print(f"  Found headers: {headers}")
            
            # Yield data
            for row in rows[1:]:
                cells = row.findall('ss:Cell', NAMESPACES)
                row_data = {}
                current_col = 0
                for cell in cells:
                    index_attr = cell.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
                    if index_attr:
                        current_col = int(index_attr) - 1
                    
                    data = cell.find('ss:Data', NAMESPACES)
                    val = data.text if data is not None and data.text else ""
                    if current_col < len(headers):
                        row_data[headers[current_col]] = val
                    current_col += 1
                
                yield row_data
                
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        traceback.print_exc()

def normalize_cod(cod):
    """
    Normaliza COD_CLIENTE/COD_ARECEBER removendo separadores de milhar (ponto)
    que o Altarede usa em campos numéricos (ex: '1.152' -> '1152').
    """
    if not cod:
        return cod
    # Se parecer um número com ponto como separador de milhar, remove os pontos
    # Ex: '1.152' -> '1152', '58.340' -> '58340'
    # Mas preserva decimais reais como '10.5'
    cleaned = cod.strip()
    parts = cleaned.split('.')
    if len(parts) > 1 and all(p.isdigit() for p in parts):
        return ''.join(parts)
    return cleaned

def get_cliente_and_endereco_by_legacy_id(db, cod_cliente_raw):
    if not cod_cliente_raw:
        return None, None

    # Tenta com o valor original e com o valor normalizado
    variants = list(dict.fromkeys([cod_cliente_raw, normalize_cod(cod_cliente_raw)]))

    for cod in variants:
        endereco = db.query(EmpresaClienteEndereco).join(EmpresaCliente).filter(
            EmpresaCliente.empresa_id == EMPRESA_ID,
            EmpresaClienteEndereco.descricao == cod
        ).first()
        if endereco:
            cliente = db.query(Cliente).filter(Cliente.id == endereco.empresa_cliente.cliente_id).first()
            return cliente, endereco

        # Fallback to Cliente.idOutros
        cliente = db.query(Cliente).filter(Cliente.empresa_id == EMPRESA_ID, Cliente.idOutros == cod).first()
        if cliente:
            return cliente, None

    return None, None

def process_planos(db, file_path):
    print("\n--- Processando Planos ---")
    count = 0
    for row in parse_xml_spreadsheet(file_path):
        cod_plano = row.get('COD_PLANO')
        if not cod_plano:
            continue
            
        try:
            servico = db.query(Servico).filter(Servico.empresa_id == EMPRESA_ID, Servico.codigo == cod_plano).first()
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
                count += 1
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error row Plano {cod_plano}: {e}")
            
    print(f"Planos importados: {count}")

def process_clientes(db, file_path):
    print("\n--- Processando Clientes ---")
    count = 0
    for row in parse_xml_spreadsheet(file_path):
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
                cliente = db.query(Cliente).filter(
                    Cliente.empresa_id == EMPRESA_ID, 
                    Cliente.cpf_cnpj == cpf_cnpj
                ).first()
                
            if not cliente:
                cliente = db.query(Cliente).filter(
                    Cliente.empresa_id == EMPRESA_ID, 
                    Cliente.idOutros == cod_cliente
                ).first()
                
            if not cliente:
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
                db.flush()
                
            emp_cli = db.query(EmpresaCliente).filter(
                EmpresaCliente.empresa_id == EMPRESA_ID,
                EmpresaCliente.cliente_id == cliente.id
            ).first()
            
            if not emp_cli:
                emp_cli = EmpresaCliente(
                    empresa_id=EMPRESA_ID,
                    cliente_id=cliente.id,
                    is_active=cliente.is_active
                )
                db.add(emp_cli)
                db.flush()
                
            # Verifica se já importou este endereço/cod_cliente
            endereco_exists = db.query(EmpresaClienteEndereco).filter(
                EmpresaClienteEndereco.empresa_cliente_id == emp_cli.id,
                EmpresaClienteEndereco.descricao == cod_cliente
            ).first()
            
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
                count += 1
                
            if count % 1000 == 0:
                db.commit()
                
        except Exception as e:
            db.rollback()
            print(f"Error row Cliente {cod_cliente}: {e}")
            
    db.commit()
    print(f"Clientes/Endereços importados: {count}")

def process_logins(db, file_path):
    print("\n--- Processando Logins (ServicoContratado) ---")
    
    # 1. Pré-carrega apenas as classes de IP dos roteadores da EMPRESA_ID
    networks_map = []
    
    from app.models.network import Router as RouterModel
    
    # Busca apenas as interfaces cujos roteadores pertencem à EMPRESA_ID
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
    if networks_map:
        for nm in networks_map:
            print(f"  Rede: {nm['network']} -> router_id={nm['router_id']}, interface_id={nm['interface_id']}")

    count = 0
    for row in parse_xml_spreadsheet(file_path):
        cod_cliente = row.get('COD_CLIENTE')
        try:
            cliente, endereco = get_cliente_and_endereco_by_legacy_id(db, cod_cliente)
            if not cliente:
                continue
                
            cod_plano = row.get('COD_PLANO')
            servico = None
            if cod_plano:
                servico = db.query(Servico).filter(Servico.empresa_id == EMPRESA_ID, Servico.codigo == cod_plano).first()
                
            if not servico:
                continue
                
            # Verifica o IP e associa ao Router
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
                
            # check if already exists by MAC, login, or simply cliente + servico + endereco
            exists = db.query(ServicoContratado).filter(
                ServicoContratado.empresa_id == EMPRESA_ID,
                ServicoContratado.cliente_id == cliente.id,
                ServicoContratado.servico_id == servico.id,
                ServicoContratado.endereco_id == (endereco.id if endereco else None)
            ).first()
            
            if exists:
                # Update existing
                exists.metodo_autenticacao = 'IP_MAC'
                exists.assigned_ip = assigned_ip
                exists.mac_address = row.get('MAC')
                # Para IP_MAC, o Altarede armazenava o IP no campo LOGIN — não são credenciais PPPoE
                exists.pppoe_username = None
                exists.pppoe_password = None

                # Número do contrato legado (CODIGO do Altarede)
                codigo_legado = row.get('CODIGO', '').strip()
                if codigo_legado and not exists.numero_contrato:
                    exists.numero_contrato = codigo_legado

                # Data de instalação / início do contrato
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

                # Se encontrou o mapeamento de rede, atualiza também
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

                # Número do contrato legado (CODIGO do Altarede)
                codigo_legado = normalize_cod(row.get('CODIGO', '').strip()) or None

                # Data de instalação / início do contrato
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
                    endereco_id=endereco.id if endereco else None,
                    router_id=router_id,
                    interface_id=interface_id,
                    ip_class_id=ip_class_id,
                    numero_contrato=codigo_legado,
                    d_contrato_ini=data_inst,
                    data_instalacao=data_inst,
                    data_inicio_cobranca=data_inst,
                    # d_contrato_fim não existe no Altarede
                    valor_unitario=servico.valor_unitario,
                    dia_emissao=dia_venc,
                    dia_vencimento=dia_venc,
                    metodo_autenticacao='IP_MAC',
                    assigned_ip=assigned_ip,
                    mac_address=row.get('MAC'),
                    # Para IP_MAC, o Altarede armazenava o IP no campo LOGIN — não são credenciais PPPoE
                    pppoe_username=None,
                    pppoe_password=None,
                    auto_emit=True,
                    is_active=True
                )
                db.add(servico_contratado)
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
    count = 0
    for row in parse_xml_spreadsheet(file_path):
        cod_cliente = row.get('COD_CLIENTE')
        try:
            cliente, _ = get_cliente_and_endereco_by_legacy_id(db, cod_cliente)
            if not cliente:
                continue
                
            cod_areceber = row.get('COD_ARECEBER')
            if not cod_areceber:
                continue
                
            exists = db.query(Receivable).filter(
                Receivable.empresa_id == EMPRESA_ID,
                Receivable.nosso_numero == cod_areceber
            ).first()
            
            if not exists:
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
                    paid_at = datetime.strptime(data_pagamento_str[:10], '%Y-%m-%d')
                    status = 'PAID'
                    
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
    count = 0
    for row in parse_xml_spreadsheet(file_path):
        cod_cliente = row.get('COD_CLIENTE')
        try:
            cliente, _ = get_cliente_and_endereco_by_legacy_id(db, cod_cliente)
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
                resolvido_em = datetime.strptime(data_conclusao_str[:10], '%Y-%m-%d')
                status = StatusTicket.FECHADO
                
            obs = row.get('OBS', 'Sem descrição')
            obs_conclusao = row.get('OBS_CONCLUSAO', '')
            user_id = 1 
            
            titulo_os = f"OS {id_os} - {row.get('TIPO_SERVICO', 'Geral')}"
            
            exists_os = db.query(Ticket).filter(
                Ticket.empresa_id == EMPRESA_ID,
                Ticket.cliente_id == cliente.id,
                Ticket.titulo == titulo_os
            ).first()
            
            if not exists_os:
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
            print(f"Empresa ID {EMPRESA_ID} não encontrada. Criando empresa padrão ID 5.")
            empresa = Empresa(id=EMPRESA_ID, razao_social="Empresa Migrada", cnpj="00000000000000", endereco="Rua A", numero="1", bairro="Centro", municipio="BH", uf="MG", codigo_ibge="0000000", cep="00000000", email="contato@empresa.com", user_id=1)
            db.add(empresa)
            db.commit()

        base_dir = "/Users/orlando/python/FastAPI/brazcom_isp/Alpha"
        
        process_planos(db, f"{base_dir}/Planos.xls")
        process_clientes(db, f"{base_dir}/Clientes.xls")
        process_logins(db, f"{base_dir}/Logins.xls")
        process_financeiro(db, f"{base_dir}/Financeiro.xls")
        process_financeiro(db, f"{base_dir}/Carnês.xls")
        process_os(db, f"{base_dir}/OS.xls")

        print("Importação concluída com sucesso!")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
