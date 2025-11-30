import React, { useEffect, useState } from 'react';
import { useCompany } from '../contexts/CompanyContext';
import api from '../services/api';
import { useSnackbar } from 'notistack';

interface CompanyOption {
  id: number;
  razao_social: string;
  nome_fantasia?: string;
}

const CompanySelector: React.FC = () => {
  const { activeCompany, setActiveCompany } = useCompany();
  const [companies, setCompanies] = useState<CompanyOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  // notistack handles auto-dismiss and queueing

  useEffect(() => {
    const fetchCompanies = async () => {
      try {
        setLoading(true);
        const res = await api.get('/empresas/');
        // Debug: log da resposta para detectar formato
        console.debug('CompanySelector: /empresas response', res);
        // Aceitar multiple formatos: res.data, res.data.data, res.data.empresas
        const data = res.data && (res.data.data || res.data.empresas || res.data);
        const companyList = data || [];
        setCompanies(companyList);

        // Se não há empresa ativa selecionada e temos empresas disponíveis, selecionar a primeira automaticamente
        if (!activeCompany && companyList.length > 0) {
          const firstCompany = companyList[0];
          try {
            await setActiveCompany(firstCompany as any);
          } catch (err) {
            console.error('Erro ao selecionar empresa automaticamente', err);
          }
        }
      } catch (e) {
        console.error('Erro ao buscar empresas', e);
      } finally {
        setLoading(false);
      }
    };
    fetchCompanies();
  }, [activeCompany, setActiveCompany, enqueueSnackbar]);

  const handleChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = Number(e.target.value);
    const selected = companies.find((c) => c.id === id) || null;
    try {
      await setActiveCompany(selected as any);
    } catch (err) {
      enqueueSnackbar('Erro ao selecionar empresa', { variant: 'error' });
    }
  };

  // Responsividade: usar select no desktop e botão + modal em telas pequenas
  return (
    <div className="flex items-center">
      {loading ? (
        <span className="text-sm text-gray-500">Carregando empresas...</span>
      ) : (
        <>
          {/* Desktop */}
          <div className="hidden md:block">
            <select
              onChange={handleChange}
              value={activeCompany?.id ?? (companies.length > 0 ? companies[0].id : '')}
              className="border rounded px-2 py-1 text-sm md:max-w-64 lg:max-w-80 xl:max-w-96"
              style={{ minWidth: '150px' }}
            >
              {companies.length === 0 && (
                <option value="">Nenhuma empresa disponível</option>
              )}
              {companies.map((c) => (
                <option key={c.id} value={c.id} title={c.nome_fantasia || c.razao_social}>
                  {c.nome_fantasia || c.razao_social}
                </option>
              ))}
            </select>
          </div>

          {/* Mobile: botão que abre modal */}
          <div className="md:hidden relative">
            <button
              onClick={() => setMobileOpen(true)}
              className="bg-white border rounded px-3 py-1 text-sm flex items-center space-x-2 max-w-48 sm:max-w-64"
              style={{ minWidth: '120px' }}
              aria-haspopup="dialog"
              aria-expanded={mobileOpen}
              title={activeCompany?.nome_fantasia || activeCompany?.razao_social || (companies.length > 0 ? companies[0].nome_fantasia || companies[0].razao_social : 'Selecionar empresa')}
            >
              <span className="truncate flex-1 text-left">
                {activeCompany?.nome_fantasia || activeCompany?.razao_social || (companies.length > 0 ? companies[0].nome_fantasia || companies[0].razao_social : 'Selecionar empresa')}
              </span>
              <svg className="w-4 h-4 text-gray-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {mobileOpen && (
              // Central modal to avoid being hidden at the bottom on some mobile layouts
              <div className="fixed inset-0 flex items-center justify-center md:hidden" style={{ zIndex: 9999 }}>
                <div className="absolute inset-0 bg-black opacity-30" style={{ zIndex: 9998 }} onClick={() => setMobileOpen(false)} />
                <div className="relative w-11/12 bg-white rounded-lg p-4 shadow-lg" style={{ maxHeight: '80vh', overflowY: 'auto', zIndex: 10000 }}>
                  <div className="flex items-center justify-between mb-2">
                    <strong>Selecionar empresa</strong>
                    <button onClick={() => setMobileOpen(false)} className="text-sm text-gray-600">Fechar</button>
                  </div>
                  <div>
                    <select
                      onChange={async (e) => { 
                        try {
                          await handleChange(e);
                          // enqueueSnack já chamado dentro de handleChange
                        } catch (err) {
                          // enqueueSnack já chamado dentro de handleChange
                        }
                        setMobileOpen(false);
                      }}
                      value={activeCompany?.id ?? (companies.length > 0 ? companies[0].id : '')}
                      className="w-full border rounded p-2"
                    >
                      {companies.length === 0 && (
                        <option value="">Nenhuma empresa disponível</option>
                      )}
                      {companies.map((c) => (
                        <option key={c.id} value={c.id} title={c.nome_fantasia || c.razao_social}>
                          {c.nome_fantasia || c.razao_social}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default CompanySelector;
