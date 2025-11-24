import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import api from '../services/api';
import { Company } from '../types'; // Importar o tipo completo

interface CompanyContextType {
  activeCompany: Company | null;
  setActiveCompany: (company: Company | null) => Promise<void>;
}

const CompanyContext = createContext<CompanyContextType | undefined>(undefined);

export const useCompany = () => {
  const ctx = useContext(CompanyContext);
  if (!ctx) throw new Error('useCompany must be used within CompanyProvider');
  return ctx;
};

export const CompanyProvider = ({ children }: { children: ReactNode }) => {
  const [activeCompany, setActiveCompanyState] = useState<Company | null>(null);

  useEffect(() => {
    // Inicializar a partir do localStorage ou do backend
    const init = async () => {
      // ⚠️ IMPORTANTE: Só buscar empresas se o usuário estiver autenticado
      const token = localStorage.getItem('token');
      if (!token) {
        // Sem token, não fazer requisições à API
        // Limpar qualquer dado de empresa no localStorage
        localStorage.removeItem('activeCompany');
        localStorage.removeItem('activeCompanyId');
        setActiveCompanyState(null);
        return;
      }

      // Prioridade: backend preference, se disponível
      try {
        const resp = await api.get('/usuarios/me/active-empresa');
        if (resp?.data) {
          setActiveCompanyState(resp.data);
          return;
        }
      } catch (e) {
        // Ignorar erros (ex.: 404 quando não definido)
      }

      // Se não há preferência no backend, tentar usar localStorage
      const saved = localStorage.getItem('activeCompany');
      if (saved) {
        try {
          setActiveCompanyState(JSON.parse(saved));
          return;
        } catch (e) {
          setActiveCompanyState(null);
        }
      }

      // Se ainda não há, buscar empresas disponíveis e selecionar automaticamente a primeira
      try {
        const res = await api.get('/empresas/');
        const data = res.data && (res.data.data || res.data.empresas || res.data);
        if (Array.isArray(data) && data.length > 0) {
          // Selecionar a primeira empresa e persistir no backend
          const first = data[0];
          try {
            await api.post('/usuarios/me/active-empresa', { empresa_id: first.id });
          } catch (e) {
            // se persistir falhar, ainda definimos localmente para UX
            console.warn('Falha ao persistir empresa ativa no backend, definindo localmente', e);
          }
          setActiveCompanyState(first);
        }
      } catch (e) {
        // não fazer nada se a lista de empresas não puder ser obtida
      }
    };
    init();
  }, []);

  useEffect(() => {
    // Guardar em localStorage para persistência entre reloads
    if (activeCompany) {
      localStorage.setItem('activeCompany', JSON.stringify(activeCompany));
      localStorage.setItem('activeCompanyId', String(activeCompany.id));
    } else {
      localStorage.removeItem('activeCompany');
      localStorage.removeItem('activeCompanyId');
    }
  }, [activeCompany]);

  const setActiveCompany = async (company: Company | null) => {
    try {
      if (company) {
        await api.post('/usuarios/me/active-empresa', { empresa_id: company.id });
      } else {
        await api.delete('/usuarios/me/active-empresa');
      }
      setActiveCompanyState(company);
    } catch (e) {
      // Falha em sincronizar com backend: ainda atualizar local para UX, opcionalmente reverter
      console.error('Erro ao setar empresa ativa:', e);
      setActiveCompanyState(company);
    }
  };

  return (
    <CompanyContext.Provider value={{ activeCompany, setActiveCompany }}>
      {children}
    </CompanyContext.Provider>
  );
};

export default CompanyContext;
