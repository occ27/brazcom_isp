import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Box, Paper, Typography, Button, IconButton, TextField, 
  CircularProgress, Chip, Snackbar, Alert, useMediaQuery, 
  useTheme, Table, TableBody, TableCell, TableContainer, 
  TableHead, TableRow, TablePagination, Card, CardContent, 
  Divider, InputAdornment, MenuItem, Tabs, Tab, Checkbox,
  Tooltip, Menu, Dialog, DialogTitle, DialogContent, DialogActions,
  Autocomplete, Grid, FormControl, InputLabel, Select
} from '@mui/material';
import { 
  PlusIcon, MagnifyingGlassIcon, XMarkIcon, 
  DocumentArrowDownIcon, CheckCircleIcon, 
  EllipsisVerticalIcon, TrashIcon, 
  ArrowPathIcon, CloudIcon, QrCodeIcon,
  ArrowTopRightOnSquareIcon,
  InformationCircleIcon,
  PrinterIcon,
  EyeIcon
} from '@heroicons/react/24/outline';
import { useCompany } from '../contexts/CompanyContext';
import { useAuth } from '../contexts/AuthContext';
import receivableService, { Receivable } from '../services/receivableService';
import { caixaService, CaixaSessao, FormaPagamento } from '../services/caixaService';
import bankAccountService, { BankAccount } from '../services/bankAccountService';
import { stringifyError } from '../utils/error';
import api from '../services/authService';
import { EnvelopeIcon, LinkIcon, ClipboardDocumentIcon } from '@heroicons/react/24/outline';
import { maskCurrency, unmaskCurrency } from '../utils/currencyUtils';

const Receivables: React.FC = () => {
  const navigate = useNavigate();
  const { activeCompany } = useCompany();
  const { user } = useAuth();
  const theme = useTheme();
  
  // State
  const [receivables, setReceivables] = useState<Receivable[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [tabValue, setTabValue] = useState(0); 
  
  // Selection
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  
  // Pagination
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [totalRows, setTotalRows] = useState(0);
  
  // Search & Filter
  const [searchTerm, setSearchTerm] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  
  // UI State
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' | 'warning' });
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedReceivable, setSelectedReceivable] = useState<Receivable | null>(null);
  const [errorDialog, setErrorDialog] = useState<{open: boolean, msg: string}>({ open: false, msg: '' });
  const [dateType, setDateType] = useState('due_date');
  const [unblockResultDialogOpen, setUnblockResultDialogOpen] = useState(false);
  const [unblockResult, setUnblockResult] = useState<{
    attempted: boolean;
    success: boolean;
    message: string;
    cliente_nome: string;
  } | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    title: string;
    message: string;
    onConfirm: () => void | Promise<void>;
    confirmColor?: 'primary' | 'secondary' | 'error' | 'success' | 'warning' | 'info';
  }>({
    open: false,
    title: '',
    message: '',
    onConfirm: () => {},
    confirmColor: 'primary'
  });
  
  // Modals
  const [openCreate, setOpenCreate] = useState(false);
  const [openDetails, setOpenDetails] = useState(false);
  const [openPdfModal, setOpenPdfModal] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [openSettle, setOpenSettle] = useState(false);
  const [settleAmount, setSettleAmount] = useState('');
  // States for Caixa
  const [sessao, setSessao] = useState<CaixaSessao | null>(null);
  const [formas, setFormas] = useState<FormaPagamento[]>([]);
  const [multaStr, setMultaStr] = useState('0,00');
  const [jurosStr, setJurosStr] = useState('0,00');
  const [descontoStr, setDescontoStr] = useState('0,00');
  const [formaId, setFormaId] = useState<number | ''>('');

  const [openAuthSettle, setOpenAuthSettle] = useState(false);
  const [authSettleEmail, setAuthSettleEmail] = useState('');
  const [authSettlePassword, setAuthSettlePassword] = useState('');
  const [authSettleError, setAuthSettleError] = useState('');
  const [authSettleLoading, setAuthSettleLoading] = useState(false);


  
  // Data for Form
  const [clients, setClients] = useState<any[]>([]);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [clientContracts, setClientContracts] = useState<any[]>([]);
  const [formData, setFormData] = useState({
    cliente_id: '',
    servico_contratado_id: '',
    tipo: 'BOLETO',
    amount: 0,
    due_date: new Date().toISOString().split('T')[0],
    bank_account_id: '',
    fine_percent: '2.0',
    interest_percent: '1.0',
  });

  const [searchClients, setSearchClients] = useState<any[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [clientSearchTerm, setClientSearchTerm] = useState('');

  const loadReceivables = useCallback(async () => {
    if (!activeCompany) return;
    setLoading(true);
    try {
      const statusMap: Record<number, string | undefined> = {
        0: undefined,
        1: 'PENDING',
        2: 'REGISTERED',
        3: 'PAID',
        4: 'REGISTRATION_FAILED',
        5: 'CANCELLED'
      };
      
      const res = await receivableService.listReceivables(
        activeCompany.id, 
        page + 1, 
        rowsPerPage, 
        startDate, 
        endDate, 
        dateType,
        statusMap[tabValue],
        searchTerm
      );
      setReceivables(res.data || []);
      setTotalRows(res.total || 0);
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao carregar cobranças', severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [activeCompany, page, rowsPerPage, startDate, endDate, dateType, tabValue, searchTerm]);

  const fetchClients = useCallback(async (search: string) => {
    if (!activeCompany) return;
    setSearchLoading(true);
    try {
      const res = await api.get(`/clientes/autocomplete/${activeCompany.id}?q=${search}&limit=20`);
      setSearchClients(res.data || []);
    } catch (e) {
      console.error('Erro ao buscar clientes', e);
    } finally {
      setSearchLoading(false);
    }
  }, [activeCompany]);

  useEffect(() => {
    if (clientSearchTerm.length >= 3) {
      const timer = setTimeout(() => {
        fetchClients(clientSearchTerm);
      }, 500);
      return () => clearTimeout(timer);
    } else if (clientSearchTerm.length === 0) {
      setSearchClients([]);
    }
  }, [clientSearchTerm, fetchClients]);
  
  // Fetch contracts when client changes
  useEffect(() => {
    const fetchContracts = async () => {
      if (!formData.cliente_id || !activeCompany) {
        setClientContracts([]);
        return;
      }
      try {
        const res = await api.get(`/servicos-contratados/cliente/${formData.cliente_id}?empresa_id=${activeCompany.id}`);
        // This endpoint returns a direct array
        const data = Array.isArray(res.data) ? res.data : (res.data.contratos || []);
        setClientContracts(data);
        
        // Auto-select first contract if only one exists
        if (data.length === 1) {
          setFormData(prev => ({ 
            ...prev, 
            servico_contratado_id: data[0].id.toString(),
            amount: data[0].valor_unitario || prev.amount
          }));
        }
      } catch (e) {
        console.error('Erro ao buscar contratos do cliente', e);
        setClientContracts([]);
      }
    };
    fetchContracts();
  }, [formData.cliente_id, activeCompany]);

  const loadFormData = useCallback(async () => {
    if (!activeCompany) return;
    try {
      const accountsRes = await bankAccountService.listBankAccounts(activeCompany.id);
      setBankAccounts(accountsRes || []);
      if (accountsRes.length > 0) {
        const first = accountsRes[0];
        setFormData(prev => ({ 
          ...prev, 
          bank_account_id: first.id.toString(),
          fine_percent: (first.multa_atraso_percentual || 2.0).toString(),
          interest_percent: (first.juros_atraso_percentual || 1.0).toString()
        }));
      }
    } catch (e) {
      console.error('Erro ao carregar dados do formulário', e);
    }
  }, [activeCompany]);

  useEffect(() => {
    if (activeCompany) {
      loadReceivables();
      loadFormData();
    }
  }, [activeCompany, loadReceivables, loadFormData]);

  // Debounce search
  useEffect(() => {
    if (activeCompany) {
      const timeoutId = setTimeout(() => {
        setPage(0);
        // loadReceivables will be triggered by dependency array
      }, 500);
      return () => clearTimeout(timeoutId);
    }
  }, [searchTerm, activeCompany]);

  // Reset page on tab change
  useEffect(() => {
    setPage(0);
  }, [tabValue]);

  const paginatedReceivables = receivables;

  const handleGenerate = async () => {
    if (!activeCompany) return;
    setGenerating(true);
    try {
      await receivableService.generateForCompany(activeCompany.id);
      setSnackbar({ open: true, message: 'Processamento de geração concluído', severity: 'success' });
      loadReceivables();
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e), severity: 'error' });
    } finally {
      setGenerating(false);
    }
  };

  const handleCreateManual = async () => {
    if (!activeCompany) return;
    try {
      await receivableService.createReceivable({
        ...formData,
        empresa_id: activeCompany.id,
        amount: formData.amount,
        cliente_id: parseInt(formData.cliente_id),
        servico_contratado_id: formData.servico_contratado_id ? parseInt(formData.servico_contratado_id) : undefined,
        bank_account_id: formData.tipo === 'BOLETO' ? parseInt(formData.bank_account_id) : undefined,
        fine_percent: parseFloat(formData.fine_percent),
        interest_percent: parseFloat(formData.interest_percent)
      });
      setSnackbar({ open: true, message: 'Cobrança criada com sucesso', severity: 'success' });
      setOpenCreate(false);
      loadReceivables();
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e), severity: 'error' });
    }
  };

  const handleOpenSettle = (r: Receivable) => {
    setSelectedReceivable(r);
    setSettleAmount(maskCurrency(r.amount.toFixed(2)));
    setOpenSettle(true);
    setAnchorEl(null);
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
      // Handle both ISO dates (T) and SQL dates (space)
      const dueDateStr = r.due_date.includes(' ') ? r.due_date.replace(' ', 'T') : (r.due_date.includes('T') ? r.due_date : r.due_date + 'T00:00:00');
      const dueDate = new Date(dueDateStr);
      const today = new Date();
      dueDate.setHours(0,0,0,0);
      today.setHours(0,0,0,0);

      if (today > dueDate) {
        const diffTime = Math.abs(today.getTime() - dueDate.getTime());
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        // Use receivable values or defaults (2% multa, 1% juros a.m.)
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
    
    // load caixa data
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
    if (!selectedReceivable || !sessao) return;
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
      loadReceivables();

      if (response.unblock_attempted) {
        setUnblockResult({
          attempted: true,
          success: response.unblock_success || false,
          message: response.unblock_message || '',
          cliente_nome: selectedReceivable.cliente_nome || 'Cliente'
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
        // requires supervisor
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
      // Import authService dynamically or if it's already there? We'll use axios directly
      // Wait, api is not imported, let me just use the global api
      // since receivableService uses api, I can just do a fetch or import api
      // I'll add an auth function inline
      const formData = new URLSearchParams();
      formData.append('username', authSettleEmail);
      formData.append('password', authSettlePassword);
      
      const res = await fetch('http://localhost:8000/auth/login', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error('Credenciais inválidas');
      const data = await res.json();
      
      const userRes = await fetch('http://localhost:8000/users/me', {
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

  const handleSettle = (id: number) => { const r = receivables.find(x => x.id === id); if (r) handleOpenSettleV2(r); };

  const handleDelete = (id: number) => {
    setConfirmDialog({
      open: true,
      title: 'Excluir Cobrança',
      message: 'Deseja excluir permanentemente esta cobrança? Esta ação removerá o registro do banco de dados e não pode ser desfeita. (Será solicitada baixa no banco se estiver registrada)',
      confirmColor: 'error',
      onConfirm: async () => {
        try {
          await receivableService.cancelReceivable(id);
          setSnackbar({ open: true, message: 'Cobrança excluída com sucesso', severity: 'success' });
          loadReceivables();
        } catch (e) {
          setSnackbar({ open: true, message: stringifyError(e), severity: 'error' });
        }
      }
    });
    setAnchorEl(null);
  };

  const handleRefund = (id: number) => {
    setConfirmDialog({
      open: true,
      title: 'Estornar Pagamento',
      message: 'Confirma o estorno do pagamento desta cobrança? O status voltará a ser PENDENTE.',
      confirmColor: 'warning',
      onConfirm: async () => {
        try {
          await receivableService.refundReceivable(id);
          setSnackbar({ open: true, message: 'Pagamento estornado com sucesso!', severity: 'success' });
          loadReceivables();
        } catch (e) {
          setSnackbar({ open: true, message: stringifyError(e), severity: 'error' });
        }
      }
    });
    setAnchorEl(null);
  };

  const handlePrint = async (id: number) => {
    setLoading(true);
    try {
      const url = await receivableService.printReceivable(id);
      setPdfUrl(url);
      setOpenPdfModal(true);
    } catch (e) {
      setSnackbar({ open: true, message: 'Erro ao gerar PDF', severity: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleSendEmail = async (id: number) => {
    setLoading(true);
    try {
      await receivableService.sendEmail(id);
      setSnackbar({ open: true, message: 'Notificação enviada com sucesso!', severity: 'success' });
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao enviar notificação', severity: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleBatchRegisterBB = async () => {
    if (!activeCompany || selectedIds.length === 0) return;
    setLoading(true);
    try {
      const bbAccount = bankAccounts.find(a => a.bank.includes('BRASIL'));
      if (!bbAccount) {
        setSnackbar({ open: true, message: 'Nenhuma conta do Banco do Brasil encontrada', severity: 'error' });
        return;
      }
      await bankAccountService.registerBoletosApi(activeCompany.id, bbAccount.id, selectedIds);
      setSnackbar({ open: true, message: 'Processamento em lote finalizado', severity: 'success' });
      setSelectedIds([]);
      loadReceivables();
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e), severity: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const getStatusChip = (status: string) => {
    const s = status?.toUpperCase();
    if (s === 'PAID') return <Chip label="Pago" size="small" color="success" />;
    if (s === 'REGISTERED') return <Chip label="Registrado" size="small" color="primary" />;
    if (s === 'PENDING') return <Chip label="Pendente" size="small" color="warning" />;
    if (s === 'CANCELLED') return <Chip label="Cancelado" size="small" color="default" />;
    return <Chip label={status} size="small" />;
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', p: 2 }}>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h5" sx={{ fontWeight: 700, color: 'primary.main' }}>
          Financeiro / Recebíveis
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {selectedIds.length > 0 && (
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button variant="contained" color="secondary" startIcon={<CloudIcon className="w-5 h-5" />} onClick={handleBatchRegisterBB}>
                Registrar ({selectedIds.length})
              </Button>
              <Button variant="contained" color="success" startIcon={<QrCodeIcon className="w-5 h-5" />} onClick={() => navigate('/checkout', { state: { receivableIds: selectedIds } })}>
                Pagar ({selectedIds.length})
              </Button>
            </Box>
          )}
          <Button variant="outlined" startIcon={<PlusIcon className="w-5 h-5" />} onClick={() => setOpenCreate(true)}>
            Nova Cobrança
          </Button>
          <Button variant="contained" startIcon={generating ? <CircularProgress size={20} color="inherit" /> : <PlusIcon className="w-5 h-5" />} onClick={handleGenerate} disabled={generating}>
            Gerar Automático
          </Button>
        </Box>
      </Box>

      <Paper sx={{ borderRadius: 3, overflow: 'hidden', flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
        <Tabs value={tabValue} onChange={(_, v) => { setTabValue(v); setPage(0); }} sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}>
          <Tab label="Todos" />
          <Tab label="Pendentes" />
          <Tab label="Registrados" />
          <Tab label="Pagos" />
          <Tab label="Falhas" />
          <Tab label="Cancelados" />
        </Tabs>

        <Box sx={{ p: 2, display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <TextField
            sx={{ flexGrow: 1, minWidth: 200 }}
            size="small"
            placeholder="Buscar por cliente ou número..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{ startAdornment: <InputAdornment position="start"><MagnifyingGlassIcon className="w-5 h-5 text-gray-400" /></InputAdornment> }}
          />
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Filtrar por</InputLabel>
            <Select
              value={dateType}
              label="Filtrar por"
              onChange={(e) => setDateType(e.target.value)}
            >
              <MenuItem value="due_date">Vencimento</MenuItem>
              <MenuItem value="issue_date">Emissão</MenuItem>
            </Select>
          </FormControl>
          <TextField type="date" label="Início" size="small" value={startDate} onChange={(e) => setStartDate(e.target.value)} InputLabelProps={{ shrink: true }} />
          <TextField type="date" label="Fim" size="small" value={endDate} onChange={(e) => setEndDate(e.target.value)} InputLabelProps={{ shrink: true }} />
          <IconButton onClick={loadReceivables} disabled={loading}><ArrowPathIcon className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} /></IconButton>
        </Box>

        <TableContainer sx={{ flexGrow: 1 }}>
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox"><Checkbox onChange={(e) => setSelectedIds(e.target.checked ? paginatedReceivables.map(r => r.id) : [])} /></TableCell>
                <TableCell>ID</TableCell>
                <TableCell>Cliente</TableCell>
                <TableCell>Emissão</TableCell>
                <TableCell>Vencimento</TableCell>
                <TableCell align="right">Valor</TableCell>
                <TableCell align="right">Vlr Pago</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Gateway / Local</TableCell>
                <TableCell align="right">Ações</TableCell>
              </TableRow>
            </TableHead>
            <TableBody sx={{ whiteSpace: 'nowrap' }}>
              {loading && receivables.length === 0 ? (
                <TableRow><TableCell colSpan={9} align="center" sx={{ py: 5 }}><CircularProgress /></TableCell></TableRow>
              ) : paginatedReceivables.map(r => (
                <TableRow key={r.id} hover>
                  <TableCell padding="checkbox">
                    <Checkbox checked={selectedIds.includes(r.id)} onChange={() => setSelectedIds(prev => prev.includes(r.id) ? prev.filter(id => id !== r.id) : [...prev, r.id])} />
                  </TableCell>
                  <TableCell>{r.id}</TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>{r.cliente_nome}</Typography>
                    <Typography variant="caption" color="text.secondary">{r.cliente_cpf_cnpj}</Typography>
                  </TableCell>
                  <TableCell>{new Date(r.issue_date).toLocaleDateString('pt-BR')}</TableCell>
                  <TableCell>{new Date(r.due_date).toLocaleDateString('pt-BR')}</TableCell>
                  <TableCell align="right">{(r.amount).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</TableCell>
                  <TableCell align="right">
                    {r.paid_amount !== null && r.paid_amount !== undefined 
                      ? (r.paid_amount).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) 
                      : '-'}
                  </TableCell>
                  <TableCell>
                    {r.status === 'REGISTRATION_FAILED' ? (
                      <Chip label="Falha" size="small" color="error" variant="outlined" onClick={() => setErrorDialog({ open: true, msg: r.registro_result || '' })} sx={{ cursor: 'pointer' }} />
                    ) : getStatusChip(r.status)}
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      <Typography variant="caption" sx={{ fontWeight: 600 }}>
                        {r.tipo === 'MERCADO_PAGO' ? 'MERCADO PAGO' : r.bank}
                        {r.local_pagamento_nome && ` - ${r.local_pagamento_nome}`}
                      </Typography>
                      {r.mp_payment_id && (
                        <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
                          MP: {r.mp_payment_id}
                        </Typography>
                      )}
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        {r.payment_url && (
                          <Tooltip title="Copiar Link de Pagamento">
                            <IconButton 
                              size="small" 
                              color="primary"
                              onClick={() => {
                                navigator.clipboard.writeText(r.payment_url!);
                                setSnackbar({ open: true, message: 'Link copiado para a área de transferência', severity: 'success' });
                              }}
                            >
                              <ClipboardDocumentIcon className="w-4 h-4" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {r.payment_url && (
                          <Tooltip title="Abrir Checkout">
                            <IconButton 
                              size="small" 
                              onClick={() => window.open(r.payment_url!, '_blank')}
                            >
                              <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                            </IconButton>
                          </Tooltip>
                        )}
                      </Box>
                    </Box>
                  </TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                      {r.bb_pix_qrcode && <IconButton size="small" color="success" onClick={() => { navigator.clipboard.writeText(r.bb_pix_qrcode!); setSnackbar({ open: true, message: 'PIX Copiado', severity: 'success' }); }} title="PIX"><QrCodeIcon className="w-4 h-4" /></IconButton>}
                      <IconButton size="small" onClick={(e) => { setAnchorEl(e.currentTarget); setSelectedReceivable(r); }}><EllipsisVerticalIcon className="w-5 h-5" /></IconButton>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination 
          component="div" 
          count={totalRows} 
          rowsPerPage={rowsPerPage} 
          page={page} 
          onPageChange={(_, p) => setPage(p)} 
          onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }} 
          labelRowsPerPage="Itens por página:"
          labelDisplayedRows={({ from, to, count }) => `${from}-${to} de ${count !== -1 ? count : `mais de ${to}`}`}
          sx={{ 
            '.MuiTablePagination-toolbar': { justifyContent: 'flex-start' },
            '.MuiTablePagination-spacer': { display: 'none' }
          }}
        />
      </Paper>

      <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}>
        <MenuItem onClick={() => { setOpenDetails(true); setAnchorEl(null); }}><EyeIcon className="w-4 h-4 mr-2" /> Detalhes</MenuItem>
        
        <MenuItem onClick={() => { selectedReceivable && handleSendEmail(selectedReceivable.id); setAnchorEl(null); }}>
          <EnvelopeIcon className="w-4 h-4 mr-2 text-blue-500" /> Enviar Notificação
        </MenuItem>

        {(selectedReceivable?.status === 'REGISTERED' || selectedReceivable?.status === 'PAID') && (
          <MenuItem onClick={() => { selectedReceivable && handlePrint(selectedReceivable.id); setAnchorEl(null); }}>
            <PrinterIcon className="w-4 h-4 mr-2 text-gray-600" /> Imprimir Boleto
          </MenuItem>
        )}
        
        {selectedReceivable?.status !== 'PAID' && selectedReceivable?.status !== 'CANCELLED' && (
          <MenuItem onClick={() => { navigate('/checkout', { state: { receivableIds: [selectedReceivable!.id] } }); setAnchorEl(null); }}>
            <QrCodeIcon className="w-4 h-4 mr-2 text-blue-500" /> Pagar (Mercado Pago)
          </MenuItem>
        )}
        
        {selectedReceivable?.status !== 'PAID' && selectedReceivable?.status !== 'CANCELLED' && (
          <MenuItem onClick={() => { handleOpenSettleV2(selectedReceivable!); setAnchorEl(null); }}>
            <CheckCircleIcon className="w-4 h-4 mr-2 text-green-500" /> Baixar
          </MenuItem>
        )}
        
        {selectedReceivable?.status === 'PAID' && (user?.is_superuser || user?.is_company_admin) && (
          <MenuItem onClick={() => { handleRefund(selectedReceivable.id); setAnchorEl(null); }}>
            <ArrowPathIcon className="w-4 h-4 mr-2 text-orange-500" /> Estornar Pagamento
          </MenuItem>
        )}
        
        {selectedReceivable?.status !== 'PAID' && (
          <MenuItem onClick={() => { handleDelete(selectedReceivable!.id); setAnchorEl(null); }}>
            <TrashIcon className="w-4 h-4 mr-2 text-red-500" /> Excluir Permanentemente
          </MenuItem>
        )}
      </Menu>

      {/* Modal PDF */}
      <Dialog open={openPdfModal} onClose={() => { setOpenPdfModal(false); setPdfUrl(null); }} maxWidth="md" fullWidth>
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          Visualização do Boleto
          <IconButton onClick={() => { setOpenPdfModal(false); setPdfUrl(null); }}><XMarkIcon className="w-6 h-6" /></IconButton>
        </DialogTitle>
        <DialogContent sx={{ p: 0, height: '80vh' }}>
          {pdfUrl ? (
            <iframe src={pdfUrl} width="100%" height="100%" style={{ border: 'none' }} title="Boleto PDF" />
          ) : (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}><CircularProgress /></Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setOpenPdfModal(false); setPdfUrl(null); }}>Fechar</Button>
          <Button variant="contained" onClick={() => window.open(pdfUrl!, '_blank')}>Abrir em Nova Aba</Button>
        </DialogActions>
      </Dialog>

      {/* Modal Nova Cobrança */}
      <Dialog open={openCreate} onClose={() => setOpenCreate(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Lançar Cobrança Manual</DialogTitle>
        <DialogContent dividers>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <Autocomplete
                options={searchClients}
                loading={searchLoading}
                getOptionLabel={(o) => o.nome_razao_social}
                onInputChange={(_, value) => setClientSearchTerm(value)}
                filterOptions={(x) => x} 
                onChange={(_, v) => setFormData({ ...formData, cliente_id: v?.id?.toString() || '' })}
                renderOption={(props, option) => (
                  <li {...props}>
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>{option.nome_razao_social}</Typography>
                      <Typography variant="caption" color="text.secondary">{option.cpf_cnpj}</Typography>
                    </Box>
                  </li>
                )}
                renderInput={(p) => (
                  <TextField 
                    {...p} 
                    label="Localizar Cliente" 
                    fullWidth 
                    size="small" 
                    variant="outlined"
                    placeholder="Digite nome ou documento..."
                    InputProps={{
                      ...p.InputProps,
                      endAdornment: (
                        <>
                          {searchLoading ? <CircularProgress color="inherit" size={20} /> : null}
                          {p.InputProps.endAdornment}
                        </>
                      ),
                    }}
                  />
                )}
              />
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth size="small">
                <InputLabel>Contrato Relacionado</InputLabel>
                <Select
                  value={formData.servico_contratado_id}
                  label="Contrato Relacionado"
                  onChange={(e) => {
                    const contractId = e.target.value;
                    const contract = clientContracts.find(c => c.id.toString() === contractId);
                    setFormData({ 
                      ...formData, 
                      servico_contratado_id: contractId,
                      amount: contract ? contract.valor_unitario : formData.amount
                    });
                  }}
                  disabled={clientContracts.length === 0}
                >
                  <MenuItem value=""><em>Nenhum (Lançamento Avulso)</em></MenuItem>
                  {clientContracts.map(c => (
                    <MenuItem key={c.id} value={c.id.toString()}>
                      Contrato #{c.id} - {c.servico_descricao || 'Internet'} ({c.valor_unitario?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth size="small">
                <InputLabel>Tipo de Cobrança</InputLabel>
                <Select
                  value={formData.tipo}
                  label="Tipo de Cobrança"
                  onChange={(e) => setFormData({ ...formData, tipo: e.target.value })}
                >
                  <MenuItem value="BOLETO">BOLETO BANCÁRIO</MenuItem>
                  <MenuItem value="MERCADO_PAGO">MERCADO PAGO (CARTÃO/PIX)</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            {formData.tipo === 'BOLETO' && (
              <Grid item xs={12}>
                <TextField 
                  select 
                  label="Conta Bancária / Banco" 
                  fullWidth 
                  size="small" 
                  value={formData.bank_account_id} 
                  onChange={(e) => {
                    const accId = e.target.value;
                    const acc = bankAccounts.find(a => a.id.toString() === accId);
                    setFormData({ 
                      ...formData, 
                      bank_account_id: accId,
                      fine_percent: (acc?.multa_atraso_percentual || 2.0).toString(),
                      interest_percent: (acc?.juros_atraso_percentual || 1.0).toString()
                    });
                  }}
                >
                  {bankAccounts.map(a => (
                    <MenuItem key={a.id} value={a.id.toString()}>
                      <Box>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>{a.bank}</Typography>
                        <Typography variant="caption" color="text.secondary">{a.titular} - {a.agencia}/{a.conta}</Typography>
                      </Box>
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
            )}
            <Grid item xs={6}>
              <TextField 
                label="Valor (R$)" 
                fullWidth 
                size="small" 
                value={maskCurrency((formData.amount || 0).toFixed(2))} 
                onChange={(e) => setFormData({ ...formData, amount: unmaskCurrency(e.target.value) })} 
              />
            </Grid>
            <Grid item xs={6}>
              <TextField type="date" label="Vencimento" fullWidth size="small" value={formData.due_date} onChange={(e) => setFormData({ ...formData, due_date: e.target.value })} InputLabelProps={{ shrink: true }} />
            </Grid>
            <Grid item xs={6}>
              <TextField 
                label="Multa (%)" 
                fullWidth 
                size="small" 
                type="number"
                value={formData.fine_percent} 
                onChange={(e) => setFormData({ ...formData, fine_percent: e.target.value })} 
              />
            </Grid>
            <Grid item xs={6}>
              <TextField 
                label="Juros Mensal (%)" 
                fullWidth 
                size="small" 
                type="number"
                value={formData.interest_percent} 
                onChange={(e) => setFormData({ ...formData, interest_percent: e.target.value })} 
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setOpenCreate(false)}>Cancelar</Button>
          <Button variant="contained" onClick={handleCreateManual} sx={{ borderRadius: 2 }}>Criar Cobrança</Button>
        </DialogActions>
      </Dialog>

      {/* Modal Detalhes */}
      <Dialog open={openDetails} onClose={() => setOpenDetails(false)} maxWidth="md" fullWidth>
        <DialogTitle>Detalhes da Cobrança #{selectedReceivable?.id}</DialogTitle>
        <DialogContent dividers>
          {selectedReceivable && (
            <Grid container spacing={2}>
              <Grid item xs={12}><Typography variant="subtitle1" sx={{ fontWeight: 600 }}>Cliente: {selectedReceivable.cliente_nome}</Typography></Grid>
              <Grid item xs={6}><Typography variant="body2">Nosso Número: {selectedReceivable.nosso_numero || '-'}</Typography></Grid>
              <Grid item xs={6}><Typography variant="body2">Status: {selectedReceivable.status}</Typography></Grid>
              <Grid item xs={12}><Divider sx={{ my: 1 }} /></Grid>
              <Grid item xs={12}>
                <Typography variant="caption" color="text.secondary">Linha Digitável:</Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>{selectedReceivable.linha_digitavel || 'Não gerada'}</Typography>
              </Grid>
              {selectedReceivable.registro_result && (
                <Grid item xs={12}>
                  <Typography variant="caption" color="text.secondary">Resultado do Banco:</Typography>
                  <pre style={{ fontSize: '11px', background: '#f5f5f5', padding: '8px' }}>{selectedReceivable.registro_result}</pre>
                </Grid>
              )}
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDetails(false)}>Fechar</Button>
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
                  Confirme o recebimento para o cliente <strong>{selectedReceivable?.cliente_nome}</strong>.
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

      {/* Modal de Status de Desbloqueio Automático ISP */}
      <Dialog open={unblockResultDialogOpen} onClose={() => setUnblockResultDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 1 }}>
          <InformationCircleIcon className="w-6 h-6 text-blue-500" />
          Resultado do Desbloqueio ISP
        </DialogTitle>
        <DialogContent dividers sx={{ pb: 3 }}>
          <Box sx={{ mb: 2 }}>
            <Typography variant="body1">
              A cobrança do cliente <strong>{unblockResult?.cliente_nome}</strong> foi baixada com sucesso no sistema.
            </Typography>
          </Box>
          {unblockResult?.success ? (
            <Alert severity="success" sx={{ borderLeft: '6px solid #2e7d32', borderRadius: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                🟢 Desbloqueio Concluído!
              </Typography>
              <Typography variant="body2" sx={{ mt: 0.5 }}>
                {unblockResult?.message}
              </Typography>
            </Alert>
          ) : (
            <Alert severity="warning" sx={{ borderLeft: '6px solid #ed6c02', borderRadius: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                ⚠️ Atenção: Falha no Desbloqueio Automático
              </Typography>
              <Typography variant="body2" sx={{ mt: 0.5 }}>
                O contrato do cliente não pôde ser ativado no MikroTik/RADIUS de forma automática.
              </Typography>
              <Typography variant="body2" sx={{ mt: 1, fontWeight: 'bold', fontFamily: 'monospace', bgcolor: 'rgba(0,0,0,0.05)', p: 1, borderRadius: 1 }}>
                Motivo: {unblockResult?.message}
              </Typography>
              <Typography variant="caption" sx={{ display: 'block', mt: 1, color: 'text.secondary' }}>
                Você precisará acessar a página de Contratos ou Roteadores para realizar o desbloqueio manual ou verificar a conectividade do Roteador.
              </Typography>
            </Alert>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button variant="contained" color={unblockResult?.success ? "success" : "warning"} onClick={() => setUnblockResultDialogOpen(false)} sx={{ borderRadius: 2, px: 3 }}>
            Entendido
          </Button>
        </DialogActions>
      </Dialog>


      {/* Modal de Confirmação Genérico */}
      <Dialog open={confirmDialog.open} onClose={() => setConfirmDialog(prev => ({ ...prev, open: false }))} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 'bold' }}>{confirmDialog.title}</DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2">{confirmDialog.message}</Typography>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setConfirmDialog(prev => ({ ...prev, open: false }))}>Cancelar</Button>
          <Button 
            variant="contained" 
            color={confirmDialog.confirmColor || 'primary'} 
            onClick={() => {
              confirmDialog.onConfirm();
              setConfirmDialog(prev => ({ ...prev, open: false }));
            }}
          >
            Confirmar
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={6000} onClose={() => setSnackbar({ ...snackbar, open: false })}>
        <Alert severity={snackbar.severity}>{snackbar.message}</Alert>
      </Snackbar>
    
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

    </Box>
  );
};

export default Receivables;
