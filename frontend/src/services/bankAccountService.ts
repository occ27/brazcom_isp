import api from './authService';

export interface BankAccount {
  id: number;
  empresa_id: number;
  name?: string;
  bank: string;
  codigo_banco?: string;
  agencia?: string;
  agencia_dv?: string;
  conta?: string;
  conta_dv?: string;
  titular?: string;
  cpf_cnpj_titular?: string;
  carteira?: string;
  carteira_variacao?: string;
  convenio?: string;
  cnab_version?: string;
  instrucao1?: string;
  instrucao2?: string;
  dias_protesto?: number;
  dias_baixa?: number;
  remittance_config?: string;
  instructions?: string;
  is_default?: boolean;
  is_active?: boolean;
  sicoob_client_id?: string;
  sicoob_access_token?: string;
  sicredi_codigo_beneficiario?: string;
  sicredi_posto?: string;
  sicredi_byte_id?: string;
  bb_client_id?: string;
  bb_client_secret?: string;
  bb_app_key?: string;
  bb_sandbox?: boolean;
  multa_atraso_percentual?: number;
  juros_atraso_percentual?: number;
  desconto_pontualidade_tipo?: 'VALOR' | 'PERCENTUAL';
  desconto_pontualidade_valor?: number;
  desconto_pontualidade_dias?: number;
  created_at: string;
  updated_at?: string;
}

const listBankAccounts = async (empresaId: number, signal?: AbortSignal): Promise<BankAccount[]> => {
  const resp = await api.get(`/empresas/${empresaId}/bank-accounts/`, { signal });
  return resp.data;
};

const listSupportedBanks = async (empresaId: number) => {
  const resp = await api.get(`/empresas/${empresaId}/bank-accounts/metadata/banks`);
  return resp.data;
};

const createBankAccount = async (empresaId: number, payload: Partial<BankAccount>) => {
  const resp = await api.post(`/empresas/${empresaId}/bank-accounts/`, payload);
  return resp.data;
};

const updateBankAccount = async (empresaId: number, bankAccountId: number, payload: Partial<BankAccount>) => {
  const resp = await api.put(`/empresas/${empresaId}/bank-accounts/${bankAccountId}`, payload);
  return resp.data;
};

const deleteBankAccount = async (empresaId: number, bankAccountId: number) => {
  const resp = await api.delete(`/empresas/${empresaId}/bank-accounts/${bankAccountId}`);
  return resp.data;
};

const initPermissions = async (empresaId: number) => {
  const resp = await api.post(`/empresas/${empresaId}/bank-accounts/init-permissions`);
  return resp.data;
};

// ---- Boletos ----
const listBoletos = async (empresaId: number, bankAccountId: number, params: any) => {
  const resp = await api.get(`/empresas/${empresaId}/bank-accounts/${bankAccountId}/boletos`, { params });
  return resp.data;
};

const generateBoletos = async (empresaId: number, bankAccountId: number, receivableIds: number[]) => {
  const resp = await api.post(`/empresas/${empresaId}/bank-accounts/${bankAccountId}/generate-boletos`, receivableIds);
  return resp.data;
};

const downloadRemessa = async (empresaId: number, bankAccountId: number, receivableIds?: number[]) => {
  const resp = await api.post(`/empresas/${empresaId}/bank-accounts/${bankAccountId}/generate-sicredi-remittance`, {
    receivable_ids: receivableIds
  });
  return resp.data;
};

const uploadRetorno = async (empresaId: number, bankAccountId: number, file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  const resp = await api.post(`/empresas/${empresaId}/bank-accounts/${bankAccountId}/retorno`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return resp.data;
};

const registerBoletosApi = async (empresaId: number, bankAccountId: number, receivableIds: number[]) => {
  const resp = await api.post(`/empresas/${empresaId}/bank-accounts/${bankAccountId}/register-boletos-api`, receivableIds);
  return resp.data;
};

const cancelBoletoApi = async (empresaId: number, bankAccountId: number, receivableId: number) => {
  const resp = await api.delete(`/empresas/${empresaId}/bank-accounts/${bankAccountId}/boletos/${receivableId}/api`);
  return resp.data;
};

const bankAccountService = {
  listBankAccounts,
  listSupportedBanks,
  createBankAccount,
  updateBankAccount,
  deleteBankAccount,
  initPermissions,
  listBoletos,
  generateBoletos,
  downloadRemessa,
  uploadRetorno,
  registerBoletosApi,
  cancelBoletoApi,
};

export default bankAccountService;

