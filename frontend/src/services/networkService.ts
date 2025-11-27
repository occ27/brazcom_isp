import api from './api';
import {
  RouterInterface,
  InterfaceIPAddress,
  IPClass,
  InterfaceIPClassAssignment,
  IPPool,
  PPPProfile,
  PPPoEServer,
  DHCPServer,
  DHCPNetwork
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

// PPPoE e DHCP Interfaces
export interface IPPoolCreate {
  router_id?: number;
  nome: string;
  ranges: string;
  comentario?: string;
  is_active?: boolean;
}

export interface IPPoolUpdate {
  router_id?: number;
  nome?: string;
  ranges?: string;
  comentario?: string;
  is_active?: boolean;
}

export interface PPPProfileCreate {
  router_id?: number;
  nome: string;
  local_address: string;
  remote_address?: string;
  rate_limit?: string;
  comentario?: string;
  is_active?: boolean;
}

export interface PPPProfileUpdate {
  router_id?: number;
  nome?: string;
  local_address?: string;
  remote_address?: string;
  rate_limit?: string;
  comentario?: string;
  is_active?: boolean;
}

export interface PPPoEServerCreate {
  router_id?: number;
  service_name: string;
  interface_id: number;
  default_profile_id: number;
  comentario?: string;
  is_active?: boolean;
}

export interface PPPoEServerUpdate {
  router_id?: number;
  service_name?: string;
  interface_id?: number;
  default_profile_id?: number;
  comentario?: string;
  is_active?: boolean;
}

export interface DHCPServerCreate {
  router_id?: number;
  name: string;
  interface_id: number;
  comentario?: string;
  is_active?: boolean;
}

export interface DHCPServerUpdate {
  router_id?: number;
  name?: string;
  interface_id?: number;
  comentario?: string;
  is_active?: boolean;
}

export interface DHCPNetworkCreate {
  router_id?: number;
  dhcp_server_id: number;
  network: string;
  gateway?: string;
  dns_servers?: string;
  lease_time?: string;
  comentario?: string;
  is_active?: boolean;
}

export interface DHCPNetworkUpdate {
  router_id?: number;
  dhcp_server_id?: number;
  network?: string;
  gateway?: string;
  dns_servers?: string;
  lease_time?: string;
  comentario?: string;
  is_active?: boolean;
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

  syncIPPools: async (routerId: number): Promise<any> => {
    const response = await api.post(`/network/routers/${routerId}/sync-ip-pools/`);
    return response.data;
  },

  syncPPPProfiles: async (routerId: number): Promise<any> => {
    const response = await api.post(`/network/routers/${routerId}/sync-ppp-profiles/`);
    return response.data;
  },

  syncPPPoEServers: async (routerId: number): Promise<any> => {
    const response = await api.post(`/network/routers/${routerId}/sync-pppoe-servers/`);
    return response.data;
  },

  applyIPConfigToInterface: async (interfaceId: number): Promise<any> => {
    const response = await api.post(`/network/interfaces/${interfaceId}/apply-ip-config/`);
    return response.data;
  },

  // IP Pools
  getIPPools: async (): Promise<IPPool[]> => {
    const response = await api.get('/network/ip-pools/');
    return response.data;
  },

  createIPPool: async (poolData: IPPoolCreate): Promise<IPPool> => {
    const response = await api.post('/network/ip-pools/', poolData);
    return response.data;
  },

  updateIPPool: async (poolId: number, poolData: IPPoolUpdate): Promise<IPPool> => {
    const response = await api.put(`/network/ip-pools/${poolId}`, poolData);
    return response.data;
  },

  deleteIPPool: async (poolId: number): Promise<void> => {
    await api.delete(`/network/ip-pools/${poolId}`);
  },

  // PPP Profiles
  getPPPProfiles: async (): Promise<PPPProfile[]> => {
    const response = await api.get('/network/ppp-profiles/');
    return response.data;
  },

  createPPPProfile: async (profileData: PPPProfileCreate): Promise<PPPProfile> => {
    const response = await api.post('/network/ppp-profiles/', profileData);
    return response.data;
  },

  updatePPPProfile: async (profileId: number, profileData: PPPProfileUpdate): Promise<PPPProfile> => {
    const response = await api.put(`/network/ppp-profiles/${profileId}`, profileData);
    return response.data;
  },

  deletePPPProfile: async (profileId: number): Promise<void> => {
    await api.delete(`/network/ppp-profiles/${profileId}`);
  },

  // PPPoE Servers
  getPPPoEServers: async (): Promise<PPPoEServer[]> => {
    const response = await api.get('/network/pppoe-servers/');
    return response.data;
  },

  createPPPoEServer: async (serverData: PPPoEServerCreate): Promise<PPPoEServer> => {
    const response = await api.post('/network/pppoe-servers/', serverData);
    return response.data;
  },

  updatePPPoEServer: async (serverId: number, serverData: PPPoEServerUpdate): Promise<PPPoEServer> => {
    const response = await api.put(`/network/pppoe-servers/${serverId}`, serverData);
    return response.data;
  },

  deletePPPoEServer: async (serverId: number): Promise<void> => {
    await api.delete(`/network/pppoe-servers/${serverId}`);
  },

  // DHCP Servers
  getDHCPServers: async (): Promise<DHCPServer[]> => {
    const response = await api.get('/network/dhcp-servers/');
    return response.data;
  },

  createDHCPServer: async (serverData: DHCPServerCreate): Promise<DHCPServer> => {
    const response = await api.post('/network/dhcp-servers/', serverData);
    return response.data;
  },

  updateDHCPServer: async (serverId: number, serverData: DHCPServerUpdate): Promise<DHCPServer> => {
    const response = await api.put(`/network/dhcp-servers/${serverId}`, serverData);
    return response.data;
  },

  deleteDHCPServer: async (serverId: number): Promise<void> => {
    await api.delete(`/network/dhcp-servers/${serverId}`);
  },

  // DHCP Networks
  getDHCPNetworks: async (): Promise<DHCPNetwork[]> => {
    const response = await api.get('/network/dhcp-networks/');
    return response.data;
  },

  createDHCPNetwork: async (networkData: DHCPNetworkCreate): Promise<DHCPNetwork> => {
    const response = await api.post('/network/dhcp-networks/', networkData);
    return response.data;
  },

  updateDHCPNetwork: async (networkId: number, networkData: DHCPNetworkUpdate): Promise<DHCPNetwork> => {
    const response = await api.put(`/network/dhcp-networks/${networkId}`, networkData);
    return response.data;
  },

  deleteDHCPNetwork: async (networkId: number): Promise<void> => {
    await api.delete(`/network/dhcp-networks/${networkId}`);
  },
};