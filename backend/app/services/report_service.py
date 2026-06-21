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
        
        address_style = ParagraphStyle('AddressStyle', parent=styles['Normal'], fontSize=7, leading=9, textColor=colors.grey)

        filter_text = f"Período: {filters.get('start_date', 'Início')} até {filters.get('end_date', 'Fim')}"
        if filters.get('status'):
            filter_text += f" | Status: {filters.get('status')}"
            
        filter_parts = []
        if filters.get('municipio'):
            filter_parts.append(f"Cidade: {filters.get('municipio')}")
        if filters.get('bairro'):
            b_list = filters.get('bairro')
            if isinstance(b_list, list):
                filter_parts.append(f"Bairros: {', '.join(b_list)}")
            else:
                filter_parts.append(f"Bairro: {b_list}")
        if filters.get('router'):
            filter_parts.append(f"Concentrador: {filters.get('router')}")
        if filters.get('interface'):
            filter_parts.append(f"Interface: {filters.get('interface')}")
        if filters.get('ip_class'):
            filter_parts.append(f"Classe IP: {filters.get('ip_class')}")
        if filter_parts:
            filter_text += f" | {' | '.join(filter_parts)}"
            
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
                Paragraph('Cliente / Endereço / Conexão', header_style),
                Paragraph('Emissão', header_style),
                Paragraph('Valor', header_style),
                Paragraph('Status', header_style)
            ]
            
            data = [headers]
            plan_total = 0.0
            for c in plan_contracts:
                val = c.get('valor_unitario', 0.0)
                plan_total += val
                
                # Montar bloco de metadados
                sub_parts = []
                if c.get('municipio') or c.get('bairro'):
                    sub_parts.append(f"{c.get('bairro', 'Sem Bairro')} ({c.get('municipio', '')})")
                if c.get('endereco_completo'):
                    sub_parts.append(c.get('endereco_completo'))
                
                net_parts = []
                if c.get('ip_address'):
                    net_parts.append(f"IP: {c.get('ip_address')}")
                if c.get('router_nome'):
                    net_parts.append(f"Concentrador: {c.get('router_nome')}")
                if c.get('interface_nome'):
                    net_parts.append(f"Interface: {c.get('interface_nome')}")
                    
                client_cell = [
                    Paragraph(f"<b>{c.get('cliente_nome', '')}</b>", cell_style)
                ]
                if sub_parts:
                    client_cell.append(Paragraph(f"End: {' - '.join(sub_parts)}", address_style))
                if net_parts:
                    client_cell.append(Paragraph(f"Rede: {' | '.join(net_parts)}", address_style))

                data.append([
                    Paragraph(str(c.get('id', '')), cell_style),
                    client_cell,
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
        
        address_style = ParagraphStyle('AddressStyle', parent=styles['Normal'], fontSize=7, leading=9, textColor=colors.grey)

        filter_text = f"Período: {filters.get('start_date', 'Início')} até {filters.get('end_date', 'Fim')}"
        if filters.get('status'):
            filter_text += f" | Status: {filters.get('status')}"
            
        filter_parts = []
        if filters.get('municipio'):
            filter_parts.append(f"Cidade: {filters.get('municipio')}")
        if filters.get('bairro'):
            b_list = filters.get('bairro')
            if isinstance(b_list, list):
                filter_parts.append(f"Bairros: {', '.join(b_list)}")
            else:
                filter_parts.append(f"Bairro: {b_list}")
        if filters.get('q'):
            filter_parts.append(f"Busca: {filters.get('q')}")
        if filter_parts:
            filter_text += f" | {' | '.join(filter_parts)}"
            
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
                Paragraph('Cliente / Endereço', header_style),
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
                
                # Montar bloco de endereço
                sub_parts = []
                if r.get('municipio') or r.get('bairro'):
                    sub_parts.append(f"{r.get('bairro', 'Sem Bairro')} ({r.get('municipio', '')})")
                if r.get('endereco_completo'):
                    sub_parts.append(r.get('endereco_completo'))
                    
                client_cell = [
                    Paragraph(f"<b>{r.get('cliente_nome', '')}</b>", cell_style)
                ]
                if sub_parts:
                    client_cell.append(Paragraph(f"End: {' - '.join(sub_parts)}", address_style))

                data.append([
                    Paragraph(str(r.get('id', '')), cell_style),
                    client_cell,
                    Paragraph(r.get('tipo', ''), cell_style),
                    Paragraph(r.get('due_date', ''), cell_style),
                    Paragraph(f"R$ {amt:.2f}", cell_style),
                    Paragraph(f"R$ {p_amt:.2f}" if r.get('paid_amount') is not None else "-", cell_style),
                    Paragraph(r.get('status', ''), cell_style),
                    Paragraph(r.get('paid_at', '') or '-', cell_style)
                ])
            
            data.append(['', Paragraph('Subtotal do Grupo', cell_style), '', '', Paragraph(f"R$ {plan_total:.2f}", cell_style), Paragraph(f"R$ {plan_paid_total:.2f}", cell_style), '', ''])
                
            table = Table(data, colWidths=[1.6*cm, 9.0*cm, 2.9*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.8*cm, 3*cm])
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

    @staticmethod
    def generate_clients_report(
        empresa: Empresa,
        clients: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> BytesIO:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=1*cm, leftMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, alignment=1, spaceAfter=10)
        group_title_style = ParagraphStyle('GroupTitleStyle', parent=styles['Heading2'], fontSize=12, color=colors.darkblue, spaceBefore=10, spaceAfter=5)
        cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=9, leading=11)
        address_style = ParagraphStyle('AddressStyle', parent=styles['Normal'], fontSize=7, leading=9, textColor=colors.grey)
        header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=10, textColor=colors.whitesmoke, fontName='Helvetica-Bold')

        elements.append(Paragraph(f"Relatório de Clientes por Bairro - {empresa.nome_fantasia or empresa.razao_social}", title_style))
        
        filter_parts = []
        if filters.get('q'):
            filter_parts.append(f"Busca: {filters.get('q')}")
        if filters.get('municipio'):
            filter_parts.append(f"Cidade: {filters.get('municipio')}")
        if filters.get('bairro'):
            b_list = filters.get('bairro')
            if isinstance(b_list, list):
                filter_parts.append(f"Bairros: {', '.join(b_list)}")
            else:
                filter_parts.append(f"Bairro: {b_list}")
            
        if filter_parts:
            elements.append(Paragraph(f"Filtros aplicados: {' | '.join(filter_parts)}", styles['Normal']))
        
        elements.append(Spacer(1, 0.5*cm))
        
        # Agrupar por Bairro
        from collections import defaultdict
        grouped_clients = defaultdict(list)
        for c in clients:
            grouped_clients[c['bairro']].append(c)
            
        for bairro, b_clients in sorted(grouped_clients.items()):
            elements.append(Paragraph(f"Bairro: {bairro}", group_title_style))
            
            headers = [
                Paragraph('ID', header_style),
                Paragraph('Cliente / Endereço', header_style),
                Paragraph('CPF / CNPJ', header_style),
                Paragraph('E-mail / Telefone', header_style),
                Paragraph('Cidade', header_style),
                Paragraph('Status', header_style)
            ]
            
            data = [headers]
            for c in b_clients:
                # Montar bloco de nome + endereço
                client_cell = [
                    Paragraph(f"<b>{c.get('nome_razao_social', '')}</b>", cell_style),
                    Paragraph(f"{c.get('endereco', '')}, {c.get('numero', '')} {c.get('complemento', '') or ''}", address_style)
                ]
                
                # Bloco de contato
                contact_cell = [
                    Paragraph(c.get('email', '') or '-', cell_style),
                    Paragraph(c.get('telefone', '') or '-', address_style)
                ]
                
                data.append([
                    Paragraph(str(c.get('id', '')), cell_style),
                    client_cell,
                    Paragraph(c.get('cpf_cnpj', ''), cell_style),
                    contact_cell,
                    Paragraph(f"{c.get('municipio', '')}/{c.get('uf', '')}", cell_style),
                    Paragraph("Ativo" if c.get('is_active') else "Inativo", cell_style)
                ])
                
            table = Table(data, colWidths=[1.2*cm, 10*cm, 4*cm, 6*cm, 4.5*cm, 2*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke])
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.5*cm))
        
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph(f"Total de registros: {len(clients)}", styles['Normal']))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_statement_report(
        empresa: Empresa,
        cliente: Cliente,
        receivables: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> BytesIO:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1*cm, leftMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, alignment=1, spaceAfter=10)
        client_title_style = ParagraphStyle('ClientTitleStyle', parent=styles['Heading2'], fontSize=11, color=colors.darkblue, spaceBefore=10, spaceAfter=5)
        cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=8, leading=10)
        header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=10, textColor=colors.whitesmoke, fontName='Helvetica-Bold')

        elements.append(Paragraph(f"Extrato Financeiro - {empresa.nome_fantasia or empresa.razao_social}", title_style))
        elements.append(Spacer(1, 0.2*cm))
        elements.append(Paragraph(f"<b>Cliente:</b> {cliente.nome_razao_social} (CPF/CNPJ: {cliente.cpf_cnpj or ''})", client_title_style))
        
        filter_text = f"Filtros aplicados - Contrato: {filters.get('contract_id', 'Todos')} | Status: {filters.get('status', 'Todos')}"
        elements.append(Paragraph(filter_text, styles['Normal']))
        elements.append(Spacer(1, 0.4*cm))

        # Calculate totals for summary box matching the frontend logic
        total_received = 0.0
        total_pending = 0.0
        for r in receivables:
            status = r.get('status', '')
            amt = r.get('amount', 0.0)
            p_amt = r.get('paid_amount', 0.0) if r.get('paid_amount') is not None else 0.0
            
            if status == 'PAID':
                total_received += p_amt if r.get('paid_amount') is not None else amt
            elif status != 'CANCELLED':
                total_pending += amt

        # Summary box layout
        summary_data = [
            [
                Paragraph("<b>Total Recebido:</b>", cell_style),
                Paragraph(f"R$ {total_received:.2f}", ParagraphStyle('RecStyle', parent=cell_style, textColor=colors.HexColor('#2e7d32'), fontName='Helvetica-Bold')),
                Paragraph("<b>Total Pendente:</b>", cell_style),
                Paragraph(f"R$ {total_pending:.2f}", ParagraphStyle('PendStyle', parent=cell_style, textColor=colors.HexColor('#ed6c02'), fontName='Helvetica-Bold'))
            ]
        ]
        summary_table = Table(summary_data, colWidths=[4.5*cm, 4.5*cm, 4.5*cm, 4.5*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.5*cm))
        
        headers = [
            Paragraph('Vencimento', header_style),
            Paragraph('Contrato', header_style),
            Paragraph('Método', header_style),
            Paragraph('Valor', header_style),
            Paragraph('Vlr Pago', header_style),
            Paragraph('Status', header_style)
        ]
        
        data = [headers]
        total_amount = 0.0
        total_paid = 0.0
        
        status_map_fin = {
            "PAID": "Pago",
            "OPEN": "Aberto",
            "CANCELLED": "Cancelado",
            "PENDING": "Pendente",
            "REJECTED": "Rejeitado"
        }

        for r in receivables:
            amt = r.get('amount', 0.0)
            p_amt = r.get('paid_amount', 0.0) if r.get('paid_amount') is not None else 0.0
            total_amount += amt
            total_paid += p_amt
            
            data.append([
                Paragraph(r.get('due_date', ''), cell_style),
                Paragraph(f"#{r.get('servico_contratado_id')}" if r.get('servico_contratado_id') else 'Avulso', cell_style),
                Paragraph(r.get('tipo', ''), cell_style),
                Paragraph(f"R$ {amt:.2f}", cell_style),
                Paragraph(f"R$ {p_amt:.2f}" if r.get('paid_amount') is not None else "-", cell_style),
                Paragraph(status_map_fin.get(r.get('status', ''), r.get('status', '')), cell_style)
            ])
            
        data.append([
            Paragraph('TOTAIS', cell_style),
            '',
            '',
            Paragraph(f"R$ {total_amount:.2f}", cell_style),
            Paragraph(f"R$ {total_paid:.2f}", cell_style),
            ''
        ])
            
        table = Table(data, colWidths=[3.5*cm, 2.5*cm, 3.5*cm, 3.2*cm, 3.2*cm, 3.1*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ]))
        elements.append(table)
        
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_caixa_session_report(
        empresa,
        sessao,
        usuario_nome: str,
        extrato: List[Any]
    ) -> BytesIO:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1*cm, leftMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, alignment=1, spaceAfter=10)
        subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Heading2'], fontSize=12, color=colors.darkblue, spaceBefore=5, spaceAfter=5)
        cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=8, leading=10)
        header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=10, textColor=colors.whitesmoke, fontName='Helvetica-Bold')

        elements.append(Paragraph(f"Relatório de Fechamento de Caixa - {empresa.nome_fantasia or empresa.razao_social}", title_style))
        elements.append(Spacer(1, 0.2*cm))
        
        # Resumo da Sessão
        sessao_info = [
            [Paragraph("<b>Caixa / Sessão:</b>", cell_style), Paragraph(f"#{sessao.id}", cell_style),
             Paragraph("<b>Status:</b>", cell_style), Paragraph(sessao.status, cell_style)],
            [Paragraph("<b>Operador:</b>", cell_style), Paragraph(usuario_nome, cell_style),
             Paragraph("<b>Local:</b>", cell_style), Paragraph(sessao.local_pagamento.nome if sessao.local_pagamento else '-', cell_style)],
            [Paragraph("<b>Abertura:</b>", cell_style), Paragraph(sessao.aberto_em.strftime('%d/%m/%Y %H:%M:%S') if sessao.aberto_em else '-', cell_style),
             Paragraph("<b>Fechamento:</b>", cell_style), Paragraph(sessao.fechado_em.strftime('%d/%m/%Y %H:%M:%S') if sessao.fechado_em else '-', cell_style)]
        ]
        
        info_table = Table(sessao_info, colWidths=[3*cm, 6*cm, 3*cm, 6*cm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.5*cm))
        
        # Resumo Financeiro
        total_entradas = sum([m.valor for m in extrato if m.tipo in ('SUPRIMENTO', 'RECEBIMENTO')])
        total_saidas = sum([m.valor for m in extrato if m.tipo == 'SANGRIA'])
        saldo_calc = sessao.saldo_inicial + total_entradas - total_saidas
        
        fin_info = [
            [
                Paragraph("<b>Saldo Inicial:</b>", cell_style), Paragraph(f"R$ {sessao.saldo_inicial:.2f}", cell_style),
                Paragraph("<b>Entradas:</b>", cell_style), Paragraph(f"R$ {total_entradas:.2f}", ParagraphStyle('In', parent=cell_style, textColor=colors.HexColor('#2e7d32')))
            ],
            [
                Paragraph("<b>Saídas (Sangria):</b>", cell_style), Paragraph(f"R$ {total_saidas:.2f}", ParagraphStyle('Out', parent=cell_style, textColor=colors.HexColor('#d32f2f'))),
                Paragraph("<b>Saldo Calculado:</b>", cell_style), Paragraph(f"R$ {saldo_calc:.2f}", ParagraphStyle('Calc', parent=cell_style, fontName='Helvetica-Bold')),
            ],
            [
                Paragraph("<b>Saldo Informado:</b>", cell_style), Paragraph(f"R$ {sessao.saldo_final:.2f}" if sessao.saldo_final is not None else '-', cell_style),
                Paragraph("<b>Diferença:</b>", cell_style), Paragraph(f"R$ {(sessao.saldo_final - saldo_calc):.2f}" if sessao.saldo_final is not None else '-', cell_style)
            ]
        ]
        
        fin_table = Table(fin_info, colWidths=[3*cm, 6*cm, 3*cm, 6*cm])
        fin_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdbdbd')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(Paragraph("Resumo Financeiro", subtitle_style))
        elements.append(fin_table)
        elements.append(Spacer(1, 0.5*cm))

        # Extrato de Movimentações
        elements.append(Paragraph("Extrato de Movimentações", subtitle_style))
        
        headers = [
            Paragraph('Data/Hora', header_style),
            Paragraph('Tipo', header_style),
            Paragraph('Forma Pgto', header_style),
            Paragraph('Descrição', header_style),
            Paragraph('Valor', header_style)
        ]
        
        data = [headers]
        
        for m in extrato:
            data.append([
                Paragraph(m.created_at.strftime('%d/%m/%Y %H:%M') if m.created_at else '', cell_style),
                Paragraph(m.tipo, cell_style),
                Paragraph(m.forma_pagamento.nome if m.forma_pagamento else '-', cell_style),
                Paragraph(m.descricao or '-', cell_style),
                Paragraph(f"{'+' if m.tipo in ('RECEBIMENTO', 'SUPRIMENTO') else '-'} R$ {m.valor:.2f}", 
                          ParagraphStyle('Val', parent=cell_style, textColor=colors.HexColor('#2e7d32') if m.tipo in ('RECEBIMENTO', 'SUPRIMENTO') else colors.HexColor('#d32f2f')))
            ])
            
        table = Table(data, colWidths=[3*cm, 2.5*cm, 3.5*cm, 6.5*cm, 2.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke])
        ]))
        elements.append(table)
        
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
