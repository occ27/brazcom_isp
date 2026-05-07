# -*- coding: utf-8 -*-
"""
Geração de boleto bancário em PDF usando ReportLab canvas.
Layout conforme padrão FEBRABAN - coordenadas precisas em mm.
Copiado do sistema Agrobraz para garantir paridade total.
"""
from __future__ import annotations

import io
import logging
from typing import Optional

from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

# ---------------------------------------------------------------------------
# Constantes de layout
# ---------------------------------------------------------------------------
PAGE_W, PAGE_H = A4          # 595.275 × 841.890 pt
ML     = 10 * mm             # margem esquerda
MR     = 10 * mm             # margem direita
MT     =  8 * mm             # margem superior
CW     = PAGE_W - ML - MR   # largura do conteúdo ≈ 190 mm

RC     = 42 * mm             # coluna direita (Vencimento, Nosso Nro, Valor)
LC     = CW - RC             # coluna esquerda

LBL_H  = 3.8 * mm           # altura do rótulo dentro da célula
LBL_FS = 6                  # font size do rótulo
VAL_FS = 9                  # font size do valor
BANK_FS = 14                # font size do código do banco
LINE_FS = 11                # font size linha digitável
LGRAY  = 0.93               # cinza claro para fundo dos rótulos

# Alturas de linha (mm)
H_CANHOTO_HDR  =  9.0
H_CANHOTO_ROW  = 10.0
H_CANHOTO_PAG  = 10.0
H_SEP          =  6.0
H_BH           = 14.0       # linha de cabeçalho (logo | banco | linha digitável)
H_STD          =  9.0       # linhas padrão de campos
H_INST         = 42.0       # bloco de instruções
H_SAC          = 20.0       # bloco do sacado
H_SACADOR      =  5.5
H_BARCODE      = 22.0

# ---------------------------------------------------------------------------
# Helpers de coordenadas
# ---------------------------------------------------------------------------

def _yt(y_top_mm: float) -> float:
    """mm a partir do topo do conteúdo → pontos ReportLab (origem = rodapé)."""
    return PAGE_H - MT - y_top_mm * mm


def _vline(c, x_pt: float, y_top_mm: float, h_mm: float):
    c.line(x_pt, _yt(y_top_mm), x_pt, _yt(y_top_mm + h_mm))


def _hline(c, y_top_mm: float, x_start=None, x_end=None):
    xs = x_start if x_start is not None else ML
    xe = x_end   if x_end   is not None else ML + CW
    y = _yt(y_top_mm)
    c.line(xs, y, xe, y)


def _cell(c, x_pt: float, y_top_mm: float, w_pt: float, h_mm: float,
          label: str = '', value: str = '', val_fs: int = VAL_FS,
          bold_val: bool = True, right_val: bool = False):
    """Desenha uma célula FEBRABAN: borda + rótulo cinza em cima + valor em baixo."""
    y_bottom = _yt(y_top_mm + h_mm)
    h_pt = h_mm * mm

    # Fundo cinza só na faixa do rótulo (topo)
    if label:
        c.setFillColorRGB(LGRAY, LGRAY, LGRAY)
        c.rect(x_pt, y_bottom + h_pt - LBL_H, w_pt, LBL_H, fill=1, stroke=0)

    # Borda
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(0.5)
    c.rect(x_pt, y_bottom, w_pt, h_pt, fill=0, stroke=1)

    c.setFillColorRGB(0, 0, 0)

    # Rótulo
    if label:
        c.setFont('Helvetica-Bold', LBL_FS)
        c.drawString(x_pt + 1.5 * mm, y_bottom + h_pt - LBL_H + 0.8 * mm, label)

    # Valor
    if value:
        c.setFont('Helvetica-Bold' if bold_val else 'Helvetica', val_fs)
        vx = x_pt + w_pt - 1.5 * mm if right_val else x_pt + 1.5 * mm
        vy = y_bottom + 2.0 * mm
        if right_val:
            c.drawRightString(vx, vy, str(value))
        else:
            c.drawString(vx, vy, str(value))


def _text(c, x_pt: float, y_top_mm: float, text: str, fs: int = 8,
          bold: bool = False, align: str = 'left', max_w: float = 0):
    fn = 'Helvetica-Bold' if bold else 'Helvetica'
    c.setFont(fn, fs)
    c.setFillColorRGB(0, 0, 0)
    y = _yt(y_top_mm)
    if align == 'right' and max_w:
        c.drawRightString(x_pt + max_w, y, str(text))
    elif align == 'center' and max_w:
        c.drawCentredString(x_pt + max_w / 2, y, str(text))
    else:
        c.drawString(x_pt, y, str(text))


# ---------------------------------------------------------------------------
# Geração do barcode ITF-25 como PIL Image
# ---------------------------------------------------------------------------

# Tabela ITF-25 (Interleaved 2 of 5): cada dígito → 5 elementos (False=estreito, True=largo)
_ITF25: dict[str, list[bool]] = {
    '0': [False, False, True,  True,  False],
    '1': [True,  False, False, False, True ],
    '2': [False, True,  False, False, True ],
    '3': [True,  True,  False, False, False],
    '4': [False, False, True,  False, True ],
    '5': [True,  False, True,  False, False],
    '6': [False, True,  True,  False, False],
    '7': [False, False, False, True,  True ],
    '8': [True,  False, False, True,  False],
    '9': [False, True,  False, True,  False],
}


def _barcode_image(code: str, narrow_mm: float = 0.38, wide_mm: float = 0.95,
                   height_mm: float = 15.0, quiet_mm: float = 5.0,
                   dpi: int = 300) -> 'PIL.Image.Image':
    """Gera imagem ITF-25 (Interleaved 2 of 5) pixel-perfect via Pillow."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None

    if len(code) % 2 != 0:
        code = '0' + code

    ppm = dpi / 25.4
    n = max(1, round(narrow_mm * ppm))
    w = max(1, round(wide_mm * ppm))
    h = max(1, round(height_mm * ppm))
    q = max(1, round(quiet_mm * ppm))

    # Start guard: estreito-bar, estreito-space, estreito-bar, estreito-space
    elements: list[tuple[bool, bool]] = [
        (True, False), (False, False), (True, False), (False, False),
    ]
    for i in range(0, len(code), 2):
        e1, e2 = _ITF25[code[i]], _ITF25[code[i + 1]]
        for j in range(5):
            elements.append((True,  e1[j]))
            elements.append((False, e2[j]))
    # End guard: largo-bar, estreito-space, estreito-bar
    elements += [(True, True), (False, False), (True, False)]

    total_px = q + sum(w if iw else n for _, iw in elements) + q
    img = Image.new('L', (total_px, h), 255)
    draw = ImageDraw.Draw(img)
    x = q
    for is_bar, is_wide in elements:
        bw = w if is_wide else n
        if is_bar:
            draw.rectangle([x, 0, x + bw - 1, h - 1], fill=0)
        x += bw

    return img


def _qrcode_image(data: str, size_mm: float = 30.0) -> 'PIL.Image.Image':
    """Gera imagem QR Code via qrcode library."""
    try:
        import qrcode
    except ImportError:
        return None

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img


# ---------------------------------------------------------------------------
# Desenhadores de seção
# ---------------------------------------------------------------------------

def _draw_canhoto(c, ctx: dict, logo_path: Optional[str], y0: float):
    """
    Desenha o canhoto (recibo do pagador).
    y0 = mm a partir do topo do conteúdo onde o canhoto começa.
    Retorna y_end (mm) = onde o canhoto termina.
    """
    x0 = ML

    # ---- Borda externa ----
    total_h = H_CANHOTO_HDR + H_CANHOTO_ROW + H_CANHOTO_ROW + H_CANHOTO_PAG
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(0.8)
    c.rect(x0, _yt(y0 + total_h), CW, total_h * mm, fill=0, stroke=1)
    c.setLineWidth(0.5)

    y = y0

    # ---- Linha 0: banco | título ----
    bank_w = 30 * mm
    _cell(c, x0, y, bank_w, H_CANHOTO_HDR, '', ctx.get('banco_codigo', ''), val_fs=BANK_FS, bold_val=True)
    _vline(c, x0 + bank_w, y, H_CANHOTO_HDR)
    _text(c, x0 + bank_w + 4 * mm, y + H_CANHOTO_HDR * 0.5,
          'BOLETO DE COBRANÇA', fs=9, bold=True)
    _hline(c, y + H_CANHOTO_HDR, x0, x0 + CW)
    y += H_CANHOTO_HDR

    # ---- Linha 1: beneficiário ----
    _cell(c, x0, y, CW, H_CANHOTO_ROW, 'BENEFICIÁRIO',
          f"{ctx.get('cedente_nome','')}   CNPJ: {ctx.get('cedente_cnpj','')}", val_fs=8)
    y += H_CANHOTO_ROW

    # ---- Linha 2: agência | nosso nro | vencimento | valor ----
    col_w = [(LC - 5 * mm) / 2, (LC - 5 * mm) / 2, 22 * mm, RC - 22 * mm]
    labels = ['AGÊNCIA / CÓD. BENEFICIÁRIO', 'NOSSO NÚMERO', 'VENCIMENTO', 'VALOR (R$)']
    values = [ctx.get('agencia_conta', ''), ctx.get('nosso_numero', ''),
              ctx.get('data_vencimento', ''), ctx.get('valor', '')]
    cx = x0
    for w_col, lbl, val in zip(col_w, labels, values):
        _cell(c, cx, y, w_col, H_CANHOTO_ROW, lbl, val, val_fs=8)
        cx += w_col
    y += H_CANHOTO_ROW

    # ---- Linha 3: pagador ----
    pagador = ctx.get('sacado_nome', '')
    doc = ctx.get('sacado_documento', '')
    if doc:
        pagador += f'   CPF/CNPJ: {doc}'
    _cell(c, x0, y, CW, H_CANHOTO_PAG, 'PAGADOR', pagador, val_fs=8)
    y += H_CANHOTO_PAG

    return y


def _draw_separator(c, y0: float):
    """Linha tracejada com tesoura."""
    y = y0 + H_SEP / 2
    c.setDash(4, 3)
    c.setLineWidth(0.5)
    c.setStrokeColorRGB(0.4, 0.4, 0.4)
    _hline(c, y)
    c.setDash()
    c.setStrokeColorRGB(0, 0, 0)
    # Posiciona a baseline do texto na linha tracejada → texto fica imediatamente acima dela
    _text(c, ML + CW / 2 - 40 * mm, y,
          '✂  RECIBO DO PAGADOR — CORTE AQUI  ✂', fs=7, align='center', max_w=80 * mm)
    return y0 + H_SEP


def _draw_ficha(c, ctx: dict, logo_path: Optional[str], y0: float):
    """Desenha a ficha de compensação a partir de y0 (mm do topo)."""
    x0 = ML
    y = y0

    # === BH-ROW: Logo | Banco | Linha digitável ===
    logo_w = 40 * mm
    bank_w = 28 * mm

    # Borda externa da linha de cabeçalho
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1.5)
    _hline(c, y)
    c.setLineWidth(0.5)

    # Logo
    logo_drawn = False
    if logo_path:
        try:
            from PIL import Image as PILImage
            pil_img = PILImage.open(logo_path)
            buf = io.BytesIO()
            pil_img.save(buf, format='PNG')
            buf.seek(0)
            img_reader = ImageReader(buf)
            logo_px_w, logo_px_h = pil_img.size
            scale = min(logo_w - 4 * mm, (H_BH - 4) * mm) / max(logo_px_w, logo_px_h) * (300 / 72)
            draw_w = logo_px_w * scale
            draw_h = logo_px_h * scale
            draw_x = x0 + 2 * mm
            draw_y = _yt(y + H_BH) + (H_BH * mm - draw_h) / 2
            c.drawImage(img_reader, draw_x, draw_y, width=draw_w, height=draw_h,
                        mask='auto', preserveAspectRatio=True)
            logo_drawn = True
        except Exception:
            pass

    if not logo_drawn:
        _text(c, x0 + 2 * mm, y + H_BH * 0.55,
              ctx.get('cedente_nome', '')[:20], fs=8, bold=True)

    # Separador logo | banco
    c.setLineWidth(2.0)
    _vline(c, x0 + logo_w, y, H_BH)
    c.setLineWidth(0.5)

    # Código do banco
    _text(c, x0 + logo_w + 2 * mm, y + H_BH * 0.4,
          ctx.get('banco_codigo', ''), fs=BANK_FS, bold=True)

    # Separador banco | linha digitável
    c.setLineWidth(2.0)
    _vline(c, x0 + logo_w + bank_w, y, H_BH)
    c.setLineWidth(0.5)

    # Linha digitável
    ld_x = x0 + logo_w + bank_w + 3 * mm
    ld_w = CW - logo_w - bank_w - 4 * mm
    c.setFont('Helvetica-Bold', LINE_FS)
    c.setFillColorRGB(0, 0, 0)
    c.drawRightString(ld_x + ld_w, _yt(y + H_BH * 0.45), ctx.get('linha_digitavel', ''))

    c.setLineWidth(2.0)
    _hline(c, y + H_BH)
    c.setLineWidth(0.5)
    y += H_BH

    # === Row 1: Local de Pagamento | Vencimento ===
    _cell(c, x0,      y, LC, H_STD, 'LOCAL DE PAGAMENTO', ctx.get('local_pagamento', ''), val_fs=7, bold_val=False)
    _cell(c, x0 + LC, y, RC, H_STD, 'VENCIMENTO', ctx.get('data_vencimento', ''), right_val=True)
    y += H_STD

    # === Row 2: Beneficiário | Agência / Cód Beneficiário ===
    cedente = f"{ctx.get('cedente_nome','')}   CNPJ: {ctx.get('cedente_cnpj','')}"
    _cell(c, x0,      y, LC, H_STD, 'BENEFICIÁRIO (CEDENTE)', cedente, val_fs=7, bold_val=False)
    _cell(c, x0 + LC, y, RC, H_STD, 'AGÊNCIA / CÓDIGO BENEFICIÁRIO', ctx.get('agencia_conta', ''))
    y += H_STD

    # === Row 3: Data Doc | Nº Doc | Espécie | Aceite | Data Proc | Nosso Número ===
    sub_cols = [28 * mm, 38 * mm, 20 * mm, 16 * mm]
    sub_total = sum(sub_cols)
    sub_labels = ['DATA DO DOCUMENTO', 'Nº DOCUMENTO', 'ESPÉCIE DOC.', 'ACEITE']
    sub_values = [ctx.get('data_emissao', ''), ctx.get('numero_documento', ''), 'DM', 'N']
    cx = x0
    for wc, lbl, val in zip(sub_cols, sub_labels, sub_values):
        _cell(c, cx, y, wc, H_STD, lbl, val, val_fs=8)
        cx += wc
    proc_w = LC - sub_total
    _cell(c, cx, y, proc_w, H_STD, 'DATA DE PROCESSAMENTO', ctx.get('data_emissao', ''), val_fs=8)
    _cell(c, x0 + LC, y, RC, H_STD, 'NOSSO NÚMERO', ctx.get('nosso_numero', ''), right_val=True)
    y += H_STD

    # === Row 4: Uso Banco | Carteira | Espécie | Qtd | Valor do Documento ===
    r4_cols = [25 * mm, 20 * mm, 20 * mm, LC - 65 * mm]
    r4_labels = ['USO DO BANCO', 'CARTEIRA', 'ESPÉCIE', 'QUANTIDADE']
    r4_values = ['', ctx.get('carteira', ''), 'R$', 'X']
    cx = x0
    for wc, lbl, val in zip(r4_cols, r4_labels, r4_values):
        _cell(c, cx, y, wc, H_STD, lbl, val, val_fs=8)
        cx += wc
    _cell(c, x0 + LC, y, RC, H_STD, 'VALOR DO DOCUMENTO', ctx.get('valor', ''), right_val=True)
    y += H_STD

    # === Bloco de instruções + deduções ===
    deduction_labels = ['DESCONTO / ABATIMENTOS', 'OUTRAS DEDUÇÕES',
                        'MORA / MULTA', 'OUTROS ACRÉSCIMOS', 'VALOR COBRADO']
    ded_h = H_INST / len(deduction_labels)

    # Borda do bloco instrucoes
    c.setLineWidth(0.5)
    c.rect(x0, _yt(y + H_INST), CW, H_INST * mm, fill=0, stroke=1)
    _vline(c, x0 + LC, y, H_INST)

    # Rótulo instruções
    c.setFillColorRGB(LGRAY, LGRAY, LGRAY)
    c.rect(x0, _yt(y + LBL_H / mm), LC, LBL_H, fill=1, stroke=0)
    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica-Bold', LBL_FS)
    c.drawString(x0 + 1.5 * mm, _yt(LBL_H / mm + y) + 0.8 * mm,
                 'INSTRUÇÕES (Texto de responsabilidade do Beneficiário)')

    # Texto das instruções
    instrucoes_text = ctx.get('instrucoes', '').replace('<br>', '\n').replace('<br/>', '\n')
    inst_y = y + LBL_H / mm + 2.0
    
    pix_qr = ctx.get('pix_qrcode')
    has_pix = bool(pix_qr)
    
    for line in instrucoes_text.split('\n'):
        c.setFont('Helvetica', 7)
        c.setFillColorRGB(0, 0, 0)
        # Reduzir largura se tiver PIX para não sobrepor
        max_inst_w = (LC - 35 * mm) if has_pix else (LC - 2 * mm)
        c.drawString(x0 + 1.5 * mm, _yt(inst_y + 2.5), line.strip()[:80 if has_pix else 120])
        inst_y += 4.5
        if inst_y > y + H_INST - 4:
            break

    # QR Code do PIX
    if has_pix:
        try:
            qr_img = _qrcode_image(pix_qr)
            if qr_img:
                buf = io.BytesIO()
                qr_img.save(buf, format='PNG')
                buf.seek(0)
                img_reader = ImageReader(buf)
                qr_size = 30 * mm
                qr_x = x0 + LC - qr_size - 2 * mm
                qr_y = _yt(y + H_INST - 2) + 2 * mm
                c.drawImage(img_reader, qr_x, qr_y, width=qr_size, height=qr_size)
                
                # Legenda do PIX
                c.setFont('Helvetica-Bold', 7)
                c.drawCentredString(qr_x + qr_size/2, qr_y + qr_size + 1 * mm, "PAGUE COM PIX")
        except Exception as e:
            logging.error(f"Erro ao desenhar QR Code PIX: {e}")

    # Deduções (coluna direita)
    dy = y
    for lbl in deduction_labels:
        _cell(c, x0 + LC, dy, RC, ded_h, lbl, '', val_fs=8)
        dy += ded_h

    y += H_INST

    # === Sacado ===
    c.rect(x0, _yt(y + H_SAC), CW, H_SAC * mm, fill=0, stroke=1)

    # Rótulo PAGADOR
    c.setFillColorRGB(LGRAY, LGRAY, LGRAY)
    c.rect(x0, _yt(y + LBL_H / mm), CW, LBL_H, fill=1, stroke=0)
    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica-Bold', LBL_FS)
    c.drawString(x0 + 1.5 * mm, _yt(LBL_H / mm + y) + 0.8 * mm, 'PAGADOR')

    sacado = ctx.get('sacado_nome', '')
    doc = ctx.get('sacado_documento', '')
    if doc:
        sacado += f'   CPF/CNPJ: {doc}'
    c.setFont('Helvetica-Bold', 8)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(x0 + 1.5 * mm, _yt(y + LBL_H / mm + 5.5), sacado)

    end_sac = ctx.get('sacado_endereco', '')
    cep = ctx.get('sacado_cep', '')
    mun = ctx.get('sacado_municipio', '')
    uf  = ctx.get('sacado_uf', '')
    addr_parts = [p for p in [end_sac, f'CEP: {cep}' if cep else '', f'{mun}/{uf}' if mun else ''] if p]
    c.setFont('Helvetica', 7.5)
    c.drawString(x0 + 1.5 * mm, _yt(y + LBL_H / mm + 11), '  '.join(addr_parts))

    y += H_SAC

    # === Sacador / Avalista ===
    c.rect(x0, _yt(y + H_SACADOR), CW, H_SACADOR * mm, fill=0, stroke=1)
    c.setFont('Helvetica', 7)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(x0 + 1.5 * mm, _yt(y + H_SACADOR * 0.6),
                 f"Sacador/Avalista: {ctx.get('cedente_nome', '')}")
    y += H_SACADOR

    # === Área do código de barras ===
    c.rect(x0, _yt(y + H_BARCODE), CW, H_BARCODE * mm, fill=0, stroke=1)

    barcode44 = ctx.get('barcode44', '')
    if barcode44:
        try:
            img = _barcode_image(barcode44, height_mm=H_BARCODE - 4)
            if img:
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                buf.seek(0)
                img_reader = ImageReader(buf)
                bar_w = 140 * mm
                bar_h = (H_BARCODE - 4) * mm
                bar_x = x0 + 2 * mm
                bar_y = _yt(y + H_BARCODE) + (H_BARCODE * mm - bar_h) / 2
                c.drawImage(img_reader, bar_x, bar_y, width=bar_w, height=bar_h,
                            mask='auto', preserveAspectRatio=False)
        except Exception:
            pass

    # Texto à direita do barcode
    c.setFont('Helvetica-Bold', 7)
    c.setFillColorRGB(0, 0, 0)
    auth_x = x0 + 144 * mm
    auth_y = _yt(y + 4)
    c.drawString(auth_x, auth_y, 'Autenticação Mecânica /')
    c.drawString(auth_x, auth_y - 3.5 * mm, 'FICHA DE COMPENSAÇÃO')

    y += H_BARCODE
    return y


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

def generate_boleto_pdf(context: dict, logo_path: Optional[str] = None) -> bytes:
    """
    Gera um boleto em PDF e retorna os bytes.

    Parâmetros:
        context: dict retornado por _build_boleto_context()
                 + campo extra 'barcode44' com os 44 dígitos do código de barras.
        logo_path: caminho absoluto para o arquivo de logo da empresa (opcional).
    """
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.setTitle('Boleto de Cobrança')

    y = 0.0  # mm a partir do topo do conteúdo

    # Canhoto
    y = _draw_canhoto(c, context, logo_path, y)

    # Separador
    y = _draw_separator(c, y)

    # Ficha de compensação
    _draw_ficha(c, context, logo_path, y)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()
