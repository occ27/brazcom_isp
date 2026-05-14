import csv
import os
import re
import sys
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.database import SessionLocal, engine
from app.models.models import (
    Empresa, Cliente, EmpresaCliente, EmpresaClienteEndereco,
    Receivable, Ticket, StatusTicket, PrioridadeTicket, CategoriaTicket,
    TipoPessoa, IndicadorIEDest, ServicoContratado, StatusContrato, TipoConexao, MetodoAutenticacao
)
from app.models.network import Router, IPPool, PPPProfile
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

def migrate(dry_run=True):
    db = SessionLocal()
    if dry_run:
        print("\n[!] MODO DRY-RUN ATIVADO\n")
    
    stats = {"planos": 0, "routers": 0, "clientes": 0, "contratos": 0, "tickets": 0, "financeiro": 0, "pulas": 0}
    planos_objetos = {}
    routers_map = {} # ID original MK (String) -> ID Brazcom (Int)
    login_to_cliente_id = {}
    
    try:
        # 1. Planos
        rows = read_mk_file("sis_plano.txt")
        for row in rows:
            if len(row) < 3: continue
            nome = row[0]
            plano = db.query(Servico).filter(Servico.codigo == nome[:60], Servico.empresa_id == EMPRESA_ID).first()
            if not plano:
                plano = Servico(
                    codigo=nome[:60], descricao=nome[:120],
                    valor_unitario=float(clean_val(row[2]) or 0),
                    tipo=TipoServico.PLANO_INTERNET.value,
                    cClass="0101010", unidade_medida="UN",
                    empresa_id=EMPRESA_ID, is_active=True
                )
                db.add(plano)
                db.flush()
                stats["planos"] += 1
            planos_objetos[nome] = plano

        # 2. Routers (NAS)
        rows = read_mk_file("nas.txt")
        for row in rows:
            if len(row) < 17: continue
            mk_id = row[0]
            ip_nas = row[2]
            router = db.query(Router).filter(Router.ip == ip_nas, Router.empresa_id == EMPRESA_ID).first()
            if not router:
                router = Router(
                    nome=row[3][:100], ip=ip_nas,
                    usuario=row[16][:100], senha=row[14],
                    tipo="Mikrotik", radius_secret=row[6],
                    empresa_id=EMPRESA_ID
                )
                db.add(router)
                db.flush()
                stats["routers"] += 1
            routers_map[str(mk_id)] = router.id

        # 3. Clientes e Contratos
        cl_rows = read_mk_file("sis_cliente.txt")
        for i, row in enumerate(cl_rows):
            if len(row) < 120: continue
            
            nome = clean_val(row[1])
            login = clean_val(row[14])
            cpf_cnpj = re.sub(r"\D", "", row[8] or "")
            if not nome or not cpf_cnpj or not login: continue
            
            # Verificar se cliente já existe (caso o banco não tenha sido limpo 100%)
            cliente = db.query(Cliente).filter(Cliente.cpf_cnpj == cpf_cnpj, Cliente.empresa_id == EMPRESA_ID).first()
            if not cliente:
                tipo_p = TipoPessoa.JURIDICA if len(cpf_cnpj) > 11 else TipoPessoa.FISICA
                cliente = Cliente(
                    nome_razao_social=nome[:255], cpf_cnpj=cpf_cnpj[:18],
                    tipo_pessoa=tipo_p, ind_ie_dest=IndicadorIEDest.NAO_CONTRIBUINTE,
                    empresa_id=EMPRESA_ID, is_active=True
                )
                db.add(cliente)
                db.flush()
                
                assoc = EmpresaCliente(empresa_id=EMPRESA_ID, cliente_id=cliente.id)
                db.add(assoc)
                db.flush()
                
                db.add(EmpresaClienteEndereco(
                    empresa_cliente_id=assoc.id,
                    endereco=(clean_val(row[3]) or "Nao informado")[:255],
                    numero=clean_val(row[43]) or "S/N",
                    bairro=(clean_val(row[4]) or "Nao informado")[:100],
                    municipio=(clean_val(row[5]) or "Nao informado")[:100],
                    uf=(clean_val(row[7]) or "PR")[:2],
                    cep=re.sub(r"\D", "", row[6] or "")[:9],
                    codigo_ibge=clean_val(row[114])
                ))
                stats["clientes"] += 1
            
            login_to_cliente_id[login] = cliente.id
            
            rad_pass = clean_val(row[42]) or "123456"
            db.add(RadiusUser(
                username=login[:100], password=rad_pass,
                ip_address=clean_val(row[22]), mac_address=clean_val(row[20]),
                empresa_id=EMPRESA_ID, cliente_id=cliente.id
            ))
            
            # Mapeamento do Router (NAS)
            mk_router_id = str(row[30]) # Coluna 'conta'
            router_id = routers_map.get(mk_router_id)
            
            if not router_id and mk_router_id:
                # Criar roteador placeholder para IDs não encontrados (ex: 1, 3)
                p_name = f"Roteador MK ID {mk_router_id}"
                p_router = db.query(Router).filter(Router.nome == p_name, Router.empresa_id == EMPRESA_ID).first()
                if not p_router:
                    p_router = Router(
                        nome=p_name, ip=f"10.255.{mk_router_id}.254", 
                        usuario="admin", senha="password",
                        tipo="Mikrotik", radius_secret="secret",
                        empresa_id=EMPRESA_ID
                    )
                    db.add(p_router)
                    db.flush()
                    stats["routers"] += 1
                router_id = p_router.id
                routers_map[mk_router_id] = router_id

            status_ativado = clean_val(row[122])
            bloqueado = clean_val(row[27])
            status_final = StatusContrato.CANCELADO if status_ativado == 'n' else (StatusContrato.SUSPENSO if bloqueado == 'sim' else StatusContrato.ATIVO)
            
            plano_obj = planos_objetos.get(row[32])
            
            # Dados de Provisionamento
            interface_name = clean_val(row[112]) # Coluna 113 (idx 112)
            pool_name = clean_val(row[118]) # Coluna 119 (idx 118)
            
            db.add(ServicoContratado(
                empresa_id=EMPRESA_ID, cliente_id=cliente.id,
                servico_id=plano_obj.id if plano_obj else 1,
                valor_unitario=plano_obj.valor_unitario if plano_obj else 0.0,
                numero_contrato=clean_val(row[40]),
                dia_emissao=int(clean_val(row[19]) or 10),
                dia_vencimento=int(clean_val(row[19]) or 10),
                status=status_final,
                tipo_conexao=TipoConexao.FIBRA,
                metodo_autenticacao=MetodoAutenticacao.RADIUS,
                router_id=router_id,
                assigned_ip=clean_val(row[22]),
                mac_address=clean_val(row[20]),
                pppoe_username=login[:50],
                pppoe_password=rad_pass[:50],
                coordenadas_gps=clean_val(row[80])[:50] if clean_val(row[80]) else None,
                is_active=(status_ativado != 'n'),
                auto_emit=True,
                # Observação: Interface e Pool no Brazcom costumam ser IDs. 
                # Como no MK é string, salvamos no campo extra ou log se necessário.
                # Para aparecer no campo 'Interface' da UI, precisamos que o router_id esteja setado.
            ))
            stats["contratos"] += 1
            
            if not dry_run and i % 100 == 0:
                db.commit()

        # 4. Suporte
        sup_rows = read_mk_file("sis_suporte.txt")
        for row in sup_rows:
            if len(row) < 10: continue
            login = row[9]
            if login in login_to_cliente_id:
                db.add(Ticket(
                    titulo=row[2][:255],
                    descricao=(clean_val(row[42]) if len(row) > 42 else "Sem descrição") or "Sem descrição",
                    status=StatusTicket.RESOLVIDO if row[6] == "fechado" else StatusTicket.ABERTO,
                    created_at=parse_date(row[3]) or func.now(),
                    empresa_id=EMPRESA_ID, cliente_id=login_to_cliente_id[login],
                    criado_por_id=1
                ))
                stats["tickets"] += 1

        # 5. Financeiro
        fin_rows = read_mk_file("sis_lanc.txt")
        for row in fin_rows:
            if len(row) < 20: continue
            venc, pag, emissao = parse_date(row[1]), parse_date(row[3]), parse_date(row[11])
            if not (venc or pag) or (pag or venc) < CUTOFF_DATE: continue
            login = row[7]
            if login in login_to_cliente_id:
                val_str = clean_val(row[18])
                val_ld = clean_val(row[17]) if len(row) > 17 else None
                db.add(Receivable(
                    amount=float(val_str or 0), due_date=venc or func.now(),
                    issue_date=emissao or func.now(), paid_at=pag,
                    status="PAID" if row[6] == "pago" else "PENDING",
                    nosso_numero=row[2][:100], linha_digitavel=val_ld[:200] if val_ld else None,
                    empresa_id=EMPRESA_ID, cliente_id=login_to_cliente_id[login],
                    bank="SICREDI"
                ))
                stats["financeiro"] += 1

        if not dry_run:
            db.commit()
            print("\n[OK] Migração DEFINITIVA concluída!")
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
    from sqlalchemy import func
    migrate(dry_run="--commit" not in sys.argv)
