Resumo curto para abertura de chamado com SVRS / SEFAZ

Contexto:
- Sistema: nfcom (desenvolvimento local). Envio para homologação SVRS.
- Empresa e NFCom de teste: empresa_id=12, nfcom_id=14 (artefatos nomeados com sufixo _14).
- Problema: transmissões retornam cStat=599 com xMotivo: "Rejeição: Não é permitida a presença de caracteres de edição no início/fim da mensagem ou entre as tags da mensagem".

O que já foi testado e anexado neste pacote:
1) XML assinado gerado localmente: temp_signed_nfcom_latest.xml
2) XML decodificado extraído do payload gravado no servidor (base64 + gzip): decoded_14.xml
3) SOAPs gerados: soap_nfcom_14_krp7k430.xml (original), soap_nfcom_14_mtime0_botvptb1.xml (gzip mtime=0 deterministic)
4) Reenvios diretos feitos com PEM (respostas): resend_sefaz_response.xml, out_resend_mtime0_resp.xml
5) Resposta do endpoint de transmissão (API): out_transmit_response.json
6) Relatório de comparação canônica: c14n_compare_report.txt
7) Arquivos canonicalizados (inclusive/exclusive) de ambos os XMLs

Perguntas / pedidos para a SEFAZ:
- Poderiam indicar o byte-offset ou trecho exato que o validador do SVRS considera como "caractere de edição" para estes arquivos anexados?
- Existe alguma validação adicional no conteudo gzip (e.g., cabeçalho gzip, campo mtime) ou no envelope SOAP que possa causar a rejeição, mesmo quando o XML canonicalizado está válido?
- Poderiam executar um diagnóstico nos dois SOAPs anexados e retornar logs com o ponto exato de falha (linha/offset/hex)?

Informações úteis:
- Hashes (SHA256) das canonicalizações e arquivos estão no arquivo 'c14n_compare_report.txt'.
- Não foram encontrados BOMs ou caracteres de controle no XML decodificado (inspeção local).
- Primeiro diff byte-exato entre o XML assinado salvo e o XML decodificado aparece no relatório (pode indicar diferença de serialização/whitespace entre storage e payload).

Hexdump ao redor do offset 257:
- Foram gerados hexdumps ±200 bytes ao redor do offset 257 para ajudar a localizar a diferença observada entre os arquivos assinados e o XML decodificado.
- Arquivos gerados (anexados no ZIP):
	- hexdump_temp_signed_nfcom_latest_around_257.txt
	- hexdump_decoded_14_around_257.txt
	- hexdump_temp_signed_nfcom_latest_c14n_inclusive_around_257.txt
	- hexdump_decoded_14_c14n_inclusive_around_257.txt
	- hexdump_summary_around_257.txt (concatena os quatro anteriores)

Esses arquivos contêm um hexdump com endereço, bytes hex e representação ASCII imprimível, além de uma tentativa de decodificação UTF-8 do trecho para facilitar a identificação do token/valor/atributo que difere.

Obrigado — favor responder com a informação mais precisa possível (offset em bytes/hex ou xpath/token).
