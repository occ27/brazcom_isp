import sys
import os
import traceback

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models.models import Cliente, EmpresaCliente, EmpresaClienteEndereco, Ticket

EMPRESA_ID = 6

def parse_pronect_csv(file_path):
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
                    current_row.append("".join(current_field))
                    rows.append(current_row)
                    current_row = []
                    current_field = []
                state = 'in_quotes'
                saw_delimiter = False
                i += 1
            else:
                if not saw_delimiter:
                    current_row.append("".join(current_field))
                    rows.append(current_row)
                    current_row = []
                    current_field = []
                current_field.append(char)
                state = 'in_unquotes'
                saw_delimiter = False
                i += 1
        elif state == 'in_quotes':
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

def clean_val(val):
    if not val or val == "\\N" or val == "NULL":
        return None
    return val.strip()

def fix_clientes_and_enderecos(db, base_dir):
    file_path = f"{base_dir}/Clientes.csv"
    print("Corrigindo Clientes e Endereços...")
    rows = parse_pronect_csv(file_path)
    headers = rows[0]
    header_map = {name: idx for idx, name in enumerate(headers)}
    
    count = 0
    for r in rows[1:]:
        if len(r) != len(headers):
            continue
        row_dict = {name: r[idx] for name, idx in header_map.items()}
        cod_cliente = clean_val(row_dict.get('COD_CLIENTE'))
        if not cod_cliente:
            continue
            
        nome = clean_val(row_dict.get('NOME')) or 'Sem Nome'
        logradouro = clean_val(row_dict.get('LOGRADOURO')) or ''
        end = clean_val(row_dict.get('ENDERECO')) or ''
        logradouro_end = f"{logradouro} {end}".strip()[:255] or 'Sem Endereço'
        bairro = clean_val(row_dict.get('BAIRRO')) or 'Centro'
        municipio = clean_val(row_dict.get('CIDADE')) or 'Cidade'
        
        # Encontra o cliente
        cliente = db.query(Cliente).filter(
            Cliente.empresa_id == EMPRESA_ID,
            Cliente.idOutros == cod_cliente
        ).first()
        
        if cliente:
            cliente.nome_razao_social = nome[:255]
            
            # Encontra endereco
            emp_cli = db.query(EmpresaCliente).filter(
                EmpresaCliente.empresa_id == EMPRESA_ID,
                EmpresaCliente.cliente_id == cliente.id
            ).first()
            if emp_cli:
                endereco = db.query(EmpresaClienteEndereco).filter(
                    EmpresaClienteEndereco.empresa_cliente_id == emp_cli.id,
                    EmpresaClienteEndereco.descricao == cod_cliente
                ).first()
                if endereco:
                    endereco.endereco = logradouro_end
                    endereco.bairro = bairro[:100]
                    endereco.municipio = municipio[:100]
            count += 1
            if count % 500 == 0:
                db.commit()
    db.commit()
    print(f"Clientes atualizados: {count}")

def fix_os(db, base_dir):
    file_path = f"{base_dir}/OS.csv"
    print("Corrigindo OS...")
    rows = parse_pronect_csv(file_path)
    headers = rows[0]
    header_map = {name: idx for idx, name in enumerate(headers)}
    
    count = 0
    for r in rows[1:]:
        if len(r) != len(headers):
            continue
        row_dict = {name: r[idx] for name, idx in header_map.items()}
        id_os = clean_val(row_dict.get('ID_OS'))
        if not id_os:
            continue
            
        tipo_servico = clean_val(row_dict.get('TIPO_SERVICO')) or 'Geral'
        titulo_correto = f"OS {id_os} - {tipo_servico}"
        obs = clean_val(row_dict.get('OBS')) or 'Sem descrição'
        obs_conclusao = clean_val(row_dict.get('OBS_CONCLUSAO')) or ''
        
        # Ticket title could have been imported with , so we search by ID starting pattern
        # Since we know `f"OS {id_os} -"` is the prefix:
        ticket = db.query(Ticket).filter(
            Ticket.empresa_id == EMPRESA_ID,
            Ticket.titulo.like(f"OS {id_os} -%")
        ).first()
        
        if ticket:
            ticket.titulo = titulo_correto[:255]
            ticket.descricao = obs
            ticket.resolucao = obs_conclusao
            count += 1
            if count % 500 == 0:
                db.commit()
    db.commit()
    print(f"OS atualizadas: {count}")

def main():
    db = SessionLocal()
    try:
        base_dir = "/Users/orlando/Downloads/Pronect"
        fix_clientes_and_enderecos(db, base_dir)
        fix_os(db, base_dir)
        print("Correção de encoding concluída com sucesso!")
    except Exception as e:
        db.rollback()
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
