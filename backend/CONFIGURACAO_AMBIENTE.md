# Configuração de Ambiente (Homologação vs Produção)

## Como Alternar Entre Ambientes

Para mudar entre **Homologação** e **Produção**, edite o arquivo `app/crud/crud_nfcom.py`:

```python
# Procure por esta linha no início do arquivo (após os imports):
AMBIENTE_PRODUCAO = False  # False = Homologação, True = Produção
```

### Para usar HOMOLOGAÇÃO:
```python
AMBIENTE_PRODUCAO = False
```

### Para usar PRODUÇÃO:
```python
AMBIENTE_PRODUCAO = True
```

## Diferenças Entre Ambientes

| Aspecto | Homologação | Produção |
|---------|-------------|----------|
| URL WebService | `https://nfcom-homologacao.svrs.rs.gov.br/ws/NFComRecepcao/NFComRecepcao.asmx` | `https://nfcom.svrs.rs.gov.br/ws/NFComRecepcao/NFComRecepcao.asmx` |
| URL QR Code (tentativa) | `https://dfe-portal.svrs.rs.gov.br/NFCom/NFCom-QRCODE.aspx` | `https://www.sefaz.rs.gov.br/NFCom/NFCom-QRCODE.aspx` |
| Parâmetro tpAmb | `2` | `1` |
| NFCom tem validade fiscal | ❌ Não | ✅ Sim |

## ⚠️ PROBLEMA CONHECIDO - URL QR Code em Homologação

### Situação Atual
O ambiente de **homologação** está rejeitando **todas** as URLs de QR Code testadas com erro:
```
cStat: 464
xMotivo: Rejeição: Endereço do site da UF da Consulta via QR Code diverge do previsto
```

### URLs Testadas (todas rejeitadas em homologação)
1. ❌ `https://www.fazenda.pr.gov.br/nfcom/qrcode`
2. ❌ `https://www.sped.fazenda.pr.gov.br/nfcom/qrcode`
3. ❌ `https://www.sefaz.rs.gov.br/NFCom/NFCom-QRCODE.aspx` (mesma de produção!)
4. ❌ `https://dfe-portal.svrs.rs.gov.br/NFCom/NFCom-QRCODE.aspx` (atual)

### O Que Sabemos
- ✅ **Produção FUNCIONA**: XML autorizado em produção usa `https://www.sefaz.rs.gov.br/NFCom/NFCom-QRCODE.aspx`
- 📖 **Documentação insuficiente**: Manual (leiaute_nfccom.txt linha 929) diz para consultar `http://dfe-portal.svrs.rs.gov.br/NFCom/` mas **não há lista publicada** de URLs
- 🔍 **Sem exemplos**: Não há XMLs de homologação autorizados disponíveis para comparação

### Recomendações

#### Opção 1: Contatar Suporte SEFAZ/SVRS (RECOMENDADO)
Entre em contato com o suporte técnico:
- **Email/Telefone**: PROCERGS ou Receita Estadual RS
- **Pergunta**: "Qual a URL correta do QR Code para NFCom em **HOMOLOGAÇÃO** para UF 41 (Paraná)?"
- **Referência**: Regra de validação G142 (cStat 464) do MOC NFCom

#### Opção 2: Testar Direto em Produção
Se tiver urgência e os demais erros foram corrigidos:
1. Altere `AMBIENTE_PRODUCAO = True` 
2. Configure certificado válido de produção
3. Teste com valores reais (a NFCom terá validade fiscal!)

## Outros Erros Já Corrigidos

✅ **cStat 599** - Assinatura inválida (whitespace)  
✅ **cStat 227** - cNF divergente na chave  
✅ **cStat 253** - DV inválido  
✅ **cStat 270** - Grupo gFat ausente  
✅ **cStat 215** - Erro de schema (pattern do QR Code)  

## Próximos Passos

1. **Se ficar bloqueado em homologação**: Contate SEFAZ ou teste em produção
2. **Quando autorizar**: Implemente eventos (cancelamento, substituição, etc.)
3. **Adicione testes unitários**: Validar geração de chave, XML, assinatura
4. **Configure backup**: Salvar XMLs autorizados em storage permanente

## Problema Conhecido: cStat 464 (URL QR Code)

### Situação Atual (Dezembro 2025)
- **Homologação**: Rejeita TODAS as URLs testadas com cStat 464
- **Produção**: Funciona com URLs específicas por estado

### URLs Testadas (todas rejeitadas em homologação):
1. `https://www.sefaz.rs.gov.br/NFCom/NFCom-QRCODE.aspx`
2. `https://dfe-portal.svrs.rs.gov.br/NFCom/NFCom-QRCODE.aspx`
3. `https://www.fazenda.pr.gov.br/nfcom/qrcode`

### URLs que Funcionam em Produção:
- **Paraná (UF 41)**: `https://www.fazenda.pr.gov.br/nfcom/qrcode`
- **Rio Grande do Sul (UF 43)**: `https://www.sefaz.rs.gov.br/NFCom/NFCom-QRCODE.aspx`

### Recomendações:
1. **Para desenvolvimento**: Use `AMBIENTE_PRODUCAO = True` (produção)
2. **Para homologação**: Contate SEFAZ/SVRS para obter URLs oficiais atualizadas
3. **Suporte**: Acesse https://dfe-portal.svrs.rs.gov.br/Nfcom para informações

## Suporte

- **Portal DFe SVRS**: https://dfe-portal.svrs.rs.gov.br/Nfcom
- **FAQ**: https://dfe-portal.svrs.rs.gov.br/Nfcom/Faq
- **Documentação**: Ver pasta `docs/` do projeto
