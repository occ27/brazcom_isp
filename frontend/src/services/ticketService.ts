import api from './authService';
import { Ticket, TicketCreate, TicketUpdate, TicketComment, TicketCommentCreate, TicketStats } from '../types';

const ticketService = {
  // Listar tickets com filtros
  listTickets: async (
    skip = 0,
    limit = 100,
    status?: string,
    prioridade?: string,
    categoria?: string,
    cliente_id?: number,
    atribuido_para_id?: number,
    search?: string
  ): Promise<Ticket[]> => {
    const params: any = { skip, limit };
    if (status) params.status = status;
    if (prioridade) params.prioridade = prioridade;
    if (categoria) params.categoria = categoria;
    if (cliente_id) params.cliente_id = cliente_id;
    if (atribuido_para_id) params.atribuido_para_id = atribuido_para_id;
    if (search) params.search = search;

    const resp = await api.get('/tickets/', { params });
    return resp.data;
  },

  // Buscar ticket por ID
  getTicket: async (ticketId: number): Promise<Ticket> => {
    const resp = await api.get(`/tickets/${ticketId}`);
    return resp.data;
  },

  // Criar novo ticket
  createTicket: async (ticket: TicketCreate): Promise<Ticket> => {
    const resp = await api.post('/tickets/', ticket);
    return resp.data;
  },

  // Atualizar ticket
  updateTicket: async (ticketId: number, ticket: TicketUpdate): Promise<Ticket> => {
    const resp = await api.put(`/tickets/${ticketId}`, ticket);
    return resp.data;
  },

  // Deletar ticket
  deleteTicket: async (ticketId: number): Promise<void> => {
    await api.delete(`/tickets/${ticketId}`);
  },

  // Adicionar comentário
  addComment: async (ticketId: number, comment: TicketCommentCreate): Promise<TicketComment> => {
    const resp = await api.post(`/tickets/${ticketId}/comments`, comment);
    return resp.data;
  },

  // Listar comentários do ticket
  getComments: async (ticketId: number): Promise<TicketComment[]> => {
    const resp = await api.get(`/tickets/${ticketId}/comments`);
    return resp.data;
  },

  // Buscar estatísticas
  getStats: async (): Promise<TicketStats> => {
    const resp = await api.get('/tickets/stats/summary');
    return resp.data;
  }
};

export default ticketService;