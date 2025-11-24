import re
from typing import Optional

def clean_string(value: str) -> str:
    """Remove espaços no início e fim, e espaços duplos."""
    if not value:
        return value
    # Remove espaços no início e fim
    cleaned = value.strip()
    # Remove espaços duplos
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned

def validate_cnpj(cnpj: str) -> bool:
    """Valida CNPJ brasileiro."""
    if not cnpj:
        return False

    # Remove caracteres não numéricos
    cnpj = re.sub(r'[^0-9]', '', cnpj)

    # CNPJ deve ter 14 dígitos
    if len(cnpj) != 14:
        return False

    # Verifica se todos os dígitos são iguais (CNPJ inválido)
    if cnpj == cnpj[0] * 14:
        return False

    # Calcula primeiro dígito verificador
    def calculate_digit(cnpj_slice: str, weights: list) -> int:
        total = sum(int(digit) * weight for digit, weight in zip(cnpj_slice, weights))
        remainder = total % 11
        return 0 if remainder < 2 else 11 - remainder

    # Pesos para cálculo dos dígitos verificadores
    weights_first = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights_second = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    # Verifica primeiro dígito
    first_digit = calculate_digit(cnpj[:12], weights_first)
    if int(cnpj[12]) != first_digit:
        return False

    # Verifica segundo dígito
    second_digit = calculate_digit(cnpj[:13], weights_second)
    if int(cnpj[13]) != second_digit:
        return False

    return True

def validate_inscricao_estadual(ie: str, uf: Optional[str] = None) -> bool:
    """Valida inscrição estadual. Aceita 'ISENTO'."""
    if not ie:
        return False

    # Converte para maiúsculo e remove espaços
    ie = ie.upper().strip()

    # Aceita ISENTO
    if ie == 'ISENTO':
        # Algumas UFs não aceitam o literal ISENTO para Inscrição Estadual
        # Regra extraída do manual NFCom: AM, BA, CE, GO, MG, MS, MT, PE, RN, SE, SP
        if uf:
            uf = uf.upper().strip()
            ufs_nao_permitem_isento = {'AM', 'BA', 'CE', 'GO', 'MG', 'MS', 'MT', 'PE', 'RN', 'SE', 'SP'}
            if uf in ufs_nao_permitem_isento:
                return False
        return True

    # Remove caracteres não alfanuméricos
    ie_clean = re.sub(r'[^A-Z0-9]', '', ie)

    # Validação básica: deve ter pelo menos 8 caracteres
    if len(ie_clean) < 8:
        return False

    # Validação básica: deve ter pelo menos alguns dígitos
    if not re.search(r'\d', ie_clean):
        return False

    # Aqui poderia implementar validação específica por estado
    # Por enquanto, apenas validações básicas
    return True


def validate_codigo_ibge(codigo: str, uf: Optional[str] = None) -> bool:
    """Valida o código IBGE do município: deve ser numérico e ter 7 dígitos.
    Se a UF for informada, verifica que os dois primeiros dígitos correspondem à UF.
    """
    if not codigo:
        return False
    codigo_clean = re.sub(r'[^0-9]', '', codigo)
    if len(codigo_clean) != 7:
        return False

    # Mapeamento dos códigos IBGE (dois primeiros dígitos) por UF
    uf_to_ibge_prefix = {
        'RO': '11','AC':'12','AM':'13','RR':'14','PA':'15','AP':'16','TO':'17',
        'MA':'21','PI':'22','CE':'23','RN':'24','PB':'25','PE':'26','AL':'27','SE':'28','BA':'29',
        'MG':'31','ES':'32','RJ':'33','SP':'35','PR':'41','SC':'42','RS':'43','MS':'50','MT':'51','GO':'52','DF':'53'
    }

    if uf:
        uf = uf.upper().strip()
        prefix = uf_to_ibge_prefix.get(uf)
        if prefix and not codigo_clean.startswith(prefix):
            return False

    return True