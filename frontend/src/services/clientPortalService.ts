import api from './api';

export interface ClienteInfo {
  id: number;
  nome_razao_social: string;
  cpf_cnpj: string;
  email: string;
  telefone: string;
  enderecos: any[];
}

export interface ServicoContratado {
  id: number;
  servico_nome: string;
  status: string;
  valor_mensal: number;
  data_contratacao: string;
}

export interface Fatura {
  id: number;
  numero: string;
  valor_total: number;
  data_emissao: string;
  data_vencimento: string;
  status: string;
}

export interface Ticket {
  id: number;
  titulo: string;
  status: string;
  prioridade: string;
  created_at: string;
}

class ClientPortalService {
  // Buscar informações do cliente logado
  async getClienteInfo(): Promise<ClienteInfo> {
    const response = await api.get('/client-portal/cliente');
    return response.data;
  }

  // Buscar serviços contratados
  async getServicosContratados(): Promise<ServicoContratado[]> {
    const response = await api.get('/client-portal/servicos');
    return response.data;
  }

  // Buscar faturas
  async getFaturas(): Promise<Fatura[]> {
    const response = await api.get('/client-portal/faturas');
    return response.data;
  }

  // Buscar tickets de suporte
  async getTickets(): Promise<Ticket[]> {
    const response = await api.get('/client-portal/tickets');
    return response.data;
  }

  // Criar novo ticket
  async createTicket(ticketData: {
    titulo: string;
    descricao: string;
    prioridade: string;
    categoria: string;
  }): Promise<Ticket> {
    const response = await api.post('/client-portal/tickets', ticketData);
    return response.data;
  }

  // Buscar detalhes de uma fatura
  async getFaturaDetail(faturaId: number): Promise<Fatura> {
    const response = await api.get(`/client-portal/faturas/${faturaId}`);
    return response.data;
  }

  // Baixar fatura em PDF
  async downloadFatura(faturaId: number): Promise<Blob> {
    const response = await api.get(`/client-portal/faturas/${faturaId}/download`, {
      responseType: 'blob'
    });
    return response.data;
  }

  // Atualizar dados do cliente
  async updateClienteInfo(clienteData: Partial<ClienteInfo>): Promise<ClienteInfo> {
    const response = await api.put('/client-portal/cliente', clienteData);
    return response.data;
  }
}

const clientPortalService = new ClientPortalService();
export default clientPortalService;