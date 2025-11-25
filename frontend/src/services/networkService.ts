import api from './api';
import {
  RouterInterface,
  InterfaceIPAddress,
  IPClass,
  InterfaceIPClassAssignment
} from '../types';

// Interfaces para criação/edição
export interface RouterInterfaceCreate {
  nome: string;
  tipo: string;
  mac_address?: string;
  comentario?: string;
  is_active?: boolean;
}

export interface RouterInterfaceUpdate {
  nome?: string;
  tipo?: string;
  mac_address?: string;
  comentario?: string;
  is_active?: boolean;
}

export interface InterfaceIPAddressCreate {
  endereco_ip: string;
  comentario?: string;
  is_primary?: boolean;
}

export interface InterfaceIPAddressUpdate {
  endereco_ip?: string;
  comentario?: string;
  is_primary?: boolean;
}

export interface IPClassCreate {
  nome: string;
  rede: string;
  gateway?: string;
  dns1?: string;
  dns2?: string;
}

export interface IPClassUpdate {
  nome?: string;
  rede?: string;
  gateway?: string;
  dns1?: string;
  dns2?: string;
}

export interface InterfaceIPClassAssignmentCreate {
  interface_id: number;
  ip_class_id: number;
}

export const networkService = {
  // Router Interfaces
  getRouterInterfaces: async (routerId: number): Promise<RouterInterface[]> => {
    const response = await api.get(`/network/routers/${routerId}/interfaces/`);
    return response.data;
  },

  createRouterInterface: async (routerId: number, interfaceData: RouterInterfaceCreate): Promise<RouterInterface> => {
    const response = await api.post(`/network/routers/${routerId}/interfaces/`, interfaceData);
    return response.data;
  },

  updateRouterInterface: async (interfaceId: number, interfaceData: RouterInterfaceUpdate): Promise<RouterInterface> => {
    const response = await api.put(`/network/interfaces/${interfaceId}`, interfaceData);
    return response.data;
  },

  deleteRouterInterface: async (interfaceId: number, confirm?: boolean): Promise<void> => {
    const params = confirm ? { confirm: true } : {};
    await api.delete(`/network/interfaces/${interfaceId}`, { params });
  },

  // Interface IP Addresses
  getInterfaceIPAddresses: async (interfaceId: number): Promise<InterfaceIPAddress[]> => {
    const response = await api.get(`/network/interfaces/${interfaceId}/ip-addresses/`);
    return response.data;
  },

  createInterfaceIPAddress: async (interfaceId: number, ipData: InterfaceIPAddressCreate): Promise<InterfaceIPAddress> => {
    const response = await api.post(`/network/interfaces/${interfaceId}/ip-addresses/`, ipData);
    return response.data;
  },

  // IP Classes
  getIPClasses: async (): Promise<IPClass[]> => {
    const response = await api.get('/network/ip-classes/');
    return response.data;
  },

  createIPClass: async (ipClassData: IPClassCreate): Promise<IPClass> => {
    const response = await api.post('/network/ip-classes/', ipClassData);
    return response.data;
  },

  updateIPClass: async (classId: number, ipClassData: IPClassUpdate): Promise<IPClass> => {
    const response = await api.put(`/network/ip-classes/${classId}`, ipClassData);
    return response.data;
  },

  deleteIPClass: async (classId: number): Promise<void> => {
    await api.delete(`/network/ip-classes/${classId}`);
  },

  // Interface IP Class Assignments
  assignIPClassToInterface: async (assignmentData: InterfaceIPClassAssignmentCreate): Promise<InterfaceIPClassAssignment> => {
    const response = await api.post('/network/interface-ip-assignments/', assignmentData);
    return response.data;
  },

  removeIPClassFromInterface: async (interfaceId: number, ipClassId: number, confirm?: boolean): Promise<void> => {
    const params = confirm ? { confirm: true } : {};
    await api.delete(`/network/interface-ip-assignments/${interfaceId}/${ipClassId}`, { params });
  },

  // Special operations
  syncRouterInterfaces: async (routerId: number): Promise<any> => {
    const response = await api.post(`/network/routers/${routerId}/sync-interfaces/`);
    return response.data;
  },

  applyIPConfigToInterface: async (interfaceId: number): Promise<any> => {
    const response = await api.post(`/network/interfaces/${interfaceId}/apply-ip-config/`);
    return response.data;
  },
};