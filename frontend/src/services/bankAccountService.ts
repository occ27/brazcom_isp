import api from './authService';

export interface BankAccount {
  id: number;
  empresa_id: number;
  bank: string;
  codigo_banco?: string;
  agencia?: string;
  agencia_dv?: string;
  conta?: string;
  conta_dv?: string;
  titular?: string;
  cpf_cnpj_titular?: string;
  carteira?: string;
  convenio?: string;
  remittance_config?: string;
  instructions?: string;
  is_default?: boolean;
  sicoob_client_id?: string;
  sicoob_access_token?: string;
  created_at: string;
  updated_at?: string;
}

const listBankAccounts = async (empresaId: number, signal?: AbortSignal): Promise<BankAccount[]> => {
  const resp = await api.get(`/empresas/${empresaId}/bank-accounts`, { signal });
  return resp.data;
};

const createBankAccount = async (empresaId: number, payload: Partial<BankAccount>) => {
  const resp = await api.post(`/empresas/${empresaId}/bank-accounts`, payload);
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

const bankAccountService = {
  listBankAccounts,
  createBankAccount,
  updateBankAccount,
  deleteBankAccount,
  initPermissions,
};

export default bankAccountService;
