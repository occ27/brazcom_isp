import api from './authService';

export interface Receivable {
  id: number;
  empresa_id: number;
  cliente_id: number;
  cliente_nome?: string;
  cliente_cpf_cnpj?: string;
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
  bb_boleto_numero?: string;
  bb_boleto_url?: string;
  bb_pix_qrcode?: string;
  bb_pix_txid?: string;
  bank_account_id?: number;
  bank_account_snapshot?: string;
  bank_payload?: string;
  created_at: string;
  updated_at?: string;
}

const listReceivables = async (empresaId: number, page = 1, perPage = 25, startDate?: string, endDate?: string, dateType = 'due_date', status?: string, search?: string) => {
  const params: any = { page, per_page: perPage, date_type: dateType };
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  if (status) params.status = status;
  if (search) params.search = search;
  const resp = await api.get(`/receivables/empresa/${empresaId}`, { params });
  return resp.data as { data: Receivable[], total: number };
};

const generateForCompany = async (empresaId: number, targetDate?: string) => {
  const params: any = {};
  if (targetDate) params.target_date = targetDate;
  const resp = await api.post(`/receivables/empresa/${empresaId}/generate`, null, { params });
  return resp.data as Receivable[];
};

const testSicoobIntegration = async (empresaId: number, bankAccountId?: number, bankAccountData?: any) => {
  const params: any = {};
  if (bankAccountId) params.bank_account_id = bankAccountId;
  const resp = await api.post(`/receivables/empresa/${empresaId}/test-sicoob`, bankAccountData || null, { params });
  return resp.data;
};

const settleReceivable = async (receivableId: number) => {
  const resp = await api.put(`/receivables/${receivableId}/settle`);
  return resp.data;
};

const cancelReceivable = async (receivableId: number) => {
  const resp = await api.delete(`/receivables/${receivableId}`);
  return resp.data;
};

const createReceivable = async (data: any) => {
  const resp = await api.post('/receivables/', data);
  return resp.data as Receivable;
};

const printReceivable = async (receivableId: number) => {
  const resp = await api.get(`/receivables/${receivableId}/print`, { responseType: 'blob' });
  const blob = new Blob([resp.data], { type: 'application/pdf' });
  return window.URL.createObjectURL(blob);
};

const receivableService = {
  listReceivables,
  generateForCompany,
  testSicoobIntegration,
  settleReceivable,
  cancelReceivable,
  createReceivable,
  printReceivable,
};

export default receivableService;
