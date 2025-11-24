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
        setCompanies(data || []);
      } catch (e) {
        console.error('Erro ao buscar empresas', e);
      } finally {
        setLoading(false);
      }
    };
    fetchCompanies();
  }, []);

  const handleChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = Number(e.target.value);
    const selected = companies.find((c) => c.id === id) || null;
    try {
      await setActiveCompany(selected as any);
      enqueueSnackbar('Empresa selecionada com sucesso', { variant: 'success' });
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
              value={activeCompany?.id ?? ''}
              className="border rounded px-2 py-1 text-sm"
            >
              <option value="">Selecione a empresa</option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>{c.nome_fantasia || c.razao_social}</option>
              ))}
            </select>
          </div>

          {/* Mobile: botão que abre modal */}
          <div className="md:hidden relative">
            <button
              onClick={() => setMobileOpen(true)}
              className="bg-white border rounded px-3 py-1 text-sm flex items-center space-x-2"
              aria-haspopup="dialog"
              aria-expanded={mobileOpen}
            >
              <span>{activeCompany?.nome_fantasia || activeCompany?.razao_social || 'Selecionar empresa'}</span>
              <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
                      value={activeCompany?.id ?? ''}
                      className="w-full border rounded p-2"
                    >
                      <option value="">Selecione a empresa</option>
                      {companies.map((c) => (
                        <option key={c.id} value={c.id}>{c.nome_fantasia || c.razao_social}</option>
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
