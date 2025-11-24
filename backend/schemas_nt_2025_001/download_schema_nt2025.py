#!/usr/bin/env python3
"""
Script para baixar os schemas NT 2025.001 do portal SEFAZ SVRS
"""

import requests
import os
from urllib.parse import quote

def download_schema():
    """Baixa o arquivo de schemas NT 2025.001"""

    # URL base do portal SVRS
    base_url = "https://dfe-portal.svrs.rs.gov.br"

    # Parâmetros do arquivo
    sistema = "NFCOM"
    tipo = "2"
    nome = "PL_NFCOM_1.00_NT2025.001 RTC_1.10_corr.zip"

    # Monta a URL completa
    download_url = f"{base_url}/{sistema}/DownloadArquivoEstatico/?sistema={sistema}&tipoArquivo={tipo}&nomeArquivo={quote(nome)}"

    print(f"Baixando schema NT 2025.001...")
    print(f"URL: {download_url}")

    try:
        # Faz o download
        response = requests.get(download_url, timeout=30)
        response.raise_for_status()

        # Salva o arquivo
        filename = "PL_NFCOM_1.00_NT2025.001_RTC_1.10_corr.zip"
        filepath = os.path.join(os.getcwd(), filename)

        with open(filepath, 'wb') as f:
            f.write(response.content)

        print(f"Arquivo baixado com sucesso: {filename}")
        print(f"Tamanho: {len(response.content)} bytes")

        return filepath

    except requests.exceptions.RequestException as e:
        print(f"Erro ao baixar o arquivo: {e}")
        return None

if __name__ == "__main__":
    download_schema()