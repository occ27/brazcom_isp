"""
Scanner simples para localizar um endpoint SOAP/WSDL no host portalnfcom.fazenda.mg.gov.br
Execute no servidor (ou no venv local) com:

    python scripts/check_mg_wsdl.py

Ele tentará várias variações de caminhos e gravará o resultado em ./tmp/mg_wsdl_scan_results.txt
"""
import requests
from urllib.parse import urljoin
import os

HOST = "https://portalnfcom.fazenda.mg.gov.br"

CANDIDATE_PATHS = [
    "/ws/NFComRecepcao/NFComRecepcao.asmx",
    "/WS/NFComRecepcao/NFComRecepcao.asmx",
    "/ws/NFComRecepcao.asmx",
    "/ws/NfcomRecepcao/NfcomRecepcao.asmx",
    "/ws/NFComRecepcao/NFComRecepcao.asmx?wsdl",
    "/ws/NFComRecepcao.asmx?wsdl",
    "/webservices/NFComRecepcao.asmx?wsdl",
    "/ws/NFCom/NFComRecepcao.asmx?wsdl",
    "/nfcom/ws/NFComRecepcao/NFComRecepcao.asmx?wsdl",
    "/WS/NFCom/NFComRecepcao.asmx",
    "/ws/nfcomrecepcao.asmx?wsdl",
    "/ws/NFComRecepcao?wsdl",
    "/WS/NFComRecepcao?wsdl",
    "/ws/NFCom/NFComRecepcao.asmx",
]

OUT_DIR = "tmp"
OUT_FILE = os.path.join(OUT_DIR, "mg_wsdl_scan_results.txt")

os.makedirs(OUT_DIR, exist_ok=True)

results = []

print("Iniciando varredura de possíveis endpoints em:", HOST)
print("Resultados serão gravados em:", OUT_FILE)
print()

for path in CANDIDATE_PATHS:
    url = urljoin(HOST, path)
    try:
        # Ignorar verificação TLS para não falhar com certificados autoassinados em testes
        resp = requests.get(url, timeout=12, verify=False)
        content_snippet = resp.content[:1000]
        has_wsdl = b"wsdl" in content_snippet.lower() or b"definitions" in content_snippet.lower() or b"<soap" in content_snippet.lower()
        is_xml = resp.headers.get("Content-Type", "").lower().find("xml") != -1
        entry = {
            "url": url,
            "status_code": resp.status_code,
            "content_type": resp.headers.get("Content-Type"),
            "looks_like_wsdl": bool(has_wsdl or is_xml),
            "snippet": content_snippet.decode('utf-8', errors='replace')
        }
        print(f"{resp.status_code} | {url} | Content-Type: {entry['content_type']} | WSDL? {entry['looks_like_wsdl']}")
        results.append(entry)
    except requests.exceptions.RequestException as e:
        entry = {"url": url, "error": str(e)}
        print(f"ERR | {url} | {e}")
        results.append(entry)

# Grava resultados completos
with open(OUT_FILE, 'w', encoding='utf-8') as f:
    import json
    json.dump(results, f, ensure_ascii=False, indent=2)

print()
print("Varredura finalizada. Verifique o arquivo:", OUT_FILE)
print("Se encontrar uma URL com status 200 e 'looks_like_wsdl': True, copie-a aqui que eu atualizo o backend.")
