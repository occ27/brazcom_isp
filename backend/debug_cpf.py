from app.core.database import get_db

db = next(get_db())
try:
    from app.models.models import Cliente
    cliente = db.query(Cliente).filter(Cliente.id == 1).first()
    if cliente:
        print(f'CPF/CNPJ armazenado: "{cliente.cpf_cnpj}"')
        print(f'Tamanho: {len(cliente.cpf_cnpj)}')
        print(f'Somente dígitos: {cliente.cpf_cnpj.replace(".", "").replace("-", "")}')

    # Testar busca com formatação
    cliente_formatado = db.query(Cliente).filter(
        Cliente.empresa_id == 1,
        Cliente.cpf_cnpj == '688.672.719-20'
    ).first()
    print(f'\nBusca com formatação: {"Encontrado" if cliente_formatado else "Não encontrado"}')

    # Testar busca sem formatação
    cliente_limpo = db.query(Cliente).filter(
        Cliente.empresa_id == 1,
        Cliente.cpf_cnpj == '68867271920'
    ).first()
    print(f'Busca sem formatação: {"Encontrado" if cliente_limpo else "Não encontrado"}')

except Exception as e:
    print(f'Erro: {e}')
finally:
    db.close()