VAM# Especificação Webservice NFCom - Análise Técnica

**Data:** 03/11/2025  
**Contexto:** Verificação de requisitos para transmissão NFCom ao SVRS

## 1. Análise do Código Atual (backend/app/crud/crud_nfcom.py)

### 1.1 Compactação do Payload

**Linha 1426-1431:**
```python
# Compacta o XML da NFCom com GZIP e codifica em Base64, como esperado pela SEFAZ.

gzip_buffer = io.BytesIO()
with gzip.GzipFile(fileobj=gzip_buffer, mode='wb') as gzip_file:
    gzip_file.write(xml_bytes)
dados_comprimidos_base64 = base64.b64encode(gzip_buffer.getvalue()).decode('utf-8')
```

**Conclusão:** O código atual **comprime** o XML com GZIP e depois codifica em Base64 antes de enviar.

### 1.2 Versão SOAP Utilizada

**Linha 1434-1437:**
```python
# O webservice espera SOAP 1.2, conforme exemplo fornecido.

soap_body = f"""<soap12:Envelope xmlns:soap12=\"http://www.w3.org/2003/05/soap-envelope\" 
xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" 
xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\">
<soap12:Header>
<nfcomCabecMsg xmlns=\"http://www.portalfiscal.inf.br/nfcom/wsdl/NFComRecepcao\">
<cUF>{cUF_header}</cUF><versaoDados>1.00</versaoDados>
</nfcomCabecMsg>
</soap12:Header>
<soap12:Body>
<nfcomDadosMsg xmlns=\"http://www.portalfiscal.inf.br/nfcom/wsdl/NFComRecepcao\">
{dados_comprimidos_base64}
</nfcomDadosMsg>
</soap12:Body>
</soap12:Envelope>"""
```

**Elementos-chave identificados:**
- Namespace SOAP: `http://www.w3.org/2003/05/soap-envelope` (SOAP 1.2)
- Elemento Header: `<nfcomCabecMsg>` com namespace `http://www.portalfiscal.inf.br/nfcom/wsdl/NFComRecepcao`
- Elemento Body: `<nfcomDadosMsg>` (mesmo namespace) contendo o payload gzipado+base64

**Conclusão:** O código atual usa **SOAP 1.2**.

### 1.3 Headers HTTP (linha ~1458)

```python
headers = {
    'Content-Type': 'application/soap+xml; charset=utf-8',
    'SOAPAction': ''
}
```

**Observação:** Content-Type `application/soap+xml` é característico de SOAP 1.2 (SOAP 1.1 usa `text/xml`).

## 2. Documentação Oficial Consultada

### 2.1 Fontes Oficiais

- **Portal SVRS NFCom:** https://dfe-portal.svrs.rs.gov.br/Nfcom
- **Legislação Base:** 
  - Ajuste SINIEF 7/22 (institui NFCom modelo 62)
  - Ato COTEPE/ICMS 26/23 (publica MOC NFCom 1.00a)
- **Manuais Disponíveis:**
  - MOC NFCom 1.00a - Visão Geral
  - MOC NFCom 1.00a - Anexo I (Leiaute e Regras de Validação)
  - Manual Anexo II (DANFE-COM)

### 2.2 Limitações da Busca

⚠️ **IMPORTANTE:** Não foi possível localizar nos documentos públicos disponíveis uma especificação técnica explícita sobre:
- Se o XML deve ser enviado compactado com GZIP
- Qual versão de SOAP (1.1 ou 1.2) é oficialmente requerida
- Detalhes do formato do `<nfcomDadosMsg>`

**Possíveis razões:**
1. A especificação pode estar no "MOC - Visão Geral" completo (que não está no repositório local)
2. Pode ser definido em documento técnico de webservices específico
3. A implementação seguiu exemplo fornecido pelo SVRS (mencionado no código)

## 3. Comparação com Outros Documentos Fiscais Eletrônicos

### 3.1 Padrão NF-e / CT-e / MDF-e

Baseado na experiência com outros documentos fiscais eletrônicos brasileiros:

- **NF-e (Nota Fiscal Eletrônica):** Utiliza XML compactado com GZIP + Base64 no envelope SOAP
- **CT-e (Conhecimento de Transporte Eletrônico):** Mesmo padrão
- **MDF-e (Manifesto Eletrônico):** Mesmo padrão

**Padrão Comum:**
```xml
<soap12:Envelope ...>
  <soap12:Body>
    <nfeDadosMsg> <!-- ou cteDadosMsg, etc -->
      [XML compactado com GZIP e codificado em Base64]
    </nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>
```

### 3.2 Inferência para NFCom

Dado que:
1. NFCom é parte do mesmo ecossistema (SPED Fiscal)
2. Usa namespace similar: `http://www.portalfiscal.inf.br/nfcom/wsdl/NFComRecepcao`
3. O código implementado segue o mesmo padrão
4. O comentário no código menciona "como esperado pela SEFAZ"

**É altamente provável** que a NFCom siga o mesmo padrão de compactação GZIP + Base64.

## 4. Análise do Erro cStat=599

### 4.1 Mensagem de Erro Recebida

```
cStat: 599
xMotivo: "Rejeição: Não é permitida a presença de caracteres de edição no início/fim da mensagem ou entre as tags da mensagem"
```

### 4.2 Possíveis Causas (NÃO relacionadas a compactação/SOAP)

1. **Caracteres invisíveis no XML:** BOM (Byte Order Mark), espaços, tabs, newlines extras
2. **Problema na canonicalização:** Espaços em branco em elementos ou atributos
3. **Problema no header GZIP:** Campos extras no header GZIP que SEFAZ interpreta como "caracteres de edição"
4. **Encoding:** Problema com UTF-8 BOM ou outro encoding marker

### 4.3 Evidências Contra Problema de Compactação

1. **Mesmo erro com mtime=0:** Script `resend_signed_exact.py` enviou GZIP com mtime=0 (determinístico) e obteve mesmo erro
2. **Resposta HTTP 200:** O servidor aceita a requisição e processa o SOAP
3. **Parse bem-sucedido:** SEFAZ consegue extrair e parsear a resposta (retorna cStat/xMotivo válidos)

**Conclusão:** Se houvesse problema fundamental com a compactação, esperaríamos:
- Erro HTTP 400/500
- Erro SOAP Fault
- Mensagem de erro sobre formato inválido do envelope

## 5. Recomendações

### 5.1 Confirmação Autoritativa Necessária

Para confirmar definitivamente os requisitos, recomenda-se:

1. **Consultar MOC Completo:**
   - Baixar "MOC NFCom 1.00a - Visão Geral" do portal SVRS
   - Buscar seção sobre "Webservices" ou "Especificações Técnicas"

2. **Consultar WSDL Oficial:**
   - Verificar se SVRS disponibiliza WSDL do serviço NFComRecepcao
   - WSDL define binding SOAP (1.1 vs 1.2) e formato de mensagens

3. **Abrir Chamado no SVRS:**
   - Anexar `diagnostics_nfcom_14.pdf` já preparado
   - Perguntar explicitamente:
     - Qual versão SOAP esperada (1.1 ou 1.2)?
     - O conteúdo de `<nfcomDadosMsg>` deve ser GZIP+Base64?
     - Qual byte/offset específico está causando rejeição 599?

### 5.2 Experimentos Adicionais

Se preferir esgotar testes locais antes do chamado:

**Teste A: XML sem compactação**
```python
# Em vez de GZIP+Base64, enviar:
dados_base64 = base64.b64encode(xml_bytes).decode('utf-8')
# (apenas Base64, sem GZIP)
```

**Teste B: Envelope SOAP 1.1**
```python
# Mudar namespace para SOAP 1.1:
# xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
# Content-Type: text/xml; charset=utf-8
```

**Teste C: Analisar header GZIP**
```python
# Adicionar diagnóstico do header GZIP criado:
gzip_bytes = gzip_buffer.getvalue()
# Verificar primeiros 10 bytes (header GZIP)
# Bytes 4-7: MTIME
# Byte 8: XFL (extra flags)
# Byte 9: OS
```

## 6. Conclusão da Análise

**Com base no código atual e padrões conhecidos:**

| Aspecto | Implementação Atual | Provável Requisito SVRS | Nível de Confiança |
|---------|---------------------|-------------------------|-------------------|
| Compactação GZIP | ✅ Sim | ✅ Sim | 🟡 Alto (inferido) |
| Encoding Base64 | ✅ Sim | ✅ Sim | 🟡 Alto (inferido) |
| SOAP Version | ✅ 1.2 | ✅ 1.2 | 🟡 Alto (inferido) |
| Content-Type | `application/soap+xml` | `application/soap+xml` | 🟡 Alto (inferido) |

**Nível de confiança:**
- 🟢 **Confirmado** = documentação oficial explícita encontrada
- 🟡 **Alto** = baseado em padrões SPED e comentários do código
- 🔴 **Incerto** = necessita confirmação

### 6.1 Próximas Ações Recomendadas

**Prioritária:**
1. Baixar e revisar "MOC NFCom 1.00a - Visão Geral" do portal SVRS
2. Procurar seção "Webservices" ou "Especificações Técnicas de Comunicação"

**Alternativa:**
- Abrir chamado no SVRS com diagnostics_nfcom_14.pdf anexado
- Texto preparado disponível em: `backend/SVRS_CHAMADO_MSG.txt`

**Se urgente (contornar problema temporariamente):**
- Executar testes A, B e C descritos acima
- Comparar respostas para identificar se formato está correto

---

**Autor:** Sistema de Análise Técnica  
**Arquivo relacionado:** `backend/app/crud/crud_nfcom.py` (linhas 1426-1550)  
**Artefatos diagnósticos:** `backend/diagnostics_nfcom_14.pdf`, `backend/SVRS_CHAMADO_MSG.txt`
