import api from './api';

export interface Role {
  id: number;
  name: string;
  description?: string;
  empresa_id?: number | null;
}

export interface Permission {
  id: number;
  name: string;
  description?: string;
}

export interface Usuario {
  id: number;
  full_name: string;
  nome?: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  active_empresa_id?: number;
  created_at: string;
  updated_at: string;
}

export interface UsuarioCreate {
  nome: string;
  email: string;
  password: string;
  is_superuser?: boolean;
}

export interface UsuarioUpdate {
  nome?: string;
  email?: string;
  password?: string;
  is_active?: boolean;
  is_superuser?: boolean;
}

export interface UsuarioEmpresa {
  usuario_id: number;
  empresa_id: number;
  is_admin: boolean;
}

class UserService {
  async getUsersByEmpresa(empresaId: number): Promise<Usuario[]> {
    const response = await api.get(`/usuarios/empresa/${empresaId}`);
    return response.data;
  }

  async createUserForEmpresa(empresaId: number, userData: UsuarioCreate): Promise<Usuario> {
    const response = await api.post(`/usuarios/empresa/${empresaId}`, userData);
    return response.data;
  }

  async associateUserToEmpresa(empresaId: number, usuarioId: number, isAdmin: boolean = false): Promise<{ message: string }> {
    const response = await api.post(`/usuarios/empresa/${empresaId}/associate`, {
      usuario_id: usuarioId,
      is_admin: isAdmin
    });
    return response.data;
  }

  async updateUser(userId: number, userData: UsuarioUpdate): Promise<Usuario> {
    const response = await api.put(`/usuarios/${userId}`, userData);
    return response.data;
  }

  async deleteUser(userId: number): Promise<void> {
    await api.delete(`/usuarios/${userId}`);
  }

  async getAllUsers(): Promise<Usuario[]> {
    const response = await api.get('/usuarios/');
    return response.data;
  }

  // RBAC methods
  async listRoles(): Promise<Role[]> {
    const response = await api.get('/access/roles');
    return response.data;
  }

  async createRole(payload: { name: string; description?: string; empresa_id?: number | null }): Promise<Role> {
    const response = await api.post('/access/roles', payload);
    return response.data;
  }

  async createPermission(payload: { name: string; description?: string }): Promise<Permission> {
    const response = await api.post('/access/permissions', payload);
    return response.data;
  }

  async assignRole(roleId: number, userId: number, empresaId?: number | null): Promise<{ status: string }> {
    const response = await api.post(`/access/roles/${roleId}/assign`, { user_id: userId, empresa_id: empresaId });
    return response.data;
  }

  async unassignRole(roleId: number, userId: number): Promise<{ status: string }> {
    const response = await api.post(`/access/roles/${roleId}/unassign`, { user_id: userId });
    return response.data;
  }

  async getUserRoles(userId: number): Promise<Role[]> {
    const response = await api.get(`/access/users/${userId}/roles`);
    return response.data;
  }

  async updateRole(roleId: number, payload: { name: string; description?: string }): Promise<Role> {
    const response = await api.put(`/access/roles/${roleId}`, payload);
    return response.data;
  }

  async deleteRole(roleId: number): Promise<{ status: string }> {
    const response = await api.delete(`/access/roles/${roleId}`);
    return response.data;
  }

  // Permissions methods
  async listPermissions(): Promise<Permission[]> {
    const response = await api.get('/access/permissions');
    return response.data;
  }

  async updatePermission(permissionId: number, payload: { name: string; description?: string }): Promise<Permission> {
    const response = await api.put(`/access/permissions/${permissionId}`, payload);
    return response.data;
  }

  async deletePermission(permissionId: number): Promise<{ status: string }> {
    const response = await api.delete(`/access/permissions/${permissionId}`);
    return response.data;
  }

  async addPermissionToRole(roleId: number, permissionId: number): Promise<{ status: string }> {
    const response = await api.post(`/access/roles/${roleId}/permissions/${permissionId}`);
    return response.data;
  }

  async removePermissionFromRole(roleId: number, permissionId: number): Promise<{ status: string }> {
    const response = await api.delete(`/access/roles/${roleId}/permissions/${permissionId}`);
    return response.data;
  }

  async listRolePermissions(roleId: number): Promise<Permission[]> {
    const response = await api.get(`/access/roles/${roleId}/permissions`);
    return response.data;
  }

  async listUserPermissions(userId: number): Promise<string[]> {
    const response = await api.get(`/access/users/${userId}/permissions`);
    return response.data;
  }
}

export default new UserService();