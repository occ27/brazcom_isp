import os
from datetime import datetime
from typing import List, Optional, Any, Dict
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.units import cm

from app.models.models import Empresa, ServicoContratado, Receivable, Cliente

class ReportService:
    @staticmethod
    def generate_contracts_report(
        empresa: Empresa,
        contracts: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> BytesIO:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=1*cm, leftMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
        elements = []
        styles = getSampleStyleSheet()
        
        # Estilos personalizados
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=1,
            spaceAfter=10
        )
        
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            wordWrap='LTR'
        )

        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.whitesmoke,
            fontName='Helvetica-Bold'
        )

        elements.append(Paragraph(f"Relatório de Contratos - {empresa.nome_fantasia or empresa.razao_social}", title_style))
        
        # Filtros aplicados
        filter_text = f"Período: {filters.get('start_date', 'Início')} até {filters.get('end_date', 'Fim')}"
        if filters.get('status'):
            filter_text += f" | Status: {filters.get('status')}"
        elements.append(Paragraph(filter_text, styles['Normal']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Tabela de Dados
        headers = [
            Paragraph('ID', header_style),
            Paragraph('Cliente', header_style),
            Paragraph('Serviço/Plano', header_style),
            Paragraph('Emissão', header_style),
            Paragraph('Valor', header_style),
            Paragraph('Status', header_style)
        ]
        
        data = [headers]
        
        for c in contracts:
            data.append([
                Paragraph(str(c.get('id', '')), cell_style),
                Paragraph(c.get('cliente_nome', ''), cell_style),
                Paragraph(c.get('servico_descricao', ''), cell_style),
                Paragraph(c.get('created_at', ''), cell_style),
                Paragraph(f"R$ {c.get('valor_unitario', 0.0):.2f}", cell_style),
                Paragraph(c.get('status', ''), cell_style)
            ])
            
        # Ajuste de larguras (landscape A4 = ~27.7cm utilizáveis)
        table = Table(data, colWidths=[1.5*cm, 9*cm, 9*cm, 3*cm, 2.5*cm, 2.7*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_financial_report(
        empresa: Empresa,
        receivables: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> BytesIO:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=1*cm, leftMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
        elements = []
        styles = getSampleStyleSheet()
        
        # Estilos personalizados
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=1,
            spaceAfter=10
        )
        
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontSize=8,
            leading=10
        )

        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.whitesmoke,
            fontName='Helvetica-Bold'
        )

        elements.append(Paragraph(f"Relatório Financeiro - {empresa.nome_fantasia or empresa.razao_social}", title_style))
        
        # Filtros aplicados
        filter_text = f"Período: {filters.get('start_date', 'Início')} até {filters.get('end_date', 'Fim')}"
        if filters.get('status'):
            filter_text += f" | Status: {filters.get('status')}"
        elements.append(Paragraph(filter_text, styles['Normal']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Tabela de Dados
        headers = [
            Paragraph('ID', header_style),
            Paragraph('Cliente', header_style),
            Paragraph('Tipo', header_style),
            Paragraph('Vencimento', header_style),
            Paragraph('Valor', header_style),
            Paragraph('Status', header_style),
            Paragraph('Pago Em', header_style)
        ]
        
        data = [headers]
        
        total_amount = 0.0
        for r in receivables:
            amount = r.get('amount', 0.0)
            total_amount += amount
            data.append([
                Paragraph(str(r.get('id', '')), cell_style),
                Paragraph(r.get('cliente_nome', ''), cell_style),
                Paragraph(r.get('tipo', ''), cell_style),
                Paragraph(r.get('due_date', ''), cell_style),
                Paragraph(f"R$ {amount:.2f}", cell_style),
                Paragraph(r.get('status', ''), cell_style),
                Paragraph(r.get('paid_at', '') or '-', cell_style)
            ])
            
        # Linha de Total
        data.append([
            '', Paragraph('TOTAL', header_style), '', '', 
            Paragraph(f"R$ {total_amount:.2f}", header_style), '', ''
        ])
            
        table = Table(data, colWidths=[1.5*cm, 8.5*cm, 3*cm, 3*cm, 3*cm, 3*cm, 3.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
