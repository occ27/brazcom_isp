import api from './api';
import { Router } from '../types';

export interface RouterCreate {
  nome: string;
  ip: string;
  porta: number;
  usuario: string;
  senha: string;
  tipo: 'mikrotik' | 'cisco' | 'ubiquiti' | 'outro';
}

export interface RouterUpdate {
  nome?: string;
  ip?: string;
  porta?: number;
  usuario?: string;
  senha?: string;
  tipo?: 'mikrotik' | 'cisco' | 'ubiquiti' | 'outro';
  is_active?: boolean;
}

export interface PPPoESetupRequest {
  interface: string;
  ip_pool_name?: string;
  local_address?: string;
  first_ip?: string;
  last_ip?: string;
  default_profile?: string;
}

export interface PPPoEStatus {
  profiles: any[];
  servers: any[];
  interfaces: any[];
  pools: any[];
  error?: string;
}

export const routerService = {
  // Buscar todos os routers
  getAll: async (): Promise<Router[]> => {
    const response = await api.get('/routers/');
    return response.data;
  },

  // Buscar router por ID
  getById: async (id: number): Promise<Router> => {
    const response = await api.get(`/routers/${id}`);
    return response.data;
  },

  // Criar novo router
  create: async (routerData: RouterCreate): Promise<Router> => {
    const response = await api.post('/routers/', routerData);
    return response.data;
  },

  // Atualizar router
  update: async (id: number, routerData: RouterUpdate): Promise<Router> => {
    const response = await api.put(`/routers/${id}`, routerData);
    return response.data;
  },

  // Deletar router
  delete: async (id: number): Promise<void> => {
    await api.delete(`/routers/${id}`);
  },

  // Configurar servidor PPPoE
  setupPPPoE: async (routerId: number, setupData: PPPoESetupRequest): Promise<any> => {
    const response = await api.post(`/network/routers/${routerId}/setup-pppoe-server`, setupData);
    return response.data;
  },

  // Obter status PPPoE
  getPPPoEStatus: async (routerId: number): Promise<PPPoEStatus> => {
    const response = await api.get(`/network/routers/${routerId}/pppoe-status`);
    return response.data;
  },

  // Buscar routers por empresa
  getByCompany: async (empresaId: number): Promise<Router[]> => {
    const response = await api.get(`/routers/?empresa_id=${empresaId}`);
    return response.data;
  },
};