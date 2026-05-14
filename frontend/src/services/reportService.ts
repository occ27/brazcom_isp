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
  }
};

export default reportService;
