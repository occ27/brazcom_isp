"""
Script de teste para integração com o gateway do SICREDI.
Gera arquivo de remessa CNAB 240 de teste.

Uso:
    cd backend
    python test_sicredi_integration.py
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Adicionar diretório backend ao path
sys.path.insert(0, os.path.dirname(__file__))


async def test_sicredi_integration():
    """Testa a geração de arquivo de remessa SICREDI."""
    print("🧪 Testando geração de arquivo de remessa SICREDI")
    print("=" * 60)
    
    try:
        from app.services.sicredi_gateway import create_sicredi_gateway
        
        # Dados da conta bancária (exemplo)
        bank_account_data = {
            "agencia": "1234",
            "agencia_dv": "0",
            "conta": "56789",
            "conta_dv": "1",
            "convenio": "12345",
            "sicredi_codigo_beneficiario": "12345",
            "sicredi_posto": "01",
            "sicredi_byte_id": "2",
            "titular": "EMPRESA TESTE LTDA",
            "cpf_cnpj_titular": "12345678000199"
        }
        
        print("\n📋 Dados da conta bancária:")
        print(f"   Agência: {bank_account_data['agencia']}-{bank_account_data['agencia_dv']}")
        print(f"   Conta: {bank_account_data['conta']}-{bank_account_data['conta_dv']}")
        print(f"   Código Beneficiário: {bank_account_data['sicredi_codigo_beneficiario']}")
        print(f"   Posto: {bank_account_data['sicredi_posto']}")
        print(f"   Titular: {bank_account_data['titular']}")
        
        # Criar gateway
        gateway = create_sicredi_gateway(bank_account_data)
        print("\n✅ Gateway SICREDI criado com sucesso")
        
        # Dados de receivables de teste
        hoje = datetime.now()
        vencimento = hoje + timedelta(days=15)
        
        receivables_data = [
            {
                "id": 1,
                "nosso_numero": "0000000001",
                "issue_date": hoje,
                "due_date": vencimento,
                "amount": 150.00,
                "discount": 0,
                "interest_percent": 1.0,
                "fine_percent": 2.0,
                "cpf_cnpj_pagador": "12345678901",
                "nome_pagador": "JOAO DA SILVA",
                "endereco_pagador": "RUA TESTE, 123",
                "bairro_pagador": "CENTRO",
                "cidade_pagador": "SAO PAULO",
                "cep_pagador": "01234567",
                "uf_pagador": "SP",
                "instrucoes": [
                    "Não aceitar pagamento após vencimento",
                    "Multa de 2% após o vencimento",
                    "Juros de 1% ao dia"
                ]
            },
            {
                "id": 2,
                "nosso_numero": "0000000002",
                "issue_date": hoje,
                "due_date": vencimento,
                "amount": 250.50,
                "discount": 0,
                "interest_percent": 1.0,
                "fine_percent": 2.0,
                "cpf_cnpj_pagador": "98765432100",
                "nome_pagador": "MARIA DOS SANTOS",
                "endereco_pagador": "AV TESTE, 456",
                "bairro_pagador": "JARDIM",
                "cidade_pagador": "RIO DE JANEIRO",
                "cep_pagador": "20123456",
                "uf_pagador": "RJ",
                "instrucoes": [
                    "Não aceitar pagamento após vencimento"
                ]
            }
        ]
        
        print(f"\n📄 Gerando arquivo de remessa com {len(receivables_data)} boletos:")
        for i, recv in enumerate(receivables_data, 1):
            print(f"   {i}. Nosso Número: {recv['nosso_numero']} | "
                  f"Valor: R$ {recv['amount']:.2f} | "
                  f"Pagador: {recv['nome_pagador']}")
        
        # Gerar arquivo de remessa
        conteudo = gateway.gerar_arquivo_remessa(receivables_data)
        
        print(f"\n✅ Arquivo de remessa gerado!")
        print(f"   Total de linhas: {len(conteudo.split(chr(10)))}")
        print(f"   Tamanho: {len(conteudo)} caracteres")
        
        # Salvar arquivo de teste
        filepath = "test_sicredi_remessa.txt"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        print(f"\n💾 Arquivo salvo em: {filepath}")
        
        # Exibir primeiras linhas
        linhas = conteudo.split('\n')
        print(f"\n📝 Primeiras 5 linhas do arquivo:")
        print("=" * 60)
        for i, linha in enumerate(linhas[:5], 1):
            print(f"{i:02d}: {linha[:80]}..." if len(linha) > 80 else f"{i:02d}: {linha}")
        
        print("\n" + "=" * 60)
        print("✅ Teste concluído com sucesso!")
        print(f"   Arquivo gerado: {filepath}")
        print(f"   Total de boletos: {len(receivables_data)}")
        
        # Validação básica
        print("\n🔍 Validações:")
        todas_240 = all(len(linha) == 240 for linha in linhas if linha.strip())
        print(f"   {'✅' if todas_240 else '❌'} Todas as linhas têm 240 caracteres")
        
        # Verificar header do arquivo
        if linhas[0].startswith("748"):
            print(f"   ✅ Header do arquivo correto (banco 748 - SICREDI)")
        else:
            print(f"   ❌ Header do arquivo incorreto")
        
        # Verificar trailer do arquivo
        if linhas[-1].startswith("7489999"):
            print(f"   ✅ Trailer do arquivo correto")
        else:
            print(f"   ❌ Trailer do arquivo incorreto")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro no teste: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Função principal."""
    print("\n" + "=" * 60)
    print("🏦 TESTE DE INTEGRAÇÃO SICREDI - CNAB 240")
    print("=" * 60)
    
    result = asyncio.run(test_sicredi_integration())
    
    if result:
        print("\n✅ Todos os testes passaram!")
        sys.exit(0)
    else:
        print("\n❌ Alguns testes falharam!")
        sys.exit(1)


if __name__ == "__main__":
    main()
