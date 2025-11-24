import { Cliente } from '../types';
import { Servico } from './servicoService';

// Interfaces based on the backend models (can be moved to a types file)
export interface NFComItemCreate {
  cClass: string;
  codigo_servico: string;
  descricao_servico: string;
  quantidade: number;
  unidade_medida: string;
  valor_unitario: number;
  valor_desconto: number;
  valor_outros: number;
  valor_total: number;
  servico_id?: number;
  cfop?: string;
  ncm?: string;
  base_calculo_icms?: number;
  aliquota_icms?: number;
  base_calculo_pis?: number;
  aliquota_pis?: number;
  base_calculo_cofins?: number;
  aliquota_cofins?: number;
}

export interface NFComFaturaCreate {
  numero_fatura: string;
  data_vencimento: string; // ISO date
  valor_fatura: number;
  codigo_barras?: string | null;
}

export interface NFComItem extends NFComItemCreate {
    id: number;
    servico?: Servico;
}

export interface NFComCreate {
  cliente_id: number | null;
  cMunFG: string;
  finalidade_emissao: string;
  tpFat: string;
  data_emissao: string;
  // Campos contratuais no nível da NFCom (snapshot quando aplicável)
  numero_contrato?: string;
  d_contrato_ini?: string;
  d_contrato_fim?: string;
  itens: NFComItemCreate[];
  faturas?: NFComFaturaCreate[];
  valor_total: number;
  informacoes_adicionais?: string;

  // Endereço do destinatário (snapshot)
  dest_endereco: string;
  dest_numero: string;
  dest_complemento?: string | null;
  dest_bairro: string;
  dest_municipio: string;
  dest_uf: string;
  dest_cep: string;
  dest_codigo_ibge: string;
}

export interface NFCom extends NFComCreate {
  id: number;
  empresa_id: number;
  numero_nf: number;
  serie: number;
  chave_acesso: string | null;
  protocolo_autorizacao: string | null;
  data_autorizacao: string | null;
  pdf_url?: string;
  xml_url?: string | null;
  cliente?: Cliente;
  itens: NFComItem[];
}

export interface NFComListResponse {
  total: number;
  nfcoms: NFCom[];
  total_geral_valor: number;
  total_autorizadas: number;
  total_pendentes: number;
  total_canceladas: number;
}

const createNFCom = async (companyId: number, nfcomData: NFComCreate): Promise<NFCom> => {
  try {
    const url = `/empresas/${companyId}/nfcom`;
    console.log('createNFCom URL:', url);
    const response = await (await import('./authService')).default.post(url, nfcomData);
    return response.data;
  } catch (err) {
    throw err;
  }
};

const updateNFCom = async (empresaId: number, nfcomId: number, nfcomData: NFComCreate): Promise<NFCom> => {
    try {
      const response = await (await import('./authService')).default.put(`/empresas/${empresaId}/nfcom/${nfcomId}`, nfcomData);
      return response.data;
    } catch (err) {
      throw err;
    }
  };

const getNFComsByCompany = async (
  companyId: number,
  page: number,
  limit: number,
  filters?: {
    search?: string;
    date_from?: string;
    date_to?: string;
    status?: 'authorized' | 'pending';
    min_value?: number;
    max_value?: number;
    order_by?: string;
    order_direction?: 'asc' | 'desc';
  }
): Promise<NFComListResponse> => {
  try {
    const skip = (page - 1) * limit;
    const params: any = { skip, limit };

    if (filters) {
      if (filters.search) params.search = filters.search;
      if (filters.date_from) params.date_from = filters.date_from;
      if (filters.date_to) params.date_to = filters.date_to;
      if (filters.status) params.status = filters.status;
      if (filters.min_value !== undefined) params.min_value = filters.min_value;
      if (filters.max_value !== undefined) params.max_value = filters.max_value;
      if (filters.order_by) params.order_by = filters.order_by;
      if (filters.order_direction) params.order_direction = filters.order_direction;
    }

    const response = await (await import('./authService')).default.get(`/empresas/${companyId}/nfcom`, {
      params
    });
    return response.data;
  } catch (err) {
    throw err;
  }
};

const getNFComById = async (empresaId: number, nfcomId: number): Promise<NFCom> => {
  try {
    const response = await (await import('./authService')).default.get(`/empresas/${empresaId}/nfcom/${nfcomId}`);
    return response.data;
  } catch (err) {
    throw err;
  }
};

const deleteNFCom = async (empresaId: number, nfcomId: number): Promise<void> => {
  try {
    const response = await (await import('./authService')).default.delete(`/empresas/${empresaId}/nfcom/${nfcomId}`);
    return response.data;
  } catch (err) {
    throw err;
  }
};

const nfcomService = {
  createNFCom,
  updateNFCom,
  getNFComsByCompany,
  getNFComById,
  deleteNFCom,
  // Emissão em massa a partir de contratos
  bulkEmitFromContracts: async (companyId: number, contractIds: number[], execute = false, transmit = false) => {
    try {
      const payload = { contract_ids: contractIds, execute, transmit };
      const response = await (await import('./authService')).default.post(`/empresas/${companyId}/nfcom/bulk-emit`, payload);
      return response.data;
    } catch (err) {
      throw err;
    }
  },
  cancelNFCom: async (companyId: number, nfcomId: number, payload: { nProt: string; xJust: string }) => {
    try {
      const response = await (await import('./authService')).default.post(`/empresas/${companyId}/nfcom/${nfcomId}/cancelar`, payload);
      return response.data;
    } catch (err) {
      throw err;
    }
  },
  sendEmails: async (companyId: number, nfcomIds: number[]) => {
    try {
      const payload = { nfcom_ids: nfcomIds };
      const response = await (await import('./authService')).default.post(`/empresas/${companyId}/nfcom/send-emails`, payload);
      return response.data;
    } catch (err) {
      throw err;
    }
  },
  getEmailStatuses: async (companyId: number, nfcomIds: number[]) => {
    try {
      const q = nfcomIds.join(',');
      const response = await (await import('./authService')).default.get(`/empresas/${companyId}/nfcom/email-status`, { params: { nfcom_ids: q } });
      return response.data as Record<number, { status: string; error_message?: string | null; sent_at?: string | null }>;
    } catch (err) {
      throw err;
    }
  },
  downloadZip: async (companyId: number, nfcomIds: number[], type: 'xml' | 'danfe') => {
    try {
      const payload = { nfcom_ids: nfcomIds, type };
      const response = await (await import('./authService')).default.post(`/empresas/${companyId}/nfcom/download-zip`, payload, { responseType: 'blob' });
      return response;
    } catch (err) {
      throw err;
    }
  },
  // Transmitir várias NFComs em lote. Backend irá transmitir em ordem e parar no primeiro erro.
  bulkTransmit: async (companyId: number, nfcomIds: number[]) => {
    try {
      const payload = { nfcom_ids: nfcomIds };
      const response = await (await import('./authService')).default.post(`/empresas/${companyId}/nfcom/bulk-transmit`, payload);
      return response.data;
    } catch (err) {
      throw err;
    }
  },
};

export default nfcomService;