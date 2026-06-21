import React, { useEffect, useState } from 'react';
import { caixaService, LocalPagamento, FormaPagamento } from '../../services/caixaService';
import { stringifyError } from '../../utils/error';
import { PlusIcon, TrashIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';

interface Props {
  empresaId: number;
}

export const CaixaConfigTab: React.FC<Props> = ({ empresaId }) => {
  const [locais, setLocais] = useState<LocalPagamento[]>([]);
  const [formas, setFormas] = useState<FormaPagamento[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [newLocal, setNewLocal] = useState('');
  const [newForma, setNewForma] = useState('');

  const loadData = async () => {
    setLoading(true);
    try {
      const [locaisRes, formasRes] = await Promise.all([
        caixaService.getLocais(empresaId, true),
        caixaService.getFormas(empresaId, true)
      ]);
      setLocais(locaisRes);
      setFormas(formasRes);
    } catch (e) {
      console.error(e);
      alert('Erro ao carregar dados do Caixa');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (empresaId) loadData();
  }, [empresaId]);

  const handleAddLocal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newLocal.trim()) return;
    try {
      await caixaService.createLocal(empresaId, { nome: newLocal });
      setNewLocal('');
      loadData();
    } catch (e) {
      alert(stringifyError(e));
    }
  };

  const handleToggleLocal = async (local: LocalPagamento) => {
    try {
      await caixaService.updateLocal(local.id, { is_active: !local.is_active });
      loadData();
    } catch (e) {
      alert(stringifyError(e));
    }
  };

  const handleDeleteLocal = async (id: number) => {
    if (!confirm('Deseja realmente excluir este local de pagamento?')) return;
    try {
      await caixaService.deleteLocal(id);
      loadData();
    } catch (e) {
      alert(stringifyError(e));
    }
  };

  const handleAddForma = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newForma.trim()) return;
    try {
      await caixaService.createForma(empresaId, { nome: newForma });
      setNewForma('');
      loadData();
    } catch (e) {
      alert(stringifyError(e));
    }
  };

  const handleToggleForma = async (forma: FormaPagamento) => {
    try {
      await caixaService.updateForma(forma.id, { is_active: !forma.is_active });
      loadData();
    } catch (e) {
      alert(stringifyError(e));
    }
  };

  const handleDeleteForma = async (id: number) => {
    if (!confirm('Deseja realmente excluir esta forma de pagamento?')) return;
    try {
      await caixaService.deleteForma(id);
      loadData();
    } catch (e) {
      alert(stringifyError(e));
    }
  };

  if (loading) {
    return <div className="p-4 text-center text-gray-500">Carregando configurações do caixa...</div>;
  }

  return (
    <div className="space-y-8">
      
      {/* Locais de Pagamento */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h4 className="text-lg font-medium text-gray-900 mb-4">Locais de Pagamento (Caixas Físicos)</h4>
        
        <form onSubmit={handleAddLocal} className="flex gap-3 mb-6">
          <input
            type="text"
            required
            value={newLocal}
            onChange={(e) => setNewLocal(e.target.value)}
            placeholder="Nome do novo local (ex: Caixa Principal, Receção...)"
            className="flex-1 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
          />
          <button
            type="submit"
            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none"
          >
            <PlusIcon className="-ml-1 mr-2 h-5 w-5" />
            Adicionar
          </button>
        </form>

        <ul className="divide-y divide-gray-200 border border-gray-200 rounded-md">
          {locais.length === 0 ? (
            <li className="px-4 py-3 text-sm text-gray-500 text-center">Nenhum local cadastrado.</li>
          ) : (
            locais.map((local) => (
              <li key={local.id} className="px-4 py-3 flex items-center justify-between">
                <div className="flex items-center">
                  <span className={`text-sm font-medium ${local.is_active ? 'text-gray-900' : 'text-gray-400 line-through'}`}>
                    {local.nome}
                  </span>
                  <span className={`ml-3 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${local.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                    {local.is_active ? 'Ativo' : 'Inativo'}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    type="button"
                    onClick={() => handleToggleLocal(local)}
                    className="text-gray-400 hover:text-indigo-600 focus:outline-none"
                    title={local.is_active ? 'Desativar' : 'Ativar'}
                  >
                    {local.is_active ? <XCircleIcon className="h-5 w-5" /> : <CheckCircleIcon className="h-5 w-5" />}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteLocal(local.id)}
                    className="text-gray-400 hover:text-red-600 focus:outline-none"
                    title="Excluir"
                  >
                    <TrashIcon className="h-5 w-5" />
                  </button>
                </div>
              </li>
            ))
          )}
        </ul>
      </div>

      {/* Formas de Pagamento */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h4 className="text-lg font-medium text-gray-900 mb-4">Formas de Pagamento (Sangria/Suprimento e Recebimentos)</h4>
        
        <form onSubmit={handleAddForma} className="flex gap-3 mb-6">
          <input
            type="text"
            required
            value={newForma}
            onChange={(e) => setNewForma(e.target.value)}
            placeholder="Nome da forma (ex: Dinheiro, PIX, Cartão Crédito...)"
            className="flex-1 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
          />
          <button
            type="submit"
            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none"
          >
            <PlusIcon className="-ml-1 mr-2 h-5 w-5" />
            Adicionar
          </button>
        </form>

        <ul className="divide-y divide-gray-200 border border-gray-200 rounded-md">
          {formas.length === 0 ? (
            <li className="px-4 py-3 text-sm text-gray-500 text-center">Nenhuma forma cadastrada.</li>
          ) : (
            formas.map((forma) => (
              <li key={forma.id} className="px-4 py-3 flex items-center justify-between">
                <div className="flex items-center">
                  <span className={`text-sm font-medium ${forma.is_active ? 'text-gray-900' : 'text-gray-400 line-through'}`}>
                    {forma.nome}
                  </span>
                  <span className={`ml-3 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${forma.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                    {forma.is_active ? 'Ativo' : 'Inativo'}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    type="button"
                    onClick={() => handleToggleForma(forma)}
                    className="text-gray-400 hover:text-indigo-600 focus:outline-none"
                    title={forma.is_active ? 'Desativar' : 'Ativar'}
                  >
                    {forma.is_active ? <XCircleIcon className="h-5 w-5" /> : <CheckCircleIcon className="h-5 w-5" />}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteForma(forma.id)}
                    className="text-gray-400 hover:text-red-600 focus:outline-none"
                    title="Excluir"
                  >
                    <TrashIcon className="h-5 w-5" />
                  </button>
                </div>
              </li>
            ))
          )}
        </ul>
      </div>

    </div>
  );
};
