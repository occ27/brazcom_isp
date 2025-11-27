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
  is_active?: boolean;

  // Novos campos específicos para ISPs
  status?: 'ATIVO' | 'SUSPENSO' | 'CANCELADO' | 'PENDENTE_INSTALACAO';
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

  // Novos campos para configuração de rede
  router_id?: number;
  interface_id?: number;
  ip_class_id?: number;
  mac_address?: string;
  assigned_ip?: string;
  metodo_autenticacao?: 'IP_MAC' | 'PPPOE' | 'HOTSPOT' | 'RADIUS';

  // Campos específicos para autenticação PPPoE
  pppoe_username?: string;
  pppoe_password?: string;

  // Related data
  cliente_nome?: string;
  cliente_razao_social?: string;
  cliente_cpf_cnpj?: string;
  cliente_telefone?: string;
  cliente_municipio?: string;
  cliente_uf?: string;
  servico_descricao?: string;
  servico_codigo?: string;
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
  ativarServico: async (contratoId: number) => {
    const response = await api.put(`/servicos-contratados/${contratoId}/ativar`);
    return response.data;
  },
  resetConnection: async (contratoId: number) => {
    const response = await api.put(`/servicos-contratados/${contratoId}/reset-connection`);
    return response.data;
  }
};

export default contratoService;
