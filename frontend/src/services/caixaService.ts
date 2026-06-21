import api from './api';

export interface LocalPagamento {
  id: number;
  empresa_id: number;
  nome: string;
  is_active: boolean;
}

export interface FormaPagamento {
  id: number;
  empresa_id: number;
  nome: string;
  is_active: boolean;
}

export interface CaixaSessao {
  id: number;
  empresa_id: number;
  usuario_id: number;
  local_pagamento_id: number;
  data_abertura: string;
  data_fechamento?: string;
  saldo_inicial: number;
  saldo_final_informado?: number;
  saldo_final_calculado?: number;
  status: string;
  usuario_nome?: string;
  local_pagamento_nome?: string;
}

export interface CaixaMovimentacao {
  id: number;
  sessao_id: number;
  usuario_id: number;
  forma_pagamento_id?: number;
  recebimento_caixa_id?: number;
  tipo: string;
  valor: number;
  descricao?: string;
  created_at: string;
  forma_pagamento_nome?: string;
}

class CaixaService {
  async getLocaisPagamento(empresaId: number): Promise<LocalPagamento[]> {
    const response = await api.get(`/caixa/locais/${empresaId}`);
    return response.data;
  }

  async getFormasPagamento(empresaId: number): Promise<FormaPagamento[]> {
    const response = await api.get(`/caixa/formas/${empresaId}`);
    return response.data;
  }

  async getSessaoAtual(empresaId: number): Promise<CaixaSessao> {
    const response = await api.get(`/caixa/sessao/atual/${empresaId}`);
    return response.data;
  }

  async abrirSessao(empresaId: number, localPagamentoId: number, saldoInicial: number): Promise<CaixaSessao> {
    const response = await api.post(`/caixa/sessao/abrir/${empresaId}`, {
      local_pagamento_id: localPagamentoId,
      saldo_inicial: saldoInicial
    });
    return response.data;
  }

  async fecharSessao(sessaoId: number, saldoFinalInformado: number): Promise<CaixaSessao> {
    const response = await api.post(`/caixa/sessao/fechar/${sessaoId}`, {
      saldo_final_informado: saldoFinalInformado
    });
    return response.data;
  }

  async getExtrato(sessaoId: number): Promise<CaixaMovimentacao[]> {
    const response = await api.get(`/caixa/sessao/${sessaoId}/extrato`);
    return response.data;
  }

  async lancarMovimentacao(sessaoId: number, data: { tipo: string; valor: number; forma_pagamento_id: number; descricao: string }): Promise<CaixaMovimentacao> {
    const response = await api.post(`/caixa/sessao/${sessaoId}/movimentacao`, data);
    return response.data;
  }

  async getSessoesHistorico(empresaId: number, page: number = 1, perPage: number = 25, status?: string): Promise<{ data: CaixaSessao[]; total: number }> {
    const params: any = { page, per_page: perPage };
    if (status) params.status = status;
    const response = await api.get(`/caixa/historico/${empresaId}`, { params });
    return response.data;
  }

  async downloadCaixaPDF(sessaoId: number): Promise<void> {
    const response = await api.get(`/caixa/sessao/${sessaoId}/pdf`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `caixa_${sessaoId}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  }

  // --- Admin API ---
  async getLocais(empresaId: number, includeInactive: boolean = false): Promise<LocalPagamento[]> {
    const response = await api.get(`/caixa/locais/${empresaId}?include_inactive=${includeInactive}`);
    return response.data;
  }
  
  async createLocal(empresaId: number, data: { nome: string }): Promise<LocalPagamento> {
    const response = await api.post(`/caixa/locais/${empresaId}`, data);
    return response.data;
  }

  async updateLocal(localId: number, data: { nome?: string; is_active?: boolean }): Promise<LocalPagamento> {
    const response = await api.put(`/caixa/locais/${localId}`, data);
    return response.data;
  }

  async deleteLocal(localId: number): Promise<void> {
    await api.delete(`/caixa/locais/${localId}`);
  }

  async getFormas(empresaId: number, includeInactive: boolean = false): Promise<FormaPagamento[]> {
    const response = await api.get(`/caixa/formas/${empresaId}?include_inactive=${includeInactive}`);
    return response.data;
  }

  async createForma(empresaId: number, data: { nome: string }): Promise<FormaPagamento> {
    const response = await api.post(`/caixa/formas/${empresaId}`, data);
    return response.data;
  }

  async updateForma(formaId: number, data: { nome?: string; is_active?: boolean }): Promise<FormaPagamento> {
    const response = await api.put(`/caixa/formas/${formaId}`, data);
    return response.data;
  }

  async deleteForma(formaId: number): Promise<void> {
    await api.delete(`/caixa/formas/${formaId}`);
  }
}

export const caixaService = new CaixaService();