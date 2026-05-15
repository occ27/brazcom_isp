// Serviços de autenticação e API para NFCom — reutiliza o cliente axios central
import api, { API_BASE_URL } from './api';

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
  is_company_admin: boolean;
  cliente_id?: number; // Para identificar usuários que são clientes
  created_at: string;
  updated_at: string;
}

// Funções helper para endpoints
export const endpoints = {
  auth: {
    login: '/auth/login',
    register: '/auth/register',
  },
  users: '/api/v1/usuarios/',
  companies: '/api/v1/companies/',
  nfcom: '/api/v1/nfcom/',
  health: '/health',
};

// Interceptor para adicionar token nas requisições
api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor para lidar com erros de autenticação
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Só redirecionar para login se:
    // 1. É um erro 401 (não autorizado)
    // 2. Não é a própria requisição de login
    // 3. Não estamos já na página de login (evita loop)
    // 4. Há um token armazenado (significa que o usuário tentou se autenticar)
    if (
      error.response?.status === 401 && 
      !error.config?.url?.includes('/auth/login') &&
      window.location.pathname !== '/' &&
      window.location.pathname !== '/login' &&
      localStorage.getItem('token')
    ) {
        // Não forçar logout automático para 401s originados de endpoints
        // que podem ser acessados por tokens de cliente (por exemplo,
        // listagem de empresas ou endpoints do client-portal). Esses 401
        // normalmente significam que o token é de cliente e está tentando
        // acessar um endpoint admin-only — nesse caso não queremos quebrar
        // a UX do portal redirecionando o usuário para a home.
        const reqUrl = error.config?.url || '';
        const doNotLogoutPrefixes = [
          '/empresas',
          '/access',
          '/client-portal',
          '/client-auth',
          '/usuarios/me/active-empresa',
        ];

        const shouldSkipLogout = doNotLogoutPrefixes.some((p) => reqUrl.startsWith(p) || reqUrl.includes(p));

        if (!shouldSkipLogout) {
          logout();
          window.location.href = '/';
        }
    }
    return Promise.reject(error);
  }
);

// Interfaces
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface RegisterData {
  email: string;
  nome: string;
  password: string;
}

// Funções de autenticação
export async function login(username: string, password: string): Promise<LoginResponse> {
  try {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await api.post(endpoints.auth.login, formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    // Store token in localStorage
    localStorage.setItem('token', response.data.access_token); localStorage.setItem('user_type', 'admin');

    return response.data;
  } catch (error: any) {

    if (error.response) {
      throw new Error(error.response.data.detail || 'Login failed');
    } else {
      throw new Error('Network error');
    }
  }
}

export async function register(userData: RegisterData): Promise<void> {
  try {
    await api.post(endpoints.auth.register, userData);
  } catch (error: any) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'Registration failed');
    } else {
      throw new Error('Network error');
    }
  }
}

export async function clientLogin(cpf_cnpj: string, password: string, empresa_id: number): Promise<LoginResponse> {
  try {
    const response = await api.post('/client-auth/login', {
      cpf_cnpj,
      password,
      empresa_id,
    });

    // Store token in localStorage
    localStorage.setItem('token', response.data.access_token); localStorage.setItem('user_type', 'client');

    return response.data;
  } catch (error: any) {

    if (error.response) {
      throw new Error(error.response.data.detail || 'Login failed');
    } else {
      throw new Error('Network error');
    }
  }
}

export function logout() {
  // Limpar token de autenticação
  localStorage.removeItem('token');
  
  // Limpar dados de empresa ativa
  localStorage.removeItem('activeCompany');
  localStorage.removeItem('activeCompanyId');
  localStorage.removeItem('user_type');
  
  // Limpar qualquer outro dado de sessão
  // localStorage.clear(); // Use com cuidado, remove TUDO
}

export function getStoredToken(): string | null {
  return localStorage.getItem('token');
}

export function setAuthToken(token: string) {
  localStorage.setItem('token', token);
}

export async function getCurrentUser(): Promise<User> {
  const userType = localStorage.getItem('user_type');
  const token = localStorage.getItem('token');
  
  if (!token) throw new Error('No token found');

  try {
    // Se sabemos que é admin, ou se não sabemos nada (priorizar admin para evitar 401s comuns)
    if (userType === 'admin' || !userType) {
      try {
        const response = await api.get('/usuarios/me');
        const userData = response.data;
        const name = userData.full_name || userData.nome;
        
        // Se conseguimos dados de admin, salvar o tipo para a próxima vez
        if (!userType) localStorage.setItem('user_type', 'admin');
        
        return {
          id: userData.id,
          email: userData.email,
          full_name: name,
          nome: name,
          is_superuser: userData.is_superuser,
          is_active: userData.is_active,
          ativo: userData.is_active,
          tipo: userData.is_superuser ? 'admin' : 'user',
          active_empresa_id: userData.active_empresa_id,
          is_company_admin: userData.is_company_admin || false,
          created_at: userData.created_at,
          updated_at: userData.updated_at,
        };
      } catch (adminError) {
        // Se falhou mas o tipo era explicitamente admin, repassa o erro
        if (userType === 'admin') throw adminError;
        // Caso contrário, continua para tentar cliente
      }
    }

    // Tentar o endpoint de cliente
    const response = await api.get('/client-auth/me');
    const clienteData = response.data;
    // Se conseguimos dados de cliente, salvar o tipo para a próxima vez
    if (!userType) localStorage.setItem('user_type', 'client');
    
    return {
      id: clienteData.id,
      email: clienteData.email,
      full_name: clienteData.nome_razao_social,
      nome: clienteData.nome_razao_social,
      is_superuser: false,
      is_active: true,
      ativo: true,
      tipo: 'user',
      active_empresa_id: undefined,
      cliente_id: clienteData.id,
      created_at: '',
      updated_at: '',
    };
  } catch (error: any) {
    if (error.response?.status === 401) {
      logout();
      throw new Error('Token expirado');
    }
    throw new Error('Erro ao obter informações do usuário');
  }
}

export default api;