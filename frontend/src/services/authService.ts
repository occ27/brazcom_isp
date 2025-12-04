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

        if (shouldSkipLogout) {
          console.log('authService: 401 recebido em endpoint não-admin, não forçando logout (cliente) =>', reqUrl);
        } else {
          console.log('authService: Token inválido/expirado, fazendo logout');
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

export async function clientLogin(cpf_cnpj: string, password: string, empresa_id: number): Promise<LoginResponse> {
  try {
    const response = await api.post('/client-auth/login', {
      cpf_cnpj,
      password,
      empresa_id,
    });

    // Store token in localStorage
    localStorage.setItem('token', response.data.access_token);

    return response.data;
  } catch (error: any) {
    // Log for debugging in the browser console (helps diagnose CORS / network issues)
    try {
      // eslint-disable-next-line no-console
      console.error('authService.clientLogin error object:', error);
      // eslint-disable-next-line no-console
      console.error('authService.clientLogin error.request:', error?.request);
      // eslint-disable-next-line no-console
      console.error('authService.clientLogin error.response:', error?.response);
    } catch (e) {}

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
    // Primeiro tentar o endpoint de cliente
    try {
      const response = await api.get('/client-auth/me');
      const clienteData = response.data;
      return {
        id: clienteData.id,
        email: clienteData.email,
        full_name: clienteData.nome_razao_social,
        nome: clienteData.nome_razao_social,
        is_superuser: false, // Clientes não são superusuários
        is_active: true, // Assumir ativo se conseguiu logar
        ativo: true,
        tipo: 'user',
        active_empresa_id: undefined, // Clientes não têm empresa ativa no mesmo sentido
        cliente_id: clienteData.id, // O próprio ID do cliente
        created_at: '', // Não disponível
        updated_at: '',
      };
    } catch (clientError) {
      // Se falhar, tentar o endpoint de usuários (admin)
      const response = await api.get('/usuarios/me');
      const userData = response.data;
      return {
        id: userData.id,
        email: userData.email,
        full_name: userData.full_name,
        nome: userData.full_name,
        is_superuser: userData.is_superuser,
        is_active: userData.is_active,
        ativo: userData.is_active,
        tipo: userData.is_superuser ? 'admin' : 'user',
        active_empresa_id: userData.active_empresa_id,
        created_at: userData.created_at,
        updated_at: userData.updated_at,
      };
    }
  } catch (error: any) {
    if (error.response?.status === 401) {
      logout();
      throw new Error('Token expirado');
    }
    throw new Error('Erro ao obter informações do usuário');
  }
}

export default api;