# -*- coding: utf-8 -*-
"""
Serviço de geração de dados de boletos bancários.
Sincronizado com Agrobraz.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

# Data base do fator de vencimento (07/10/1997)
_FATOR_BASE = date(1997, 10, 7)

def _mod10(number: str) -> int:
    total = 0
    for i, ch in enumerate(reversed(number)):
        v = int(ch) * (2 if i % 2 == 0 else 1)
        total += (v // 10) + (v % 10)
    r = total % 10
    return 0 if r == 0 else 10 - r

def _mod11(number: str, base: int = 9) -> int:
    total = 0
    multiplier = 2
    for ch in reversed(number):
        total += int(ch) * multiplier
        multiplier = 2 if multiplier == base else multiplier + 1
    r = total % 11
    if r in (0, 1): return 1
    return 11 - r

def _mod11_barcode(barcode_43: str) -> int:
    weights = list(range(2, 10))
    total = 0
    for i, ch in enumerate(reversed(barcode_43)):
        total += int(ch) * weights[i % 8]
    r = total % 11
    if r in (0, 1): return 1
    return 11 - r

def compute_fator_vencimento(due: date) -> str:
    delta = (due - _FATOR_BASE).days
    if delta > 9999:
        new_base = _FATOR_BASE + timedelta(days=9999 + 1)
        delta = (due - new_base).days + 1000
    return str(delta).zfill(4)

def compute_valor_str(amount: Decimal) -> str:
    centavos = int(round(float(amount) * 100))
    return str(centavos).zfill(10)

def _campo_livre_bb(agency: str, account: str, convenio: str,
                    carteira: str, nosso_numero_seq: str) -> str:
    conv7 = (convenio or '').zfill(7)[:7]
    seq10 = nosso_numero_seq.zfill(10)[:10]
    cart2 = (carteira or '17').zfill(2)[:2]
    return '000000' + conv7 + seq10 + cart2

def compute_campo_livre(bank_code: str, agency: str, account: str,
                         convenio: str, carteira: str, nosso_numero_seq: str) -> str:
    if bank_code == '001':
        return _campo_livre_bb(agency, account, convenio, carteira, nosso_numero_seq)
    # Adicionar outros bancos se necessário conforme Agrobraz
    return (agency + account + nosso_numero_seq).zfill(25)[:25]

def compute_barcode44(banco: str, moeda: str, fator: str,
                      valor: str, campo_livre: str) -> str:
    seq43 = banco + moeda + fator + valor + campo_livre
    dv = _mod11_barcode(seq43)
    return banco + moeda + str(dv) + fator + valor + campo_livre

def compute_linha_digitavel(barcode44: str) -> str:
    banco, moeda, dv_barcode, fator, valor, campo = barcode44[0:3], barcode44[3:4], barcode44[4:5], barcode44[5:9], barcode44[9:19], barcode44[19:44]
    c1_data = banco + moeda + campo[0:5]
    c2_data = campo[5:15]
    c3_data = campo[15:25]
    dac1, dac2, dac3 = str(_mod10(c1_data)), str(_mod10(c2_data)), str(_mod10(c3_data))
    f1 = c1_data[0:5] + '.' + c1_data[5:] + dac1
    f2 = c2_data[0:5] + '.' + c2_data[5:] + dac2
    f3 = c3_data[0:5] + '.' + c3_data[5:] + dac3
    return f'{f1} {f2} {f3} {dv_barcode} {fator}{valor}'
