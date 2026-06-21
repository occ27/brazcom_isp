import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Paper, Typography, Button, IconButton, TextField, CircularProgress, Chip, Snackbar, Alert, useMediaQuery, useTheme, MenuItem, FormControl, InputLabel, Select, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TablePagination, Card, CardContent, Divider, Pagination, SelectChangeEvent, InputAdornment, Dialog, DialogTitle, DialogContent, DialogActions, Menu, ListItemIcon, ListItemText, Grid, Tooltip } from '@mui/material';
import { PlusIcon, PencilIcon, TrashIcon, MagnifyingGlassIcon, XMarkIcon, DocumentTextIcon, EllipsisVerticalIcon, UserIcon, MapPinIcon, WrenchScrewdriverIcon, BanknotesIcon, ChatBubbleLeftRightIcon, SignalIcon, CalendarDaysIcon, EnvelopeIcon, PhoneIcon, DocumentArrowDownIcon, ArrowTopRightOnSquareIcon, CheckCircleIcon, ExclamationCircleIcon, BellIcon, EyeIcon, InformationCircleIcon } from '@heroicons/react/24/outline';
import api from '../services/authService';
import { formatCurrency } from '../utils/currencyUtils';
import { useAuth } from '../contexts/AuthContext';
import { useCompany } from '../contexts/CompanyContext';
import clientService, { ClientCreate } from '../services/clientService';
import { companyService } from '../services/companyService';
import { stringifyError } from '../utils/error';
import reportService from '../services/reportService';
import ticketService from '../services/ticketService';
import receivableService, { Receivable } from '../services/receivableService';
import { caixaService, CaixaSessao, FormaPagamento } from '../services/caixaService';

const Clients: React.FC = () => {
  const { user } = useAuth();
  const { activeCompany } = useCompany();
  const navigate = useNavigate();
  const [clients, setClients] = useState<any[]>([]);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editingClient, setEditingClient] = useState<any | null>(null);
  const [cepLoading, setCepLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('basic');

  // Pagination state
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [totalRows, setTotalRows] = useState(0);

  // Search state
  const [searchTerm, setSearchTerm] = useState('');

  const [formData, setFormData] = useState<any>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' | 'warning' });

  // Statement state
  const [statementOpen, setStatementOpen] = useState(false);
  const [selectedClientForStatement, setSelectedClientForStatement] = useState<any | null>(null);
  const [clientReceivables, setClientReceivables] = useState<any[]>([]);
  const [clientContracts, setClientContracts] = useState<any[]>([]);
  const [statementFilterContract, setStatementFilterContract] = useState<string>('all');
  const [statementFilterStatus, setStatementFilterStatus] = useState<string>('all');
  const [statementLoading, setStatementLoading] = useState(false);
  const [printingStatement, setPrintingStatement] = useState(false);
  const [statementTab, setStatementTab] = useState<string>('overview');
  const [clientTickets, setClientTickets] = useState<any[]>([]);
  const [ticketsLoading, setTicketsLoading] = useState(false);

  // Caixa / Baixa states
  const [sessao, setSessao] = useState<CaixaSessao | null>(null);
  const [formas, setFormas] = useState<FormaPagamento[]>([]);
  const [formaId, setFormaId] = useState<number | ''>('');
  const [multaStr, setMultaStr] = useState('0,00');
  const [jurosStr, setJurosStr] = useState('0,00');
  const [descontoStr, setDescontoStr] = useState('0,00');
  const [openSettle, setOpenSettle] = useState(false);
  const [selectedReceivable, setSelectedReceivable] = useState<Receivable | null>(null);
  const [unblockResultDialogOpen, setUnblockResultDialogOpen] = useState(false);
  const [unblockResult, setUnblockResult] = useState<{
    attempted: boolean;
    success: boolean;
    message: string;
    cliente_nome: string;
  } | null>(null);

  // Supervisor authorization states
  const [openAuthSettle, setOpenAuthSettle] = useState(false);
  const [authSettleEmail, setAuthSettleEmail] = useState('');
  const [authSettlePassword, setAuthSettlePassword] = useState('');
  const [authSettleError, setAuthSettleError] = useState('');
  const [authSettleLoading, setAuthSettleLoading] = useState(false);

  // Menu state
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedClientForMenu, setSelectedClientForMenu] = useState<any | null>(null);

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, client: any) => {
    setAnchorEl(event.currentTarget);
    setSelectedClientForMenu(client);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedClientForMenu(null);
  };

  const handleExportPDF = async () => {
    if (!activeCompany) return;
    try {
      setLoading(true);
      const blob = await reportService.generateClientsPdf(activeCompany.id, { q: searchTerm });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `relatorio_clientes_${new Date().getTime()}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      setSnackbar({ open: false, message: 'Relatório gerado com sucesso!', severity: 'success' });
    } catch (error: any) {
      setSnackbar({ open: true, message: stringifyError(error), severity: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const loadClients = useCallback(async () => {
    if (!activeCompany) return;
    setLoading(true);
    try {
      const data = await clientService.getClientsByCompany(activeCompany.id, page + 1, rowsPerPage, searchTerm || undefined);
      setClients(data.clientes || []);
      setTotalRows(data.total || 0);
    } catch (e) {
      console.error(e);
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao carregar clientes', severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [activeCompany, page, rowsPerPage, searchTerm]);

  useEffect(() => {
    if (activeCompany) {
      loadClients();
    }
  }, [activeCompany, loadClients]);

  // Debounce search
  useEffect(() => {
    if (activeCompany) {
      const timeoutId = setTimeout(() => {
        setPage(0);
        loadClients();
      }, 500); // Debounce for 500ms

      return () => clearTimeout(timeoutId);
    }
  }, [searchTerm, activeCompany]);

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(isMobile ? newPage - 1 : newPage);
  };

  const handleTableRowsPerPageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleMobileRowsPerPageChange = (event: SelectChangeEvent<number>) => {
    setRowsPerPage(event.target.value as number);
    setPage(0);
  };

  const handleInputChange = (field: string, value: any) => {
    setFormData((prev: any) => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors((prev: Record<string, string>) => ({ ...prev, [field]: '' }));
  };

  const handleAddressChange = (index: number, field: string, value: any) => {
    setFormData((prev: any) => {
      const newEnderecos = [...(prev.enderecos || [])];
      if (!newEnderecos[index]) newEnderecos[index] = {};
      newEnderecos[index] = { ...newEnderecos[index], [field]: value };
      return { ...prev, enderecos: newEnderecos };
    });
    if (errors[`enderecos[${index}].${field}`]) {
      setErrors((prev: Record<string, string>) => ({ ...prev, [`enderecos[${index}].${field}`]: '' }));
    }
  };

  const handleCepChange = async (index: number, value: string) => {
    const formattedCep = companyService.formatCEPInput(value);
    handleAddressChange(index, 'cep', formattedCep);

    const cepClean = formattedCep.replace(/\D/g, '');
    if (cepClean.length === 8 && companyService.validateCEP(formattedCep)) {
      setCepLoading(true);
      try {
        const addressData = await companyService.searchCEP(formattedCep);
        if (addressData) {
          handleAddressChange(index, 'endereco', addressData.endereco);
          handleAddressChange(index, 'bairro', addressData.bairro);
          handleAddressChange(index, 'municipio', addressData.municipio);
          handleAddressChange(index, 'uf', addressData.uf);
          handleAddressChange(index, 'codigo_ibge', addressData.codigo_ibge);
        }
      } catch (error) {
        console.error('Erro ao buscar CEP:', error);
      } finally {
        setCepLoading(false);
      }
    }
  };

  const handleAddAddress = () => {
    setFormData((prev: any) => ({
      ...prev,
      enderecos: [
        ...(prev.enderecos || []),
        {
          is_principal: !(prev.enderecos && prev.enderecos.length > 0),
          cep: '', endereco: '', numero: '', complemento: '', bairro: '', municipio: '', uf: '', codigo_ibge: ''
        }
      ]
    }));
  };

  const handleRemoveAddress = (index: number) => {
    setFormData((prev: any) => {
      const newEnderecos = prev.enderecos.filter((_: any, i: number) => i !== index);
      if (newEnderecos.length > 0 && prev.enderecos[index].is_principal) {
        newEnderecos[0].is_principal = true;
      }
      return { ...prev, enderecos: newEnderecos };
    });
  };

  const handleOpen = async (client?: any) => {
    setErrors({});
    setActiveTab('basic');

    if (client) {
      try {
        setLoading(true);
        const fullClient = await clientService.getClient(client.id);
        setEditingClient(fullClient);
        let primaryAddr: any = null;
        if (fullClient.enderecos && Array.isArray(fullClient.enderecos) && fullClient.enderecos.length > 0) {
          primaryAddr = fullClient.enderecos.find((a: any) => a.is_principal) || fullClient.enderecos[0];
        }
        setFormData({
          nome_razao_social: fullClient.nome_razao_social,
          cpf_cnpj: fullClient.cpf_cnpj,
          tipo_pessoa: fullClient.tipo_pessoa || 'F',
          ind_ie_dest: fullClient.ind_ie_dest || '9',
          inscricao_estadual: fullClient.inscricao_estadual || '',
          email: fullClient.email || '',
          telefone: fullClient.telefone || '',
          data_nascimento: fullClient.data_nascimento || '',
          recebe_notificacoes: fullClient.recebe_notificacoes !== false,
          enderecos: fullClient.enderecos && fullClient.enderecos.length > 0 ? fullClient.enderecos : [{
            is_principal: true,
            endereco: '', numero: '', complemento: '', bairro: '', municipio: '', uf: '', codigo_ibge: '', cep: ''
          }],
        });
        setOpen(true);
      } catch (error) {
        setSnackbar({ open: true, message: stringifyError(error) || 'Erro ao carregar dados do cliente.', severity: 'error' });
      } finally {
        setLoading(false);
      }
    } else {
      setEditingClient(null);
      setFormData({
        nome_razao_social: '',
        cpf_cnpj: '',
        tipo_pessoa: 'F',
        ind_ie_dest: '9',
        inscricao_estadual: '',
        email: '',
        telefone: '',
        data_nascimento: '',
        recebe_notificacoes: true,
        enderecos: [{
          is_principal: true,
          endereco: '', numero: '', complemento: '', bairro: '', municipio: '', uf: '', codigo_ibge: '', cep: ''
        }],
      });
      setOpen(true);
    }
  };

  const handleClose = () => { setOpen(false); setEditingClient(null); };

  const handleOpenStatement = async (client: any) => {
    if (!activeCompany) return;
    setSelectedClientForStatement(client);
    setStatementOpen(true);
    setStatementLoading(true);
    setStatementFilterContract('all');
    setStatementFilterStatus('all');
    setStatementTab('overview');
    try {
      // Fetch full client details (to get addresses and other fields)
      const fullClient = await clientService.getClient(client.id);
      setSelectedClientForStatement(fullClient);

      // Load Receivables
      const recRes = await api.get(`/receivables/cliente/${client.id}?empresa_id=${activeCompany.id}`);
      setClientReceivables(recRes.data || []);
      
      // Load Contracts
      const conRes = await api.get(`/servicos-contratados/cliente/${client.id}?empresa_id=${activeCompany.id}`);
      setClientContracts(conRes.data || []);

      // Load Tickets
      setTicketsLoading(true);
      try {
        const ticketRes = await ticketService.listTickets(0, 100, undefined, undefined, undefined, client.id);
        setClientTickets(ticketRes.data || []);
      } catch (err) {
        console.error('Erro ao carregar tickets do cliente', err);
        setClientTickets([]);
      } finally {
        setTicketsLoading(false);
      }
    } catch (e) {
      console.error('Erro ao carregar dados do extrato', e);
      setSnackbar({ open: true, message: 'Erro ao carregar dados completos do cliente', severity: 'error' });
    } finally {
      setStatementLoading(false);
    }
  };

  const parseCurrencyInput = (val: string): number => {
    if (!val) return 0;
    const clean = val.replace(/\./g, '').replace(',', '.');
    const floatVal = parseFloat(clean);
    return isNaN(floatVal) ? 0 : floatVal;
  };

  const formatMoneyInput = (val: string): string => {
    let digits = val.replace(/\D/g, '');
    if (!digits) return '';
    const floatVal = parseInt(digits, 10) / 100;
    return new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(floatVal);
  };

  const handleMoneyChange = (val: string, setter: (v: string) => void) => {
    setter(formatMoneyInput(val));
  };
  
  const calculateTotalSettle = () => {
    if (!selectedReceivable) return 0;
    const base = selectedReceivable.amount;
    const multa = parseCurrencyInput(multaStr);
    const juros = parseCurrencyInput(jurosStr);
    const desconto = parseCurrencyInput(descontoStr);
    return base + multa + juros - desconto;
  };

  const handleOpenSettleV2 = async (r: Receivable) => {
    setSelectedReceivable(r);
    setOpenSettle(true);
    let defaultMulta = 0;
    let defaultJuros = 0;

    if (r.due_date) {
      const dueDateStr = r.due_date.includes(' ') ? r.due_date.replace(' ', 'T') : (r.due_date.includes('T') ? r.due_date : r.due_date + 'T00:00:00');
      const dueDate = new Date(dueDateStr);
      const today = new Date();
      dueDate.setHours(0,0,0,0);
      today.setHours(0,0,0,0);

      if (today > dueDate) {
        const diffTime = Math.abs(today.getTime() - dueDate.getTime());
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        const finePercent = r.fine_percent != null ? r.fine_percent : 2.0; 
        const interestPercent = r.interest_percent != null ? r.interest_percent : 1.0;
        
        defaultMulta = r.amount * (finePercent / 100);
        defaultJuros = r.amount * ((interestPercent / 30) / 100) * diffDays;
      }
    }

    setMultaStr(new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(defaultMulta));
    setJurosStr(new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(defaultJuros));
    setDescontoStr('0,00');
    setFormaId('');
    
    try {
      if (activeCompany) {
        const sessaoData = await caixaService.getSessaoAtual(activeCompany.id);
        setSessao(sessaoData);
        const formasData = await caixaService.getFormas(activeCompany.id);
        setFormas(formasData.filter(f => f.is_active));
      }
    } catch (e: any) {
      if (e.response?.status === 404) {
        setSessao(null);
      }
    }
  };

  const processSettleRequest = async () => {
    if (!selectedReceivable || !sessao || !activeCompany) return;
    const total = calculateTotalSettle();
    
    try {
      const response = await receivableService.settleReceivable(selectedReceivable.id, {
        paid_amount: total,
        multa: parseCurrencyInput(multaStr),
        juros: parseCurrencyInput(jurosStr),
        desconto: parseCurrencyInput(descontoStr),
        splits: [{
          forma_pagamento_id: Number(formaId),
          amount: total
        }]
      });

      setOpenSettle(false);

      // Refresh client statement receivables
      if (selectedClientForStatement) {
        setStatementLoading(true);
        try {
          const recRes = await api.get(`/receivables/cliente/${selectedClientForStatement.id}?empresa_id=${activeCompany.id}`);
          setClientReceivables(recRes.data || []);
        } catch (e) {
          console.error('Erro ao recarregar extrato após baixa', e);
        } finally {
          setStatementLoading(false);
        }
      }

      if (response.unblock_attempted) {
        setUnblockResult({
          attempted: true,
          success: response.unblock_success || false,
          message: response.unblock_message || '',
          cliente_nome: selectedReceivable.cliente_nome || selectedClientForStatement?.nome_razao_social || 'Cliente'
        });
        setUnblockResultDialogOpen(true);
      } else {
        setSnackbar({ open: true, message: 'Cobrança recebida com sucesso.', severity: 'success' });
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || "Erro ao baixar cobrança");
    }
  };

  const handleConfirmSettleV2 = async () => {
    if (!selectedReceivable || !sessao) return;
    if (formaId === '') {
      alert("Selecione a forma de pagamento");
      return;
    }
    
    const total = calculateTotalSettle();
    if (total <= 0) {
      alert("O total não pode ser menor ou igual a zero.");
      return;
    }

    const desconto = parseCurrencyInput(descontoStr);
    if (desconto > 0) {
      if (!user?.is_superuser && !user?.is_company_admin) {
        setAuthSettleEmail('');
        setAuthSettlePassword('');
        setAuthSettleError('');
        setOpenAuthSettle(true);
        return;
      }
    }
    
    await processSettleRequest();
  };

  const handleAuthSettleSubmit = async () => {
    setAuthSettleError('');
    setAuthSettleLoading(true);
    try {
      const formData = new URLSearchParams();
      formData.append('username', authSettleEmail);
      formData.append('password', authSettlePassword);
      
      const baseUrl = api.defaults.baseURL || 'http://localhost:8000';
      const res = await fetch(`${baseUrl}/auth/login`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error('Credenciais inválidas');
      const data = await res.json();
      
      const userRes = await fetch(`${baseUrl}/users/me`, {
        headers: { 'Authorization': `Bearer ${data.access_token}` }
      });
      const userData = await userRes.json();
      
      if (!userData.is_superuser && !userData.is_company_admin) {
        throw new Error('Usuário não tem permissão para autorizar desconto.');
      }
      
      setOpenAuthSettle(false);
      await processSettleRequest();
    } catch (err: any) {
      setAuthSettleError(err.message || 'Erro ao autorizar');
    } finally {
      setAuthSettleLoading(false);
    }
  };

  const handlePrintStatement = async () => {
    if (!selectedClientForStatement || !activeCompany) return;
    setPrintingStatement(true);
    try {
      const blob = await reportService.generateStatementPdf(
        selectedClientForStatement.id,
        activeCompany.id,
        {
          contrato_id: statementFilterContract === 'all' ? undefined : statementFilterContract,
          status: statementFilterStatus === 'all' ? undefined : statementFilterStatus
        }
      );
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `extrato_${selectedClientForStatement.nome_razao_social.replace(/\s+/g, '_')}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
      setSnackbar({ open: true, message: 'PDF do extrato gerado com sucesso!', severity: 'success' });
    } catch (error) {
      console.error(error);
      setSnackbar({ open: true, message: 'Erro ao gerar PDF do extrato', severity: 'error' });
    } finally {
      setPrintingStatement(false);
    }
  };

  const filteredReceivables = clientReceivables.filter(r => {
    const matchContract = statementFilterContract === 'all' || r.servico_contratado_id?.toString() === statementFilterContract;
    const matchStatus = statementFilterStatus === 'all' || r.status === statementFilterStatus;
    return matchContract && matchStatus;
  });

  const statementTotals = filteredReceivables.reduce((acc, r) => {
    if (r.status === 'PAID') acc.paid += (r.paid_amount !== null && r.paid_amount !== undefined ? r.paid_amount : r.amount);
    else if (r.status !== 'CANCELLED') acc.pending += r.amount;
    return acc;
  }, { paid: 0, pending: 0 });

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    // Nome / razão
    if (!formData.nome_razao_social || !String(formData.nome_razao_social).trim()) {
      newErrors.nome_razao_social = 'Nome / Razão Social é obrigatório';
    }

    // CPF / CNPJ
    const rawCpfCnpj = (formData.cpf_cnpj || '').toString();
    const digits = rawCpfCnpj.replace(/\D/g, '');
    if (!digits) {
      newErrors.cpf_cnpj = 'CPF/CNPJ é obrigatório';
    } else if (formData.tipo_pessoa === 'F') {
      if (digits.length !== 11 || !clientService.validateCPF(rawCpfCnpj)) {
        newErrors.cpf_cnpj = 'CPF inválido';
      }
    } else {
      if (digits.length !== 14 || !companyService.validateCNPJ(rawCpfCnpj)) {
        newErrors.cpf_cnpj = 'CNPJ inválido';
      }
    }

    // E-mail (quando informado deve ser válido)
    if (formData.email && String(formData.email).trim() && !clientService.validateEmail(formData.email)) {
      newErrors.email = 'E-mail inválido';
    }

    // Telefone (quando informado deve ter DDD + número)
    if (formData.telefone && String(formData.telefone).trim() && !clientService.validatePhone(formData.telefone)) {
      newErrors.telefone = 'Telefone inválido (informe DDD + número)';
    }

    // Data de Nascimento (não pode ser no futuro - apenas Pessoa Física)
    if (formData.tipo_pessoa === 'F' && formData.data_nascimento) {
      const birth = new Date(formData.data_nascimento);
      if (birth > new Date()) {
        newErrors.data_nascimento = 'Data de nascimento não pode ser no futuro';
      }
    }

    // Regras para Pessoa Jurídica
    if (formData.tipo_pessoa === 'J') {
      // Inscrição estadual conforme indicador
      if (formData.ind_ie_dest && formData.ind_ie_dest !== '9') {
        if (!companyService.validateInscricaoEstadual(formData.inscricao_estadual || '', formData.enderecos?.[0]?.uf || '')) {
          newErrors.inscricao_estadual = 'Inscrição estadual inválida ou obrigatória conforme indicador';
        }
      }
    }

    // Validação de endereço
    const enderecos = formData.enderecos || [];
    enderecos.forEach((end: any, idx: number) => {
      const addressTouched = ['endereco', 'numero', 'bairro', 'municipio', 'uf', 'cep'].some((k) => !!end[k]);
      // Se for PJ tem que ter o primeiro endereço. Se for PF tem que ter se algo foi tocado ou se é o único e está parcialmente preenchido.
      if (addressTouched || (formData.tipo_pessoa === 'J' && idx === 0)) {
        if (!end.endereco) newErrors[`enderecos[${idx}].endereco`] = 'Endereço é obrigatório';
        if (!end.bairro) newErrors[`enderecos[${idx}].bairro`] = 'Bairro é obrigatório';
        if (!end.municipio) newErrors[`enderecos[${idx}].municipio`] = 'Município é obrigatório';
        if (!end.uf) newErrors[`enderecos[${idx}].uf`] = 'UF é obrigatório';
        if (!end.cep) newErrors[`enderecos[${idx}].cep`] = 'CEP é obrigatório';
        else if (!companyService.validateCEP(end.cep)) newErrors[`enderecos[${idx}].cep`] = 'CEP inválido';

        if (end.codigo_ibge && !companyService.validateCodigoIBGE(end.codigo_ibge, end.uf)) {
          newErrors[`enderecos[${idx}].codigo_ibge`] = 'Código IBGE inválido ou incompatível com a UF';
        }
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      setSnackbar({ open: true, message: 'Por favor, corrija os erros do formulário.', severity: 'warning' });
      return;
    }
    if (!activeCompany) return;
    try {
      const payload: any = { ...formData };
      
      // Limpar data de nascimento se for Pessoa Jurídica
      if (payload.tipo_pessoa !== 'F') {
        payload.data_nascimento = null;
      } else if (!payload.data_nascimento) {
        payload.data_nascimento = null;
      }
      
      // Filtrar endereços vazios se não for PJ
      if (payload.tipo_pessoa === 'F') {
         payload.enderecos = payload.enderecos.filter((end: any) => 
            ['endereco', 'numero', 'bairro', 'municipio', 'uf', 'cep'].some((k) => !!end[k])
         );
      }

      let createdClient = null;
      if (editingClient) {
        await clientService.updateClient(activeCompany.id, editingClient.id, payload);
      } else {
        createdClient = await clientService.createClient(activeCompany.id, payload);
      }
      setSnackbar({ open: true, message: `Cliente ${editingClient ? 'atualizado' : 'criado'} com sucesso!`, severity: 'success' });
      handleClose();
      loadClients();

      if (!editingClient && createdClient && createdClient.id) {
        navigate('/contracts', {
          state: {
            preselectClientId: createdClient.id,
            preselectClientName: createdClient.nome_razao_social,
            preselectClientCpfCnpj: createdClient.cpf_cnpj,
            preselectClientAddresses: createdClient.enderecos || []
          }
        });
      }
    } catch (error: any) {
      const msg = stringifyError(error) || 'Erro ao salvar cliente';
      setSnackbar({ open: true, message: msg, severity: 'error' });
    }
  };

  const handleDelete = async (clientId: number) => {
    if (!activeCompany) return;
    if (window.confirm('Tem certeza que deseja excluir este cliente?')) {
      try {
        await clientService.deleteClient(activeCompany.id, clientId);
        setSnackbar({ open: true, message: 'Cliente excluído com sucesso!', severity: 'success' });
        loadClients();
      } catch (error: any) {
        const msg = stringifyError(error) || 'Erro ao excluir cliente';
        setSnackbar({ open: true, message: msg, severity: 'error' });
      }
    }
  };

  if (!activeCompany) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6">Nenhuma empresa ativa</Typography>
        <Typography variant="body2" color="text.secondary">Selecione a empresa para ver os clientes.</Typography>
      </Paper>
    );
  }

  const renderClientCards = () => (
    <Box sx={{ display: 'grid', gap: 2 }}>
      {clients.map((c) => (
        <Card key={c.id} variant="outlined">
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="h6" sx={{ fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {c.nome_razao_social}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  {clientService.formatCpfCnpj(c.cpf_cnpj)}
                </Typography>
              </Box>
              <Chip label={c.is_active ? 'Ativo' : 'Inativo'} color={c.is_active ? 'success' : 'default'} size="small" />
            </Box>
            <Divider sx={{ my: 1.5 }} />
             <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
               <Typography variant="body2">{c.email || '-'}</Typography>
               <Box>
                <IconButton size="small" onClick={(e) => handleMenuOpen(e, c)}>
                  <EllipsisVerticalIcon className="w-5 h-5" />
                </IconButton>
               </Box>
             </Box>
          </CardContent>
        </Card>
      ))}
    </Box>
  );

  const renderClientTable = () => (
    <TableContainer component={Paper} sx={{ flexGrow: 1, overflow: 'auto' }}>
      <Table stickyHeader aria-label="clients table">
        <TableHead>
          <TableRow>
            <TableCell>Nome / Razão Social</TableCell>
            <TableCell>CPF / CNPJ</TableCell>
            <TableCell>Email</TableCell>
            <TableCell>Status</TableCell>
            <TableCell align="right">Ações</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {clients.map((c) => (
            <TableRow hover key={c.id}>
              <TableCell>{c.nome_razao_social}</TableCell>
              <TableCell>{clientService.formatCpfCnpj(c.cpf_cnpj)}</TableCell>
              <TableCell>{c.email || '-'}</TableCell>
              <TableCell>
                <Chip label={c.is_active ? 'Ativo' : 'Inativo'} color={c.is_active ? 'success' : 'default'} size="small" />
              </TableCell>
              <TableCell align="right">
                <IconButton size="small" onClick={(e) => handleMenuOpen(e, c)}>
                  <EllipsisVerticalIcon className="w-5 h-5" />
                </IconButton>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  const renderPagination = () => {
    if (isMobile) {
      return (
        <Box sx={{ 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          gap: 2, 
          py: 3, 
          mt: 2,
          borderTop: '1px solid', 
          borderColor: 'divider',
          bgcolor: 'background.paper'
        }}>
          <Pagination 
            count={Math.ceil(totalRows / rowsPerPage)} 
            page={page + 1} 
            onChange={handleChangePage} 
            color="primary" 
            size="small"
          />
          <FormControl size="small" sx={{minWidth: 120}}>
            <InputLabel>Itens/pág.</InputLabel>
            <Select
              value={rowsPerPage}
              label="Itens/pág."
              onChange={handleMobileRowsPerPageChange}
            >
              <MenuItem value={5}>5</MenuItem>
              <MenuItem value={10}>10</MenuItem>
              <MenuItem value={25}>25</MenuItem>
            </Select>
          </FormControl>
        </Box>
      )
    }

    return (
      <TablePagination
        rowsPerPageOptions={[5, 10, 25, 50, 100]}
        component="div"
        count={totalRows}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={handleChangePage}
        onRowsPerPageChange={handleTableRowsPerPageChange}
        labelRowsPerPage="Itens por página:"
        sx={{ 
          flexShrink: 0, 
          borderTop: '1px solid', 
          borderColor: 'divider',
          bgcolor: 'background.paper',
          '.MuiTablePagination-toolbar': { justifyContent: 'flex-start' },
          '.MuiTablePagination-spacer': { display: 'none' }
        }}
      />
    )
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ flexShrink: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, gap: 1 }}>
        <Typography variant="h5" sx={{ fontWeight: 'bold' }}>Clientes</Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button 
            variant="outlined" 
            startIcon={<DocumentArrowDownIcon className="w-5 h-5" />} 
            onClick={handleExportPDF}
            disabled={loading}
          >
            PDF
          </Button>
          <Button variant="contained" startIcon={<PlusIcon className="w-5 h-5" />} onClick={() => handleOpen()}>
            Novo Cliente
          </Button>
        </Box>
      </Box>

      {/* Search Bar */}
      <Box sx={{ flexShrink: 0, mb: 2 }}>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Buscar por nome, CPF/CNPJ, email, telefone ou ID..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <MagnifyingGlassIcon className="w-5 h-5 text-gray-400" />
              </InputAdornment>
            ),
            endAdornment: searchTerm ? (
              <InputAdornment position="end">
                <IconButton size="small" onClick={() => setSearchTerm('')}>
                  <XMarkIcon className="w-4 h-4" />
                </IconButton>
              </InputAdornment>
            ) : null
          }}
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: 2,
            }
          }}
        />
      </Box>

      <Box sx={{ flexGrow: 1, overflow: 'auto', p: isMobile ? 1 : 0 }}>
        {loading && !open ? (
          <Box sx={{ display: 'flex', flexGrow: 1, justifyContent: 'center', alignItems: 'center' }}><CircularProgress /></Box>
        ) : isMobile ? (
          renderClientCards()
        ) : (
          renderClientTable()
        )}
        
        {/* Pagination inside scrollable area */}
        {!loading && renderPagination()}
      </Box>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-0 sm:p-4">
          <div
            className="absolute inset-0 bg-gradient-to-br from-black/60 via-black/50 to-black/70 backdrop-blur-md"
            onClick={handleClose}
          />
          <div className="relative bg-gradient-to-br from-white via-gray-50 to-blue-50 border border-borderLight rounded-2xl sm:rounded-3xl shadow-modern-hover w-full max-w-sm sm:max-w-md lg:max-w-3xl h-full sm:h-auto max-h-screen sm:max-h-[90vh] flex flex-col overflow-hidden">
            <div className="flex items-center justify-between p-3 sm:p-6 border-b border-borderLight bg-gradient-to-r from-white to-blue-50/30 flex-shrink-0">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-lg sm:rounded-xl flex items-center justify-center shadow">
                  <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M3 7h18M3 12h18M3 17h18" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                </div>
                <div>
                  <h2 className="text-base sm:text-xl font-bold text-text bg-gradient-to-r from-indigo-700 to-indigo-600 bg-clip-text text-transparent">
                    {editingClient ? 'Editar Cliente' : 'Novo Cliente'}
                  </h2>
                  <p className="text-xs sm:text-sm text-textLight hidden sm:block">Informações do cliente para emissão de NFCom.</p>
                </div>
              </div>
              <button
                onClick={handleClose}
                className="p-2 hover:bg-red-50 rounded-xl transition-all duration-200 flex items-center justify-center flex-shrink-0 shadow-sm hover:shadow-md group"
                style={{ minWidth: 40, minHeight: 40 }}
                aria-label="Fechar"
              >
                <svg
                  className="w-5 h-5 sm:w-6 sm:h-6 text-red-400 group-hover:text-red-600 transition-colors"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="relative border-b border-borderLight bg-surfaceElevated shadow-modern flex-shrink-0">
              <div className="flex overflow-x-auto sm:overflow-x-visible">
                {[
                  { id: 'basic', label: 'Dados Básicos', icon: '📋', color: 'blue' },
                  { id: 'address', label: 'Endereço', icon: '📍', color: 'green' },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center space-x-1 sm:space-x-2 px-3 sm:px-6 py-3 sm:py-5 font-medium tab-transition whitespace-nowrap flex-shrink-0 relative rounded-t-lg ${
                      activeTab === tab.id
                        ? `tab-gradient-${tab.color} text-${tab.color === 'blue' ? 'blue' : tab.color === 'green' ? 'green' : 'orange'}-700 shadow-modern-hover`
                        : `text-textLight hover:text-text hover:bg-surface/70 tab-hover-scale`
                    }`}
                  >
                    <span className="text-sm sm:text-base">{tab.icon}</span>
                    <span className="text-xs sm:text-sm font-semibold">{tab.label}</span>
                    {activeTab === tab.id && (
                      <div className={`absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r ${
                        tab.color === 'blue' ? 'from-blue-500 to-blue-600' :
                        tab.color === 'green' ? 'from-green-500 to-green-600' :
                        'from-orange-500 to-orange-600'
                      } rounded-t-sm`} />
                    )}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-3 sm:p-6 min-h-0 bg-gradient-to-b from-white to-gray-50/30">
              {activeTab === 'basic' && (
                <div className="space-y-4 sm:space-y-6">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                    <div className="sm:col-span-2">
                      <TextField
                        label="Nome / Razão Social *"
                        value={formData.nome_razao_social || ''}
                        onChange={(e) => handleInputChange('nome_razao_social', e.target.value)}
                        fullWidth
                        size="small"
                        error={!!errors.nome_razao_social}
                        helperText={errors.nome_razao_social}
                      />
                    </div>

                    <div>
                      <FormControl fullWidth size="small" error={!!errors.tipo_pessoa}>
                        <InputLabel>Tipo Pessoa</InputLabel>
                        <Select
                          value={formData.tipo_pessoa || 'F'}
                          label="Tipo Pessoa"
                          onChange={(e) => handleInputChange('tipo_pessoa', e.target.value)}
                        >
                          <MenuItem value={'F'}>Física</MenuItem>
                          <MenuItem value={'J'}>Jurídica</MenuItem>
                        </Select>
                        {errors.tipo_pessoa && <p className="text-sm text-red-600 mt-1">{errors.tipo_pessoa}</p>}
                      </FormControl>
                    </div>

                    <div>
                      <TextField
                        fullWidth
                        label={formData.tipo_pessoa === 'F' ? 'CPF' : 'CNPJ'}
                        value={formData.cpf_cnpj || ''}
                        onChange={(e) => handleInputChange('cpf_cnpj', clientService.formatCpfCnpjInput(e.target.value))}
                        placeholder={formData.tipo_pessoa === 'F' ? '000.000.000-00' : '00.000.000/0000-00'}
                        size="small"
                        error={!!errors.cpf_cnpj}
                        helperText={errors.cpf_cnpj}
                        inputProps={{ maxLength: formData.tipo_pessoa === 'F' ? 14 : 18 }}
                      />
                    </div>
                    {formData.tipo_pessoa === 'J' && (
                      <>
                        <div>
                          <FormControl fullWidth size="small" error={!!errors.ind_ie_dest}>
                            <InputLabel>Indicador de IE</InputLabel>
                            <Select
                              value={formData.ind_ie_dest || '9'}
                              label="Indicador de IE"
                              onChange={(e) => handleInputChange('ind_ie_dest', e.target.value)}
                            >
                              <MenuItem value={'1'}>Contribuinte ICMS</MenuItem>
                              <MenuItem value={'2'}>Contribuinte Isento</MenuItem>
                              <MenuItem value={'9'}>Não Contribuinte</MenuItem>
                            </Select>
                            {errors.ind_ie_dest && <p className="text-sm text-red-600 mt-1">{errors.ind_ie_dest}</p>}
                          </FormControl>
                        </div>
                        <div>
                          <TextField
                            fullWidth
                            label="Inscrição Estadual"
                            value={formData.inscricao_estadual || ''}
                            onChange={(e) => handleInputChange('inscricao_estadual', e.target.value.toUpperCase())}
                            placeholder="Digite a IE ou 'ISENTO'"
                            size="small"
                            error={!!errors.inscricao_estadual}
                            helperText={errors.inscricao_estadual}
                            disabled={formData.ind_ie_dest === '9'}
                            InputProps={{
                              readOnly: formData.ind_ie_dest === '2',
                            }}
                          />
                        </div>
                      </>
                    )}
                    <div>
                      <TextField
                        label="Telefone"
                        value={formData.telefone || ''}
                        onChange={(e) => handleInputChange('telefone', clientService.formatPhoneInput(e.target.value))}
                        fullWidth
                        size="small"
                        error={!!errors.telefone}
                        helperText={errors.telefone}
                      />
                    </div>
                    <div>
                      <TextField
                        label="E-mail"
                        value={formData.email || ''}
                        onChange={(e) => handleInputChange('email', e.target.value)}
                        fullWidth
                        size="small"
                        error={!!errors.email}
                        helperText={errors.email}
                      />
                    </div>
                    {formData.tipo_pessoa === 'F' && (
                      <div>
                        <TextField
                          label="Data de Nascimento"
                          type="date"
                          value={formData.data_nascimento || ''}
                          onChange={(e) => handleInputChange('data_nascimento', e.target.value)}
                          fullWidth
                          size="small"
                          InputLabelProps={{ shrink: true }}
                          error={!!errors.data_nascimento}
                          helperText={errors.data_nascimento}
                        />
                      </div>
                    )}
                    <div className="sm:col-span-2">
                      <label className={`flex items-center gap-3 p-3 rounded-xl border-2 transition-all cursor-pointer select-none ${
                        formData.recebe_notificacoes
                          ? 'border-indigo-400 bg-indigo-50/40'
                          : 'border-gray-200 hover:border-gray-300 bg-white'
                      }`}>
                        <input
                          type="checkbox"
                          id="recebe_notificacoes"
                          checked={!!formData.recebe_notificacoes}
                          onChange={(e) => handleInputChange('recebe_notificacoes', e.target.checked)}
                          className="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500 cursor-pointer"
                        />
                        <div>
                          <span className="font-semibold text-sm text-text">🔔 Cliente autoriza receber notificações</span>
                          <span className="block text-xs text-textLight mt-0.5">Quando ativo, o sistema poderá enviar cobranças e avisos por e-mail e/ou WhatsApp para este cliente.</span>
                        </div>
                      </label>
                    </div>
                  </div>
                </div>
              )}
              {activeTab === 'address' && (
                <div className="space-y-6">
                  {(formData.enderecos || []).map((endereco: any, index: number) => (
                    <div key={index} className="relative bg-gray-50 p-4 rounded-xl border border-gray-200">
                      <div className="absolute top-2 right-2 flex gap-2">
                        {index === 0 && (
                           <Chip label="Principal" size="small" color="primary" />
                        )}
                        {index > 0 && (
                          <IconButton size="small" onClick={() => handleRemoveAddress(index)} color="error" title="Remover este endereço">
                            <TrashIcon className="w-4 h-4" />
                          </IconButton>
                        )}
                      </div>
                      
                      <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary', fontWeight: 'bold' }}>
                        Endereço {index + 1}
                      </Typography>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                        <div>
                          <TextField
                            fullWidth
                            label="CEP *"
                            value={endereco.cep || ''}
                            onChange={(e) => handleCepChange(index, e.target.value)}
                            error={!!errors[`enderecos[${index}].cep`]}
                            helperText={errors[`enderecos[${index}].cep`]}
                            placeholder="00000-000"
                            InputProps={{
                              endAdornment: cepLoading ? <CircularProgress size={16} /> : null,
                            }}
                            size="small"
                          />
                        </div>

                        <div className="sm:col-span-2">
                          <TextField
                            fullWidth
                            label="Endereço *"
                            value={endereco.endereco || ''}
                            onChange={(e) => handleAddressChange(index, 'endereco', e.target.value)}
                            error={!!errors[`enderecos[${index}].endereco`]}
                            helperText={errors[`enderecos[${index}].endereco`]}
                            size="small"
                          />
                        </div>

                        <div>
                          <TextField
                            fullWidth
                            label="Número"
                            value={endereco.numero || ''}
                            onChange={(e) => handleAddressChange(index, 'numero', e.target.value)}
                            error={!!errors[`enderecos[${index}].numero`]}
                            helperText={errors[`enderecos[${index}].numero`]}
                            size="small"
                          />
                        </div>

                        <div>
                          <TextField
                            fullWidth
                            label="Complemento"
                            value={endereco.complemento || ''}
                            onChange={(e) => handleAddressChange(index, 'complemento', e.target.value)}
                            size="small"
                          />
                        </div>

                        <div>
                          <TextField
                            fullWidth
                            label="Bairro *"
                            value={endereco.bairro || ''}
                            onChange={(e) => handleAddressChange(index, 'bairro', e.target.value)}
                            error={!!errors[`enderecos[${index}].bairro`]}
                            helperText={errors[`enderecos[${index}].bairro`]}
                            size="small"
                          />
                        </div>

                        <div>
                          <TextField
                            fullWidth
                            label="Município *"
                            value={endereco.municipio || ''}
                            InputProps={{
                              readOnly: true,
                            }}
                            error={!!errors[`enderecos[${index}].municipio`]}
                            helperText={errors[`enderecos[${index}].municipio`] || "Preenchido automaticamente pelo CEP"}
                            size="small"
                          />
                        </div>

                        <div>
                          <TextField
                            fullWidth
                            label="UF *"
                            value={endereco.uf || ''}
                            InputProps={{
                              readOnly: true,
                            }}
                            error={!!errors[`enderecos[${index}].uf`]}
                            helperText={errors[`enderecos[${index}].uf`] || "Automático"}
                            size="small"
                          />
                        </div>

                        <div>
                          <TextField
                            fullWidth
                            label="Código IBGE"
                            value={endereco.codigo_ibge || ''}
                            InputProps={{
                              readOnly: true,
                            }}
                            error={!!errors[`enderecos[${index}].codigo_ibge`]}
                            helperText={errors[`enderecos[${index}].codigo_ibge`] || "Automático"}
                            size="small"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                  
                  <div className="flex justify-center mt-4">
                    <Button
                      variant="outlined"
                      startIcon={<PlusIcon className="w-4 h-4" />}
                      onClick={handleAddAddress}
                      size="small"
                      sx={{ borderRadius: '8px' }}
                    >
                      Adicionar Novo Endereço
                    </Button>
                  </div>
                </div>
              )}
            </div>

            <div className="flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-2 sm:gap-3 p-3 sm:p-6 border-t border-borderLight bg-gradient-to-r from-gray-50 to-blue-50/30 flex-shrink-0 shadow-modern">
              <div className="hidden sm:flex items-center space-x-2 text-xs sm:text-sm text-indigo-600 text-center sm:text-left">
                <span className="text-xs sm:text-lg">💡</span>
                <p className="leading-tight font-normal text-xs">Preencha os dados do cliente corretamente.</p>
              </div>
              <div className="flex gap-2 sm:gap-3 justify-center sm:justify-end">
                <button onClick={handleClose} className="px-4 sm:px-5 py-2 sm:py-2.5 btn-secondary rounded-lg sm:rounded-xl shadow-sm hover:shadow-md transition-all duration-200 font-semibold flex-shrink-0 text-sm sm:text-sm">Cancelar</button>
                <button onClick={handleSubmit} className="px-4 sm:px-5 py-2 sm:py-2.5 btn-primary rounded-lg sm:rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 font-semibold flex-shrink-0 text-sm sm:text-sm bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700">{editingClient ? 'Atualizar' : 'Criar'}</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Menu de Ações Único */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        <MenuItem onClick={() => { if (selectedClientForMenu) handleOpenStatement(selectedClientForMenu); handleMenuClose(); }}>
          <ListItemIcon><UserIcon className="w-4 h-4 text-indigo-500" /></ListItemIcon>
          <ListItemText primary="Painel do Cliente" />
        </MenuItem>
        <MenuItem onClick={() => { if (selectedClientForMenu) handleOpen(selectedClientForMenu); handleMenuClose(); }}>
          <ListItemIcon><PencilIcon className="w-4 h-4 text-blue-500" /></ListItemIcon>
          <ListItemText primary="Editar" />
        </MenuItem>
        <Divider />
        <MenuItem onClick={() => { if (selectedClientForMenu) handleDelete(selectedClientForMenu.id); handleMenuClose(); }} sx={{ color: 'error.main' }}>
          <ListItemIcon><TrashIcon className="w-4 h-4 text-red-500" /></ListItemIcon>
          <ListItemText primary="Excluir" />
        </MenuItem>
      </Menu>

      {/* Modal Painel do Cliente (Ficha e Extrato) */}
      <Dialog 
        open={statementOpen} 
        onClose={() => setStatementOpen(false)} 
        maxWidth="lg" 
        fullWidth
        scroll="paper"
        PaperProps={{
          sx: {
            borderRadius: 3,
            minHeight: '80vh',
            maxHeight: '90vh',
            bgcolor: 'grey.50'
          }
        }}
      >
        <DialogTitle sx={{ 
          p: 0,
          borderBottom: '1px solid', 
          borderColor: 'divider',
          bgcolor: 'white'
        }}>
          {/* Header */}
          <Box sx={{ 
            p: 3, 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
            color: 'white',
            gap: 2,
            flexWrap: 'wrap'
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexGrow: 1 }}>
              <Box sx={{ 
                width: 48, 
                height: 48, 
                borderRadius: 2, 
                bgcolor: 'rgba(255, 255, 255, 0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <UserIcon className="w-7 h-7 text-white" />
              </Box>
              <Box>
                <Typography variant="h5" sx={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
                  {selectedClientForStatement?.nome_razao_social}
                  <Chip 
                    label={selectedClientForStatement?.is_active ? 'ATIVO' : 'INATIVO'} 
                    color={selectedClientForStatement?.is_active ? 'success' : 'default'} 
                    size="small" 
                    sx={{ fontWeight: 'bold', bgcolor: selectedClientForStatement?.is_active ? 'success.dark' : 'grey.600', color: 'white' }} 
                  />
                </Typography>
                <Typography variant="body2" sx={{ opacity: 0.85, display: 'flex', alignItems: 'center', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                  <span>{selectedClientForStatement?.tipo_pessoa === 'F' ? 'CPF: ' : 'CNPJ: '}</span>
                  <span>{clientService.formatCpfCnpj(selectedClientForStatement?.cpf_cnpj)}</span>
                  {selectedClientForStatement?.email && <span> • {selectedClientForStatement?.email}</span>}
                  {selectedClientForStatement?.telefone && <span> • {selectedClientForStatement?.telefone}</span>}
                </Typography>
              </Box>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Button
                size="small"
                variant="contained"
                onClick={() => { setStatementOpen(false); handleOpen(selectedClientForStatement); }}
                startIcon={<PencilIcon className="w-4 h-4" />}
                sx={{ 
                  textTransform: 'none', 
                  bgcolor: 'rgba(255, 255, 255, 0.2)', 
                  color: 'white',
                  fontWeight: 'bold',
                  borderRadius: 2,
                  boxShadow: 'none',
                  '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.3)', boxShadow: 'none' }
                }}
              >
                Editar Cadastro
              </Button>
              <IconButton onClick={() => setStatementOpen(false)} sx={{ color: 'white' }}>
                <XMarkIcon className="w-7 h-7" />
              </IconButton>
            </Box>
          </Box>

          {/* Navigation Tabs */}
          <Box sx={{ 
            bgcolor: 'white', 
            borderBottom: '1px solid', 
            borderColor: 'divider',
            display: 'flex', 
            overflowX: 'auto',
            px: 2
          }}>
            {[
              { id: 'overview', label: 'Visão Geral', icon: <UserIcon className="w-5 h-5" /> },
              { id: 'details', label: 'Dados Cadastrais', icon: <MapPinIcon className="w-5 h-5" /> },
              { id: 'contracts', label: 'Contratos e Conectividade', icon: <SignalIcon className="w-5 h-5" /> },
              { id: 'financial', label: 'Extrato Financeiro', icon: <BanknotesIcon className="w-5 h-5" /> },
              { id: 'tickets', label: 'Atendimentos (Tickets)', icon: <ChatBubbleLeftRightIcon className="w-5 h-5" /> }
            ].map(tab => (
              <Button
                key={tab.id}
                onClick={() => setStatementTab(tab.id)}
                startIcon={tab.icon}
                sx={{
                  py: 2,
                  px: 3,
                  borderRadius: 0,
                  color: statementTab === tab.id ? 'primary.main' : 'text.secondary',
                  borderBottom: '3px solid',
                  borderColor: statementTab === tab.id ? 'primary.main' : 'transparent',
                  fontWeight: statementTab === tab.id ? 'bold' : 'normal',
                  '&:hover': {
                    bgcolor: 'grey.50'
                  },
                  textTransform: 'none',
                  fontSize: '0.95rem',
                  whiteSpace: 'nowrap'
                }}
              >
                {tab.label}
              </Button>
            ))}
          </Box>
        </DialogTitle>

        <DialogContent sx={{ p: 3, bgcolor: 'grey.50' }}>
          {statementLoading ? (
            <Box sx={{ py: 15, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
              <CircularProgress size={50} />
              <Typography variant="body2" color="text.secondary">Carregando informações completas do cliente...</Typography>
            </Box>
          ) : (
            <>
              {/* TAB: OVERVIEW */}
              {statementTab === 'overview' && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  {/* KPI Grid */}
                  <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: '1fr 1fr 1fr 1fr' }, gap: 2.5 }}>
                    {/* Financeiro Recebido */}
                    <Card 
                      variant="outlined" 
                      onClick={() => setStatementTab('financial')}
                      sx={{ 
                        borderRadius: 3, 
                        boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease-in-out',
                        '&:hover': {
                          transform: 'translateY(-2px)',
                          boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)',
                          borderColor: 'success.300',
                          bgcolor: 'success.50/5'
                        }
                      }}
                    >
                      <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2.5 }}>
                        <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: 'success.50', color: 'success.main' }}>
                          <BanknotesIcon className="w-7 h-7" />
                        </Box>
                        <Box>
                          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>Total Recebido</Typography>
                          <Typography variant="h6" sx={{ fontWeight: 'bold', color: 'success.dark', mt: 0.5 }}>
                            {formatCurrency(clientReceivables.reduce((acc, r) => r.status === 'PAID' ? acc + (r.paid_amount ?? r.amount) : acc, 0))}
                          </Typography>
                        </Box>
                      </CardContent>
                    </Card>

                    {/* Financeiro Pendente */}
                    <Card 
                      variant="outlined" 
                      onClick={() => setStatementTab('financial')}
                      sx={{ 
                        borderRadius: 3, 
                        boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease-in-out',
                        '&:hover': {
                          transform: 'translateY(-2px)',
                          boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)',
                          borderColor: 'warning.300',
                          bgcolor: 'warning.50/5'
                        }
                      }}
                    >
                      <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2.5 }}>
                        <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: 'warning.50', color: 'warning.main' }}>
                          <BanknotesIcon className="w-7 h-7" />
                        </Box>
                        <Box>
                          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>Total Pendente</Typography>
                          <Typography variant="h6" sx={{ fontWeight: 'bold', color: 'warning.dark', mt: 0.5 }}>
                            {formatCurrency(clientReceivables.reduce((acc, r) => (r.status !== 'PAID' && r.status !== 'CANCELLED' && new Date(r.due_date) >= new Date()) ? acc + r.amount : acc, 0))}
                          </Typography>
                        </Box>
                      </CardContent>
                    </Card>

                    {/* Financeiro Atrasado */}
                    <Card 
                      variant="outlined" 
                      onClick={() => setStatementTab('financial')}
                      sx={{ 
                        borderRadius: 3, 
                        boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease-in-out',
                        '&:hover': {
                          transform: 'translateY(-2px)',
                          boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)',
                          borderColor: 'error.300',
                          bgcolor: 'error.50/5'
                        }
                      }}
                    >
                      <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2.5 }}>
                        <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: 'error.50', color: 'error.main' }}>
                          <BanknotesIcon className="w-7 h-7" />
                        </Box>
                        <Box>
                          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>Total Atrasado</Typography>
                          <Typography variant="h6" sx={{ fontWeight: 'bold', color: 'error.dark', mt: 0.5 }}>
                            {formatCurrency(clientReceivables.reduce((acc, r) => (r.status !== 'PAID' && r.status !== 'CANCELLED' && new Date(r.due_date) < new Date()) ? acc + r.amount : acc, 0))}
                          </Typography>
                        </Box>
                      </CardContent>
                    </Card>

                    {/* Contratos Ativos */}
                    <Card 
                      variant="outlined" 
                      onClick={() => setStatementTab('contracts')}
                      sx={{ 
                        borderRadius: 3, 
                        boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease-in-out',
                        '&:hover': {
                          transform: 'translateY(-2px)',
                          boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)',
                          borderColor: 'primary.300',
                          bgcolor: 'primary.50/5'
                        }
                      }}
                    >
                      <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2.5 }}>
                        <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: 'primary.50', color: 'primary.main' }}>
                          <SignalIcon className="w-7 h-7" />
                        </Box>
                        <Box>
                          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>Contratos Ativos</Typography>
                          <Typography variant="h6" sx={{ fontWeight: 'bold', color: 'primary.dark', mt: 0.5 }}>
                            {clientContracts.filter(c => c.status === 'ATIVO').length} / {clientContracts.length}
                          </Typography>
                        </Box>
                      </CardContent>
                    </Card>
                  </Box>

                  {/* Overview layout */}
                  <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1.5fr 1fr' }, gap: 3 }}>
                    {/* Active Contract Tech Summary */}
                    <Paper variant="outlined" sx={{ p: 3, borderRadius: 3, display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <Typography variant="h6" sx={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 1 }}>
                        <SignalIcon className="w-5 h-5 text-blue-500" />
                        Serviço e Conectividade Atual
                      </Typography>
                      <Divider />
                      {clientContracts.length === 0 ? (
                        <Box sx={{ py: 4, textAlign: 'center' }}>
                          <Typography variant="body2" color="text.secondary">Nenhum contrato assinado ou instalado.</Typography>
                        </Box>
                      ) : (
                        clientContracts.map(c => (
                          <Box key={c.id} sx={{ p: 2, mb: 1, bgcolor: 'grey.50', borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
                              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: 'primary.800' }}>
                                Contrato #{c.id} - {c.servico_descricao || 'Internet'}
                              </Typography>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Tooltip title="Editar Contrato">
                                  <IconButton
                                    size="small"
                                    onClick={() => {
                                      setStatementOpen(false);
                                      navigate('/contracts', { state: { editContractId: c.id } });
                                    }}
                                    sx={{ color: 'primary.main', p: 0.5 }}
                                  >
                                    <PencilIcon className="w-4 h-4" />
                                  </IconButton>
                                </Tooltip>
                                <Tooltip title="Abrir Chamado para este Contrato">
                                  <IconButton
                                    size="small"
                                    onClick={() => {
                                      setStatementOpen(false);
                                      navigate('/tickets', { 
                                        state: { 
                                          preselectClientId: selectedClientForStatement.id,
                                          preselectClientName: selectedClientForStatement.nome_razao_social,
                                          preselectContractId: c.id,
                                          openCreate: true
                                        } 
                                      });
                                    }}
                                    sx={{ color: 'warning.main', p: 0.5 }}
                                  >
                                    <ChatBubbleLeftRightIcon className="w-4 h-4" />
                                  </IconButton>
                                </Tooltip>
                                <Chip 
                                  label={c.status} 
                                  size="small" 
                                  color={c.status === 'ATIVO' ? 'success' : 'warning'} 
                                  sx={{ fontWeight: 'bold' }}
                                />
                              </Box>
                            </Box>
                            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
                              <Box>
                                <Typography variant="caption" color="text.secondary" display="block">Tipo de Conexão</Typography>
                                <Typography variant="body2" sx={{ fontWeight: 500 }}>{c.tipo_conexao || 'FIBRA'}</Typography>
                              </Box>
                              <Box>
                                <Typography variant="caption" color="text.secondary" display="block">Usuário PPPoE</Typography>
                                <Typography variant="body2" sx={{ fontWeight: 500, fontFamily: 'monospace' }}>{c.pppoe_username || '-'}</Typography>
                              </Box>
                              <Box>
                                <Typography variant="caption" color="text.secondary" display="block">Serial ONU</Typography>
                                <Typography variant="body2" sx={{ fontWeight: 500 }}>{c.onu_serial || '-'}</Typography>
                              </Box>
                              <Box>
                                <Typography variant="caption" color="text.secondary" display="block">Sinal Recebido (Rx)</Typography>
                                <Typography variant="body2" sx={{ fontWeight: 500, color: c.onu_sinal ? 'success.main' : 'text.secondary' }}>
                                  {c.onu_sinal ? `${c.onu_sinal} dBm` : '-'}
                                </Typography>
                              </Box>
                            </Box>
                          </Box>
                        ))
                      )}
                    </Paper>

                    {/* Support & Notification summaries */}
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                      {/* Ticket quick status */}
                      <Paper variant="outlined" sx={{ p: 3, borderRadius: 3, display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Typography variant="h6" sx={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 1 }}>
                            <ChatBubbleLeftRightIcon className="w-5 h-5 text-blue-500" />
                            Últimos Chamados
                          </Typography>
                          <Button
                            size="small"
                            variant="text"
                            startIcon={<PlusIcon className="w-4 h-4" />}
                            onClick={() => {
                              setStatementOpen(false);
                              navigate('/tickets', { 
                                state: { 
                                  preselectClientId: selectedClientForStatement.id,
                                  preselectClientName: selectedClientForStatement.nome_razao_social,
                                  openCreate: true
                                } 
                              });
                            }}
                            sx={{ textTransform: 'none', fontWeight: 'bold' }}
                          >
                            Novo
                          </Button>
                        </Box>
                        <Divider />
                        {ticketsLoading ? (
                          <CircularProgress size={24} sx={{ mx: 'auto', my: 2 }} />
                        ) : clientTickets.length === 0 ? (
                          <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>Nenhum chamado de suporte aberto.</Typography>
                        ) : (
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                            {clientTickets.slice(0, 3).map(ticket => (
                              <Box key={ticket.id} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0, flexGrow: 1 }}>
                                  <Tooltip title="Ver no Suporte">
                                    <IconButton
                                      size="small"
                                      onClick={() => {
                                        setStatementOpen(false);
                                        navigate('/tickets', { 
                                          state: { 
                                            preselectClientId: selectedClientForStatement.id,
                                            preselectClientName: selectedClientForStatement.nome_razao_social 
                                          } 
                                        });
                                      }}
                                      sx={{ color: 'primary.main', p: 0.5, flexShrink: 0 }}
                                    >
                                      <EyeIcon className="w-4 h-4" />
                                    </IconButton>
                                  </Tooltip>
                                  <Box sx={{ minWidth: 0 }}>
                                    <Typography variant="body2" sx={{ fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: { xs: 120, md: 150 } }}>
                                      #{ticket.id} - {ticket.titulo}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                      {new Date(ticket.created_at).toLocaleDateString('pt-BR')} • {ticket.categoria}
                                    </Typography>
                                  </Box>
                                </Box>
                                <Chip 
                                  label={ticket.status} 
                                  size="small" 
                                  color={ticket.status === 'ABERTO' ? 'info' : ticket.status === 'EM_ANDAMENTO' ? 'warning' : 'success'} 
                                  variant="outlined"
                                  sx={{ fontSize: '0.7rem', height: 20 }}
                                />
                              </Box>
                            ))}
                          </Box>
                        )}
                      </Paper>

                      {/* Notification Auth card */}
                      <Paper variant="outlined" sx={{ p: 3, borderRadius: 3, bgcolor: selectedClientForStatement?.recebe_notificacoes ? 'success.50/10' : 'grey.100', border: '1px solid', borderColor: selectedClientForStatement?.recebe_notificacoes ? 'success.100' : 'divider' }}>
                        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                          <Box sx={{ color: selectedClientForStatement?.recebe_notificacoes ? 'success.main' : 'text.secondary', mt: 0.5 }}>
                            <BellIcon className="w-6 h-6" />
                          </Box>
                          <Box>
                            <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>Notificações por Email e WhatsApp</Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, fontSize: '0.85rem' }}>
                              {selectedClientForStatement?.recebe_notificacoes 
                                ? 'Autorizado. O cliente recebe avisos de cobrança, faturas e avisos de manutenção automática.' 
                                : 'Bloqueado. O cliente optou por não receber avisos automáticos.'
                              }
                            </Typography>
                          </Box>
                        </Box>
                      </Paper>
                    </Box>
                  </Box>
                </Box>
              )}

              {/* TAB: DETAILS */}
              {statementTab === 'details' && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  <Paper variant="outlined" sx={{ p: 3, borderRadius: 3 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                      <Typography variant="h6" sx={{ fontWeight: 'bold' }}>Dados Pessoais / Cadastrais</Typography>
                      <Button
                        size="small"
                        variant="text"
                        startIcon={<PencilIcon className="w-4 h-4" />}
                        onClick={() => { setStatementOpen(false); handleOpen(selectedClientForStatement); }}
                        sx={{ textTransform: 'none', fontWeight: 'bold' }}
                      >
                        Editar Cadastro
                      </Button>
                    </Box>
                    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: '1fr 1fr 1fr' }, gap: 3 }}>
                      <Box>
                        <Typography variant="caption" color="text.secondary">Nome / Razão Social</Typography>
                        <Typography variant="body1" sx={{ fontWeight: 500 }}>{selectedClientForStatement?.nome_razao_social}</Typography>
                      </Box>
                      <Box>
                        <Typography variant="caption" color="text.secondary">CPF / CNPJ</Typography>
                        <Typography variant="body1" sx={{ fontWeight: 500 }}>{clientService.formatCpfCnpj(selectedClientForStatement?.cpf_cnpj)}</Typography>
                      </Box>
                      <Box>
                        <Typography variant="caption" color="text.secondary">Tipo Pessoa</Typography>
                        <Typography variant="body1" sx={{ fontWeight: 500 }}>{selectedClientForStatement?.tipo_pessoa === 'F' ? 'Física' : 'Jurídica'}</Typography>
                      </Box>
                      <Box>
                        <Typography variant="caption" color="text.secondary">E-mail</Typography>
                        <Typography variant="body1" sx={{ fontWeight: 500 }}>{selectedClientForStatement?.email || '-'}</Typography>
                      </Box>
                      <Box>
                        <Typography variant="caption" color="text.secondary">Telefone / WhatsApp</Typography>
                        <Typography variant="body1" sx={{ fontWeight: 500 }}>{selectedClientForStatement?.telefone || '-'}</Typography>
                      </Box>
                      {selectedClientForStatement?.tipo_pessoa === 'F' && (
                        <Box>
                          <Typography variant="caption" color="text.secondary">Data de Nascimento</Typography>
                          <Typography variant="body1" sx={{ fontWeight: 500 }}>
                            {selectedClientForStatement?.data_nascimento ? new Date(selectedClientForStatement.data_nascimento + 'T00:00:00').toLocaleDateString('pt-BR') : '-'}
                          </Typography>
                        </Box>
                      )}
                      {selectedClientForStatement?.tipo_pessoa === 'J' && (
                        <>
                          <Box>
                            <Typography variant="caption" color="text.secondary">Indicador IE</Typography>
                            <Typography variant="body1" sx={{ fontWeight: 500 }}>
                              {selectedClientForStatement?.ind_ie_dest === '1' ? 'Contribuinte ICMS' : selectedClientForStatement?.ind_ie_dest === '2' ? 'Contribuinte Isento' : 'Não Contribuinte'}
                            </Typography>
                          </Box>
                          <Box>
                            <Typography variant="caption" color="text.secondary">Inscrição Estadual</Typography>
                            <Typography variant="body1" sx={{ fontWeight: 500 }}>{selectedClientForStatement?.inscricao_estadual || '-'}</Typography>
                          </Box>
                        </>
                      )}
                      <Box>
                        <Typography variant="caption" color="text.secondary">Data de Cadastro</Typography>
                        <Typography variant="body1" sx={{ fontWeight: 500 }}>
                          {selectedClientForStatement?.created_at ? new Date(selectedClientForStatement.created_at).toLocaleDateString('pt-BR') : '-'}
                        </Typography>
                      </Box>
                    </Box>
                  </Paper>

                  <Paper variant="outlined" sx={{ p: 3, borderRadius: 3 }}>
                    <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>Endereços Vinculados</Typography>
                    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2.5 }}>
                      {!selectedClientForStatement?.enderecos || selectedClientForStatement.enderecos.length === 0 ? (
                        <Typography variant="body2" color="text.secondary">Nenhum endereço cadastrado para este cliente.</Typography>
                      ) : (
                        selectedClientForStatement.enderecos.map((end: any, idx: number) => (
                          <Card key={end.id || idx} variant="outlined" sx={{ borderRadius: 2.5, borderColor: end.is_principal ? 'primary.200' : 'divider', bgcolor: end.is_principal ? 'primary.50/10' : 'background.paper' }}>
                            <CardContent sx={{ p: 2.5 }}>
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
                                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: end.is_principal ? 'primary.800' : 'text.primary' }}>
                                  Endereço {idx + 1}
                                </Typography>
                                {end.is_principal && (
                                  <Chip label="Principal" color="primary" size="small" sx={{ fontWeight: 'bold', height: 20 }} />
                                )}
                              </Box>
                              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                  {end.endereco}, {end.numero} {end.complemento && `(${end.complemento})`}
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                  {end.bairro} — {end.municipio}/{end.uf}
                                </Typography>
                                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'flex', gap: 2 }}>
                                  <span>CEP: {end.cep}</span>
                                  {end.codigo_ibge && <span>IBGE: {end.codigo_ibge}</span>}
                                </Typography>
                              </Box>
                            </CardContent>
                          </Card>
                        ))
                      )}
                    </Box>
                  </Paper>
                </Box>
              )}

              {/* TAB: CONTRACTS & CONNECTIVITY */}
              {statementTab === 'contracts' && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="h6" sx={{ fontWeight: 'bold' }}>Contratos Registrados</Typography>
                    <Button
                      size="small"
                      variant="contained"
                      startIcon={<PlusIcon className="w-4 h-4" />}
                      onClick={() => {
                        setStatementOpen(false);
                        navigate('/contracts', { 
                          state: { 
                            preselectClientId: selectedClientForStatement.id,
                            preselectClientName: selectedClientForStatement.nome_razao_social,
                            preselectClientCpfCnpj: selectedClientForStatement.cpf_cnpj,
                            preselectClientAddresses: selectedClientForStatement.enderecos || []
                          } 
                        });
                      }}
                      sx={{ textTransform: 'none', fontWeight: 'bold', borderRadius: 2 }}
                    >
                      Novo Contrato
                    </Button>
                  </Box>
                  {clientContracts.length === 0 ? (
                    <Paper variant="outlined" sx={{ p: 5, textAlign: 'center' }}>
                      <Typography variant="h6" color="text.secondary">Nenhum contrato ativo ou inativo</Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        Este cliente não possui serviços contratados cadastrados.
                      </Typography>
                    </Paper>
                  ) : (
                    clientContracts.map(c => (
                      <Paper key={c.id} variant="outlined" sx={{ p: 3, borderRadius: 3, position: 'relative' }}>
                        {/* Title & Status Header */}
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 2, mb: 3 }}>
                          <Box>
                            <Typography variant="h6" sx={{ fontWeight: 'bold', color: 'primary.800' }}>
                              Contrato #{c.id} — {c.servico_descricao || 'Internet'}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              Período: {c.d_contrato_ini ? new Date(c.d_contrato_ini + 'T00:00:00').toLocaleDateString('pt-BR') : 'Sem data inicial'} até {c.d_contrato_fim ? new Date(c.d_contrato_fim + 'T00:00:00').toLocaleDateString('pt-BR') : 'Vigência indeterminada'}
                            </Typography>
                          </Box>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                            <Button
                              size="small"
                              variant="outlined"
                              startIcon={<PencilIcon className="w-4 h-4" />}
                              onClick={() => {
                                setStatementOpen(false);
                                navigate('/contracts', { state: { editContractId: c.id } });
                              }}
                              sx={{ textTransform: 'none', fontWeight: 'bold', borderRadius: 2 }}
                            >
                              Editar Contrato
                            </Button>
                            <Button
                              size="small"
                              variant="outlined"
                              color="warning"
                              startIcon={<ChatBubbleLeftRightIcon className="w-4 h-4" />}
                              onClick={() => {
                                setStatementOpen(false);
                                navigate('/tickets', { 
                                  state: { 
                                    preselectClientId: selectedClientForStatement.id,
                                    preselectClientName: selectedClientForStatement.nome_razao_social,
                                    preselectContractId: c.id,
                                    openCreate: true
                                  } 
                                });
                              }}
                              sx={{ textTransform: 'none', fontWeight: 'bold', borderRadius: 2 }}
                            >
                              Abrir Chamado
                            </Button>
                            <Chip 
                              label={c.status} 
                              color={c.status === 'ATIVO' ? 'success' : c.status === 'SUSPENSO' ? 'warning' : 'error'}
                              sx={{ fontWeight: 'bold' }} 
                            />
                          </Box>
                        </Box>

                        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 4 }}>
                          {/* Left: General/Financial Details */}
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
                            <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: 'grey.700', borderBottom: '1px solid', borderColor: 'divider', pb: 0.5 }}>
                              Faturamento e Cobrança
                            </Typography>
                            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
                              <Box>
                                <Typography variant="caption" color="text.secondary">Mensalidade</Typography>
                                <Typography variant="body1" sx={{ fontWeight: 'bold', color: 'primary.700' }}>{formatCurrency(c.valor_total ?? c.valor_unitario)}</Typography>
                              </Box>
                              <Box>
                                <Typography variant="caption" color="text.secondary">Vencimento</Typography>
                                <Typography variant="body1" sx={{ fontWeight: 500 }}>Todo dia {c.dia_vencimento || c.dia_emissao}</Typography>
                              </Box>
                              <Box>
                                <Typography variant="caption" color="text.secondary">Periodicidade</Typography>
                                <Typography variant="body1" sx={{ fontWeight: 500 }}>{c.periodicidade || 'MENSAL'}</Typography>
                              </Box>
                              <Box>
                                <Typography variant="caption" color="text.secondary">Método Preferido</Typography>
                                <Typography variant="body1" sx={{ fontWeight: 500 }}>{c.payment_method || 'BOLETO'}</Typography>
                              </Box>
                            </Box>
                            {c.assinado_em && (
                              <Box sx={{ mt: 1, p: 1.5, bgcolor: 'success.50/10', borderRadius: 2, border: '1px dashed', borderColor: 'success.200' }}>
                                <Typography variant="caption" color="success.dark" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, fontWeight: 'bold' }}>
                                  <CheckCircleIcon className="w-4 h-4" /> Contrato Assinado Digitalmente
                                </Typography>
                                <Typography variant="caption" color="text.secondary" display="block" sx={{ fontSize: '0.75rem', mt: 0.5 }}>
                                  Assinado em: {new Date(c.assinado_em).toLocaleString('pt-BR')} (IP: {c.assinatura_ip || '-'})
                                </Typography>
                              </Box>
                            )}
                          </Box>

                          {/* Right: Technical Details */}
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
                            <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: 'grey.700', borderBottom: '1px solid', borderColor: 'divider', pb: 0.5 }}>
                              Configurações Técnicas (Provisionamento)
                            </Typography>
                            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
                              <Box>
                                <Typography variant="caption" color="text.secondary">Conexão</Typography>
                                <Typography variant="body1" sx={{ fontWeight: 500 }}>{c.tipo_conexao || 'FIBRA'}</Typography>
                              </Box>
                              <Box>
                                <Typography variant="caption" color="text.secondary">Autenticação</Typography>
                                <Typography variant="body1" sx={{ fontWeight: 500 }}>{c.metodo_autenticacao || 'PPPOE'}</Typography>
                              </Box>
                              <Box>
                                <Typography variant="caption" color="text.secondary">Usuário PPPoE</Typography>
                                <Typography variant="body1" sx={{ fontWeight: 'bold', fontFamily: 'monospace' }}>{c.pppoe_username || '-'}</Typography>
                              </Box>
                              <Box>
                                <Typography variant="caption" color="text.secondary">Senha PPPoE</Typography>
                                <Typography variant="body1" sx={{ fontWeight: 500, fontFamily: 'monospace' }}>{c.pppoe_password || '-'}</Typography>
                              </Box>
                              <Box>
                                <Typography variant="caption" color="text.secondary">IP Designado</Typography>
                                <Typography variant="body1" sx={{ fontWeight: 500, fontFamily: 'monospace' }}>{c.assigned_ip || '-'}</Typography>
                              </Box>
                              <Box>
                                <Typography variant="caption" color="text.secondary">MAC Address</Typography>
                                <Typography variant="body1" sx={{ fontWeight: 500, fontFamily: 'monospace' }}>{c.mac_address || '-'}</Typography>
                              </Box>
                            </Box>
                            
                            {/* ONU / Fiber specifics */}
                            {(c.onu_serial || c.olt_nome || c.cto_nome) && (
                              <Box sx={{ mt: 1.5, p: 2, bgcolor: 'grey.50', borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
                                <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'grey.700', display: 'block', mb: 1 }}>Detalhamento da Fibra (FTTH)</Typography>
                                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5 }}>
                                  <Box>
                                    <Typography variant="caption" color="text.secondary">Equipamento ONU</Typography>
                                    <Typography variant="body2" sx={{ fontSize: '0.85rem' }}>{c.onu_modelo || 'Padrão'} ({c.onu_serial})</Typography>
                                  </Box>
                                  <Box>
                                    <Typography variant="caption" color="text.secondary">Sinal Recebido</Typography>
                                    <Typography variant="body2" sx={{ fontSize: '0.85rem', fontWeight: 'bold', color: c.onu_sinal ? 'success.main' : 'text.secondary' }}>
                                      {c.onu_sinal ? `${c.onu_sinal} dBm` : '-'}
                                    </Typography>
                                  </Box>
                                  <Box>
                                    <Typography variant="caption" color="text.secondary">OLT / PON</Typography>
                                    <Typography variant="body2" sx={{ fontSize: '0.85rem' }}>{c.olt_nome || '-'} {c.olt_pon && `(PON ${c.olt_pon})`}</Typography>
                                  </Box>
                                  <Box>
                                    <Typography variant="caption" color="text.secondary">CTO / Porta</Typography>
                                    <Typography variant="body2" sx={{ fontSize: '0.85rem' }}>{c.cto_nome || '-'} {c.cto_porta && `(Porta ${c.cto_porta})`}</Typography>
                                  </Box>
                                </Box>
                              </Box>
                            )}
                          </Box>
                        </Box>
                      </Paper>
                    ))
                  )}
                </Box>
              )}

              {/* TAB: FINANCIAL STATEMENT */}
              {statementTab === 'financial' && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  <Box sx={{ mb: 1, display: 'flex', gap: 2.5, alignItems: 'center', flexWrap: 'wrap', bgcolor: 'white', p: 2, borderRadius: 3, border: '1px solid', borderColor: 'divider' }}>
                    <FormControl size="small" sx={{ minWidth: 260 }}>
                      <InputLabel>Filtrar por Contrato</InputLabel>
                      <Select
                        value={statementFilterContract}
                        label="Filtrar por Contrato"
                        onChange={(e) => setStatementFilterContract(e.target.value)}
                      >
                        <MenuItem value="all">Todos os Contratos / Lançamentos</MenuItem>
                        {clientContracts.map(c => (
                          <MenuItem key={c.id} value={c.id.toString()}>
                            Contrato #{c.id} - {c.servico_descricao || 'Internet'}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>

                    <FormControl size="small" sx={{ minWidth: 170 }}>
                      <InputLabel>Status</InputLabel>
                      <Select
                        value={statementFilterStatus}
                        label="Status"
                        onChange={(e) => setStatementFilterStatus(e.target.value)}
                      >
                        <MenuItem value="all">Todos os Status</MenuItem>
                        <MenuItem value="PENDING">PENDENTE</MenuItem>
                        <MenuItem value="PAID">PAGO</MenuItem>
                        <MenuItem value="CANCELLED">CANCELADO</MenuItem>
                      </Select>
                    </FormControl>
                    
                    <Box sx={{ ml: 'auto', display: 'flex', gap: 3, p: 1, px: 2, bgcolor: 'grey.50', borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
                      <Box>
                        <Typography variant="caption" color="text.secondary" display="block" sx={{ fontWeight: 500 }}>Total Recebido</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'success.main' }}>{formatCurrency(statementTotals.paid)}</Typography>
                      </Box>
                      <Divider orientation="vertical" flexItem />
                      <Box>
                        <Typography variant="caption" color="text.secondary" display="block" sx={{ fontWeight: 500 }}>Total Pendente</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'warning.main' }}>{formatCurrency(statementTotals.pending)}</Typography>
                      </Box>
                    </Box>
                  </Box>

                  <Paper variant="outlined" sx={{ borderRadius: 3, overflow: 'hidden' }}>
                    <TableContainer>
                      <Table size="medium">
                        <TableHead sx={{ bgcolor: 'grey.50' }}>
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold' }}>Vencimento</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Contrato</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Banco/Método</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>Valor</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>Vlr Pago</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Status</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>Ações</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {filteredReceivables.length === 0 ? (
                            <TableRow><TableCell colSpan={7} align="center" sx={{ py: 6, color: 'text.secondary' }}>Nenhuma cobrança encontrada com os filtros selecionados.</TableCell></TableRow>
                          ) : filteredReceivables.map(r => (
                            <TableRow key={r.id} hover>
                              <TableCell>{new Date(r.due_date).toLocaleDateString('pt-BR')}</TableCell>
                              <TableCell>{r.servico_contratado_id ? `#${r.servico_contratado_id}` : 'Avulso'}</TableCell>
                              <TableCell>{r.tipo === 'MERCADO_PAGO' ? 'Mercado Pago' : r.bank}</TableCell>
                              <TableCell align="right" sx={{ fontWeight: 500 }}>{formatCurrency(r.amount)}</TableCell>
                              <TableCell align="right">
                                {r.paid_amount !== null && r.paid_amount !== undefined ? formatCurrency(r.paid_amount) : '-'}
                              </TableCell>
                              <TableCell>
                                <Chip 
                                  label={r.status === 'PAID' ? 'PAGO' : r.status === 'CANCELLED' ? 'CANCELADO' : 'PENDENTE'} 
                                  size="small" 
                                  color={r.status === 'PAID' ? 'success' : r.status === 'CANCELLED' ? 'default' : 'warning'} 
                                  variant="outlined"
                                  sx={{ fontWeight: 'bold' }}
                                />
                              </TableCell>
                              <TableCell align="right">
                                <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                                  {r.status !== 'PAID' && r.status !== 'CANCELLED' && (
                                    <Button 
                                      size="small" 
                                      variant="text" 
                                      color="success"
                                      startIcon={<CheckCircleIcon className="w-4 h-4" />} 
                                      onClick={() => handleOpenSettleV2(r)}
                                      sx={{ textTransform: 'none', py: 0, fontWeight: 'bold' }}
                                    >
                                      Baixar
                                    </Button>
                                  )}
                                  {r.payment_url && (
                                    <Button 
                                      size="small" 
                                      variant="text" 
                                      startIcon={<ArrowTopRightOnSquareIcon className="w-4 h-4" />} 
                                      onClick={() => window.open(r.payment_url, '_blank')}
                                      sx={{ textTransform: 'none', py: 0 }}
                                    >
                                      Pagar
                                    </Button>
                                  )}
                                  <Button
                                    size="small"
                                    variant="text"
                                    color="secondary"
                                    startIcon={<BanknotesIcon className="w-4 h-4" />}
                                    onClick={() => {
                                      setStatementOpen(false);
                                      navigate('/receivables', { 
                                        state: { 
                                          preselectClientSearch: selectedClientForStatement.nome_razao_social
                                        } 
                                      });
                                    }}
                                    sx={{ textTransform: 'none', py: 0 }}
                                  >
                                    Acessar
                                  </Button>
                                </Box>
                              </TableCell>
                            </TableRow>
                          ))}
                          {filteredReceivables.length > 0 && (
                            <TableRow sx={{ bgcolor: 'grey.50', '& td': { fontWeight: 'bold' } }}>
                              <TableCell colSpan={3} align="right">TOTAIS:</TableCell>
                              <TableCell align="right">
                                {formatCurrency(filteredReceivables.reduce((acc, r) => acc + r.amount, 0))}
                              </TableCell>
                              <TableCell align="right">
                                {formatCurrency(filteredReceivables.reduce((acc, r) => acc + (r.paid_amount || 0), 0))}
                              </TableCell>
                              <TableCell colSpan={2} />
                            </TableRow>
                          )}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </Paper>

                  {filteredReceivables.length > 0 && (
                    <Box sx={{ p: 2.5, bgcolor: 'primary.50/20', borderRadius: 3, border: '1px solid', borderColor: 'primary.100', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box>
                        <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: 'primary.800' }}>
                          Resumo do Filtro
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {filteredReceivables.length} registro(s) encontrado(s)
                        </Typography>
                      </Box>
                      <Box sx={{ textAlign: 'right' }}>
                        <Typography variant="caption" color="text.secondary">Soma dos Lançamentos</Typography>
                        <Typography variant="h5" sx={{ fontWeight: 'bold', color: 'primary.800' }}>
                          {formatCurrency(filteredReceivables.reduce((acc, r) => acc + r.amount, 0))}
                        </Typography>
                      </Box>
                    </Box>
                  )}
                </Box>
              )}

              {/* TAB: TECHNICAL SUPPORT (TICKETS) */}
              {statementTab === 'tickets' && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="h6" sx={{ fontWeight: 'bold' }}>Chamados de Suporte</Typography>
                    <Button
                      size="small"
                      variant="contained"
                      startIcon={<PlusIcon className="w-4 h-4" />}
                      onClick={() => {
                        setStatementOpen(false);
                        navigate('/tickets', { 
                          state: { 
                            preselectClientId: selectedClientForStatement.id,
                            preselectClientName: selectedClientForStatement.nome_razao_social 
                          } 
                        });
                      }}
                      sx={{ textTransform: 'none', fontWeight: 'bold', borderRadius: 2 }}
                    >
                      Abrir Novo Chamado
                    </Button>
                  </Box>
                  {ticketsLoading ? (
                    <Box sx={{ py: 10, display: 'flex', justifyContent: 'center' }}><CircularProgress /></Box>
                  ) : clientTickets.length === 0 ? (
                    <Paper variant="outlined" sx={{ p: 5, textAlign: 'center' }}>
                      <Typography variant="h6" color="text.secondary">Nenhum chamado registrado</Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        Este cliente não possui tickets ou chamados abertos no sistema.
                      </Typography>
                    </Paper>
                  ) : (
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      {clientTickets.map(ticket => (
                        <Paper key={ticket.id} variant="outlined" sx={{ p: 3, borderRadius: 3 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 2, mb: 1.5 }}>
                            <Box>
                              <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                                #{ticket.id} - {ticket.titulo}
                              </Typography>
                              <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', gap: 2, mt: 0.5, flexWrap: 'wrap' }}>
                                <span>Criado em: {new Date(ticket.created_at).toLocaleString('pt-BR')}</span>
                                <span>Categoria: <strong>{ticket.categoria}</strong></span>
                                <span>Responsável: <strong>{ticket.atribuido_para_nome || 'Não atribuído'}</strong></span>
                              </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                              <Button
                                size="small"
                                variant="outlined"
                                startIcon={<ChatBubbleLeftRightIcon className="w-4 h-4" />}
                                onClick={() => {
                                  setStatementOpen(false);
                                  navigate('/tickets', { 
                                    state: { 
                                      preselectClientId: selectedClientForStatement.id,
                                      preselectClientName: selectedClientForStatement.nome_razao_social 
                                    } 
                                  });
                                }}
                                sx={{ textTransform: 'none', fontWeight: 'bold', borderRadius: 2 }}
                              >
                                Ver no Suporte
                              </Button>
                              <Chip 
                                label={ticket.prioridade} 
                                size="small" 
                                color={ticket.prioridade === 'URGENTE' || ticket.prioridade === 'ALTA' ? 'error' : 'default'}
                                variant="filled"
                                sx={{ fontWeight: 'bold' }}
                              />
                              <Chip 
                                label={ticket.status} 
                                size="small" 
                                color={ticket.status === 'ABERTO' ? 'info' : ticket.status === 'EM_ANDAMENTO' ? 'warning' : ticket.status === 'RESOLVIDO' || ticket.status === 'FECHADO' ? 'success' : 'default'}
                                sx={{ fontWeight: 'bold' }}
                              />
                            </Box>
                          </Box>
                          <Divider sx={{ my: 1.5 }} />
                          <Box>
                            <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'grey.700', mb: 0.5 }}>Descrição do Problema:</Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-line' }}>{ticket.descricao}</Typography>
                          </Box>
                          {ticket.resolucao && (
                            <Box sx={{ mt: 2, p: 2, bgcolor: 'success.50/10', borderRadius: 2.5, border: '1px solid', borderColor: 'success.100' }}>
                              <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'success.dark', mb: 0.5 }}>Resolução do Técnico:</Typography>
                              <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-line' }}>{ticket.resolucao}</Typography>
                              {ticket.resolvido_em && (
                                <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1, fontSize: '0.75rem' }}>
                                  Finalizado em: {new Date(ticket.resolvido_em).toLocaleString('pt-BR')}
                                </Typography>
                              )}
                            </Box>
                          )}
                        </Paper>
                      ))}
                    </Box>
                  )}
                </Box>
              )}
            </>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2.5, px: 3, borderTop: '1px solid', borderColor: 'divider', bgcolor: 'white', display: 'flex', justifyContent: 'space-between' }}>
          {statementTab === 'financial' ? (
            <Button
              variant="contained"
              color="primary"
              disabled={printingStatement || statementLoading || filteredReceivables.length === 0}
              onClick={handlePrintStatement}
              startIcon={printingStatement ? <CircularProgress size={20} color="inherit" /> : <DocumentArrowDownIcon className="w-5 h-5" />}
              sx={{ borderRadius: 2.5, px: 3, py: 1, textTransform: 'none', fontWeight: 'bold' }}
            >
              {printingStatement ? 'Gerando...' : 'Gerar PDF do Extrato'}
            </Button>
          ) : (
            <div />
          )}
          <Button 
            onClick={() => setStatementOpen(false)} 
            variant="outlined" 
            color="inherit"
            sx={{ borderRadius: 2.5, px: 3, py: 1, textTransform: 'none', fontWeight: 'bold' }}
          >
            Fechar Painel
          </Button>
        </DialogActions>
      </Dialog>

      {/* Modal Confirmar Recebimento V2 */}
      <Dialog open={openSettle} onClose={() => setOpenSettle(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 'bold' }}>Receber Cobrança #{selectedReceivable?.id}</DialogTitle>
        <DialogContent dividers>
          {!sessao ? (
            <Alert severity="warning">
              Você não possui um caixa aberto. Abra o caixa primeiro na tela "Meu Caixa" para poder receber pagamentos.
            </Alert>
          ) : (
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Typography variant="body2" gutterBottom>
                  Confirme o recebimento para o cliente <strong>{selectedReceivable?.cliente_nome || selectedClientForStatement?.nome_razao_social}</strong>.
                </Typography>
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  label="Valor Original"
                  fullWidth
                  value={selectedReceivable ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(selectedReceivable.amount) : ''}
                  disabled
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel id="forma-pagamento-label">Forma de Pagamento</InputLabel>
                  <Select
                    labelId="forma-pagamento-label"
                    value={formaId}
                    label="Forma de Pagamento"
                    onChange={(e) => setFormaId(e.target.value as number)}
                  >
                    <MenuItem value="">Selecione</MenuItem>
                    {formas.map(f => (
                      <MenuItem key={f.id} value={f.id}>{f.nome}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} sm={4}>
                <TextField
                  label="Multa (R$)"
                  fullWidth
                  value={multaStr}
                  disabled
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Juros (R$)"
                  fullWidth
                  value={jurosStr}
                  disabled
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Desconto (R$)"
                  fullWidth
                  value={descontoStr}
                  onChange={(e) => handleMoneyChange(e.target.value, setDescontoStr)}
                />
              </Grid>

              <Grid item xs={12}>
                <Box sx={{ p: 2, bgcolor: '#f5f5f5', borderRadius: 1, textAlign: 'right' }}>
                  <Typography variant="subtitle1" color="text.secondary">Total a Receber</Typography>
                  <Typography variant="h4" color="success.main" sx={{ fontWeight: 'bold' }}>
                    {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(calculateTotalSettle())}
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenSettle(false)}>Cancelar</Button>
          {sessao && (
            <Button variant="contained" color="success" onClick={handleConfirmSettleV2} disabled={formaId === ''}>
              Confirmar Recebimento
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Modal de Autorização de Desconto */}
      <Dialog open={openAuthSettle} onClose={() => setOpenAuthSettle(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 'bold', color: 'error.main' }}>Autorização Necessária</DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" gutterBottom>
            O desconto de <strong>R$ {descontoStr}</strong> exige aprovação de um supervisor ou administrador.
          </Typography>
          {authSettleError && <Alert severity="error" sx={{ my: 1 }}>{authSettleError}</Alert>}
          <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="E-mail do Supervisor"
              fullWidth
              value={authSettleEmail}
              onChange={(e) => setAuthSettleEmail(e.target.value)}
            />
            <TextField
              label="Senha"
              type="password"
              fullWidth
              value={authSettlePassword}
              onChange={(e) => setAuthSettlePassword(e.target.value)}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenAuthSettle(false)} disabled={authSettleLoading}>Cancelar</Button>
          <Button variant="contained" color="error" onClick={handleAuthSettleSubmit} disabled={authSettleLoading || !authSettleEmail || !authSettlePassword}>
            {authSettleLoading ? 'Autorizando...' : 'Autorizar Desconto'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Modal de Status de Desbloqueio Automático ISP */}
      <Dialog open={unblockResultDialogOpen} onClose={() => setUnblockResultDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 1 }}>
          <InformationCircleIcon className="w-6 h-6 text-blue-500" />
          Resultado do Desbloqueio ISP
        </DialogTitle>
        <DialogContent dividers sx={{ pb: 3 }}>
          <Box sx={{ mb: 2 }}>
            {unblockResult?.success ? (
              <Alert severity="success" sx={{ mb: 2 }}>
                O sinal de internet do cliente foi liberado automaticamente no servidor MikroTik!
              </Alert>
            ) : (
              <Alert severity="warning" sx={{ mb: 2 }}>
                O recebimento foi confirmado, mas não foi possível liberar a internet automaticamente: <br />
                <strong>{unblockResult?.message || 'Sem conexão com o concentrador.'}</strong>
              </Alert>
            )}
            <Typography variant="body2">
              Cliente: <strong>{unblockResult?.cliente_nome}</strong> <br />
              Status do Comando: {unblockResult?.success ? 'Sucesso' : 'Falha / Atenção Manual Necessária'}
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUnblockResultDialogOpen(false)} variant="contained" color="primary">
            Ok, Entendido
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={5000} onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}>
        <Alert severity={snackbar.severity} onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default Clients;