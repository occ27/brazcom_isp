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
        
    # Renderizar
    html_content = mytemplate.render(
        contrato=contrato_obj,
        cliente=cliente_obj,
        empresa=empresa_obj,
        servico=servico_obj,
        data_hoje=data_formatada,
        format_currency=format_currency,
        getattr=getattr # Passar getattr explicitamente para o contexto do template
    )
    
    return html_content
