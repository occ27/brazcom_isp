import api from './authService';

export const reportService = {
  generateContractsPdf: async (empresaId: number, params: { start_date?: string; end_date?: string; status?: string }) => {
    const response = await api.get('/reports/contracts/pdf', {
      params: { ...params, empresa_id: empresaId },
      responseType: 'blob'
    });
    return response.data;
  },
  
  generateFinancialPdf: async (empresaId: number, params: { start_date?: string; end_date?: string; status?: string }) => {
    const response = await api.get('/reports/financial/pdf', {
      params: { ...params, empresa_id: empresaId },
      responseType: 'blob'
    });
    return response.data;
  },
  
  generateClientsPdf: async (empresaId: number, params: { q?: string; municipio?: string; bairro?: string[] }) => {
    const searchParams = new URLSearchParams();
    searchParams.append('empresa_id', String(empresaId));
    if (params.q) searchParams.append('q', params.q);
    if (params.municipio) searchParams.append('municipio', params.municipio);
    if (params.bairro) {
      params.bairro.forEach(b => searchParams.append('bairro', b));
    }
    const response = await api.get(`/reports/clients/pdf?${searchParams.toString()}`, {
      responseType: 'blob'
    });
    return response.data;
  },

  getClientsLocations: async (empresaId: number): Promise<Record<string, string[]>> => {
    const response = await api.get('/reports/clients/locations', {
      params: { empresa_id: empresaId }
    });
    return response.data;
  }
};

export default reportService;
