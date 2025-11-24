import axios from 'axios';

// ========================================================================
// Configuração da URL Base da API
// ========================================================================
// A URL é definida pela variável de ambiente REACT_APP_API_BASE_URL:
//
// DESENVOLVIMENTO LOCAL (sem Docker):
//   REACT_APP_API_BASE_URL=http://localhost:8000
//   Frontend (porta 3000) -> Backend (porta 8000)
//
// PRODUÇÃO (com Docker + Apache):
//   REACT_APP_API_BASE_URL=/api
//   Apache faz proxy reverso: /api -> http://localhost:8013
//
const REACT_APP_API_BASE_URL = process.env.REACT_APP_API_BASE_URL;

const computeApiBase = () => {
  if (REACT_APP_API_BASE_URL) {
    return REACT_APP_API_BASE_URL.replace(/\/$/, '');
  }

  // Fallback para desenvolvimento local se a variável não estiver definida
  return 'http://localhost:8000';
};

export const API_BASE_URL = computeApiBase();

// Configuração base do axios
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para adicionar X-Active-Empresa automaticamente quando definido
api.interceptors.request.use((config) => {
  try {
    const activeCompanyId = localStorage.getItem('activeCompanyId');
    if (activeCompanyId) {
      config.headers = config.headers || {};
      config.headers['X-Active-Empresa'] = activeCompanyId;
    }

    // Anexar token de autenticação (se presente) para endpoints protegidos
    const token = localStorage.getItem('token');
    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch (e) {
    // localStorage pode não estar disponível em alguns ambientes (SSR)
  }
  return config;
});

// Debugging: intercept and log network errors that result in no response
api.interceptors.response.use(
  (res) => res,
  (error) => {
    // Log full error to console to aid debugging when error.response is undefined
    try {
      // eslint-disable-next-line no-console
      console.error('API network error:', error?.message, error);
      // eslint-disable-next-line no-console
      console.error('Axios error.request:', error?.request);
      // eslint-disable-next-line no-console
      console.error('Axios error.response:', error?.response);
    } catch (e) {}
    return Promise.reject(error);
  }
);

// Serviço de autenticação
export const authService = {
  // Registrar novo usuário
  register: async (userData) => {
    try {
      const response = await api.post('/usuarios/register', userData);
      return response.data;
    } catch (error) {
      throw error.response?.data || error.message;
    }
  },

  // Fazer login
  login: async (credentials) => {
    try {
      // Para OAuth2, precisamos enviar como form data, não JSON
      const formData = new URLSearchParams();
      formData.append('username', credentials.username);
      formData.append('password', credentials.password);

      const response = await api.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });
      return response.data;
    } catch (error) {
      throw error.response?.data || error.message;
    }
  },

  // Obter dados do usuário logado
  getCurrentUser: async (token) => {
    try {
      const response = await api.get('/usuarios/me', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      return response.data;
    } catch (error) {
      throw error.response?.data || error.message;
    }
  },

  // Atualizar dados do usuário
  updateCurrentUser: async (userData, token) => {
    try {
      const response = await api.put('/usuarios/me', userData, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      return response.data;
    } catch (error) {
      throw error.response?.data || error.message;
    }
  },
};

export default api;