import os
from datetime import datetime
from typing import List, Optional, Any, Dict
from io import BytesIO
from collections import defaultdict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
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
        title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, alignment=1, spaceAfter=10)
        group_title_style = ParagraphStyle('GroupTitleStyle', parent=styles['Heading2'], fontSize=12, color=colors.darkblue, spaceBefore=10, spaceAfter=5)
        cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=8, leading=10, wordWrap='LTR')
        header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=10, textColor=colors.whitesmoke, fontName='Helvetica-Bold')
        summary_style = ParagraphStyle('SummaryStyle', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold', spaceBefore=10)

        elements.append(Paragraph(f"Relatório de Contratos - {empresa.nome_fantasia or empresa.razao_social}", title_style))
        
        filter_text = f"Período: {filters.get('start_date', 'Início')} até {filters.get('end_date', 'Fim')}"
        if filters.get('status'):
            filter_text += f" | Status: {filters.get('status')}"
        elements.append(Paragraph(filter_text, styles['Normal']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Agrupamento por Plano
        grouped_contracts = defaultdict(list)
        summary_data = defaultdict(lambda: {'count': 0, 'total_value': 0.0})
        
        for c in contracts:
            plan_name = c.get('servico_descricao', 'Sem Plano')
            grouped_contracts[plan_name].append(c)
            summary_data[plan_name]['count'] += 1
            summary_data[plan_name]['total_value'] += c.get('valor_unitario', 0.0)

        # Iterar sobre grupos
        for plan_name, plan_contracts in sorted(grouped_contracts.items()):
            elements.append(Paragraph(f"Plano: {plan_name}", group_title_style))
            
            headers = [
                Paragraph('ID', header_style),
                Paragraph('Cliente', header_style),
                Paragraph('Emissão', header_style),
                Paragraph('Valor', header_style),
                Paragraph('Status', header_style)
            ]
            
            data = [headers]
            plan_total = 0.0
            for c in plan_contracts:
                val = c.get('valor_unitario', 0.0)
                plan_total += val
                data.append([
                    Paragraph(str(c.get('id', '')), cell_style),
                    Paragraph(c.get('cliente_nome', ''), cell_style),
                    Paragraph(c.get('created_at', ''), cell_style),
                    Paragraph(f"R$ {val:.2f}", cell_style),
                    Paragraph(c.get('status', ''), cell_style)
                ])
            
            # Linha de subtotal do plano
            data.append(['', Paragraph('Subtotal do Plano', cell_style), '', Paragraph(f"R$ {plan_total:.2f}", cell_style), ''])
                
            table = Table(data, colWidths=[1.5*cm, 12*cm, 4*cm, 4*cm, 5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.5*cm))

        # Página de Resumo
        elements.append(PageBreak())
        elements.append(Paragraph("Resumo Detalhado por Plano", title_style))
        elements.append(Spacer(1, 0.5*cm))
        
        summary_table_data = [[
            Paragraph('Plano', header_style),
            Paragraph('Qtd. Contratos', header_style),
            Paragraph('Valor Mensal Total', header_style)
        ]]
        
        grand_total_qty = 0
        grand_total_value = 0.0
        
        for plan_name, stats in sorted(summary_data.items()):
            grand_total_qty += stats['count']
            grand_total_value += stats['total_value']
            summary_table_data.append([
                Paragraph(plan_name, cell_style),
                Paragraph(str(stats['count']), cell_style),
                Paragraph(f"R$ {stats['total_value']:.2f}", cell_style)
            ])
            
        summary_table_data.append([
            Paragraph('TOTAL GERAL', header_style),
            Paragraph(str(grand_total_qty), header_style),
            Paragraph(f"R$ {grand_total_value:.2f}", header_style)
        ])
        
        summary_table = Table(summary_table_data, colWidths=[12*cm, 6*cm, 6*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgrey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.black),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(summary_table)
        
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
        
        title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, alignment=1, spaceAfter=10)
        group_title_style = ParagraphStyle('GroupTitleStyle', parent=styles['Heading2'], fontSize=12, color=colors.darkgreen, spaceBefore=10, spaceAfter=5)
        cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=8, leading=10)
        header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=10, textColor=colors.whitesmoke, fontName='Helvetica-Bold')

        elements.append(Paragraph(f"Relatório Financeiro - {empresa.nome_fantasia or empresa.razao_social}", title_style))
        
        filter_text = f"Período: {filters.get('start_date', 'Início')} até {filters.get('end_date', 'Fim')}"
        if filters.get('status'):
            filter_text += f" | Status: {filters.get('status')}"
        elements.append(Paragraph(filter_text, styles['Normal']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Agrupamento por Plano (Serviço)
        grouped_fin = defaultdict(list)
        status_summary = defaultdict(lambda: {'count': 0, 'total': 0.0, 'paid_total': 0.0})
        
        for r in receivables:
            plan_name = r.get('servico_nome', 'Avulso/Outros')
            grouped_fin[plan_name].append(r)
            status_summary[r.get('status', 'Indefinido')]['count'] += 1
            status_summary[r.get('status', 'Indefinido')]['total'] += r.get('amount', 0.0)
            status_summary[r.get('status', 'Indefinido')]['paid_total'] += r.get('paid_amount', 0.0) if r.get('paid_amount') is not None else 0.0

        for plan_name, items in sorted(grouped_fin.items()):
            elements.append(Paragraph(f"Plano: {plan_name}", group_title_style))
            
            headers = [
                Paragraph('ID', header_style),
                Paragraph('Cliente', header_style),
                Paragraph('Tipo', header_style),
                Paragraph('Vencimento', header_style),
                Paragraph('Valor', header_style),
                Paragraph('Vlr Pago', header_style),
                Paragraph('Status', header_style),
                Paragraph('Pago Em', header_style)
            ]
            
            data = [headers]
            plan_total = 0.0
            plan_paid_total = 0.0
            for r in items:
                amt = r.get('amount', 0.0)
                p_amt = r.get('paid_amount', 0.0) if r.get('paid_amount') is not None else 0.0
                plan_total += amt
                plan_paid_total += p_amt
                data.append([
                    Paragraph(str(r.get('id', '')), cell_style),
                    Paragraph(r.get('cliente_nome', ''), cell_style),
                    Paragraph(r.get('tipo', ''), cell_style),
                    Paragraph(r.get('due_date', ''), cell_style),
                    Paragraph(f"R$ {amt:.2f}", cell_style),
                    Paragraph(f"R$ {p_amt:.2f}" if r.get('paid_amount') is not None else "-", cell_style),
                    Paragraph(r.get('status', ''), cell_style),
                    Paragraph(r.get('paid_at', '') or '-', cell_style)
                ])
            
            data.append(['', Paragraph('Subtotal do Grupo', cell_style), '', '', Paragraph(f"R$ {plan_total:.2f}", cell_style), Paragraph(f"R$ {plan_paid_total:.2f}", cell_style), '', ''])
                
            table = Table(data, colWidths=[1.2*cm, 6.8*cm, 2.5*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.8*cm, 3*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.5*cm))

        # Página de Resumo Financeiro
        elements.append(PageBreak())
        elements.append(Paragraph("Resumo por Status Financeiro", title_style))
        elements.append(Spacer(1, 0.5*cm))
        
        sum_data = [[
            Paragraph('Status', header_style),
            Paragraph('Qtd. Títulos', header_style),
            Paragraph('Valor Total Devido', header_style),
            Paragraph('Valor Total Pago', header_style)
        ]]
        
        g_qty = 0
        g_total = 0.0
        g_paid_total = 0.0
        for stat, s_data in sorted(status_summary.items()):
            g_qty += s_data['count']
            g_total += s_data['total']
            g_paid_total += s_data['paid_total']
            sum_data.append([
                Paragraph(stat, cell_style),
                Paragraph(str(s_data['count']), cell_style),
                Paragraph(f"R$ {s_data['total']:.2f}", cell_style),
                Paragraph(f"R$ {s_data['paid_total']:.2f}", cell_style)
            ])
            
        sum_data.append([
            Paragraph('TOTAL GERAL', header_style),
            Paragraph(str(g_qty), header_style),
            Paragraph(f"R$ {g_total:.2f}", header_style),
            Paragraph(f"R$ {g_paid_total:.2f}", header_style)
        ])
        
        sum_table = Table(sum_data, colWidths=[9*cm, 5*cm, 5*cm, 5*cm])
        sum_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgrey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.black),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        elements.append(sum_table)
        
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
