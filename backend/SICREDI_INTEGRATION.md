# Integração SICREDI - CNAB 240

## Visão Geral

Este módulo implementa a geração de arquivos de remessa no padrão CNAB 240 para o banco SICREDI (código 748), permitindo o registro de boletos bancários.

## Diferenças entre SICOOB e SICREDI

### SICOOB
- **Tipo**: API REST online
- **Autenticação**: Client ID + Access Token
- **Registro**: Imediato via API
- **Retorno**: Dados do boleto (código de barras, linha digitável) em tempo real

### SICREDI
- **Tipo**: Arquivo de remessa CNAB 240
- **Autenticação**: Código do beneficiário, posto e agência/conta
- **Registro**: Via arquivo enviado ao banco
- **Retorno**: Processamento assíncrono pelo banco

## Configuração de Conta Bancária SICREDI

Para configurar uma conta SICREDI, você precisa dos seguintes dados:

```json
{
  "bank": "SICREDI",
  "codigo_banco": "748",
  "agencia": "1234",
  "agencia_dv": "0",
  "conta": "56789",
  "conta_dv": "1",
  "titular": "NOME DA EMPRESA LTDA",
  "cpf_cnpj_titular": "12345678000199",
  "carteira": "1",
  "convenio": "12345",
  "sicredi_codigo_beneficiario": "12345",
  "sicredi_posto": "01",
  "sicredi_byte_id": "2",
  "multa_atraso_percentual": 2.0,
  "juros_atraso_percentual": 1.0
}
```

### Campos Específicos do SICREDI

- **sicredi_codigo_beneficiario**: Código do beneficiário fornecido pelo banco (5 dígitos)
- **sicredi_posto**: Posto de atendimento (2 dígitos, geralmente "01")
- **sicredi_byte_id**: Byte de identificação (1 dígito, geralmente "2")

## Fluxo de Trabalho

### 1. Criar Receivables (Boletos)

```python
from app.services.receivable_service import generate_receivables_for_company

# Gerar receivables para uma empresa
receivables = generate_receivables_for_company(
    db=db,
    empresa_id=1,
    target_date=date.today()
)
```

### 2. Registrar Boletos

Ao criar um receivable com conta bancária SICREDI, o sistema automaticamente:

1. Gera o "nosso número" sequencial
2. Marca o boleto como `PENDING_REMITTANCE` (pendente de remessa)
3. Cria um snapshot dos dados da conta bancária

```python
from app.services.billing_service import BillingService

# Registrar boleto (marca como pendente de remessa)
await BillingService.register_receivable_with_bank(db, receivable)
```

### 3. Gerar Arquivo de Remessa

Para gerar o arquivo CNAB 240 com os boletos pendentes:

**Via API:**
```bash
POST /empresas/{empresa_id}/bank-accounts/{bank_account_id}/generate-sicredi-remittance
```

**Via código:**
```python
from app.services.billing_service import BillingService

filepath = BillingService.generate_sicredi_remittance_file(
    db=db,
    empresa_id=1,
    bank_account_id=5,
    receivable_ids=[1, 2, 3]  # Opcional: IDs específicos
)
```

### 4. Enviar Arquivo ao Banco

O arquivo gerado deve ser enviado ao banco SICREDI através do canal apropriado:

- Internet Banking
- Sistema próprio do banco
- Integração EDI (se disponível)

### 5. Processar Retorno (Futuro)

O banco retorna um arquivo de retorno CNAB 240 com o status dos boletos:

- Boletos registrados com sucesso
- Código de barras e linha digitável
- Erros de registro

> **Nota**: A funcionalidade de processamento de arquivo de retorno ainda não está implementada.

## Estrutura do Arquivo CNAB 240

O arquivo gerado segue o layout oficial do SICREDI:

```
Header do Arquivo (1 linha)
  ├─ Header do Lote (1 linha)
  ├─ Segmento P - Boleto 1 (1 linha)
  ├─ Segmento Q - Sacado 1 (1 linha)
  ├─ Segmento R - Multa/Juros 1 (1 linha)
  ├─ Segmento P - Boleto 2 (1 linha)
  ├─ Segmento Q - Sacado 2 (1 linha)
  ├─ Segmento R - Multa/Juros 2 (1 linha)
  ├─ ...
  ├─ Trailer do Lote (1 linha)
Trailer do Arquivo (1 linha)
```

Cada linha possui exatamente **240 caracteres**.

### Segmentos

#### Segmento P
Contém os dados principais do boleto:
- Nosso número
- Valor
- Data de vencimento
- Data de emissão
- Código de juros e multa

#### Segmento Q
Contém os dados do sacado (pagador):
- CPF/CNPJ
- Nome
- Endereço completo

#### Segmento R
Contém informações adicionais:
- Multa
- Mensagens/instruções
- Descontos adicionais

## Teste

Para testar a geração de arquivo de remessa:

```bash
cd backend
python test_sicredi_integration.py
```

Isso gerará um arquivo `test_sicredi_remessa.txt` com boletos de teste.

## API Endpoints

### Listar Contas Bancárias
```
GET /empresas/{empresa_id}/bank-accounts
```

### Criar Conta Bancária SICREDI
```
POST /empresas/{empresa_id}/bank-accounts
Content-Type: application/json

{
  "bank": "SICREDI",
  "agencia": "1234",
  "conta": "56789",
  "sicredi_codigo_beneficiario": "12345",
  // ... outros campos
}
```

### Gerar Arquivo de Remessa
```
POST /empresas/{empresa_id}/bank-accounts/{bank_account_id}/generate-sicredi-remittance
Content-Type: application/json

{
  "receivable_ids": [1, 2, 3]  // Opcional
}
```

Retorno:
```json
{
  "status": "success",
  "message": "Arquivo de remessa SICREDI gerado com sucesso",
  "filepath": "uploads/remessas/sicredi_remessa_1_20251208_150030.txt",
  "download_url": "/uploads/remessas/sicredi_remessa_1_20251208_150030.txt"
}
```

## Migração de Banco de Dados

Para adicionar suporte ao SICREDI em um banco existente:

```bash
cd backend
alembic upgrade add_sicredi_support_20251208
```

Isso irá:
1. Adicionar "SICREDI" ao enum Bank
2. Adicionar campos `sicredi_codigo_beneficiario`, `sicredi_posto` e `sicredi_byte_id` à tabela `bank_accounts`

## Status dos Boletos

- **PENDING**: Boleto criado mas não processado
- **PENDING_REMITTANCE**: Boleto aguardando geração de arquivo de remessa
- **REMITTED**: Boleto incluído em arquivo de remessa
- **REGISTERED**: Boleto registrado com sucesso (após retorno do banco)
- **PAID**: Boleto pago
- **CANCELLED**: Boleto cancelado
- **REGISTRATION_FAILED**: Falha no registro

## Limitações Atuais

1. ❌ Processamento de arquivo de retorno não implementado
2. ❌ Baixa automática de boletos
3. ❌ Alteração de boletos após remessa
4. ⚠️ Suporte apenas para carteira simples (código 1)
5. ⚠️ Sem validação de DV do nosso número

## Próximos Passos

- [ ] Implementar processamento de arquivo de retorno CNAB 240
- [ ] Adicionar geração de arquivo de baixa de boletos
- [ ] Implementar alteração de vencimento via arquivo de remessa
- [ ] Validar DV do nosso número
- [ ] Suporte para outras carteiras do SICREDI
- [ ] Integração com Internet Banking via API (se disponível)

## Referências

- [Layout CNAB 240 SICREDI](https://developers.sicredi.com.br/)
- [Manual de Cobrança SICREDI](https://www.sicredi.com.br/)
- Documentação FEBRABAN CNAB 240

## Suporte

Para questões técnicas sobre a integração, consulte:
- Documentação oficial do SICREDI
- Gerente de conta do banco SICREDI
- Equipe de desenvolvimento
