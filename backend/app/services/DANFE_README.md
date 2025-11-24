# DANFE-COM - Documento Auxiliar da NFCom

## Visão Geral

Este documento descreve o novo layout específico do DANFE-COM (Documento Auxiliar da Nota Fiscal de Serviços de Comunicação), desenvolvido para se diferenciar do layout padrão da NF-e e ser mais adequado aos serviços de telecomunicações.

## Principais Diferenças do Layout Anterior

### 1. **Design Específico para Telecomunicações**
- **Paleta de cores**: Azul telecom (#2b6cb0) ao invés do azul genérico
- **Fonte menor**: Otimização para melhor aproveitamento do espaço em A4
- **Margens reduzidas**: 10mm ao invés de 15mm para mais conteúdo

### 2. **Cabeçalho Compacto**
- Logo reduzida para 25x25mm (anteriormente 30x30mm)
- QR Code menor para 25x25mm
- Título mais compacto com quebra de linha otimizada
- Marca d'água de homologação mais sutil (fonte 60 ao invés de 70)

### 3. **Dados da Nota Fiscal**
- **Layout em 2 linhas**: Modelo/Série/Número/Página na primeira linha
- **Segunda linha**: Datas e tipos de emissão
- **Chave de acesso**: Mais proeminente com fonte maior
- **Cabeçalhos azuis claros** (#bee3f8) específicos para telecom

### 4. **Emitente e Destinatário**
- **Layout mais eficiente**: Melhor distribuição de espaço
- **4 colunas** para dados do emitente (Razão Social, CNPJ, Bairro, Insc. Estadual)
- **Destinatário simplificado**: Foco nos dados essenciais

### 5. **Serviços de Comunicação**
- **Cabeçalho específico**: "SERVIÇOS DE COMUNICAÇÃO PRESTADOS"
- **Coluna Código do Serviço**: Destacada e posicionada após Item
- **Larguras otimizadas**: Melhor distribuição para telecom
- **Fonte menor**: 7pt para mais informações visíveis

### 6. **Cálculo dos Impostos**
- **Seção renomeada**: "CÁLCULO DOS IMPOSTOS"
- **Layout dinâmico**: Mostra apenas tributos com valores > 0
- **ICMS, PIS, COFINS**: Tributos comuns em serviços de comunicação
- **Destaque no total**: Borda azul e fundo amarelo suave

### 7. **Dados de Cobrança**
- **Cabeçalho específico**: "DADOS DE COBRANÇA / FATURAMENTO"
- **Código de barras compacto**: Mostra apenas parte do código longo
- **Colunas otimizadas**: Melhor distribuição para telecom

### 8. **Rodapé Específico**
- **Fonte menor**: 6pt para mais informações
- **Informações adicionais**: Campo `nfcom.informacoes_adicionais` exibido quando presente
- **Protocolo de autorização**: Quando disponível

## Paleta de Cores

| Elemento | Cor | Código Hex |
|----------|-----|------------|
| Cabeçalhos de seção | Azul Telecom | #2b6cb0 |
| Fundo de cabeçalhos | Azul Claro | #bee3f8 |
| Texto principal | Preto | #000000 |
| Labels | Cinza Escuro | #4a5568 |
| Linhas alternadas | Cinza Muito Claro | #f7fafc |
| Destaque total | Amarelo Suave | #fef5e7 |
| Borda destaque | Azul Telecom | #2b6cb0 |

## Estrutura do Documento

```
┌─────────────────────────────────────────────────┐
│ LOGO │        DANFE-COM         │     QR      │
│      │ Documento Auxiliar da    │    CODE     │
│      │ Nota Fiscal de Serviços  │             │
│      │ de Comunicação           │             │
├─────────────────────────────────────────────────┤
│ MODELO SÉRIE NÚMERO PÁGINA                     │
│ DATA EMISSÃO DATA SAÍDA TIPO FINALIDADE        │
├─────────────────────────────────────────────────┤
│ CHAVE DE ACESSO: [44 dígitos]                  │
├─────────────────────────────────────────────────┤
│ EMITENTE                                        │
│ RAZÃO SOCIAL │ CNPJ │ ENDEREÇO │ INSC. EST.   │
│ [dados completos...]                           │
├─────────────────────────────────────────────────┤
│ DESTINATÁRIO / TOMADOR DO SERVIÇO              │
│ NOME │ CPF/CNPJ │ ENDEREÇO │ BAIRRO           │
│ [dados completos...]                           │
├─────────────────────────────────────────────────┤
│ SERVIÇOS DE COMUNICAÇÃO PRESTADOS              │
│ ITEM │ CÓDIGO │ DESCRIÇÃO │ UN │ QTD │ VL.UNIT│
│      │ SERVIÇO │           │    │     │        │
├─────────────────────────────────────────────────┤
│ CÁLCULO DOS IMPOSTOS                           │
│ ICMS │ PIS │ COFINS │ VALOR TOTAL              │
├─────────────────────────────────────────────────┤
│ DADOS DE COBRANÇA / FATURAMENTO (opcional)     │
│ NÚMERO │ VENCIMENTO │ VALOR │ CÓDIGO BARRAS   │
├─────────────────────────────────────────────────┤
│ Informações Adicionais: [texto]                │
│ Gerado em: [data/hora] Protocolo: [número]     │
└─────────────────────────────────────────────────┘
```

## Funcionalidades Especiais

### Ambiente de Homologação
- Marca d'água diagonal "SEM VALOR FISCAL"
- Alerta vermelho no cabeçalho
- Indicação no rodapé

### Tributos Dinâmicos
- Exibe apenas tributos com valores maiores que zero
- Ordem: ICMS → PIS → COFINS → Total
- Formatação brasileira (R$ #.###,##)

### Código de Barras
- Exibe versão compacta para códigos longos
- Formato: "1234567890...1234567890"

### Responsividade
- Layout otimizado para A4
- Fontes proporcionais
- Espaçamentos otimizados

## Campos Utilizados

### NFCom
- `numero_nf`, `serie`, `data_emissao`
- `tipo_emissao`, `finalidade_emissao`
- `chave_acesso`, `protocolo_autorizacao`
- `valor_icms`, `valor_pis`, `valor_cofins`, `valor_total`
- `informacoes_adicionais`

### Empresa
- `razao_social`, `cnpj`, `inscricao_estadual`
- `endereco`, `numero`, `bairro`, `municipio`, `uf`, `cep`
- `logo_url`, `ambiente_nfcom`

### Cliente
- `nome_razao_social`, `cpf_cnpj`

### NFComItem
- `codigo_servico`, `descricao_servico`
- `unidade_medida`, `quantidade`
- `valor_unitario`, `valor_total`

### Faturas (opcional)
- `numero_fatura`, `data_vencimento`, `valor_fatura`
- `codigo_barras`

## Considerações Técnicas

- **Biblioteca**: ReportLab 4.4.4
- **Formato**: PDF A4
- **Codificação**: UTF-8
- **Fonte**: Helvetica (padrão)
- **Resolução QR**: 25x25mm (versão 1, correção L)
- **Logo**: Até 25x25mm (redimensionado automaticamente)

## Manutenção

Para modificar o layout:
1. Edite `danfe_generator_new.py`
2. Teste as alterações
3. Copie para `danfe_generator.py` quando aprovado
4. Atualize este documento conforme necessário

## Compatibilidade

- Compatível com Python 3.8+
- Testado com FastAPI e SQLAlchemy
- Suporte a ambientes Windows/Linux
- Geração automática de QR Code
- Carregamento de logos PNG/JPG
   - Código de barras em fonte menor para caber na linha
   - Linhas alternadas para facilitar leitura

8. **Rodapé**
   - Data e hora de geração do DANFE
   - Protocolo de autorização (quando disponível)
   - Aviso de homologação repetido (se aplicável)

### Recursos Técnicos

#### Formatação Automática
- **CPF/CNPJ**: Detecta automaticamente o tamanho e formata corretamente
- **Valores Monetários**: R$ com separadores de milhar e 2 casas decimais
- **Datas**: Formato brasileiro (DD/MM/AAAA)
- **Chave de Acesso**: Fonte monoespaçada e centralizada

#### Logo da Empresa
- Carrega automaticamente de `empresa.logo_url`
- Redimensiona para 30x30mm mantendo proporções
- Se não houver logo, exibe placeholder "LOGO EMPRESA"
- Suporta PNG, JPG e outros formatos de imagem

#### QR Code
- Gerado automaticamente com a chave de acesso
- Tamanho 30x30mm para fácil leitura por smartphones
- Tratamento de erros caso não seja possível gerar

#### Homologação
- **Marca d'água diagonal**: "SEM VALOR FISCAL" e "HOMOLOGAÇÃO" em fonte grande, rotacionada 45°, com transparência
- **Aviso no cabeçalho**: em vermelho, destacado
- **Aviso no rodapé**: repetido para garantir visibilidade
- Detecta automaticamente via `empresa.ambiente_nfcom == 'homologacao'`

#### Cores e Estilos
- **Azul Corporativo**: #003366 para cabeçalhos e elementos importantes
- **Fundo Alternado**: #F9F9F9 para linhas ímpares nas tabelas
- **Fundo Títulos**: #E6EEF5 (azul bem claro) para os labels dos campos
- **Destaque Total**: #FFF8DC (bege claro) para o valor total da nota

## 📋 Como Usar

### Adicionar Logo da Empresa

1. Faça upload da logo pela interface (seção de empresas)
2. A logo será salva automaticamente em `uploads/logos/`
3. O caminho é armazenado em `empresa.logo_url`
4. O DANFE carregará automaticamente a logo ao gerar o PDF

### Gerar DANFE

O DANFE é gerado automaticamente ao clicar em "Visualizar DANFE" ou "Baixar DANFE" na interface:

```python
from app.services.danfe_generator import generate_danfe

# Buscar NFCom com relacionamentos
nfcom = db.query(NFCom).options(
    joinedload(NFCom.empresa),
    joinedload(NFCom.cliente),
    joinedload(NFCom.itens),
    joinedload(NFCom.faturas)
).filter(NFCom.id == nfcom_id).first()

# Gerar PDF
pdf_buffer = generate_danfe(nfcom)

# Retornar como StreamingResponse
return StreamingResponse(
    pdf_buffer,
    media_type="application/pdf",
    headers={"Content-Disposition": f"inline; filename=danfe_{nfcom.numero_nf}.pdf"}
)
```

## 🔧 Requisitos

### Dependências Python
```txt
reportlab==4.4.4
qrcode==7.4.2
Pillow  # Para manipulação de imagens (logo)
```

### Estrutura de Diretórios
```
backend/
  uploads/
    logos/          # Logos das empresas
  app/
    services/
      danfe_generator.py       # Gerador novo
      danfe_generator_old.py   # Backup da versão anterior
```

## 🎯 Próximas Melhorias Possíveis

- [ ] Suporte a múltiplas páginas (quebra automática de itens)
- [ ] Adicionar observações/informações complementares
- [ ] Incluir assinatura digital visual
- [ ] Suporte a diferentes tamanhos de papel (A4, Carta)
- [ ] Exportação em outros formatos (HTML, Excel)
- [ ] Personalização de cores por empresa
- [ ] Tradução para outros idiomas

## 📝 Notas de Versão

### v2.0.0 - Nova Versão Profissional (06/11/2025)
- ✨ Layout completamente redesenhado
- ✨ Adicionado suporte a logo da empresa
- ✨ QR Code integrado no cabeçalho
- ✨ Melhor legibilidade com cores e fontes otimizadas
- ✨ Formatação automática de CPF/CNPJ
- ✨ Tabelas com linhas alternadas
- ✨ Marca d'água para ambiente de homologação
- 🐛 Corrigidos problemas de contraste em títulos
- 🐛 Corrigido formato de datas

### v1.0.0 - Versão Inicial
- Geração básica de DANFE-COM
- Campos obrigatórios da NFCom
- QR Code separado

## 📄 Licença

Este código é parte do sistema NFCom Brazcom.
