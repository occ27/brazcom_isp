import api from './authService';

export interface ContractsFiltersData {
  routers: { id: number; nome: string }[];
  ip_classes: { id: number; name: string }[];
  interfaces: { id: number; name: string; router_id: number }[];
}

export const reportService = {
  generateContractsPdf: async (
    empresaId: number, 
    params: { 
      start_date?: string; 
      end_date?: string; 
      status?: string;
      municipio?: string;
      bairro?: string[];
      router_id?: number;
      interface_id?: number;
      ip_class_id?: number;
    }
  ) => {
    const searchParams = new URLSearchParams();
    searchParams.append('empresa_id', String(empresaId));
    if (params.start_date) searchParams.append('start_date', params.start_date);
    if (params.end_date) searchParams.append('end_date', params.end_date);
    if (params.status) searchParams.append('status', params.status);
    if (params.municipio) searchParams.append('municipio', params.municipio);
    if (params.bairro) {
      params.bairro.forEach(b => searchParams.append('bairro', b));
    }
    if (params.router_id) searchParams.append('router_id', String(params.router_id));
    if (params.interface_id) searchParams.append('interface_id', String(params.interface_id));
    if (params.ip_class_id) searchParams.append('ip_class_id', String(params.ip_class_id));

    const response = await api.get(`/reports/contracts/pdf?${searchParams.toString()}`, {
      responseType: 'blob'
    });
    return response.data;
  },
  
  generateFinancialPdf: async (
    empresaId: number, 
    params: { 
      start_date?: string; 
      end_date?: string; 
      status?: string;
      date_type?: string;
      municipio?: string;
      bairro?: string[];
    }
  ) => {
    const searchParams = new URLSearchParams();
    searchParams.append('empresa_id', String(empresaId));
    if (params.start_date) searchParams.append('start_date', params.start_date);
    if (params.end_date) searchParams.append('end_date', params.end_date);
    if (params.status) searchParams.append('status', params.status);
    if (params.date_type) searchParams.append('date_type', params.date_type);
    if (params.municipio) searchParams.append('municipio', params.municipio);
    if (params.bairro) {
      params.bairro.forEach(b => searchParams.append('bairro', b));
    }

    const response = await api.get(`/reports/financial/pdf?${searchParams.toString()}`, {
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
  },

  getContractsFilters: async (empresaId: number): Promise<ContractsFiltersData> => {
    const response = await api.get('/reports/contracts/filters', {
      params: { empresa_id: empresaId }
    });
    return response.data;
  }
};

export default reportService;
