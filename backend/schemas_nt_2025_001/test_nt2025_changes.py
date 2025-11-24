#!/usr/bin/env python3
"""
Script para testar transmissão NFCom com CNPJ alfanumérico conforme NT 2025.001
"""

import requests
import os
from pathlib import Path
from lxml import etree as ET
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
import base64
import hashlib
import uuid
from datetime import datetime

def load_certificate_and_key():
    """Carrega certificado e chave privada"""
    cert_path = Path(__file__).parent / "certificado.p12"
    if not cert_path.exists():
        raise FileNotFoundError(f"Certificado não encontrado: {cert_path}")

    # Para este teste, vamos usar dados mock
    return None, None

def create_nfcom_xml_with_alphanumeric_cnpj():
    """Cria XML NFCom com CNPJ alfanumérico conforme NT 2025.001"""

    # Dados de teste
    cnpj_emitente = "99887766554432"  # CNPJ numérico normal
    cnpj_destinatario = "12345678901234"  # CNPJ numérico normal

    # Vamos testar com um CNPJ que contenha letras (conforme novo padrão)
    # Mas primeiro vamos manter numérico para ver se funciona

    # Criar XML básico
    ns = {'nfcom': 'http://www.portalfiscal.inf.br/nfcom'}

    root = ET.Element("NFCom", nsmap=ns)
    root.set("versao", "1.00")

    # infNFCom
    inf_nfcom = ET.SubElement(root, "infNFCom")
    inf_nfcom.set("Id", "NFCom12345678901234567890123456789012345678901234")

    # ide
    ide = ET.SubElement(inf_nfcom, "ide")
    ET.SubElement(ide, "cUF").text = "43"  # RS
    ET.SubElement(ide, "tpAmb").text = "2"  # Homologação
    ET.SubElement(ide, "mod").text = "62"  # NFCom
    ET.SubElement(ide, "serie").text = "1"
    ET.SubElement(ide, "nNF").text = "1"
    ET.SubElement(ide, "cNF").text = "12345678"
    ET.SubElement(ide, "cDV").text = "1"
    ET.SubElement(ide, "dhEmi").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
    ET.SubElement(ide, "tpEmis").text = "1"
    ET.SubElement(ide, "nSiteAutoriz").text = "0"

    # emit
    emit = ET.SubElement(inf_nfcom, "emit")
    ET.SubElement(emit, "CNPJ").text = cnpj_emitente
    ET.SubElement(emit, "IE").text = "1234567890"
    ET.SubElement(emit, "CRT").text = "3"
    ET.SubElement(emit, "xNome").text = "EMPRESA TESTE LTDA"
    ET.SubElement(emit, "xFant").text = "EMPRESA TESTE"

    # enderEmit
    ender_emit = ET.SubElement(emit, "enderEmit")
    ET.SubElement(ender_emit, "xLgr").text = "RUA TESTE"
    ET.SubElement(ender_emit, "nro").text = "123"
    ET.SubElement(ender_emit, "xBairro").text = "CENTRO"
    ET.SubElement(ender_emit, "cMun").text = "4314902"  # Porto Alegre
    ET.SubElement(ender_emit, "xMun").text = "PORTO ALEGRE"
    ET.SubElement(ender_emit, "CEP").text = "90000000"
    ET.SubElement(ender_emit, "UF").text = "RS"

    # dest
    dest = ET.SubElement(inf_nfcom, "dest")
    ET.SubElement(dest, "CNPJ").text = cnpj_destinatario
    ET.SubElement(dest, "xNome").text = "CLIENTE TESTE"
    ET.SubElement(dest, "indIEDest").text = "9"

    # enderDest
    ender_dest = ET.SubElement(dest, "enderDest")
    ET.SubElement(ender_dest, "xLgr").text = "RUA CLIENTE"
    ET.SubElement(ender_dest, "nro").text = "456"
    ET.SubElement(ender_dest, "xBairro").text = "BAIRRO"
    ET.SubElement(ender_dest, "cMun").text = "4314902"
    ET.SubElement(ender_dest, "xMun").text = "PORTO ALEGRE"
    ET.SubElement(ender_dest, "CEP").text = "90000000"
    ET.SubElement(ender_dest, "UF").text = "RS"

    # det
    det = ET.SubElement(inf_nfcom, "det")
    det.set("nItem", "1")

    # prod
    prod = ET.SubElement(det, "prod")
    ET.SubElement(prod, "cProd").text = "SERV01"
    ET.SubElement(prod, "xProd").text = "SERVICO DE TELECOMUNICACOES"
    ET.SubElement(prod, "cClass").text = "01010101"
    ET.SubElement(prod, "CFOP").text = "5301"
    ET.SubElement(prod, "uMed").text = "1"
    ET.SubElement(prod, "qFaturada").text = "1.0000"
    ET.SubElement(prod, "vItem").text = "100.00"
    ET.SubElement(prod, "vProd").text = "100.00"

    # imposto
    imposto = ET.SubElement(det, "imposto")

    # ICMS
    icms = ET.SubElement(imposto, "ICMS")
    icms00 = ET.SubElement(icms, "ICMS00")
    ET.SubElement(icms00, "CST").text = "00"
    ET.SubElement(icms00, "vBC").text = "0.00"
    ET.SubElement(icms00, "pICMS").text = "0.00"
    ET.SubElement(icms00, "vICMS").text = "0.00"

    # PIS
    pis = ET.SubElement(imposto, "PIS")
    ET.SubElement(pis, "CST").text = "01"
    ET.SubElement(pis, "vBC").text = "0.00"
    ET.SubElement(pis, "pPIS").text = "0.00"
    ET.SubElement(pis, "vPIS").text = "0.00"

    # COFINS
    cofins = ET.SubElement(imposto, "COFINS")
    ET.SubElement(cofins, "CST").text = "01"
    ET.SubElement(cofins, "vBC").text = "0.00"
    ET.SubElement(cofins, "pCOFINS").text = "0.00"
    ET.SubElement(cofins, "vCOFINS").text = "0.00"

    # infIntermed
    inf_intermed = ET.SubElement(inf_nfcom, "infIntermed")
    ET.SubElement(inf_intermed, "CNPJ").text = cnpj_emitente
    ET.SubElement(inf_intermed, "idCadIntTran").text = "12345"

    # infNFComSupl (opcional)
    # infRespTec (opcional)

    return ET.tostring(root, encoding='unicode', method='xml')

def test_transmission():
    """Testa transmissão do NFCom"""

    # Criar XML
    xml_content = create_nfcom_xml_with_alphanumeric_cnpj()

    print("XML gerado:")
    print(xml_content[:1000] + "..." if len(xml_content) > 1000 else xml_content)

    # Salvar XML para análise
    with open("test_nfcom_nt2025.xml", "w", encoding="utf-8") as f:
        f.write(xml_content)

    print("\nXML salvo em: test_nfcom_nt2025.xml")

    # Nota: Para transmissão real seria necessário:
    # 1. Assinar digitalmente o XML
    # 2. Comprimir em ZIP
    # 3. Enviar via SOAP para SEFAZ

    return xml_content

if __name__ == "__main__":
    test_transmission()