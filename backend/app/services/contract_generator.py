from mako.template import Template
from datetime import datetime
import os
from app.models.models import ServicoContratado, Cliente, Empresa, Servico

def format_currency(value):
    if value is None:
        return "0,00"
    return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

class DotDict(dict):
    """Permite acessar chaves de dicionário com sintaxe de ponto."""
    def __getattr__(self, name):
        if name in self:
            return self[name]
        return None

def generate_contract_html(contrato_data: dict, cliente: Cliente, empresa: Empresa, servico: Servico):
    """
    Gera o HTML do contrato preenchido.
    contrato_data: dict retornado pelo CRUD (com relacionamentos carregados)
    """
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'contrato_template.html')
    
    # Mako Template
    mytemplate = Template(filename=template_path)
    
    # Converter tudo para DotDict para o template usar sintaxe de ponto com segurança
    contrato_obj = DotDict(contrato_data)
    if 'ativos' in contrato_obj:
        contrato_obj['ativos'] = [DotDict(a) for a in contrato_obj['ativos']]
        
    cliente_obj = DotDict({k: v for k, v in cliente.__dict__.items() if not k.startswith('_')}) if cliente else DotDict()
    empresa_obj = DotDict({k: v for k, v in empresa.__dict__.items() if not k.startswith('_')}) if empresa else DotDict()
    servico_obj = DotDict({k: v for k, v in servico.__dict__.items() if not k.startswith('_')}) if servico else DotDict()
    
    # Data formatada em português
    meses = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
        7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    now = datetime.now()
    data_formatada = f"{now.day} de {meses[now.month]} de {now.year}"
    
    # Processar assinatura se existir
    assinado_em_formatado = None
    if contrato_obj.assinado_em:
        dt_ass = contrato_obj.assinado_em
        if isinstance(dt_ass, str):
            try:
                dt_ass = datetime.fromisoformat(dt_ass.replace('Z', '+00:00'))
            except:
                dt_ass = now
        assinado_em_formatado = f"{dt_ass.day} de {meses[dt_ass.month]} de {dt_ass.year} às {dt_ass.strftime('%H:%M:%S')}"
    
    # Garantir que URLs de arquivos da empresa sejam absolutas para o template
    from app.core.config import settings
    if empresa_obj.assinatura_digital_url and empresa_obj.assinatura_digital_url.startswith('/files'):
        empresa_obj.assinatura_digital_url = f"{settings.BACKEND_URL}{empresa_obj.assinatura_digital_url}"
    if empresa_obj.logo_url and empresa_obj.logo_url.startswith('/files'):
        empresa_obj.logo_url = f"{settings.BACKEND_URL}{empresa_obj.logo_url}"
        
    # Renderizar
    html_content = mytemplate.render(
        contrato=contrato_obj,
        cliente=cliente_obj,
        empresa=empresa_obj,
        servico=servico_obj,
        data_hoje=data_formatada,
        assinado_em_formatado=assinado_em_formatado,
        format_currency=format_currency,
        getattr=getattr # Passar getattr explicitamente para o contexto do template
    )
    
    return html_content
