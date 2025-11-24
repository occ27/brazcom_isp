Resumo das regras NFCOM (modelo 62) aplicáveis a campos de Cliente
=================================================

Base: MOC - Anexo I – Leiaute e Regras de Validação da NFCom (MOC 1.00a). Texto completo extraído para `docs/leiaute_nfccom.txt`.

Regras principais aplicáveis ao cadastro de cliente/destinatário (resumo prático para implementação):

1) Tipo de pessoa / documento
- `tipo_pessoa`: 'F' (física) ou 'J' (jurídica).
- Se `tipo_pessoa` = 'F' deve informar CPF (11 dígitos). Enviar apenas dígitos no payload.
- Se `tipo_pessoa` = 'J' deve informar CNPJ (14 dígitos). Enviar apenas dígitos no payload.
- Validar dígitos verificadores de CPF e CNPJ (rejeição NFCom: G22/G23/G12/G13).

2) Inscrição Estadual (IE)
- Campo `inscricao_estadual` aceita literal "ISENTO" em alguns casos.
- Para tomador/contribuinte (indIEDest=1) a IE deve ser informada (não aceitar vazia nem ISENTO).
- Para tomador isento (indIEDest=2) a IE deve conter o literal "ISENTO".
- Algumas UFs NÃO aceitam o literal "ISENTO" (rejeição: G28): AM, BA, CE, GO, MG, MS, MT, PE, RN, SE, SP. Não permitir ISENTO nesses estados.
- Validação de IE por UF pode envolver regras de formato e dígito verificador específicas (normalização com zeros não significativos antes da validação na SEFAZ). Implementar validação por UF quando possível; caso contrário, validar ao menos presença/ISENTO e padrões básicos.

3) Endereço / CEP / UF / Código IBGE
- `cep` deve ter 8 dígitos (apenas números). Sistema já preenche município/UF/código IBGE via consulta de CEP quando possível.
- `uf` deve ser sigla válida de estado brasileiro (2 letras). Preferir maiúsculas.
- `codigo_ibge` (código do município) deve ter 7 dígitos numéricos. Quando `uf` informado, os dois primeiros dígitos do `codigo_ibge` devem corresponder ao prefixo IBGE da UF.
- `municipio` / `uf` devem ser coerentes com `codigo_ibge` (quando possível, derivar do CEP e deixar `municipio`/`uf` como readonly para evitar inconsistência).
- Para pessoa jurídica (`tipo_pessoa === 'J'`) deve haver ao menos um endereço principal com campos mínimos: `endereco`, `numero`, `bairro`, `municipio`, `uf`, `cep` (8 dígitos) — conforme Regra G25/G30.

4) Telefone
- Limpar para dígitos apenas no payload. Aceitar ao menos 8 dígitos (fixo) e possibilitar 10-11 dígitos com DDD. Validar mínimo 8.

5) E-mail
- Validação sintática básica (regex). Comprimento máximo razoável (ex.: 255).

6) Normalizações
- `nome_razao_social` deve ser trim, remover espaços duplicados e normalizado (p.ex. upper case). O manual sugere normalização — adotar uppercase e trim.
- Todos os documentos (CPF/CNPJ/CEP/telefone/codigo_ibge) devem ser enviados apenas com dígitos.

7) Regras de consistência e rejeições (principais códigos do manual)
- Rejeições importantes que impactam cadastro/uso: G22 (CNPJ inválido), G23 (CPF inválido), G26 (IE isento deve ser literal ISENTO), G28 (UF não aceita ISENTO), G29/G30 (município x UF x IBGE inconsistentes), entre outras (G25, G31).

Implementação recomendada (passos práticos)
-------------------------------------------
1) Backend: reforçar validadores Pydantic (já parcialmente implementados em `backend/app/schemas/cliente.py`) para cobrir:
   - Verificação de CPF/CNPJ (dígitos verificadores).
   - IE: bloquear ISENTO em UFs proibidas; permitir ISENTO onde cabível; integrar validação por UF quando disponível.
   - Código IBGE: 7 dígitos e prefixo compatível com UF (quando UF informado).
   - CEP/UF/municipio: CEP com 8 dígitos; ao preencher via CEP, travar municipio/uf para evitar inconsistência.

2) Frontend: aplicar validações espelhadas em `Clients.tsx`:
   - Máscaras e `maxLength` já aplicadas (CPF 14, CNPJ 18), validar contagem de dígitos limpos (11/14) antes de enviar.
   - Impedir seleção de "ISENTO" em UFs que não aceitam (UI: validador inline mostrando mensagem e limpando campo se inválido).
   - Validar `codigo_ibge` (7 dígitos) e, se o usuário inserir manualmente, verificar prefixo x UF; preferir preencher via CEP.
   - Bloquear envio se houver inconsistências e exibir mensagens claras (campo + snackbar).

3) Testes: criar testes unitários (pytest) cobrindo PF e PJ, IE=ISENTO em estados que aceitam e que não aceitam, CEP automático, CPF/CNPJ inválidos.

Próximos passos que posso executar agora
--------------------------------------
- Gerar este resumo como arquivo (feito). (`docs/NFCOM-client-validation.md` criado)
- Aplicar a validação que impede literal ISENTO em UFs proibidas (já adicionado em `backend/app/core/validators.py`).
- Implementar checagem do `codigo_ibge` x `uf` (já adicionado ao backend: validação no momento de criação/validação de endereços).
- Atualizar frontend (`Clients.tsx`) para impedir ISENTO em UFs listadas e validar `codigo_ibge` e `cep` antes do submit.

Diga qual próximo passo você prefere que eu execute agora:  
- A: Atualizar frontend (`Clients.tsx`) para bloquear ISENTO em UFs proibidas e validar `codigo_ibge` e `cep` inline.  
- B: Criar testes unitários backend para as novas validações (pytest).  
- C: Implementar validação completa de IE por UF (mais trabalhoso — preciso confirmar regras específicas para cada UF no manual).  
- D: Outra (describe).  

Se quiser, já aplico a mudança no frontend (opção A) para a aba Endereço e Dados Básicos, e depois rodamos um teste rápido de criação de cliente sem subir toda a UI.  
