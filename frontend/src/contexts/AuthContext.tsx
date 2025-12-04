import React, { useContext, useState, createContext, useEffect } from 'react';
import * as authService from '../services/authService';
import userService from '../services/userService';

interface AppUser {
  id: number;
  email: string;
  full_name: string;
  nome?: string; // Mantido para compatibilidade
  is_superuser: boolean;
  is_active: boolean;
  ativo?: boolean; // Mantido para compatibilidade
  tipo?: 'admin' | 'user'; // Mantido para compatibilidade
  active_empresa_id?: number;
  cliente_id?: number; // Para identificar usuários que são clientes
  created_at: string;
  updated_at: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: AppUser | null;
  loading: boolean;
  error: string | null;
  permissions: string[];
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  register: (userData: any) => Promise<void>;
  loadUserInfo: () => Promise<void>;
  hasPermission: (name: string) => boolean;
  reloadPermissions: () => Promise<void>;
  isClientUser: () => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<string[]>([]);

  useEffect(() => {
    // Initialize auth on app start
    const token = authService.getStoredToken();
    if (token) {
      // Carregar informações do usuário
      loadUserInfo();
    } else {
      setLoading(false);
    }
  }, []);

  const loadUserInfo = async () => {
    console.log('🔥 LOADUSERINFO STARTED');
    try {
      const userData = await authService.getCurrentUser();
      console.log('📦 USER DATA RECEIVED:', userData);
      setUser(userData);

      // Aguardar um tick para garantir que o estado foi atualizado
      await new Promise(resolve => setTimeout(resolve, 0));

      // Se for usuário cliente (cliente_id presente) pular carregamento de permissões
      if (userData.cliente_id !== undefined && userData.cliente_id !== null) {
        setPermissions([]);
      } else {
        // load aggregated permissions for the user (apenas para usuários administrativos)
        try {
          const perms = await userService.listUserPermissions(userData.id);
          setPermissions(perms || []);
        } catch (e) {
          console.warn('Não foi possível carregar permissões do usuário', e);
          setPermissions([]);
        }
      }
      setIsAuthenticated(true);

    } catch (error) {
      console.error('❌ ERRO LOAD USER INFO:', error);
      // Token pode estar expirado, fazer logout
      logout();
    } finally {
      setLoading(false);
    }
  };

  const reloadPermissions = async () => {
    if (!user) return;
    try {
      const perms = await userService.listUserPermissions(user.id);
      setPermissions(perms || []);
    } catch (e) {
      console.warn('Erro ao recarregar permissões', e);
    }
  };

  const isClientUser = () => {
    return user ? user.cliente_id !== null && user.cliente_id !== undefined : false;
  };

  const hasPermission = (name: string) => {
    if (!user) return false;
    if (user.is_superuser) return true;
    return permissions.includes(name);
  };

  const login = async (username: string, password: string) => {
    try {
      setError(null);
      setLoading(true);

      await authService.login(username, password);
      // Após login bem-sucedido, carregar informações do usuário
      await loadUserInfo();

    } catch (error: any) {
      setError(error.message || 'Erro ao fazer login');
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const register = async (userData: any) => {
    try {
      setError(null);
      setLoading(true);

      await authService.register(userData);
    } catch (error: any) {
      setError(error.message || 'Erro ao registrar');
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    authService.logout();
    setUser(null);
    setIsAuthenticated(false);
    setError(null);
  };

  const value = {
    isAuthenticated,
    user,
    loading,
    error,
    permissions,
    login,
    logout,
    register,
    loadUserInfo,
    hasPermission,
    reloadPermissions,
    isClientUser,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}