import api from './authService';

export interface ClienteEnderecoCreate {
  descricao?: string;
  endereco: string;
  numero: string;
  complemento?: string;
  bairro: string;
  municipio: string;
  uf: string;
  cep: string;
  codigo_ibge?: string;
  is_principal?: boolean;
}

export interface ClientCreate {
  nome_razao_social: string;
  cpf_cnpj: string;
  tipo_pessoa: 'F' | 'J';
  ind_ie_dest: '1' | '2' | '9'; // 1: Contribuinte ICMS, 2: Isento, 9: Não contribuinte
  inscricao_estadual?: string;
  email?: string;
  telefone?: string;
  enderecos?: ClienteEnderecoCreate[];
}

export interface ClientResponse extends ClientCreate {
  id: number;
  empresa_id: number;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface ClientListResponse {
  total: number;
  clientes: ClientResponse[];
}

export const clientService = {
  async getClientsByCompany(empresaId: number, page: number, limit: number, q?: string): Promise<ClientListResponse> {
    const skip = (page - 1) * limit;
    const params: any = { skip, limit };
    if (q) params.q = q;
    const response = await api.get(`/clientes/empresa/${empresaId}`, { params });
    // Backend may return either { total, clientes } or a raw array of clients.
    const data = response.data;
    if (Array.isArray(data)) {
      return { total: data.length, clientes: data };
    }
    if (data && typeof data === 'object' && Array.isArray(data.clientes)) {
      return data;
    }
    // Fallback: try to coerce
    return { total: (data?.clientes?.length) || 0, clientes: data?.clientes || [] };
  },

  async getClientById(clienteId: number, empresaId?: number): Promise<ClientResponse> {
    const params: any = {};
    if (empresaId) params.empresa_id = empresaId;
    const response = await api.get(`/clientes/${clienteId}`, { params });
    return response.data;
  },

  async getClient(id: number): Promise<ClientResponse> {
    const response = await api.get(`/clientes/${id}`);
    return response.data;
  },

  async createClient(empresaId: number, client: ClientCreate): Promise<ClientResponse> {
    // empresa_id é passado como query param conforme rota backend
    const response = await api.post(`/clientes/?empresa_id=${empresaId}`, client);
    return response.data;
  },

  async updateClient(empresaId: number, id: number, client: Partial<ClientCreate>): Promise<ClientResponse> {
    const response = await api.put(`/clientes/${id}?empresa_id=${empresaId}`, client);
    return response.data;
  },

  async deleteClient(empresaId: number, id: number, removeOrphan: boolean = false): Promise<void> {
    const q = removeOrphan ? `?empresa_id=${empresaId}&remove_orphan_cliente=true` : `?empresa_id=${empresaId}`;
    await api.delete(`/clientes/${id}${q}`);
  },

  // Address management (per-association)
  async createAddress(empresaId: number, clienteId: number, endereco: ClienteEnderecoCreate) {
    const response = await api.post(`/clientes/${clienteId}/enderecos?empresa_id=${empresaId}`, endereco);
    return response.data;
  },

  async updateAddress(empresaId: number, clienteId: number, enderecoId: number, endereco: Partial<ClienteEnderecoCreate>) {
    const response = await api.put(`/clientes/${clienteId}/enderecos/${enderecoId}?empresa_id=${empresaId}`, endereco);
    return response.data;
  },

  async deleteAddress(empresaId: number, clienteId: number, enderecoId: number) {
    const response = await api.delete(`/clientes/${clienteId}/enderecos/${enderecoId}?empresa_id=${empresaId}`);
    return response.data;
  },

  // Utilitários básicos de formatação (cpf/cnpj/telefone)
  formatCpfCnpj(value: string): string {
    const cleaned = value.replace(/\D/g, '');
    if (cleaned.length === 11) {
      return `${cleaned.slice(0,3)}.${cleaned.slice(3,6)}.${cleaned.slice(6,9)}-${cleaned.slice(9)}`;
    }
    if (cleaned.length === 14) {
      return `${cleaned.slice(0,2)}.${cleaned.slice(2,5)}.${cleaned.slice(5,8)}/${cleaned.slice(8,12)}-${cleaned.slice(12)}`;
    }
    return value;
  },

  // Aplica máscara dinâmica enquanto o usuário digita: CPF (xxx.xxx.xxx-xx) ou CNPJ (xx.xxx.xxx/xxxx-xx)
  formatCpfCnpjInput(value: string): string {
    const cleaned = value.replace(/\D/g, '');
    if (!cleaned) return '';

    if (cleaned.length <= 11) {
      // CPF
      const match = cleaned.match(/^(\d{0,3})(\d{0,3})(\d{0,3})(\d{0,2})$/);
      if (!match) return value;
      return [
        match[1] ? match[1] : '',
        match[2] ? '.' + match[2] : '',
        match[3] ? '.' + match[3] : '',
        match[4] ? '-' + match[4] : ''
      ].join('');
    }

    // CNPJ
    const match = cleaned.match(/^(\d{0,2})(\d{0,3})(\d{0,3})(\d{0,4})(\d{0,2})$/);
    if (!match) return value;
    return [
      match[1] ? match[1] : '',
      match[2] ? '.' + match[2] : '',
      match[3] ? '.' + match[3] : '',
      match[4] ? '/' + match[4] : '',
      match[5] ? '-' + match[5] : ''
    ].join('');
  },

  formatPhoneInput(value: string): string {
    const cleaned = value.replace(/\D/g, '');
    const match = cleaned.match(/^(\d{0,2})(\d{0,5})(\d{0,4})$/);
    if (!match) return value;
    const ddd = match[1] ? '(' + match[1] : '';
    const prefix = match[1] ? ') ' : '';
    const number = match[2] ? match[2] : '';
    const suffix = match[3] ? '-' + match[3] : '';
    return ddd + prefix + number + suffix;
  },

  // Validadores úteis
  validateCPF(cpf: string): boolean {
    const cleaned = (cpf || '').replace(/\D/g, '');
    if (cleaned.length !== 11) return false;
    if (/^(\d)\1+$/.test(cleaned)) return false;

    const calc = (t: number) => {
      let sum = 0;
      for (let i = 0; i < t - 1; i++) sum += parseInt(cleaned[i]) * (t - i);
      const d = 11 - (sum % 11);
      return d >= 10 ? 0 : d;
    };

    return calc(10) === parseInt(cleaned[9]) && calc(11) === parseInt(cleaned[10]);
  },

  validateEmail(email: string): boolean {
    if (!email) return false;
    // Simples verificação RFC-like (suficiente para UI)
    const re = /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@(([^<>()[\]\\.,;:\s@"]+\.)+[^<>()[\]\\.,;:\s@"]{2,})$/i;
    return re.test(email);
  },

  validatePhone(phone: string): boolean {
    if (!phone) return false;
    const digits = phone.replace(/\D/g, '');
    // Aceitar DDD + número: mínimo 10 dígitos (ex: 11 91234-5678) ou 8 sem DDD
    return digits.length >= 10;
  }
};

export default clientService;
