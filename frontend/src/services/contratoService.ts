import api from './authService';

export interface Contrato {
  id: number;
  empresa_id?: number;
  cliente_id: number;
  servico_id: number;
  numero_contrato?: string;
  d_contrato_ini?: string;
  d_contrato_fim?: string;
  vencimento?: string; // legacy ISO date for invoice due date (kept for compatibility)
  dia_vencimento?: number; // day of month for invoice due date (1-31)
  periodicidade?: string;
  dia_emissao?: number;
  quantidade?: number;
  valor_unitario?: number;
  valor_total?: number;
  auto_emit?: boolean;
  auto_emit_nfcom?: boolean;
  is_active?: boolean;

  // Novos campos específicos para ISPs
  status?: 'ATIVO' | 'SUSPENSO' | 'CANCELADO' | 'PENDENTE_INSTALACAO' | 'AGUARDANDO_ASSINATURA';
  endereco_id?: number;
  endereco_instalacao?: string;
  tipo_conexao?: 'FIBRA' | 'RADIO' | 'CABO' | 'SATELITE' | 'ADSL' | 'OUTRO';
  coordenadas_gps?: string;
  data_instalacao?: string;
  responsavel_tecnico?: string;
  periodo_carencia?: number;
  multa_atraso_percentual?: number;
  taxa_instalacao?: number;
  taxa_instalacao_paga?: boolean;
  sla_garantido?: number;
  velocidade_garantida?: string;
  subscription_id?: number;

  router_id?: number;
  interface_id?: number;
  ip_class_id?: number;
  mac_address?: string;
  assigned_ip?: string;
  metodo_autenticacao?: 'IP_MAC' | 'PPPOE' | 'HOTSPOT' | 'RADIUS';

  // Informações de instalação de Fibra Óptica (FTTH)
  onu_serial?: string;
  onu_modelo?: string;
  onu_sinal?: string;
  olt_nome?: string;
  olt_pon?: string;
  cto_nome?: string;
  cto_porta?: string;
  metragem_drop?: number;
  vlan_id?: number;

  // Campos específicos para assinatura digital
  assinatura_token?: string;
  assinado_em?: string;
  assinatura_ip?: string;
  assinatura_data?: string;

  // Campos específicos para autenticação PPPoE
  pppoe_username?: string;
  pppoe_password?: string;

  // Ativos (Equipamentos) relacionados
  ativos?: AtivoContrato[];
  
  // Documentação Jurídica
  contrato_anatel_url?: string;

  // Relacionamento com conta bancária para cobrança
  bank_account_id?: number;
  payment_method?: 'BOLETO' | 'MERCADO_PAGO';
  observacoes_instalacao?: string;

  // Related data
  cliente_nome?: string;
  cliente_razao_social?: string;
  cliente_cpf_cnpj?: string;
  cliente_telefone?: string;
  cliente_municipio?: string;
  cliente_uf?: string;
  servico_descricao?: string;
  servico_codigo?: string;
  bank_account_bank?: string;
  bank_account_agencia?: string;
  bank_account_conta?: string;
}

export interface AtivoContrato {
  id?: number;
  contrato_id?: number;
  tipo_equipamento: string;
  modelo?: string;
  patrimonio?: string;
  serial_number?: string;
  login_acesso?: string;
  senha_acesso?: string;
  is_comodato: boolean;
  observacoes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ContratoListResponse {
  total: number;
  contratos: Contrato[];
}

const getContratosByEmpresa = async (empresaId: number, signal?: AbortSignal): Promise<Contrato[]> => {
  const response = await api.get(`/servicos-contratados/empresa/${empresaId}`, { signal });
  return response.data;
};

const getContratosByEmpresaPaginated = async (empresaId: number, page: number, limit: number, q?: string, diaVencimentoMin?: number, diaVencimentoMax?: number, signal?: AbortSignal): Promise<ContratoListResponse> => {
  const skip = (page - 1) * limit;
  const params: any = { skip, limit };
  if (q) params.q = q;
  if (diaVencimentoMin !== undefined) params.dia_vencimento_min = diaVencimentoMin;
  if (diaVencimentoMax !== undefined) params.dia_vencimento_max = diaVencimentoMax;
  const response = await api.get(`/servicos-contratados/empresa/${empresaId}`, { params, signal });
  const data = response.data;
  // Backend returns array directly, total is in X-Total-Count header
  const total = parseInt(response.headers['x-total-count'] || data.length.toString());
  return { total, contratos: data };
};

const contratoService = {
  getContratosByEmpresa,
  getContratosByEmpresaPaginated,
  createContrato: async (empresaId: number, payload: Partial<Contrato>) => {
    const response = await api.post(`/servicos-contratados/empresa/${empresaId}`, payload);
    return response.data;
  },
  updateContrato: async (empresaId: number, contratoId: number, payload: Partial<Contrato>) => {
    const response = await api.put(`/servicos-contratados/empresa/${empresaId}/${contratoId}`, payload);
    return response.data;
  },
  deleteContrato: async (empresaId: number, contratoId: number) => {
    const response = await api.delete(`/servicos-contratados/empresa/${empresaId}/${contratoId}`);
    return response.data;
  },
  ativarServico: async (id: number) => {
    const response = await api.put(`/servicos-contratados/${id}/ativar`);
    return response.data;
  },
  suspenderServico: async (id: number) => {
    const response = await api.put(`/servicos-contratados/${id}/suspender`);
    return response.data;
  },
  resetConnection: async (id: number) => {
    const response = await api.put(`/servicos-contratados/${id}/reset-connection`);
    return response.data;
  },
  syncRouter: async (id: number) => {
    const response = await api.post(`/servicos-contratados/${id}/sync-router`);
    return response.data;
  },
  reiniciarAssinatura: async (id: number) => {
    const response = await api.post(`/servicos-contratados/${id}/reiniciar-assinatura`);
    return response.data;
  },
  async getContratoById(id: number): Promise<Contrato> {
    const res = await api.get(`/servicos-contratados/${id}`);
    return res.data;
  },
  async getContratoTermoUrl(empresaId: number, contratoId: number): Promise<string> {
    const response = await api.get(`/servicos-contratados/${contratoId}/contrato-html`, { 
      responseType: 'text' 
    });
    const blob = new Blob([response.data], { type: 'text/html' });
    return URL.createObjectURL(blob);
  }
};

export default contratoService;
