print('🎯 EXEMPLO: NFCom com Taxa de Instalação + Plano de Assinatura')
print('=' * 80)
print()

# Simulação dos dados de um contrato com taxa de instalação
contrato_exemplo = {
    'id': 123,
    'numero_contrato': 'CT-2025-001',
    'cliente_id': 456,
    'servico_id': 789,
    'valor_unitario': 99.90,  # Plano mensal
    'quantidade': 1,
    'taxa_instalacao': 150.00,  # Taxa única de instalação
    'taxa_instalacao_paga': False,
    'd_contrato_ini': '2025-11-25',
    'd_contrato_fim': '2026-11-25'
}

servico_exemplo = {
    'id': 789,
    'codigo': 'PLANO_FIBRA_50M',
    'descricao': 'Plano Fibra 50 Mega',
    'cClass': '010101',  # Código de classificação para telecom
    'cfop': '5301',  # CFOP para serviços de comunicação
    'aliquota_icms': 18.0,
    'aliquota_pis': 0.65,
    'aliquota_cofins': 3.0
}

print('📋 DADOS DO CONTRATO:')
print(f'   Número: {contrato_exemplo["numero_contrato"]}')
print(f'   Vigência: {contrato_exemplo["d_contrato_ini"]} a {contrato_exemplo["d_contrato_fim"]}')
print(f'   Plano: R$ {contrato_exemplo["valor_unitario"]:.2f}/mês')
print(f'   Taxa de Instalação: R$ {contrato_exemplo["taxa_instalacao"]:.2f} (não paga)')
print()

print('📄 ESTRUTURA DA NFCom GERADA:')
print()

nfcom = {
    'numero_nf': '000001',
    'serie': '1',
    'cliente_id': contrato_exemplo['cliente_id'],
    'numero_contrato': contrato_exemplo['numero_contrato'],
    'd_contrato_ini': contrato_exemplo['d_contrato_ini'],
    'd_contrato_fim': contrato_exemplo['d_contrato_fim'],
    'valor_total': contrato_exemplo['valor_unitario'] + contrato_exemplo['taxa_instalacao'],
    'itens': []
}

# Item 1: Plano de assinatura
nfcom['itens'].append({
    'numero_item': 1,
    'codigo_servico': servico_exemplo['codigo'],
    'descricao_servico': servico_exemplo['descricao'],
    'cClass': servico_exemplo['cClass'],
    'cfop': servico_exemplo['cfop'],
    'quantidade': contrato_exemplo['quantidade'],
    'valor_unitario': contrato_exemplo['valor_unitario'],
    'valor_total': contrato_exemplo['valor_unitario'],
    'aliquota_icms': servico_exemplo['aliquota_icms'],
    'aliquota_pis': servico_exemplo['aliquota_pis'],
    'aliquota_cofins': servico_exemplo['aliquota_cofins'],
    'tipo': 'SERVIÇO_RECORRENTE'
})

# Item 2: Taxa de instalação
nfcom['itens'].append({
    'numero_item': 2,
    'codigo_servico': 'TAXA_INSTALACAO',
    'descricao_servico': 'Taxa de Instalação de Serviço de Telecomunicações',
    'cClass': '010101',  # Mesmo código de classificação
    'cfop': '5307',  # CFOP específico para instalação
    'quantidade': 1,
    'valor_unitario': contrato_exemplo['taxa_instalacao'],
    'valor_total': contrato_exemplo['taxa_instalacao'],
    'aliquota_icms': 18.0,  # Mesma alíquota
    'aliquota_pis': 0.65,   # Mesmas alíquotas de PIS/COFINS
    'aliquota_cofins': 3.0,
    'tipo': 'SERVIÇO_UNICO'
})

print('🏢 CABEÇALHO DA NFCom:')
print(f'   Número: {nfcom["numero_nf"]}')
print(f'   Série: {nfcom["serie"]}')
print(f'   Contrato: {nfcom["numero_contrato"]}')
print(f'   Vigência: {nfcom["d_contrato_ini"]} a {nfcom["d_contrato_fim"]}')
print(f'   Valor Total: R$ {nfcom["valor_total"]:.2f}')
print()

print('📦 ITENS DA NFCom:')
for item in nfcom['itens']:
    print(f'   Item {item["numero_item"]}:')
    print(f'      Serviço: {item["codigo_servico"]} - {item["descricao_servico"]}')
    print(f'      CFOP: {item["cfop"]} | Classe: {item["cClass"]}')
    print(f'      Qtde: {item["quantidade"]} | Valor Unit.: R$ {item["valor_unitario"]:.2f}')
    print(f'      Valor Total: R$ {item["valor_total"]:.2f}')
    print(f'      ICMS: {item["aliquota_icms"]}% | PIS: {item["aliquota_pis"]}% | COFINS: {item["aliquota_cofins"]}%')
    print(f'      Tipo: {item["tipo"]}')
    print()

print('✅ RESULTADO:')
print('   • NFCom emitida com 2 itens distintos')
print('   • Taxa de instalação marcada como paga no contrato')
print('   • Atributos fiscais diferenciados por tipo de serviço')
print('   • Valor total = Plano + Taxa de Instalação')
print()
print('💡 VANTAGENS:')
print('   • Separação clara entre serviços recorrentes e únicos')
print('   • Tributação adequada para cada tipo de serviço')
print('   • Controle automático de taxas pagas')
print('   • Conformidade com legislação fiscal')