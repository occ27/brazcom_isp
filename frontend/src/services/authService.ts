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
    try {
      // debug: confirmar que um token está sendo anexado (não logar o token em si)
      // eslint-disable-next-line no-console
      console.log('authService: token presente, anexando Authorization header')
    } catch (e) {}
  } else {
    try {
      // eslint-disable-next-line no-console
      console.log('authService: nenhum token encontrado no localStorage')
    } catch (e) {}
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
      console.log('authService: Token inválido/expirado, fazendo logout');
      logout();
      window.location.href = '/';
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
    localStorage.setItem('token', response.data.access_token);

    return response.data;
  } catch (error: any) {
    // Log for debugging in the browser console (helps diagnose CORS / network issues)
    try {
      // eslint-disable-next-line no-console
      console.error('authService.login error object:', error);
      // eslint-disable-next-line no-console
      console.error('authService.login error.request:', error?.request);
      // eslint-disable-next-line no-console
      console.error('authService.login error.response:', error?.response);
    } catch (e) {}

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

export function logout() {
  // Limpar token de autenticação
  localStorage.removeItem('token');
  
  // Limpar dados de empresa ativa
  localStorage.removeItem('activeCompany');
  localStorage.removeItem('activeCompanyId');
  
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
  try {
    const response = await api.get('/usuarios/me');
    // Mapear os campos do backend para o formato esperado pelo frontend
    const userData = response.data;
    return {
      id: userData.id,
      email: userData.email,
      full_name: userData.full_name,
      nome: userData.full_name, // Campo de compatibilidade
      is_superuser: userData.is_superuser,
      is_active: userData.is_active,
      ativo: userData.is_active, // Campo de compatibilidade
      tipo: userData.is_superuser ? 'admin' : 'user', // Campo de compatibilidade
      active_empresa_id: userData.active_empresa_id,
      created_at: userData.created_at,
      updated_at: userData.updated_at,
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