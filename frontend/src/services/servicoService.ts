import api from './authService';

export interface Servico {
  id: number;
  empresa_id?: number;
  tipo: string;  // 'SERVICO' ou 'PLANO_INTERNET'
  cClass?: string;
  codigo?: string;
  descricao: string;
  unidade_medida?: string;
  valor_unitario?: number;
  cfop?: string;
  ncm?: string;
  base_calculo_icms_default?: number;
  aliquota_icms_default?: number;
  ativo?: boolean;
  upload_speed?: number;
  download_speed?: number;
  max_limit?: string;
  fidelity_months?: number;
  billing_cycle?: string;
  notes?: string;
  promotional_price?: number;
  promotional_months?: number;
  promotional_active?: boolean;
}

const getServicosByEmpresa = async (empresaId: number, signal?: AbortSignal): Promise<Servico[]> => {
  const response = await api.get(`/servicos/empresa/${empresaId}`, { params: { limit: 100 }, signal });
  return response.data;
};

export interface ServicoListResponse {
  total: number;
  servicos: Servico[];
}

const getServicosByEmpresaPaginated = async (empresaId: number, page: number, limit: number, q?: string, signal?: AbortSignal): Promise<ServicoListResponse> => {
  const skip = (page - 1) * limit;
  const params: any = { skip, limit };
  if (q) params.q = q;
  const response = await api.get(`/servicos/empresa/${empresaId}`, { params, signal });
  const data = response.data;
  // Backend returns array directly, total is in X-Total-Count header
  const total = parseInt(response.headers['x-total-count'] || data.length.toString());
  return { total, servicos: data };
};

const searchServicos = async (empresaId: number, q: string, limit: number = 20, signal?: AbortSignal): Promise<Servico[]> => {
  const response = await api.get(`/servicos/empresa/${empresaId}`, { params: { q, limit }, signal });
  return response.data;
};

const servicoService = {
  getServicosByEmpresa,
  getServicosByEmpresaPaginated,
  searchServicos,
  getServicoById: async (servicoId: number) => {
    const response = await api.get(`/servicos/${servicoId}`);
    return response.data;
  },
  createServico: async (empresaId: number, payload: Partial<Servico>) => {
    const response = await api.post(`/empresas/${empresaId}/servicos`, payload);
    return response.data;
  },
  updateServico: async (empresaId: number, servicoId: number, payload: Partial<Servico>) => {
    // empresaId included for permission/route; backend expects empresa-scoped endpoint
    const response = await api.put(`/empresas/${empresaId}/servicos/${servicoId}`, payload);
    return response.data;
  },
  deleteServico: async (empresaId: number, servicoId: number) => {
    const response = await api.delete(`/empresas/${empresaId}/servicos/${servicoId}`);
    return response.data;
  },
};

export default servicoService;
