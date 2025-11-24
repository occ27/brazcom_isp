"""
Gerador de DANFE-COM (Documento Auxiliar da NFCom) - Nova versão profissional
Conforme especificações do MOC - Manual de Orientação do Contribuinte
Layout profissional inspirado no padrão CIGAM
"""
from io import BytesIO
from datetime import datetime
from typing import Optional
import qrcode
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics import renderPDF

from app.models.models import NFCom
from app.core.database import SessionLocal
from app.core.config import settings
from app.models import models as models_module

styles = getSampleStyleSheet()


def format_chave_acesso(chave: str) -> str:
    """Formata a chave de acesso em 11 blocos de 4 dígitos (44 no total)."""
    if not chave:
        return ""
    chave = ''.join([c for c in str(chave) if c.isdigit()])
    return ' '.join([chave[i:i+4] for i in range(0, min(len(chave), 44), 4)])


def format_date(date_obj) -> str:
    """Formata data"""
    if not date_obj:
        return ""
    if isinstance(date_obj, str):
        # Se já for string, tenta extrair apenas a data
        if 'T' in date_obj:
            date_obj = date_obj.split('T')[0]
        if isinstance(date_obj, str) and len(date_obj) == 10:
            parts = date_obj.split('-')
            if len(parts) == 3:
                return f"{parts[2]}/{parts[1]}/{parts[0]}"
        return date_obj
    return date_obj.strftime("%d/%m/%Y")


def generate_qr_code(qr_url: str) -> BytesIO:
    """
    Gera QR Code com a URL completa do QR Code da NFCom
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    return img_buffer


def extract_qr_code_url_from_xml(xml_content: str) -> str:
    """
    Extrai a URL completa do QR Code do XML da NFCom.
    
    Args:
        xml_content: Conteúdo XML da NFCom
        
    Returns:
        URL completa do QR Code ou string vazia se não encontrar
    """
    if not xml_content:
        return ""
    
    try:
        from lxml import etree
        
        # Parse do XML
        root = etree.fromstring(xml_content.encode('utf-8'))
        
        # Procura pelo elemento qrCodNFCom em infNFComSupl
        qr_element = root.find('.//{http://www.portalfiscal.inf.br/nfcom}qrCodNFCom')
        if qr_element is not None and qr_element.text:
            return qr_element.text.strip()
        
        # Fallback: procurar em infAdic/infCpl (onde pode estar como texto)
        inf_cpl = root.find('.//{http://www.portalfiscal.inf.br/nfcom}infCpl')
        if inf_cpl is not None and inf_cpl.text:
            # Procura por URL que começa com https e contém chNFCom
            import re
            url_pattern = r'https?://[^\s]+chNFCom=[^\s]+'
            match = re.search(url_pattern, inf_cpl.text)
            if match:
                return match.group(0)
                
    except Exception as e:
        print(f"Erro ao extrair URL do QR Code do XML: {e}")
    
    return ""


def format_cpf_cnpj(doc: str) -> str:
    """Formata CPF ou CNPJ automaticamente"""
    if not doc:
        return ""
    doc = doc.replace(".", "").replace("-", "").replace("/", "")
    if len(doc) == 11:  # CPF
        return f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
    elif len(doc) == 14:  # CNPJ
        return f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
    return doc


def format_currency(value: float) -> str:
    """Formata valor monetário"""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def create_rounded_chip(text, width, height, bg_color, text_color=colors.white):
    """Cria um chip com cantos arredondados"""
    drawing = Drawing(width, height)

    # Fundo arredondado
    rect = Rect(0, 0, width, height)
    rect.fillColor = bg_color
    rect.strokeColor = bg_color
    rect.strokeWidth = 0.5
    drawing.add(rect)

    # Texto centralizado
    clean_text = text.replace('<b>', '').replace('</b>', '')
    text_obj = String(width/2, height/2 - 2, clean_text, fontSize=8, fontName='Helvetica-Bold', fillColor=text_color, textAnchor='middle')
    drawing.add(text_obj)

    return drawing


def generate_danfe(nfcom: NFCom) -> BytesIO:
    """Gera o DANFE-COM em PDF no padrão MOC Anexo II - Modelo II (preto e branco)."""
    buffer = BytesIO()

    empresa = nfcom.empresa
    is_homologacao = (empresa.ambiente_nfcom == 'homologacao') if empresa and getattr(empresa, 'ambiente_nfcom', None) else False

    def add_watermark(canvas_obj, _doc):
        if is_homologacao:
            canvas_obj.saveState()
            canvas_obj.setFont('Helvetica-Bold', 56)
            canvas_obj.setFillGray(0.9)
            canvas_obj.translate(A4[0] / 2, A4[1] / 2)
            canvas_obj.rotate(45)
            canvas_obj.drawCentredString(0, 0, 'SEM VALOR FISCAL')
            canvas_obj.restoreState()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )

    title_style = ParagraphStyle('Title', parent=styles['Normal'], fontSize=14, alignment=TA_CENTER, fontName='Helvetica-Bold')
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER, fontName='Helvetica')
    subtitle_left_style = ParagraphStyle('SubtitleLeft', parent=styles['Normal'], fontSize=7, alignment=TA_LEFT, fontName='Helvetica')
    section_title_style = ParagraphStyle('SectionTitle', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold')
    label_style = ParagraphStyle('Label', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold')
    value_style = ParagraphStyle('Value', parent=styles['Normal'], fontSize=8, fontName='Helvetica')
    value_bold_style = ParagraphStyle('ValueBold', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')

    elements = []

    # ==================== DIVISÃO I - TÍTULO ====================
    chave_acesso = nfcom.chave_acesso or ''
    
    # Extrair a URL completa do QR Code do XML gravado (prioridade absoluta).
    # Em alguns fluxos a instância `nfcom` pode não conter o campo `xml_gerado`
    # (consulta parcial no endpoint). Tentamos recarregar do banco se necessário.
    xml_content = getattr(nfcom, 'xml_gerado', None)
    if not xml_content and getattr(nfcom, 'id', None):
        try:
            db = SessionLocal()
            fresh = db.query(models_module.NFCom).filter(models_module.NFCom.id == nfcom.id).first()
            if fresh is not None:
                xml_content = getattr(fresh, 'xml_gerado', None)
        except Exception:
            xml_content = None
        finally:
            try:
                db.close()
            except Exception:
                pass

    qr_code_url = extract_qr_code_url_from_xml(xml_content)
    if not qr_code_url and chave_acesso:
        # Fallback: construir URL se não conseguir extrair do XML
        from app.crud.crud_nfcom import get_qrcode_url_base
        uf_code = chave_acesso[:2] if chave_acesso else "41"
        empresa_ambiente = getattr(empresa, 'ambiente_nfcom', None) if empresa else None
        qr_code_base_url = get_qrcode_url_base(uf_code, ambiente=empresa_ambiente)
        tpAmb = "2" if empresa_ambiente in ('homologacao', 'homologação', 'homolog') else "1"
        params = f"?chNFCom={chave_acesso}&tpAmb={tpAmb}"
        # Se a nota foi emitida em contingência, adiciona o parâmetro &sign.
        try:
            tipo_em = getattr(nfcom, 'tipo_emissao', None)
            is_contingencia = False
            # Aceita enum ou string
            if tipo_em is not None:
                try:
                    # Comparar com a Enum definida no modelo quando possível
                    is_contingencia = (tipo_em == models_module.TipoEmissao.CONTINGENCIA) or (str(tipo_em).upper().find('CONTINGENCIA') != -1)
                except Exception:
                    is_contingencia = (str(tipo_em).upper().find('CONTINGENCIA') != -1)
            if is_contingencia and getattr(settings, 'SECRET_KEY', None):
                import hashlib
                to_sign = (chave_acesso or '') + settings.SECRET_KEY
                signature = hashlib.sha1(to_sign.encode('utf-8')).hexdigest()
                params += f"&sign={signature}"
        except Exception:
            # Não bloquear a geração do DANFE por falha na assinatura do QR
            pass
        qr_code_url = qr_code_base_url + params
    logo_img = None
    if empresa:
        # Primeiro tenta usar o logo_url se existir
        if empresa.logo_url:
            try:
                # Converte caminho URL (/files/logos/...) para caminho do sistema de arquivos
                if empresa.logo_url.startswith('/files/'):
                    # Remove /files/ do início e junta com o diretório de uploads
                    relative_path = empresa.logo_url[7:]  # Remove '/files/'
                    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads')
                    logo_path = os.path.join(uploads_dir, relative_path)
                else:
                    # Assume que é um caminho absoluto do sistema de arquivos
                    logo_path = empresa.logo_url
                
                if os.path.exists(logo_path):
                    logo_img = Image(logo_path, width=25 * mm, height=25 * mm)
                    logo_img.hAlign = 'CENTER'
            except Exception:
                logo_img = None
        
        # Se não conseguiu carregar pelo logo_url, tenta procurar em uploads/logos
        # (fallback para compatibilidade com logos antigas)
        if logo_img is None:
            logos_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads', 'logos')
            if os.path.exists(logos_dir):
                logo_files = [f for f in os.listdir(logos_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
                if logo_files:
                    # Usa o primeiro arquivo de logo encontrado (fallback)
                    logo_path = os.path.join(logos_dir, logo_files[0])
                    try:
                        logo_img = Image(logo_path, width=25 * mm, height=25 * mm)
                        logo_img.hAlign = 'CENTER'
                    except Exception:
                        logo_img = None

    # QRCode para o cabeçalho
    qr_header_img = None
    if qr_code_url:
        try:
            qr_header_img = Image(generate_qr_code(qr_code_url), width=25 * mm, height=25 * mm)
        except Exception:
            qr_header_img = None

    # Dados do emitente (com linha em branco separando título dos dados)
    emitente_data = [
        Paragraph('DOCUMENTO AUXILIAR DA NOTA FISCAL FATURA DE SERVIÇOS DE COMUNICAÇÃO ELETRÔNICA', subtitle_left_style),
        Spacer(1, 2 * mm),  # linha em branco maior
        Paragraph(getattr(empresa, 'razao_social', '') or '', value_style),
        Paragraph(f"{getattr(empresa, 'endereco', '') or ''}, {getattr(empresa, 'numero', '') or ''} {getattr(empresa, 'complemento', '') or ''}, {getattr(empresa, 'bairro', '') or ''}", value_style),
        Paragraph(f"{getattr(empresa, 'cep', '') or ''}, {getattr(empresa, 'municipio', '') or ''}, {getattr(empresa, 'codigo_ibge', '') or ''}", value_style),
        Paragraph(format_cpf_cnpj(getattr(empresa, 'cnpj', '') or ''), value_style),
        Paragraph(getattr(empresa, 'inscricao_estadual', '') or '', value_style),
    ]

    header_tbl = Table([[logo_img if logo_img else Paragraph('', value_style), 
                        emitente_data]], 
                       colWidths=[40 * mm, 150 * mm])
    header_tbl.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # Centralizar logo horizontalmente
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (1, 0), (1, -1), 8),  # Padding maior acima dos dados do emitente
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (0, -1), 8),  # Padding maior antes da logo
        ('LEFTPADDING', (1, 0), (1, -1), 10),  # Padding maior à esquerda dos dados do emitente
        ('RIGHTPADDING', (1, 0), (1, -1), 3),
    ]))
    elements.append(header_tbl)
    elements.append(Spacer(1, 2 * mm))

    # ==================== DIVISÃO I.1 - QR CODE E CHAVE DE ACESSO ====================
    # QRCode 
    qr_div_img = None
    if qr_code_url:
        try:
            qr_div_img = Image(generate_qr_code(qr_code_url), width=30 * mm, height=30 * mm)
        except Exception:
            qr_div_img = None

    # Coluna esquerda: QRCode à esquerda + Dados da Nota Fiscal à direita
    # Título DANFE-COM centralizado
    danfe_title_style = ParagraphStyle(
        'DanfeTitle',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica-Bold',
        alignment=0,  # Centralizado
    )
    
    nota_fiscal_info = [
        [Paragraph('<b>DANFE-COM</b>', danfe_title_style)],
        [Spacer(1, 6 * mm)],
        [Paragraph(f'<b>NOTA FISCAL No:</b> {str(nfcom.numero_nf or "").zfill(8)}', value_style)],
        [Paragraph(f'<b>SÉRIE:</b> {nfcom.serie or ""}', value_style)],
        [Spacer(1, 2 * mm)],
        [Paragraph(f'<b>DATA DE EMISSÃO:</b> {format_date(nfcom.data_emissao)}', value_style)],
    ]
    
    nota_info_table = Table(nota_fiscal_info, colWidths=[55 * mm])
    nota_info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # Centraliza apenas o título DANFE-COM
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),   # Alinha à esquerda os demais itens
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    left_col = Table([[qr_div_img if qr_div_img else Paragraph('', value_style), nota_info_table]], 
                     colWidths=[35 * mm, 55 * mm])
    left_col.setStyle(TableStyle([
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),  # Linha vertical entre QR e dados
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (0, -1), 3),  # Padding QRCode
        ('LEFTPADDING', (1, 0), (1, -1), 10),  # Padding maior para coluna NOTA FISCAL
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))

    # Coluna direita: Consulta pela Chave de Acesso
    # URL do site de consulta (ajuste conforme o estado/ambiente)
    url_consulta = "https://www.nfcom.fazenda.gov.br/portal/consultaRecaptcha.aspx"
    
    # Formatar protocolo de autorização com data/hora
    protocolo_info = ""
    if nfcom.protocolo_autorizacao:
        protocolo_texto = f"Protocolo de Autorização: {nfcom.protocolo_autorizacao}"
        
        # Verifica se há data_autorizacao (DateTime com timezone)
        if hasattr(nfcom, 'data_autorizacao') and nfcom.data_autorizacao:
            try:
                if hasattr(nfcom.data_autorizacao, 'strftime'):
                    # Formata data e hora: DD/MM/AAAA às HH:MM:SS
                    data_hora = nfcom.data_autorizacao.strftime("%d/%m/%Y às %H:%M:%S")
                    protocolo_texto += f" - {data_hora}"
            except:
                pass
        
        protocolo_info = protocolo_texto
    
    right_content = [
        [Paragraph('<b>CONSULTA PELA CHAVE DE ACESSO</b>', section_title_style)],
        [Paragraph(f'<font size="6">{url_consulta}</font>', value_style)],
        [Spacer(1, 2 * mm)],
        [Paragraph('<b>CHAVE DE ACESSO:</b>', label_style)],
        [Paragraph(format_chave_acesso(chave_acesso or ''), value_style)],
        [Spacer(1, 2 * mm)],
        [Paragraph(f'<font size="6">{protocolo_info}</font>', value_style)],
    ]
    
    right_col = Table(right_content, colWidths=[90 * mm])
    right_col.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),  # Padding esquerdo igual ao da NOTA FISCAL
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))

    # Tabela principal com borda cinza discreta
    qr_info_tbl = Table([[left_col, right_col]], colWidths=[95 * mm, 95 * mm])
    qr_info_tbl.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),  # Linhas internas verticais e horizontais
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))

    elements.append(qr_info_tbl)
    elements.append(Spacer(1, 2 * mm))

    # ==================== DIVISÃO II - DESTINATÁRIO E FATURAMENTO ====================
    cliente = nfcom.cliente
    
    # ID do cliente
    cliente_id = str(getattr(cliente, 'id', '')) if cliente and hasattr(cliente, 'id') else ''
    
    # Formatar telefone se existir
    telefone = ""
    if cliente and hasattr(cliente, 'telefone') and cliente.telefone:
        tel = str(cliente.telefone).replace("(", "").replace(")", "").replace("-", "").replace(" ", "")
        if len(tel) >= 10:
            telefone = f"{tel[:2]}.{tel[2:7]}-{tel[7:]}"
        else:
            telefone = str(cliente.telefone)
    
    # Coluna esquerda: Dados do Destinatário
    dest_content = [
        [Paragraph('<b>DESTINATÁRIO / TOMADOR</b>', section_title_style)],
        [Paragraph(f'<b>{getattr(cliente, "nome_razao_social", "") or ""}</b>', value_style)],
        [Paragraph(f"{nfcom.dest_endereco or ''}, {nfcom.dest_numero or ''} {nfcom.dest_complemento or ''} - {nfcom.dest_bairro or ''} - {nfcom.dest_municipio or ''}/{nfcom.dest_uf or ''} - CEP: {nfcom.dest_cep or ''}", value_style)],
        [Spacer(1, 3 * mm)],
        [Paragraph(f'<b>CNPJ/CPF:</b> {format_cpf_cnpj(getattr(cliente, "cpf_cnpj", "") or "")} | <b>I.E.:</b> {getattr(cliente, "inscricao_estadual", "") or ""}', value_style)],
        [Paragraph(f'Cód. Cliente: {cliente_id} - Telefone: {telefone} - Período: {format_date(nfcom.data_emissao)}', value_style)],
    ]
    
    dest_left = Table(dest_content, colWidths=[95 * mm])
    dest_left.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    # Coluna direita: Resumo dos Serviços
    # Título centralizado
    resumo_title_style = ParagraphStyle(
        'ResumoTitle',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold',
        alignment=1,  # Centralizado
    )
    
    dest_right = Table([
        [Paragraph('<b>RESUMO DOS SERVIÇOS</b>', resumo_title_style)],
    ], colWidths=[95 * mm])
    dest_right.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    # Tabela principal com 2 colunas
    dest_fatura_tbl = Table([[dest_left, dest_right]], colWidths=[95 * mm, 95 * mm])
    dest_fatura_tbl.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),  # Linha vertical entre as colunas
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    elements.append(dest_fatura_tbl)
    elements.append(Spacer(1, 2 * mm))
    
    # ==================== REFERÊNCIA, VENCIMENTO E TOTAL A PAGAR ====================
    # Obtém dados da fatura (primeira fatura se houver múltiplas)
    referencia = ""
    vencimento = ""
    total_pagar = ""
    
    if nfcom.faturas and len(nfcom.faturas) > 0:
        fatura = nfcom.faturas[0]
        referencia = fatura.numero_fatura or ""
        vencimento = format_date(fatura.data_vencimento) if fatura.data_vencimento else ""
        total_pagar = format_currency(fatura.valor_fatura) if fatura.valor_fatura else ""
    
    pagamento_data = [
        [
            Paragraph(f'<b>REFERÊNCIA:</b> {referencia}', value_style), 
            Paragraph(f'<b>VENCIMENTO:</b> {vencimento}', value_style), 
            Paragraph(f'<b>TOTAL A PAGAR:</b> {total_pagar}', value_style)
        ],
    ]
    
    pagamento_tbl = Table(pagamento_data, colWidths=[63.33 * mm, 63.33 * mm, 63.34 * mm])
    pagamento_tbl.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    
    elements.append(pagamento_tbl)
    elements.append(Spacer(1, 2 * mm))
  
    # ==================== DIVISÃO IV - ITENS ====================
    if nfcom.itens:
        # Título da seção
        itens_title = Table([[Paragraph('<b>ITENS / SERVIÇOS</b>', section_title_style)]], colWidths=[190 * mm])
        itens_title.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(itens_title)
        
        # Cabeçalho e dados dos itens
        itens_header = [
            Paragraph('<b>ITEM</b>', label_style),
            Paragraph('<b>CÓDIGO</b>', label_style),
            Paragraph('<b>DESCRIÇÃO DO SERVIÇO</b>', label_style),
            Paragraph('<b>UN</b>', label_style),
            Paragraph('<b>QTD</b>', label_style),
            Paragraph('<b>VL. UNIT.</b>', label_style),
            Paragraph('<b>VL. TOTAL</b>', label_style),
        ]
        itens_data = [itens_header]
        for idx, item in enumerate(nfcom.itens, 1):
            itens_data.append([
                Paragraph(f'<para align="center">{idx}</para>', value_style),
                Paragraph(item.codigo_servico or '', value_style),
                Paragraph(item.descricao_servico or '', value_style),
                Paragraph(f'<para align="center">{item.unidade_medida or ""}</para>', value_style),
                Paragraph(f'<para align="right">{item.quantidade or 0}</para>', value_style),
                Paragraph(f'<para align="right">{format_currency(item.valor_unitario or 0)}</para>', value_style),
                Paragraph(f'<para align="right">{format_currency(item.valor_total or 0)}</para>', value_style),
            ])
        itens_table = Table(itens_data, colWidths=[15 * mm, 25 * mm, 70 * mm, 15 * mm, 20 * mm, 22.5 * mm, 22.5 * mm])
        itens_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Fundo cinza no cabeçalho
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # Centraliza cabeçalho
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(itens_table)
        elements.append(Spacer(1, 2 * mm))

    # ==================== DIVISÃO V - CÁLCULO DOS IMPOSTOS ====================
    def _calc_total_pis_cofins():
        pis_total = nfcom.valor_pis or 0
        cofins_total = nfcom.valor_cofins or 0
        if nfcom.itens:
            if not pis_total:
                for it in nfcom.itens:
                    if getattr(it, 'base_calculo_pis', None) and getattr(it, 'aliquota_pis', None):
                        pis_total += it.base_calculo_pis * (it.aliquota_pis / 100)
            if not cofins_total:
                for it in nfcom.itens:
                    if getattr(it, 'base_calculo_cofins', None) and getattr(it, 'aliquota_cofins', None):
                        cofins_total += it.base_calculo_cofins * (it.aliquota_cofins / 100)
        return pis_total, cofins_total

    total_pis, total_cofins = _calc_total_pis_cofins()
    total_icms = nfcom.valor_icms or 0
    total_bc_icms = sum((it.base_calculo_icms or 0) for it in (nfcom.itens or []))
    valor_total = nfcom.valor_total or 0

    # Título da seção
    totais_title = Table([[Paragraph('<b>CÁLCULO DOS IMPOSTOS</b>', section_title_style)]], colWidths=[190 * mm])
    totais_title.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(totais_title)
    
    trib_table = Table([
        [
            Paragraph('<b>BC ICMS</b>', label_style), 
            Paragraph('<b>VL. ICMS</b>', label_style),
            Paragraph('<b>VL. PIS</b>', label_style), 
            Paragraph('<b>VL. COFINS</b>', label_style),
            Paragraph('<b>VALOR TOTAL DA NFCom</b>', label_style),
        ],
        [
            Paragraph(f'<para align="right">{format_currency(total_bc_icms)}</para>', value_style),
            Paragraph(f'<para align="right">{format_currency(total_icms)}</para>', value_style),
            Paragraph(f'<para align="right">{format_currency(total_pis)}</para>', value_style),
            Paragraph(f'<para align="right">{format_currency(total_cofins)}</para>', value_style),
            Paragraph(f'<para align="right"><b>{format_currency(valor_total)}</b></para>', value_bold_style),
        ]
    ], colWidths=[38 * mm, 38 * mm, 38 * mm, 38 * mm, 38 * mm])
    trib_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Fundo cinza no cabeçalho
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # Centraliza cabeçalho
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(trib_table)
    elements.append(Spacer(1, 2 * mm))

    # ==================== INFORMAÇÕES DOS TRIBUTOS / RESERVADO AO FISCO ====================
    # Coluna esquerda: Informações dos Tributos (1/3 da largura = ~63.33mm)
    tributos_left_title = ParagraphStyle(
        'TributosTitle',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold',
        alignment=1,  # Centralizado
    )
    
    # Valores dos tributos
    valor_pis = total_pis
    valor_cofins = total_cofins
    valor_fust = getattr(nfcom, 'valor_fust', 0) or 0
    valor_funtel = getattr(nfcom, 'valor_funtel', 0) or 0
    
    # Formata valores (deixa em branco se for zero)
    def format_valor_tributo(valor):
        return f'<para align="right">{format_currency(valor)}</para>' if valor > 0 else ''
    
    # Tabela interna explícita dos tributos (mais robusta que acessar _cellvalues)
    tributos_inner = Table([
        [Paragraph('<b>TRIBUTO</b>', label_style), Paragraph('<b>VALOR</b>', label_style)],
        [Paragraph('PIS', value_style), Paragraph(format_valor_tributo(valor_pis), value_style)],
        [Paragraph('COFINS', value_style), Paragraph(format_valor_tributo(valor_cofins), value_style)],
        [Paragraph('FUST', value_style), Paragraph(format_valor_tributo(valor_fust), value_style)],
        [Paragraph('FUNTEL', value_style), Paragraph(format_valor_tributo(valor_funtel), value_style)],
    ], colWidths=[31.5 * mm, 31.5 * mm])

    tributos_inner.setStyle(TableStyle([
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('BOX', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Fundo cinza no cabeçalho
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # Centraliza cabeçalho
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    tributos_left = Table([
        [Paragraph('<b>INFORMAÇÕES DOS TRIBUTOS</b>', tributos_left_title)],
        [tributos_inner],
    ], colWidths=[63.34 * mm])

    tributos_left.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    # Coluna direita: Reservado ao Fisco (2/3 da largura = ~126.66mm)
    fisco_data = [
        [Paragraph('<b>RESERVADO AO FISCO</b>', tributos_left_title)],
        [Paragraph('', value_style)],
    ]
    
    fisco_right = Table(fisco_data, colWidths=[126.66 * mm])
    fisco_right.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    # Tabela principal com 2 colunas (1/3 + 2/3)
    tributos_fisco_tbl = Table([[tributos_left, fisco_right]], colWidths=[63.34 * mm, 126.66 * mm])
    tributos_fisco_tbl.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),  # Linha vertical entre as colunas
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    elements.append(tributos_fisco_tbl)
    elements.append(Spacer(1, 2 * mm))

    # ==================== INFORMAÇÕES COMPLEMENTARES / ÁREA DO CONTRIBUINTE ====================
    info_compl_title = Table([[Paragraph('<b>INFORMAÇÕES COMPLEMENTARES DE INTERESSE DO CONTRIBUINTE</b>', section_title_style)]], colWidths=[190 * mm])
    info_compl_title.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(info_compl_title)
    
    info_compl_text = nfcom.informacoes_adicionais if nfcom.informacoes_adicionais else ''
    info_compl_content = Table([[Paragraph(info_compl_text, value_style)]], colWidths=[190 * mm], rowHeights=[25 * mm])
    info_compl_content.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(info_compl_content)
    elements.append(Spacer(1, 2 * mm))

    # ==================== ÁREA DO CONTRIBUINTE E DETERMINAÇÕES DA ANATEL ====================
    anatel_title = Table([[Paragraph('<b>ÁREA DO CONTRIBUINTE E DETERMINAÇÕES DA ANATEL</b>', section_title_style)]], colWidths=[190 * mm])
    anatel_title.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(anatel_title)
    
    anatel_content = Table([[Paragraph('<i>Área reservada para informações regulamentadas pela ANATEL (detalhamento de serviços, ligações, etc.)</i>', value_style)]], colWidths=[190 * mm])
    anatel_content.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
    ]))
    elements.append(anatel_content)

    doc.build(elements, onFirstPage=add_watermark, onLaterPages=add_watermark)
    buffer.seek(0)
    return buffer
