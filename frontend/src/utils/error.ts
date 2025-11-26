export function stringifyError(e: any): string {
  try {
    const detail = e?.response?.data?.detail ?? e?.message ?? e;
    if (!detail) return 'Erro desconhecido';
    if (Array.isArray(detail)) {
      return detail.map(d => {
        if (typeof d === 'string') {
          return d;
        }
        if (d?.loc && d?.msg) {
          // Formatar erros de validação do Pydantic de forma mais amigável
          const field = d.loc[d.loc.length - 1]; // Último elemento do loc é o nome do campo
          
          // Mapeamento de campos para nomes amigáveis em português
          const fieldNames: { [key: string]: string } = {
            'cliente_id': 'Cliente',
            'servico_id': 'Plano de Internet',
            'valor_unitario': 'Valor Unitário',
            'quantidade': 'Quantidade',
            'dia_emissao': 'Dia de Emissão',
            'd_contrato_ini': 'Data de Início do Contrato',
            'd_contrato_fim': 'Data de Fim do Contrato',
            'data_instalacao': 'Data de Instalação',
            'dia_vencimento': 'Dia de Vencimento',
            'numero_contrato': 'Número do Contrato',
            'periodicidade': 'Periodicidade',
            'endereco_instalacao': 'Endereço de Instalação',
            'tipo_conexao': 'Tipo de Conexão',
            'velocidade_garantida': 'Velocidade Garantida',
            'sla_garantido': 'SLA Garantido',
            'periodo_carencia': 'Período de Carência',
            'multa_atraso_percentual': 'Multa por Atraso',
            'taxa_instalacao': 'Taxa de Instalação',
            'responsavel_tecnico': 'Responsável Técnico',
            'interface_id': 'Interface',
            'ip_class_id': 'Classe IP',
            'mac_address': 'Endereço MAC',
            'assigned_ip': 'IP Atribuído',
            'metodo_autenticacao': 'Método de Autenticação'
          };
          
          const friendlyFieldName = fieldNames[field] || field;
          
          // Traduzir mensagens comuns
          if (d.msg === 'Field required') {
            return `${friendlyFieldName} é obrigatório`;
          }
          if (d.msg.includes('should be greater than or equal to')) {
            return `${friendlyFieldName} deve ser maior ou igual a ${d.msg.split(' ').pop()}`;
          }
          if (d.msg.includes('should be less than or equal to')) {
            return `${friendlyFieldName} deve ser menor ou igual a ${d.msg.split(' ').pop()}`;
          }
          if (d.type === 'value_error' && d.ctx?.error) {
            // Para erros de validators customizados
            const errorMsg = d.ctx.error;
            if (typeof errorMsg === 'string') {
              // Mapear mensagens específicas
              if (errorMsg.includes('interface_id é obrigatório')) {
                return 'Interface é obrigatória';
              }
              if (errorMsg.includes('ip_class_id é obrigatório')) {
                return 'Classe IP é obrigatória';
              }
              if (errorMsg.includes('mac_address é obrigatório')) {
                return 'Endereço MAC é obrigatório';
              }
              if (errorMsg.includes('mac_address deve estar no formato')) {
                return 'Endereço MAC deve estar no formato AA:BB:CC:DD:EE:FF';
              }
              if (errorMsg.includes('assigned_ip é obrigatório')) {
                return 'IP Atribuído é obrigatório';
              }
              return errorMsg;
            }
          }
          
          return `${friendlyFieldName}: ${d.msg}`;
        }
        return d?.msg || JSON.stringify(d);
      }).join('; ');
    }
    if (typeof detail === 'object') {
      return detail.msg || detail.message || JSON.stringify(detail);
    }
    return String(detail);
  } catch (err) {
    return 'Erro ao processar mensagem de erro';
  }
}
