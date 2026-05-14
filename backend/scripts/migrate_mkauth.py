import csv
import os
import re
import sys
import hashlib
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from app.core.database import SessionLocal, engine
from app.models.models import (
    Empresa, Cliente, EmpresaCliente, EmpresaClienteEndereco,
    Receivable, Ticket, StatusTicket, PrioridadeTicket, CategoriaTicket,
    TipoPessoa, IndicadorIEDest, ServicoContratado, StatusContrato, TipoConexao, MetodoAutenticacao
)
from app.models.network import Router, IPPool, PPPProfile, RouterInterface, IPClass
from app.models.radius import RadiusUser
from app.models.servico_model import Servico, TipoServico

# Configurações
DATA_DIR = "/Users/orlando/Downloads/opt/mk-auth/dados/2405K1305WJpHxJZ"
EMPRESA_ID = 1
CUTOFF_YEARS = 2
CUTOFF_DATE = datetime.now() - timedelta(days=CUTOFF_YEARS * 365)

def clean_val(val):
    if not val or val == "\\N" or val == "NULL":
        return None
    return val

def parse_date(date_str):
    if not date_str or date_str == "\\N" or date_str == "0000-00-00 00:00:00" or date_str == "0000-00-00":
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None

def read_mk_file(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="latin1") as f:
        content = f.read()
    content = content.replace("\\\n", " ").replace("\\\r\n", " ")
    lines = content.splitlines()
    data = []
    for line in lines:
        if line.strip():
            data.append(line.split("\t"))
    return data

def generate_placeholder_ip(mk_id):
    h = int(hashlib.md5(str(mk_id).encode()).hexdigest(), 16)
    return f"10.255.{ (h >> 8) & 0xFF }.{ h & 0xFF }"

def migrate(dry_run=True):
    db = SessionLocal()
    if dry_run:
        print("\n[!] MODO DRY-RUN ATIVADO\n")
    
    stats = {"planos": 0, "routers": 0, "interfaces": 0, "pools": 0, "clientes": 0, "contratos": 0, "tickets": 0, "financeiro": 0}
    planos_objetos = {}
    routers_map = {}
    interface_map = {}
    pool_map = {}
    login_to_cliente_id = {}
    
    try:
        # 1. Planos
        rows = read_mk_file("sis_plano.txt")
        for row in rows:
            if len(row) < 3: continue
            nome = row[0]
            plano = db.query(Servico).filter(Servico.codigo == nome[:60], Servico.empresa_id == EMPRESA_ID).first()
            if not plano:
                plano = Servico(codigo=nome[:60], descricao=nome[:120], valor_unitario=float(clean_val(row[2]) or 0), tipo=TipoServico.PLANO_INTERNET.value, empresa_id=EMPRESA_ID, is_active=True)
                db.add(plano)
                db.flush()
                stats["planos"] += 1
            planos_objetos[nome] = plano

        # 2. Routers, Interfaces e Pools
        nas_rows = read_mk_file("nas.txt")
        for row in nas_rows:
            if len(row) < 17: continue
            mk_id, ip_nas = row[0], row[2]
            router = db.query(Router).filter(Router.ip == ip_nas, Router.empresa_id == EMPRESA_ID).first()
            if not router:
                router = Router(nome=row[3][:100], ip=ip_nas, usuario=row[16][:100], senha=row[14], tipo="Mikrotik", radius_secret=row[6], empresa_id=EMPRESA_ID)
                db.add(router)
                db.flush()
                stats["routers"] += 1
            routers_map[str(mk_id)] = router.id

        cl_rows = read_mk_file("sis_cliente.txt")
        for row in cl_rows:
            if len(row) < 120: continue
            mk_router_id = str(row[30])
            router_id = routers_map.get(mk_router_id)
            if not router_id and mk_router_id:
                p_name = f"Router MK {mk_router_id}"[:100]
                p_router = db.query(Router).filter(Router.nome == p_name, Router.empresa_id == EMPRESA_ID).first()
                if not p_router:
                    p_router = Router(nome=p_name, ip=generate_placeholder_ip(mk_router_id), usuario="admin", senha="password", tipo="Mikrotik", radius_secret="secret", empresa_id=EMPRESA_ID)
                    db.add(p_router)
                    db.flush()
                    stats["routers"] += 1
                router_id = p_router.id
                routers_map[mk_router_id] = router_id
            
            if not router_id: continue
            if_name = clean_val(row[112]) or "ether1"
            if (router_id, if_name) not in interface_map:
                interface = db.query(RouterInterface).filter(RouterInterface.router_id == router_id, RouterInterface.nome == if_name).first()
                if not interface:
                    interface = RouterInterface(router_id=router_id, nome=if_name[:100], tipo="ethernet")
                    db.add(interface)
                    db.flush()
                    stats["interfaces"] += 1
                else:
                    interface_map[(router_id, if_name)] = interface.id
                interface_map[(router_id, if_name)] = interface.id
            
            pool_name = clean_val(row[118])
            if pool_name and pool_name not in pool_map:
                p_class = db.query(IPClass).filter(IPClass.nome == pool_name, IPClass.empresa_id == EMPRESA_ID).first()
                if not p_class:
                    p_class = IPClass(nome=pool_name[:100], rede="10.0.0.0/24", empresa_id=EMPRESA_ID)
                    db.add(p_class)
                    db.flush()
                    stats["pools"] += 1
                pool_map[pool_name] = p_class.id

        # 3. Clientes e Contratos
        for i, row in enumerate(cl_rows):
            if len(row) < 120: continue
            nome, login = clean_val(row[1]), clean_val(row[14])
            cpf_cnpj = re.sub(r"\D", "", row[8] or "")
            if not nome or not cpf_cnpj or not login: continue
            
            cliente = db.query(Cliente).filter(Cliente.cpf_cnpj == cpf_cnpj, Cliente.empresa_id == EMPRESA_ID).first()
            if not cliente:
                tipo_p = TipoPessoa.JURIDICA if len(cpf_cnpj) > 11 else TipoPessoa.FISICA
                cliente = Cliente(
                    nome_razao_social=nome[:255], 
                    cpf_cnpj=cpf_cnpj[:18], 
                    tipo_pessoa=tipo_p, 
                    empresa_id=EMPRESA_ID,
                    ind_ie_dest=IndicadorIEDest.NAO_CONTRIBUINTE
                )
                db.add(cliente)
                db.flush()
                assoc = EmpresaCliente(empresa_id=EMPRESA_ID, cliente_id=cliente.id)
                db.add(assoc)
                db.flush()
                db.add(EmpresaClienteEndereco(
                    empresa_cliente_id=assoc.id, endereco=(clean_val(row[3]) or "")[:255], numero=(clean_val(row[43]) or "S/N")[:20],
                    bairro=(clean_val(row[4]) or "")[:100], municipio=(clean_val(row[5]) or "")[:100], uf=(clean_val(row[7]) or "PR")[:2],
                    cep=(clean_val(row[6]) or "00000-000")[:10], is_principal=True
                ))
                stats["clientes"] += 1
            
            login_to_cliente_id[login] = cliente.id
            router_id = routers_map.get(str(row[30]))
            if_id = interface_map.get((router_id, clean_val(row[112]) or "ether1"))
            p_id = pool_map.get(clean_val(row[118]))
            
            # Verificar se contrato já existe para este cliente e número
            num_contrato = clean_val(row[40])
            exist_cont = db.query(ServicoContratado).filter(ServicoContratado.cliente_id == cliente.id, ServicoContratado.numero_contrato == num_contrato).first()
            if not exist_cont:
                status_ativado, bloqueado = clean_val(row[122]), clean_val(row[27])
                status_final = StatusContrato.CANCELADO if status_ativado == 'n' else (StatusContrato.SUSPENSO if bloqueado == 'sim' else StatusContrato.ATIVO)
                plano_obj = planos_objetos.get(row[32])
                
                db.add(ServicoContratado(
                    empresa_id=EMPRESA_ID, cliente_id=cliente.id, servico_id=plano_obj.id if plano_obj else 1,
                    valor_unitario=plano_obj.valor_unitario if plano_obj else 0.0,
                    numero_contrato=num_contrato, dia_emissao=int(clean_val(row[19]) or 10),
                    dia_vencimento=int(clean_val(row[19]) or 10), status=status_final,
                    tipo_conexao=TipoConexao.FIBRA, metodo_autenticacao=MetodoAutenticacao.RADIUS,
                    router_id=router_id, interface_id=if_id, ip_class_id=p_id,
                    pppoe_username=login[:50], pppoe_password=clean_val(row[42]) or "123456",
                    endereco_instalacao=(f"{row[3]}, {row[43]} - {row[4]}")[:500], is_active=(status_ativado != 'n')
                ))
                stats["contratos"] += 1
            
            if not dry_run and i % 100 == 0: db.commit()

        # 4. Tickets (Idempotente)
        sup_rows = read_mk_file("sis_suporte.txt")
        for row in sup_rows:
            if len(row) < 10: continue
            login = row[9]
            if login in login_to_cliente_id:
                cl_id = login_to_cliente_id[login]
                titulo = row[2][:255]
                c_at = parse_date(row[3]) or datetime.now()
                
                # Check if ticket already exists
                exist_ticket = db.query(Ticket).filter(Ticket.cliente_id == cl_id, Ticket.titulo == titulo, Ticket.created_at == c_at).first()
                if not exist_ticket:
                    desc = (clean_val(row[42]) if len(row) > 42 else "Sem descrição") or "Sem descrição"
                    db.add(Ticket(
                        titulo=titulo, descricao=desc,
                        status=StatusTicket.RESOLVIDO if row[6] == "fechado" else StatusTicket.ABERTO,
                        created_at=c_at, empresa_id=EMPRESA_ID, cliente_id=cl_id, criado_por_id=1
                    ))
                    stats["tickets"] += 1

        # 5. Financeiro (Idempotente)
        fin_rows = read_mk_file("sis_lanc.txt")
        for row in fin_rows:
            if len(row) < 20: continue
            venc, pag = parse_date(row[1]), parse_date(row[3])
            if not (venc or pag) or (pag or venc) < CUTOFF_DATE: continue
            if row[7] in login_to_cliente_id:
                nosso_num = row[2][:100]
                cl_id = login_to_cliente_id[row[7]]
                
                # Check if receivable exists
                exist_rec = db.query(Receivable).filter(Receivable.cliente_id == cl_id, Receivable.nosso_numero == nosso_num).first()
                if not exist_rec:
                    db.add(Receivable(
                        amount=float(clean_val(row[18]) or 0), due_date=venc or datetime.now(), paid_at=pag,
                        status="PAID" if row[6] == "pago" else "PENDING", nosso_numero=nosso_num,
                        empresa_id=EMPRESA_ID, cliente_id=cl_id, bank="SICREDI"
                    ))
                    stats["financeiro"] += 1

        if not dry_run:
            db.commit()
            print("\n[OK] Migração IDEMPOTENTE COMPLETA concluída!")
        else:
            db.rollback()
            print("\n--- RELATÓRIO DE PREVISÃO ---")
            for k, v in stats.items(): print(f"{k.capitalize()}: {v}")

    except Exception as e:
        db.rollback()
        print(f"\n[ERRO] {e}")
        import traceback; traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    migrate(dry_run="--commit" not in sys.argv)
