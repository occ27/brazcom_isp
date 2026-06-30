import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { caixaService, CaixaSessao, LocalPagamento, FormaPagamento, CaixaMovimentacao } from '../services/caixaService';
import { CurrencyDollarIcon, ArrowDownCircleIcon, ArrowUpCircleIcon, ArchiveBoxIcon, ArchiveBoxXMarkIcon } from '@heroicons/react/24/outline';

const CaixaPDV: React.FC = () => {
  const { user } = useAuth();
  const [sessao, setSessao] = useState<CaixaSessao | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // States for Abrir Caixa
  const [locais, setLocais] = useState<LocalPagamento[]>([]);
  const [selectedLocal, setSelectedLocal] = useState<number | ''>('');
  const [saldoInicialStr, setSaldoInicialStr] = useState<string>('');

  // States for Caixa Aberto
  const [movimentacoes, setMovimentacoes] = useState<CaixaMovimentacao[]>([]);
  const [formas, setFormas] = useState<FormaPagamento[]>([]);
  const [tipoMov, setTipoMov] = useState<'SANGRIA' | 'SUPRIMENTO'>('SUPRIMENTO');
  const [valorMovStr, setValorMovStr] = useState<string>('');
  const [descMov, setDescMov] = useState<string>('');
  const [selectedForma, setSelectedForma] = useState<number | ''>('');

  // States for Fechar Caixa
  const [isClosing, setIsClosing] = useState(false);
  const [saldoFinalStr, setSaldoFinalStr] = useState<string>('');

  useEffect(() => {
    if (user?.active_empresa_id) {
      loadInitialData(user.active_empresa_id);
    }
  }, [user]);

  const loadInitialData = async (empresaId: number) => {
    try {
      setLoading(true);
      setError(null);
      // Carregar Locais de Pagamento para o combo
      const locaisData = await caixaService.getLocaisPagamento(empresaId);
      setLocais(locaisData);
      
      const formasData = await caixaService.getFormasPagamento(empresaId);
      setFormas(formasData);

      try {
        const sessaoData = await caixaService.getSessaoAtual(empresaId);
        setSessao(sessaoData);
        if (sessaoData) {
          loadExtrato(sessaoData.id);
        }
      } catch (e: any) {
        if (e.response && e.response.status === 404) {
          setSessao(null); // Nenhum caixa aberto
        } else {
          throw e;
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao carregar dados do caixa');
    } finally {
      setLoading(false);
    }
  };

  const loadExtrato = async (sessaoId: number) => {
    try {
      const extrato = await caixaService.getExtrato(sessaoId);
      setMovimentacoes(extrato);
    } catch (err) {
      console.error('Erro ao carregar extrato', err);
    }
  };

  // Helper para formatar moeda
  const parseCurrencyInput = (val: string): number => {
    if (!val) return 0;
    const clean = val.replace(/\./g, '').replace(',', '.');
    const floatVal = parseFloat(clean);
    return isNaN(floatVal) ? 0 : floatVal;
  };

  const formatCurrency = (val: number): string => {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
  };

  const handleMoneyInputChange = (val: string, setter: (v: string) => void) => {
    let digits = val.replace(/\D/g, '');
    if (!digits) {
      setter('');
      return;
    }
    const floatVal = parseInt(digits, 10) / 100;
    // Format to pt-BR without the R$ prefix
    const formatted = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(floatVal);
    setter(formatted);
  };

  const handleAbrirCaixa = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user?.active_empresa_id || selectedLocal === '') return;
    try {
      const saldo = parseCurrencyInput(saldoInicialStr);
      const novaSessao = await caixaService.abrirSessao(user.active_empresa_id, Number(selectedLocal), saldo);
      setSessao(novaSessao);
      setSaldoInicialStr('');
      loadExtrato(novaSessao.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao abrir caixa');
    }
  };

  const handleLancarMovimentacao = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessao || selectedForma === '') return;
    try {
      const valor = parseCurrencyInput(valorMovStr);
      if (valor <= 0) {
        alert("O valor deve ser maior que zero.");
        return;
      }
      await caixaService.lancarMovimentacao(sessao.id, {
        tipo: tipoMov,
        valor: valor,
        forma_pagamento_id: Number(selectedForma),
        descricao: descMov
      });
      setValorMovStr('');
      setDescMov('');
      loadExtrato(sessao.id);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Erro ao lançar movimentação');
    }
  };

  const handleFecharCaixa = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessao) return;
    try {
      const saldoFinal = parseCurrencyInput(saldoFinalStr);
      await caixaService.fecharSessao(sessao.id, saldoFinal);
      setSessao(null);
      setIsClosing(false);
      setSaldoFinalStr('');
      setMovimentacoes([]);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Erro ao fechar caixa');
    }
  };

  if (loading) {
    return <div className="p-6 text-center text-gray-500">Carregando caixa...</div>;
  }

  // --- RENDERS ---

  if (!sessao) {
    return (
      <div className="max-w-md mx-auto mt-10">
        <div className="bg-white p-8 rounded-lg shadow-md border border-gray-100">
          <div className="text-center mb-6">
            <ArchiveBoxIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h2 className="mt-4 text-2xl font-bold text-gray-900">O seu caixa está fechado</h2>
            <p className="mt-2 text-sm text-gray-500">Abra o caixa para começar a receber pagamentos e realizar movimentações.</p>
          </div>

          {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">{error}</div>}

          <form onSubmit={handleAbrirCaixa} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Local de Pagamento</label>
              <select
                required
                value={selectedLocal}
                onChange={(e) => setSelectedLocal(Number(e.target.value))}
                className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
              >
                <option value="" disabled>Selecione o Local</option>
                {locais.map(l => (
                  <option key={l.id} value={l.id}>{l.nome}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Saldo Inicial (Troco em Gaveta)</label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <span className="text-gray-500 sm:text-sm">R$</span>
                </div>
                <input
                  type="text"
                  value={saldoInicialStr}
                  onChange={(e) => handleMoneyInputChange(e.target.value, setSaldoInicialStr)}
                  className="focus:ring-indigo-500 focus:border-indigo-500 block w-full pl-10 sm:text-sm border-gray-300 rounded-md"
                  placeholder="0,00"
                />
              </div>
            </div>
            <button
              type="submit"
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Abrir Caixa
            </button>
          </form>
        </div>
      </div>
    );
  }

  // --- Caixa Aberto Dashboard ---

  const totalRecebimentos = movimentacoes.filter(m => m.tipo === 'RECEBIMENTO').reduce((acc, m) => acc + m.valor, 0);
  const totalSuprimentos = movimentacoes.filter(m => m.tipo === 'SUPRIMENTO').reduce((acc, m) => acc + m.valor, 0);
  const totalSangrias = movimentacoes.filter(m => m.tipo === 'SANGRIA').reduce((acc, m) => acc + m.valor, 0);
  const saldoAtualCalculado = sessao.saldo_inicial + totalRecebimentos + totalSuprimentos - totalSangrias;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      
      {/* Header do Caixa */}
      <div className="md:flex md:items-center md:justify-between mb-6">
        <div className="flex-1 min-w-0">
          <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl sm:truncate flex items-center">
            <ArchiveBoxIcon className="h-8 w-8 mr-3 text-indigo-600" />
            Caixa: {sessao.local_pagamento_nome || 'Local Desconhecido'}
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Operador: {sessao.usuario_nome} • Aberto em: {new Date(sessao.data_abertura).toLocaleString('pt-BR')}
          </p>
        </div>
        <div className="mt-4 flex md:mt-0 md:ml-4">
          <button
            onClick={() => setIsClosing(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700"
          >
            <ArchiveBoxXMarkIcon className="-ml-1 mr-2 h-5 w-5" />
            Fechar Caixa
          </button>
        </div>
      </div>

      {/* Cards de Resumo */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <div className="bg-white overflow-hidden shadow rounded-lg border-l-4 border-blue-500">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0"><CurrencyDollarIcon className="h-6 w-6 text-gray-400" /></div>
              <div className="ml-5 w-0 flex-1"><dl><dt className="text-sm font-medium text-gray-500 truncate">Saldo Inicial</dt><dd className="text-lg font-medium text-gray-900">{formatCurrency(sessao.saldo_inicial)}</dd></dl></div>
            </div>
          </div>
        </div>
        <div className="bg-white overflow-hidden shadow rounded-lg border-l-4 border-green-500">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0"><ArrowUpCircleIcon className="h-6 w-6 text-green-400" /></div>
              <div className="ml-5 w-0 flex-1"><dl><dt className="text-sm font-medium text-gray-500 truncate">Entradas (Receb. + Sup.)</dt><dd className="text-lg font-medium text-gray-900">{formatCurrency(totalRecebimentos + totalSuprimentos)}</dd></dl></div>
            </div>
          </div>
        </div>
        <div className="bg-white overflow-hidden shadow rounded-lg border-l-4 border-red-500">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0"><ArrowDownCircleIcon className="h-6 w-6 text-red-400" /></div>
              <div className="ml-5 w-0 flex-1"><dl><dt className="text-sm font-medium text-gray-500 truncate">Saídas (Sangrias)</dt><dd className="text-lg font-medium text-gray-900">{formatCurrency(totalSangrias)}</dd></dl></div>
            </div>
          </div>
        </div>
        <div className="bg-indigo-50 overflow-hidden shadow rounded-lg border-l-4 border-indigo-600">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0"><ArchiveBoxIcon className="h-6 w-6 text-indigo-600" /></div>
              <div className="ml-5 w-0 flex-1"><dl><dt className="text-sm font-medium text-indigo-800 truncate">Saldo Calculado</dt><dd className="text-2xl font-bold text-indigo-900">{formatCurrency(saldoAtualCalculado)}</dd></dl></div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Nova Movimentação */}
        <div className="lg:col-span-1">
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Lançamento Manual</h3>
            <form onSubmit={handleLancarMovimentacao} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Tipo de Movimentação</label>
                <div className="mt-2 grid grid-cols-2 gap-3">
                  <button type="button" onClick={() => setTipoMov('SUPRIMENTO')} className={`py-2 px-3 flex justify-center text-sm font-medium rounded-md border ${tipoMov === 'SUPRIMENTO' ? 'border-green-500 bg-green-50 text-green-700' : 'border-gray-300 text-gray-700 bg-white hover:bg-gray-50'}`}>Suprimento</button>
                  <button type="button" onClick={() => setTipoMov('SANGRIA')} className={`py-2 px-3 flex justify-center text-sm font-medium rounded-md border ${tipoMov === 'SANGRIA' ? 'border-red-500 bg-red-50 text-red-700' : 'border-gray-300 text-gray-700 bg-white hover:bg-gray-50'}`}>Sangria</button>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Forma de Pagamento</label>
                <select
                  required
                  value={selectedForma}
                  onChange={(e) => setSelectedForma(Number(e.target.value))}
                  className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
                >
                  <option value="" disabled>Selecione</option>
                  {formas.map(f => (
                    <option key={f.id} value={f.id}>{f.nome}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Valor</label>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <span className="text-gray-500 sm:text-sm">R$</span>
                  </div>
                  <input
                    type="text"
                    required
                    value={valorMovStr}
                    onChange={(e) => handleMoneyInputChange(e.target.value, setValorMovStr)}
                    className="focus:ring-indigo-500 focus:border-indigo-500 block w-full pl-10 sm:text-sm border-gray-300 rounded-md"
                    placeholder="0,00"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Descrição (Opcional)</label>
                <input
                  type="text"
                  value={descMov}
                  onChange={(e) => setDescMov(e.target.value)}
                  className="mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md"
                  placeholder="Ex: Troco inicial, Retirada para pagamento..."
                />
              </div>

              <button
                type="submit"
                className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${tipoMov === 'SUPRIMENTO' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}`}
              >
                Lançar {tipoMov === 'SUPRIMENTO' ? 'Suprimento' : 'Sangria'}
              </button>
            </form>
          </div>
        </div>

        {/* Extrato de Movimentações */}
        <div className="lg:col-span-2">
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 border-b border-gray-200 sm:px-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900">Extrato da Sessão</h3>
            </div>
            <ul className="divide-y divide-gray-200 overflow-y-auto max-h-[500px]">
              {movimentacoes.length === 0 ? (
                <li className="px-6 py-4 text-center text-gray-500 text-sm">Nenhuma movimentação registrada.</li>
              ) : (
                movimentacoes.map((mov) => (
                  <li key={mov.id} className="px-4 py-4 sm:px-6 hover:bg-gray-50 transition duration-150">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <div className={`flex-shrink-0 h-10 w-10 rounded-full flex items-center justify-center ${mov.tipo === 'SANGRIA' ? 'bg-red-100' : 'bg-green-100'}`}>
                          {mov.tipo === 'SANGRIA' ? <ArrowDownCircleIcon className="h-6 w-6 text-red-600" /> : <ArrowUpCircleIcon className="h-6 w-6 text-green-600" />}
                        </div>
                        <div className="ml-4">
                          <p className="text-sm font-medium text-gray-900 truncate">{mov.tipo}</p>
                          <p className="text-xs text-gray-500">{mov.forma_pagamento_nome || 'N/A'} • {new Date(mov.created_at).toLocaleTimeString('pt-BR')} - {mov.descricao}</p>
                        </div>
                      </div>
                      <div className={`text-sm font-semibold ${mov.tipo === 'SANGRIA' ? 'text-red-600' : 'text-green-600'}`}>
                        {mov.tipo === 'SANGRIA' ? '-' : '+'}{formatCurrency(mov.valor)}
                      </div>
                    </div>
                  </li>
                ))
              )}
            </ul>
          </div>
        </div>

      </div>

      {/* Modal de Fechamento */}
      {isClosing && (
        <div className="fixed z-10 inset-0 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => setIsClosing(false)} aria-hidden="true"></div>
            <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
            <div className="inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-sm sm:w-full sm:p-6">
              <div>
                <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
                  <ArchiveBoxXMarkIcon className="h-6 w-6 text-red-600" aria-hidden="true" />
                </div>
                <div className="mt-3 text-center sm:mt-5">
                  <h3 className="text-lg leading-6 font-medium text-gray-900" id="modal-title">Fechar Caixa</h3>
                  <div className="mt-2">
                    <p className="text-sm text-gray-500 mb-4">
                      Realize a contagem do dinheiro em gaveta (Blind Close). Informe o valor total exato que está no caixa físico.
                    </p>
                    <form onSubmit={handleFecharCaixa}>
                      <div>
                        <div className="mt-1 relative rounded-md shadow-sm">
                          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <span className="text-gray-500 sm:text-sm">R$</span>
                          </div>
                          <input
                            type="text"
                            required
                            value={saldoFinalStr}
                            onChange={(e) => handleMoneyInputChange(e.target.value, setSaldoFinalStr)}
                            className="focus:ring-red-500 focus:border-red-500 block w-full pl-10 sm:text-sm border-gray-300 rounded-md"
                            placeholder="0,00"
                          />
                        </div>
                      </div>
                      <div className="mt-5 sm:mt-6 sm:grid sm:grid-cols-2 sm:gap-3 sm:grid-flow-row-dense">
                        <button
                          type="submit"
                          className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-red-600 text-base font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 sm:col-start-2 sm:text-sm"
                        >
                          Confirmar Fechamento
                        </button>
                        <button
                          type="button"
                          onClick={() => setIsClosing(false)}
                          className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:col-start-1 sm:text-sm"
                        >
                          Cancelar
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default CaixaPDV;