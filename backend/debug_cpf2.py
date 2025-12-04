from app.core.database import get_db
from app.crud.crud_cliente import get_cliente_by_cpf_cnpj_and_empresa

db = next(get_db())
try:
    # Testar com CPF formatado
    cliente1 = get_cliente_by_cpf_cnpj_and_empresa(db, cpf_cnpj='688.672.719-20', empresa_id=1)
    print(f'Busca com CPF formatado: {"Encontrado" if cliente1 else "Não encontrado"}')
    if cliente1:
        print(f'Cliente: {cliente1.nome_razao_social}, Senha: {cliente1.password_hash is not None}')

    # Testar com CPF limpo
    cliente2 = get_cliente_by_cpf_cnpj_and_empresa(db, cpf_cnpj='68867271920', empresa_id=1)
    print(f'Busca com CPF limpo: {"Encontrado" if cliente2 else "Não encontrado"}')
    if cliente2:
        print(f'Cliente: {cliente2.nome_razao_social}, Senha: {cliente2.password_hash is not None}')

except Exception as e:
    print(f'Erro: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()