#!/usr/bin/env python3
"""
Script detalhado para diagnosticar o erro 500 em produção
Execute este script dentro do container Docker: docker exec -it nfcom_backend python /app/diagnose_error.py
"""

import sys
import os
import traceback

# Adicionar o diretório atual ao path
sys.path.append('/app')

def test_database_connection():
    """Testa a conexão básica com o banco"""
    print("=== TESTANDO CONEXÃO COM BANCO ===")
    try:
        from app.core.database import get_db, engine
        print("✓ Importação do database OK")

        # Testar engine
        with engine.connect() as conn:
            result = conn.execute("SELECT 1 as test")
            row = result.fetchone()
            print(f"✓ Conexão com engine OK, teste: {row[0]}")

        # Testar session
        db = next(get_db())
        print("✓ Sessão do banco OK")
        db.close()
        return True
    except Exception as e:
        print(f"✗ Erro na conexão com banco: {e}")
        traceback.print_exc()
        return False

def test_crud_function():
    """Testa especificamente a função problemática"""
    print("\n=== TESTANDO FUNÇÃO CRUD PROBLEMÁTICA ===")
    try:
        from app.crud.crud_servico_contratado import get_servicos_contratados_by_cliente
        from app.core.database import get_db
        print("✓ Importação da função CRUD OK")

        db = next(get_db())
        print("✓ Sessão do banco obtida")

        # Testar com os parâmetros do erro
        cliente_id = 2979
        empresa_id = 25

        print(f"Executando: get_servicos_contratados_by_cliente(cliente_id={cliente_id}, empresa_id={empresa_id})")
        contratos = get_servicos_contratados_by_cliente(db, cliente_id=cliente_id, empresa_id=empresa_id)

        print(f"✓ Função executada com sucesso!")
        print(f"  - Tipo do retorno: {type(contratos)}")
        print(f"  - Número de contratos: {len(contratos) if contratos else 0}")

        if contratos:
            print(f"  - Primeiro contrato: {contratos[0]}")

        db.close()
        return True
    except Exception as e:
        print(f"✗ Erro na função CRUD: {e}")
        traceback.print_exc()
        return False

def test_data_integrity():
    """Verifica se os dados necessários existem"""
    print("\n=== VERIFICANDO INTEGRIDADE DOS DADOS ===")
    try:
        from app.core.database import get_db
        from app.models import models

        db = next(get_db())

        # Verificar cliente
        cliente = db.query(models.Cliente).filter(models.Cliente.id == 2979).first()
        if cliente:
            print(f"✓ Cliente 2979 encontrado: {cliente.nome_razao_social}")
        else:
            print("✗ Cliente 2979 NÃO encontrado")

        # Verificar empresa
        empresa = db.query(models.Empresa).filter(models.Empresa.id == 25).first()
        if empresa:
            print(f"✓ Empresa 25 encontrada: {empresa.razao_social}")
        else:
            print("✗ Empresa 25 NÃO encontrada")

        # Verificar contratos
        contratos = db.query(models.ServicoContratado).filter(
            models.ServicoContratado.cliente_id == 2979,
            models.ServicoContratado.empresa_id == 25,
            models.ServicoContratado.is_active == True
        ).all()

        print(f"✓ Encontrados {len(contratos)} contratos ativos")

        # Verificar serviços referenciados
        for contrato in contratos:
            servico = db.query(models.Servico).filter(models.Servico.id == contrato.servico_id).first()
            if servico:
                print(f"✓ Serviço {contrato.servico_id} encontrado: {servico.descricao}")
            else:
                print(f"✗ Serviço {contrato.servico_id} NÃO encontrado")

        db.close()
        return True
    except Exception as e:
        print(f"✗ Erro na verificação de dados: {e}")
        traceback.print_exc()
        return False

def test_route_logic():
    """Testa a lógica da rota completa"""
    print("\n=== TESTANDO LÓGICA COMPLETA DA ROTA ===")
    try:
        from app.core.database import get_db
        from app.crud import crud_empresa, crud_servico_contratado
        from app.models import models

        db = next(get_db())

        cliente_id = 2979
        empresa_id = 25

        # Simular as verificações da rota
        print("1. Verificando empresa...")
        db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
        if not db_empresa:
            print("✗ Empresa não encontrada")
            return False
        print("✓ Empresa encontrada")

        print("2. Executando query principal...")
        contratos = crud_servico_contratado.get_servicos_contratados_by_cliente(db, cliente_id=cliente_id, empresa_id=empresa_id)
        print(f"✓ Query executada, {len(contratos)} contratos retornados")

        print("3. Simulando verificação de permissões...")
        # Simular usuário (assumindo superuser para teste)
        user_empresas_ids = [empresa_id]  # Simular que usuário tem acesso
        for contrato in contratos:
            if contrato.get('empresa_id') not in user_empresas_ids:
                print(f"✗ Usuário sem permissão para contrato da empresa {contrato.get('empresa_id')}")
                return False
        print("✓ Verificações de permissão OK")

        db.close()
        return True
    except Exception as e:
        print(f"✗ Erro na lógica da rota: {e}")
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    print("Iniciando diagnóstico detalhado do erro 500...")
    print("=" * 60)

    results = []

    # Executar todos os testes
    results.append(("Conexão com banco", test_database_connection()))
    results.append(("Função CRUD", test_crud_function()))
    results.append(("Integridade dos dados", test_data_integrity()))
    results.append(("Lógica da rota", test_route_logic()))

    # Resumo
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES:")
    for test_name, success in results:
        status = "✓ PASSOU" if success else "✗ FALHOU"
        print(f"  {test_name}: {status}")

    # Conclusão
    all_passed = all(success for _, success in results)
    if all_passed:
        print("\n🎉 Todos os testes passaram! O problema pode estar em:")
        print("   - Configuração do FastAPI (middlewares, CORS, etc.)")
        print("   - Problemas de serialização JSON")
        print("   - Timeouts ou limites de recursos")
        print("   - Problemas específicos do ambiente de execução")
    else:
        print("\n❌ Alguns testes falharam. Verifique os erros acima.")

if __name__ == "__main__":
    main()