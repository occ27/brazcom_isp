export type PageType =
  | 'dashboard'
  | 'profile'
  | 'clients'
  | 'companies'
  | 'contracts'
  | 'services'
  | 'nfcom'
  | 'reports'
  | 'users'
  | 'routers'
  | 'settings';

export interface User {
  id: number;
  email: string;
  nome: string;
  tipo: 'admin' | 'user';
  ativo: boolean;
  created_at: string;
  updated_at: string;
}

export interface Company {
  id: number;
  razao_social: string;
  nome_fantasia?: string;
  cnpj: string;
  inscricao_estadual?: string;
  endereco: string;  // Agora obrigatório
  numero: string;    // Agora obrigatório
  complemento?: string;
  bairro: string;    // Agora obrigatório
  municipio: string; // Agora obrigatório
  uf: string;        // Agora obrigatório
  codigo_ibge: string; // Agora obrigatório
  cep: string;       // Agora obrigatório
  telefone?: string;
  email: string;     // Agora obrigatório
  regime_tributario?: string;
  cnae_principal?: string; // Novo campo opcional
  
  // Novos campos para logo, certificado e email
  logo_url?: string;
  certificado_path?: string;
  certificado_senha?: string;
  smtp_server?: string;
  smtp_port?: number;
  smtp_user?: string;
  smtp_password?: string;
  // Preferência do ambiente para transmissão NFCom
  ambiente_nfcom?: 'producao' | 'homologacao';
  
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface Cliente {
  id: number;
  empresa_id: number;
  nome_razao_social: string;
  cpf_cnpj: string;
  tipo_pessoa: 'F' | 'J';
  ind_ie_dest: '1' | '2' | '9';
  inscricao_estadual?: string;
  email?: string;
  telefone?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  enderecos?: any[]; // Simplified for now
}

export interface NFCom {
  id: number;
  numero: string;
  serie: string;
  data_emissao: string;
  data_vencimento: string;
  valor: number;
  descricao_servico: string;
  company_id: number;
  status: 'emitida' | 'cancelada' | 'vencida';
  informacoes_adicionais?: string;
  created_at: string;
  updated_at: string;
  company?: Company;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

export interface Router {
  id: number;
  empresa_id: number;
  nome: string;
  ip: string;
  porta: number;
  usuario: string;
  senha: string;
  tipo: 'mikrotik' | 'cisco' | 'ubiquiti' | 'outro';
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  empresa?: Company;
}