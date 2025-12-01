import api from './authService';

export interface Receivable {
  id: number;
  empresa_id: number;
  cliente_id: number;
  servico_contratado_id?: number;
  nfcom_fatura_id?: number;
  tipo: string;
  issue_date: string;
  due_date: string;
  amount: number;
  discount: number;
  interest_percent: number;
  fine_percent: number;
  bank: string;
  carteira?: string;
  agencia?: string;
  conta?: string;
  nosso_numero?: string;
  bank_registration_id?: string;
  codigo_barras?: string;
  linha_digitavel?: string;
  status: string;
  registered_at?: string;
  printed_at?: string;
  sent_at?: string;
  paid_at?: string;
  registro_result?: string;
  pdf_url?: string;
  bank_account_id?: number;
  bank_account_snapshot?: string;
  bank_payload?: string;
  created_at: string;
  updated_at?: string;
}

const listReceivables = async (empresaId: number, skip = 0, limit = 100) => {
  const resp = await api.get(`/receivables/empresa/${empresaId}`, { params: { skip, limit } });
  return resp.data as Receivable[];
};

const generateForCompany = async (empresaId: number, targetDate?: string) => {
  const params: any = {};
  if (targetDate) params.target_date = targetDate;
  const resp = await api.post(`/receivables/empresa/${empresaId}/generate`, null, { params });
  return resp.data as Receivable[];
};

const testSicoobIntegration = async (empresaId: number, bankAccountId?: number) => {
  const params: any = {};
  if (bankAccountId) params.bank_account_id = bankAccountId;
  const resp = await api.post(`/receivables/empresa/${empresaId}/test-sicoob`, null, { params });
  return resp.data;
};

const receivableService = {
  listReceivables,
  generateForCompany,
  testSicoobIntegration,
};

export default receivableService;
