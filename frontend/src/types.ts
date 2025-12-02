export type PageType =
  | 'dashboard'
  | 'profile'
  | 'clients'
  | 'companies'
  | 'contracts'
  | 'services'
  | 'nfcom'
  | 'bank-accounts'
  | 'receivables'
  | 'tickets'
  | 'reports'
  | 'users'
  | 'roles'
  | 'permissions'
  | 'routers'
  | 'ip-classes'
  | 'pppoe'
  | 'dhcp'
  | 'settings';

export interface User {
  id: number;
  email: string;
  full_name: string;
  nome?: string; // Mantido para compatibilidade
  is_superuser: boolean;
  is_active: boolean;
  ativo?: boolean; // Mantido para compatibilidade
  tipo?: 'admin' | 'user'; // Mantido para compatibilidade
  active_empresa_id?: number;
  created_at: string;
  updated_at: string;
}

// Alias para evitar conflitos
export type AppUser = User;

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
  
  // Configuração de cobrança: conta bancária padrão (opcional)
  default_bank_account_id?: number;
  
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
  tipo: 'mikrotik' | 'cisco' | 'ubiquiti' | 'outro';
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  empresa?: Company;
  interfaces?: RouterInterface[];
}

export interface RouterInterface {
  id: number;
  router_id: number;
  nome: string;
  tipo: string;
  mac_address?: string;
  comentario?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  enderecos_ip?: InterfaceIPAddress[];
  ip_classes?: IPClass[];
}

export interface InterfaceIPAddress {
  id: number;
  interface_id: number;
  endereco_ip: string;
  comentario?: string;
  is_primary: boolean;
  created_at: string;
  updated_at?: string;
}

export interface IPClass {
  id: number;
  empresa_id: number;
  nome: string;
  rede: string;
  gateway?: string;
  dns1?: string;
  dns2?: string;
  created_at: string;
  updated_at?: string;
  interfaces?: RouterInterface[];
}

export interface InterfaceIPClassAssignment {
  id: number;
  interface_id: number;
  ip_class_id: number;
  assigned_at: string;
  applied_configs?: string[];
  application_status?: string;
}

// PPPoE e DHCP Types
export interface IPPool {
  id: number;
  empresa_id: number;
  router_id?: number;
  nome: string;
  ranges: string;
  comentario?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  empresa?: Company;
  router?: Router;
}

export interface PPPProfile {
  id: number;
  empresa_id: number;
  router_id?: number;
  nome: string;
  local_address: string;
  remote_address_pool_id?: number;
  rate_limit?: string;
  comentario?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  empresa?: Company;
  router?: Router;
  remote_address_pool?: IPPool;
}

export interface PPPoEServer {
  id: number;
  empresa_id: number;
  router_id?: number;
  service_name: string;
  interface_id: number;
  default_profile_id: number;
  comentario?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  empresa?: Company;
  router?: Router;
  interface?: RouterInterface;
  default_profile?: PPPProfile;
}

export interface DHCPServer {
  id: number;
  empresa_id: number;
  router_id?: number;
  name: string;
  interface_id: number;
  comentario?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  empresa?: Company;
  router?: Router;
  interface?: RouterInterface;
  networks?: DHCPNetwork[];
}

export interface DHCPNetwork {
  id: number;
  empresa_id: number;
  router_id?: number;
  dhcp_server_id: number;
  network: string;
  gateway?: string;
  dns_servers?: string;
  lease_time?: string;
  comentario?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  empresa?: Company;
  router?: Router;
  dhcp_server?: DHCPServer;
}

// ===== TIPOS DE TICKETS/SUPORTE =====

export type StatusTicket = 'ABERTO' | 'EM_ANDAMENTO' | 'AGUARDANDO_CLIENTE' | 'RESOLVIDO' | 'FECHADO' | 'CANCELADO';
export type PrioridadeTicket = 'BAIXA' | 'NORMAL' | 'ALTA' | 'URGENTE';
export type CategoriaTicket = 'TECNICO' | 'COBRANCA' | 'INSTALACAO' | 'SUPORTE' | 'CANCELAMENTO' | 'OUTRO';

export interface Ticket {
  id: number;
  empresa_id: number;
  cliente_id?: number;
  criado_por_id: number;
  atribuido_para_id?: number;
  titulo: string;
  descricao: string;
  status: StatusTicket;
  prioridade: PrioridadeTicket;
  categoria: CategoriaTicket;
  resolucao?: string;
  resolvido_em?: string;
  resolvido_por_id?: number;
  prazo_resolucao?: string;
  tempo_gasto_minutos: number;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  // Dados relacionados
  cliente_nome?: string;
  criado_por_nome: string;
  atribuido_para_nome?: string;
  resolvido_por_nome?: string;
  comentarios_count: number;
}

export interface TicketComment {
  id: number;
  ticket_id: number;
  usuario_id: number;
  comentario: string;
  is_internal: boolean;
  created_at: string;
  updated_at?: string;
}

export interface TicketStats {
  total_tickets: number;
  tickets_abertos: number;
  tickets_em_andamento: number;
  tickets_resolvidos: number;
  tickets_fechados: number;
  tickets_hoje: number;
  tickets_semana: number;
  tickets_mes: number;
  tempo_medio_resolucao_horas?: number;
}

export interface TicketCreate {
  titulo: string;
  descricao: string;
  prioridade: PrioridadeTicket;
  categoria: CategoriaTicket;
  cliente_id?: number;
  atribuido_para_id?: number;
  prazo_resolucao?: string;
}

export interface TicketUpdate {
  titulo?: string;
  descricao?: string;
  status?: StatusTicket;
  prioridade?: PrioridadeTicket;
  categoria?: CategoriaTicket;
  atribuido_para_id?: number;
  resolucao?: string;
  prazo_resolucao?: string;
  tempo_gasto_minutos?: number;
}

export interface TicketCommentCreate {
  comentario: string;
  is_internal: boolean;
}