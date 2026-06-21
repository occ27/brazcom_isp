import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { stringifyError } from '../utils/error';
import {
  Box, Paper, Typography, Button, IconButton, TextField, CircularProgress, Snackbar, Alert,
  Dialog, DialogTitle, DialogContent, DialogActions, Autocomplete, FormControl, InputLabel, Select, MenuItem, Menu,
  Card, CardContent, Divider, Chip, Tooltip, SelectChangeEvent, useMediaQuery, useTheme,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TablePagination, Pagination,
  Checkbox, Tabs, Tab, FormHelperText, InputAdornment
} from '@mui/material';
import L from 'leaflet';
import { MapContainer, TileLayer, Marker, Popup, Tooltip as LeafletTooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import {
  PlusIcon, ArrowPathIcon, CloudIcon, QrCodeIcon,
  ArrowTopRightOnSquareIcon,
  InformationCircleIcon,
  PrinterIcon,
  EyeIcon,
  PlayIcon,
  PencilIcon,
  CloudArrowUpIcon,
  PauseIcon,
  TrashIcon as TrashIconMUI,
  DocumentTextIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
  EnvelopeIcon,
  CheckCircleIcon,
  EllipsisVerticalIcon
} from '@heroicons/react/24/outline';
import { useCompany } from '../contexts/CompanyContext';
import { useAuth } from '../contexts/AuthContext';
import contratoService, { Contrato, ContratoListResponse, AtivoContrato } from '../services/contratoService';
import clientService from '../services/clientService';
import servicoService, { Servico } from '../services/servicoService';
import bankAccountService, { BankAccount } from '../services/bankAccountService';
import { routerService } from '../services/routerService';
import { networkService } from '../services/networkService';
import { Cliente, Router, RouterInterface, IPClass } from '../types';
import { generateAvailableIPs } from '../utils/networkUtils';
import api from '../services/api';
import { maskCurrency, unmaskCurrency } from '../utils/currencyUtils';

const Contracts: React.FC = () => {
  const { activeCompany } = useCompany();
  const { hasPermission } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  // Normalize date-like values to YYYY-MM-DD suitable for <input type="date">.
  // Preserve the date component without applying local timezone shifts.
  const toLocalDateInputString = (val: any): string => {
    if (!val) return '';
    // If already in YYYY-MM-DD form, return as-is
    if (typeof val === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(val)) return val;

    // If string contains a date at start (ISO timestamp), take the date portion
    if (typeof val === 'string') {
      const m = val.match(/^(\d{4}-\d{2}-\d{2})/);
      if (m) return m[1];
    }

    try {
      const d = typeof val === 'number' ? new Date(val) : (val instanceof Date ? val : new Date(String(val)));
      if (isNaN(d.getTime())) return '';
      // Use UTC getters to avoid TZ offset changing the calendar date
      const yyyy = d.getUTCFullYear();
      const mm = String(d.getUTCMonth() + 1).padStart(2, '0');
      const dd = String(d.getUTCDate()).padStart(2, '0');
      return `${yyyy}-${mm}-${dd}`;
    } catch (e) {
      return '';
    }
  };
  const formatDate = (d: any) => {
    if (!d) return '-';
    try {
      // If it's a YYYY-MM-DD string, format directly to avoid timezone issues
      if (typeof d === 'string') {
        const m = d.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (m) return `${m[3]}/${m[2]}/${m[1]}`;
      }
      const dt = new Date(d);
      if (isNaN(dt.getTime())) return '-';
      // Use UTC components to avoid local timezone shifting the date
      const dd = String(dt.getUTCDate()).padStart(2, '0');
      const mm = String(dt.getUTCMonth() + 1).padStart(2, '0');
      const yyyy = dt.getUTCFullYear();
      return `${dd}/${mm}/${yyyy}`;
    } catch (e) {
      return '-';
    }
  };
  // use shared stringifyError from utils
  const [contratos, setContratos] = useState<Contrato[]>([]);
  const [viewMode, setViewMode] = useState<'table' | 'map'>('table');
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [loading, setLoading] = useState<boolean>(true);
  const [openPdfModal, setOpenPdfModal] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [openContractModal, setOpenContractModal] = useState(false);
  const [contractHtmlUrl, setContractHtmlUrl] = useState<string | null>(null);
  const [openForm, setOpenForm] = useState(false);
  const [editing, setEditing] = useState<Contrato | null>(null);
  const [viewOnly, setViewOnly] = useState(false);
  const [viewingContractId, setViewingContractId] = useState<number | null>(null);
  const [form, setForm] = useState<Partial<Contrato>>({
    quantidade: 1,
    periodicidade: 'MENSAL',
    valor_unitario: undefined, // Campo obrigatório, deve ser preenchido pelo usuário
    dia_emissao: 1, // Valor padrão para dia de emissão
    auto_emit: true,
    auto_emit_nfcom: true,
    is_active: true,
    status: 'AGUARDANDO_ASSINATURA',
    periodo_carencia: 0,
    multa_atraso_percentual: 0.0,
    taxa_instalacao: 0.0,
    taxa_instalacao_paga: false,
    tipo_conexao: 'FIBRA', // Valor padrão: Fibra Óptica
    // Campos de data opcionais
    d_contrato_ini: undefined,
    d_contrato_fim: undefined,
    data_inicio_cobranca: undefined,
    data_instalacao: undefined,
    // Novos campos de rede
    router_id: undefined,
    interface_id: undefined,
    ip_class_id: undefined,
    mac_address: '',
    assigned_ip: '',
    metodo_autenticacao: undefined,
    // Campos PPPoE
    pppoe_username: '',
    pppoe_password: '',
    payment_method: 'BOLETO',
    // Campos Fibra (FTTH)
    onu_serial: '',
    onu_modelo: '',
    onu_sinal: '',
    olt_nome: '',
    olt_pon: '',
    cto_nome: '',
    cto_porta: '',
    metragem_drop: undefined,
    vlan_id: undefined,
    olt_id: undefined,
    cto_id: undefined,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' | 'warning' });
  const [clientAddresses, setClientAddresses] = useState<any[]>([]);

  // Tab state for form organization
  const [tabValue, setTabValue] = useState(0);
  const [showPppoePassword, setShowPppoePassword] = useState(false);

  // Pagination state
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [previousRowsPerPage, setPreviousRowsPerPage] = useState(10);
  const [totalRows, setTotalRows] = useState(0);

  // Search state
  const [searchTerm, setSearchTerm] = useState('');

  // Status filter state
  const [filterStatus, setFilterStatus] = useState<string>('');

  // Due date filter state
  const [diaVencimentoMin, setDiaVencimentoMin] = useState<number | ''>('');
  const [diaVencimentoMax, setDiaVencimentoMax] = useState<number | ''>('');

  // Bulk selection state
  const [selectedContracts, setSelectedContracts] = useState<number[]>([]);
  const [bulkEmitLoading, setBulkEmitLoading] = useState(false);
  const [bulkDialogOpen, setBulkDialogOpen] = useState(false);

  // Menu de ações
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [activeMenuContractId, setActiveMenuContractId] = useState<number | null>(null);

  const handleOpenMenu = (event: React.MouseEvent<HTMLElement>, contractId: number) => {
    setAnchorEl(event.currentTarget);
    setActiveMenuContractId(contractId);
  };

  const handleCloseMenu = () => {
    setAnchorEl(null);
    setActiveMenuContractId(null);
  };
  const [bulkExecuteFlag, setBulkExecuteFlag] = useState(false);
  const [bulkTransmitFlag, setBulkTransmitFlag] = useState(false);
  const [bulkPreviewResult, setBulkPreviewResult] = useState<any | null>(null);
  const [bulkPreviewLoading, setBulkPreviewLoading] = useState(false);
  const [bulkExecuteLoading, setBulkExecuteLoading] = useState(false);

  const [clients, setClients] = useState<Cliente[]>([]);
  const [clientSearch, setClientSearch] = useState('');
  const [clientLoading, setClientLoading] = useState(false);

  const [servicos, setServicos] = useState<Servico[]>([]);
  const [servicoSearch, setServicoSearch] = useState('');
  const [servicoLoading, setServicoLoading] = useState(false);

  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [bankAccountLoading, setBankAccountLoading] = useState(false);

  // Network configuration state
  const [routers, setRouters] = useState<Router[]>([]);
  const [interfaces, setInterfaces] = useState<RouterInterface[]>([]);
  const [availableIPs, setAvailableIPs] = useState<string[]>([]);
  const [networkLoading, setNetworkLoading] = useState(false);
  const [olts, setOlts] = useState<any[]>([]);
  const [ctos, setCtos] = useState<any[]>([]);
  const [oltSearch, setOltSearch] = useState('');
  const [ctoSearch, setCtoSearch] = useState('');
  const [oltsLoading, setOltsLoading] = useState(false);
  const [ctosLoading, setCtosLoading] = useState(false);
  const oltSearchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const ctoSearchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const clientSearchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const servicoSearchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Helper function to check if contract is expired
  const isContractExpired = useCallback((contrato: Contrato): boolean => {
    if (!contrato.d_contrato_fim || !contrato.is_active) return false;

    try {
      const endDate = new Date(contrato.d_contrato_fim);
      const today = new Date();
      today.setHours(0, 0, 0, 0); // Reset time to start of day

      // Check if date is valid
      if (isNaN(endDate.getTime())) return false;

      return endDate < today;
    } catch (error) {
      console.error('Error parsing contract end date:', contrato.d_contrato_fim, error);
      return false;
    }
  }, []);

  // Helper function to check if contract is eligible for NFCom emission
  const isContractEligibleForEmission = useCallback((contrato: Contrato): boolean => {
    return contrato.is_active === true && !isContractExpired(contrato);
  }, [isContractExpired]);

  // Clear selection when contracts change
  useEffect(() => {
    setSelectedContracts([]);
  }, [contratos]);

  // Handle individual contract selection
  const handleContractSelect = useCallback((contractId: number, checked: boolean) => {
    setSelectedContracts(prev =>
      checked
        ? [...prev, contractId]
        : prev.filter(id => id !== contractId)
    );
  }, []);

  // Handle select all contracts
  const handleSelectAll = useCallback((checked: boolean) => {
    setSelectedContracts(checked ? contratos.map(c => c.id) : []);
  }, [contratos]);

  // Check if all contracts are selected
  const isAllSelected = useMemo(() => {
    return contratos.length > 0 && selectedContracts.length === contratos.length;
  }, [contratos, selectedContracts]);

  // Check if some (but not all) contracts are selected
  const isIndeterminate = useMemo(() => {
    return selectedContracts.length > 0 && selectedContracts.length < contratos.length;
  }, [contratos, selectedContracts]);

  // Calculate total value of selected contracts
  const selectedContractsTotalValue = useMemo(() => {
    return contratos
      .filter(c => selectedContracts.includes(c.id))
      .reduce((total, contrato) => total + (contrato.valor_total || 0), 0);
  }, [contratos, selectedContracts]);

  const [bulkUnlockLoading, setBulkUnlockLoading] = useState(false);

  const handleBulkUnlock = useCallback(async () => {
    const suspendedContracts = selectedContracts.filter(id => {
      const c = contratos.find(c => c.id === id);
      return c?.status === 'SUSPENSO';
    });

    if (suspendedContracts.length === 0) {
      setSnackbar({ open: true, message: 'Nenhum contrato suspenso selecionado', severity: 'warning' });
      return;
    }

    if (!window.confirm(`Tem certeza que deseja desbloquear ${suspendedContracts.length} cliente(s)?`)) return;

    setBulkUnlockLoading(true);
    try {
      const results = await Promise.allSettled(suspendedContracts.map(id => contratoService.ativarServico(id)));
      
      const fulfilled = results.filter(r => r.status === 'fulfilled');
      const rejected = results.filter(r => r.status === 'rejected');
      
      const successfulIds = suspendedContracts.filter((_, index) => results[index].status === 'fulfilled');
      
      if (rejected.length > 0) {
        setSnackbar({ 
          open: true, 
          message: `${fulfilled.length} desbloqueado(s) com sucesso. ${rejected.length} falharam.`, 
          severity: fulfilled.length > 0 ? 'warning' : 'error' 
        });
      } else {
        setSnackbar({ open: true, message: `${fulfilled.length} serviço(s) desbloqueado(s) com sucesso!`, severity: 'success' });
      }
      
      setSelectedContracts(prev => prev.filter(id => !successfulIds.includes(id)));
      
      // Use the ref since load might have dependencies we don't want to add to handleBulkUnlock
      loadRef.current();
    } catch (e) {
      setSnackbar({ open: true, message: 'Erro inesperado ao desbloquear serviços', severity: 'error' });
    } finally {
      setBulkUnlockLoading(false);
    }
  }, [selectedContracts, contratos]);

  // Open bulk emit dialog
  const handleBulkEmitNFCom = useCallback(() => {
    if (selectedContracts.length === 0) {
      setSnackbar({ open: true, message: 'Selecione pelo menos um contrato', severity: 'warning' });
      return;
    }

    setBulkPreviewResult(null);
    setBulkExecuteFlag(false);
    setBulkTransmitFlag(false);
    setBulkDialogOpen(true);
  }, [selectedContracts]);

  const previewBulkEmit = useCallback(async () => {
    if (!activeCompany) return;
    setBulkPreviewLoading(true);
    try {
      const nfcomService = (await import('../services/nfcomService')).default;
      const result = await nfcomService.bulkEmitFromContracts(activeCompany.id, selectedContracts, false, false);
      setBulkPreviewResult(result);
    } catch (error) {
      console.error('Erro preview bulk emit:', error);
      setSnackbar({ open: true, message: 'Erro ao executar pré-visualização (dry-run)', severity: 'error' });
    } finally {
      setBulkPreviewLoading(false);
    }
  }, [selectedContracts, activeCompany]);

  const confirmBulkEmit = useCallback(async () => {
    if (!activeCompany) return;
    setBulkExecuteLoading(true);
    try {
      const nfcomService = (await import('../services/nfcomService')).default;
      const result = await nfcomService.bulkEmitFromContracts(activeCompany.id, selectedContracts, bulkExecuteFlag, bulkTransmitFlag);

      const totalProcessed = result.total_processed ?? selectedContracts.length;
      const totalSuccess = result.total_success ?? (result.successes ? result.successes.length : 0);
      const totalFailed = result.total_failed ?? (result.failures ? result.failures.length : 0);

      setSnackbar({
        open: true,
        message: `Relatório: processados ${totalProcessed}, com sucesso ${totalSuccess}, falhas ${totalFailed}`,
        severity: totalFailed > 0 ? 'warning' : 'success'
      });

      if (result.failures && result.failures.length > 0) {
        // eslint-disable-next-line no-console
        console.warn('Bulk emit failures:', result.failures);
      }

      const successfulIds = (result.successes || []).map((s: any) => s.contract_id).filter(Boolean) as number[];
      setSelectedContracts(prev => prev.filter(id => !successfulIds.includes(id)));

      setBulkDialogOpen(false);
    } catch (error) {
      console.error('Erro ao confirmar bulk emit:', error);
      setSnackbar({ open: true, message: 'Erro ao executar emissão em lote', severity: 'error' });
    } finally {
      setBulkExecuteLoading(false);
    }
  }, [selectedContracts, activeCompany, bulkExecuteFlag, bulkTransmitFlag]);

  const load = useCallback(async () => {
    if (!activeCompany) return;
    setLoading(true);
    try {
      const data: ContratoListResponse = await contratoService.getContratosByEmpresaPaginated(
        activeCompany.id,
        page + 1,
        rowsPerPage,
        searchTerm || undefined,
        diaVencimentoMin || undefined,
        diaVencimentoMax || undefined,
        filterStatus || undefined
      );
      setContratos(data.contratos);
      setTotalRows(data.total);
    } catch (e) {
      setSnackbar({ open: true, message: 'Erro ao carregar contratos', severity: 'error' });
    } finally { setLoading(false); }
  }, [activeCompany, page, rowsPerPage, searchTerm, diaVencimentoMin, diaVencimentoMax, filterStatus]);

  useEffect(() => { if (activeCompany) load(); }, [activeCompany, load]);

  // Load contracts when page or rowsPerPage changes (but not searchTerm, handled by debounce)
  useEffect(() => {
    if (activeCompany && page >= 0 && rowsPerPage > 0) {
      load();
    }
  }, [page, rowsPerPage, activeCompany, load]);

  // Keep a ref to the latest `load` so the debounce effect can call it without
  // having `load` as a dependency (which would change when `page` changes and
  // cause the debounce effect to re-run and reset the page to 0).
  const loadRef = useRef(load);
  useEffect(() => { loadRef.current = load; }, [load]);

  // Debounce search (only depends on the search/filter values and activeCompany)
  useEffect(() => {
    if (activeCompany) {
      const timeoutId = setTimeout(() => {
        setPage(0);
        // call the latest load implementation from the ref
        loadRef.current();
      }, 500); // Debounce for 500ms

      return () => clearTimeout(timeoutId);
    }
  }, [searchTerm, diaVencimentoMin, diaVencimentoMax, filterStatus, activeCompany]);

  // Ajustar paginação para carregar todos os contratos quando estiver no modo mapa
  useEffect(() => {
    if (viewMode === 'map') {
      setPreviousRowsPerPage(rowsPerPage);
      setPage(0);
      setRowsPerPage(1000); // Exibe até 1000 contratos de uma vez no mapa
    } else if (rowsPerPage === 1000) {
      setPage(0);
      setRowsPerPage(previousRowsPerPage);
    }
  }, [viewMode]);

  // Load bank accounts when activeCompany changes
  useEffect(() => {
    if (activeCompany) {
      loadBankAccounts();
    }
  }, [activeCompany]);

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

  const handlePrintContract = async (contractId: number) => {
    if (!activeCompany) return;
    setViewingContractId(contractId);
    try {
      const url = await contratoService.getContratoTermoUrl(activeCompany.id, contractId);
      setContractHtmlUrl(url);
      setOpenContractModal(true);
    } catch (e) {
      setSnackbar({ open: true, message: 'Erro ao carregar termo de adesão', severity: 'error' });
    }
  };

  const handleSendContractNotification = async (contratoId: number) => {
    try {
      setLoading(true);
      await api.post(`/servicos-contratados/${contratoId}/enviar-email`);
      setSnackbar({
        open: true,
        message: 'Notificação do contrato enviada com sucesso!',
        severity: 'success'
      });
    } catch (error: any) {
      console.error('Erro ao enviar notificação do contrato:', error);
      setSnackbar({
        open: true,
        message: `Erro ao enviar notificação: ${error.response?.data?.detail || 'Erro desconhecido'}`,
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const loadClients = useCallback(async (search: string = '') => {
    if (!activeCompany) return;
    setClientLoading(true);
    try {
      // When search is empty, this will return the first page (limit 10).
      const response = await clientService.getClientsByCompany(activeCompany.id, 1, 20, search || undefined);
      const list = response.clientes || [];

      setClients(prev => {
        // Se estivermos limpando a busca, voltamos para a lista inicial (10-20 itens)
        if (!search) return list;

        // Se estivermos buscando, mesclamos os resultados com o cliente atualmente selecionado no form (se houver)
        // para garantir que o Autocomplete não perca o label do item selecionado.
        const currentId = form.cliente_id;
        const currentClient = prev.find(c => c.id === currentId);

        if (currentClient && !list.some(c => c.id === currentId)) {
          return [currentClient, ...list];
        }
        return list;
      });
    } catch (error) {
      console.error("Erro ao carregar clientes:", error);
      setClients([]);
    } finally {
      setClientLoading(false);
    }
  }, [activeCompany, form.cliente_id]);

  const loadServicos = useCallback(async (search: string = '') => {
    if (!activeCompany) return;
    setServicoLoading(true);
    try {
      const response = await servicoService.getServicosByEmpresaPaginated(activeCompany.id, 1, 20, search || undefined);
      const list = response.servicos || [];

      setServicos(prev => {
        if (!search) return list;
        const currentId = form.servico_id;
        const currentServico = prev.find(s => s.id === currentId);

        if (currentServico && !list.some(s => s.id === currentId)) {
          return [currentServico, ...list];
        }
        return list;
      });
    } catch (error) {
      console.error("Erro ao carregar serviços:", error);
      setServicos([]);
    } finally {
      setServicoLoading(false);
    }
  }, [activeCompany, form.servico_id]);

  const loadBankAccounts = useCallback(async () => {
    if (!activeCompany) return;
    setBankAccountLoading(true);
    try {
      const response = await bankAccountService.listBankAccounts(activeCompany.id);
      setBankAccounts(response || []);
    } catch (error) {
      console.error("Erro ao carregar contas bancárias:", error);
      setBankAccounts([]);
    } finally {
      setBankAccountLoading(false);
    }
  }, [activeCompany]);


  const loadRouters = useCallback(async () => {
    if (!activeCompany) return;
    setNetworkLoading(true);
    try {
      const resp = await routerService.getByCompany(activeCompany.id);
      setRouters(resp || []);
    } catch (error) {
      console.error("Erro ao carregar routers:", error);
      setRouters([]);
    } finally {
      setNetworkLoading(false);
    }
  }, [activeCompany]);

  const loadInterfaces = useCallback(async (routerId?: number) => {
    if (!activeCompany || !routerId) {
      setInterfaces([]);
      return;
    }
    try {
      const resp = await networkService.getRouterInterfaces(routerId);
      setInterfaces(resp || []);
    } catch (error) {
      console.error("Erro ao carregar interfaces:", error);
      setInterfaces([]);
    }
  }, [activeCompany]);

  const loadOLTs = useCallback(async (search = '', forceOltId?: number) => {
    try {
      setOltsLoading(true);
      const resp = await api.get('/ftth/olts', {
        params: { search, limit: 100 }
      });
      let loadedOlts = resp.data || [];
      if (forceOltId && !loadedOlts.some((o: any) => o.id === forceOltId)) {
        try {
          const singleResp = await api.get(`/ftth/olts/${forceOltId}`);
          if (singleResp.data) {
            loadedOlts = [singleResp.data, ...loadedOlts];
          }
        } catch (err) {
          console.error("Erro ao carregar OLT por ID:", err);
        }
      }
      setOlts(loadedOlts);
    } catch (error) {
      console.error("Erro ao carregar OLTs:", error);
    } finally {
      setOltsLoading(false);
    }
  }, []);

  const loadCTOs = useCallback(async (search = '', oltId?: number, proximityCoords?: string, forceCtoId?: number) => {
    try {
      setCtosLoading(true);
      const params: any = { search, limit: 100 };
      if (oltId) {
        params.olt_id = oltId;
      }
      if (proximityCoords) {
        params.proximidade_gps = proximityCoords;
      }
      const resp = await api.get('/ftth/ctos', { params });
      let loadedCtos = Array.isArray(resp.data) ? resp.data : (resp.data?.data || []);
      if (forceCtoId && !loadedCtos.some((c: any) => c.id === forceCtoId)) {
        try {
          const singleResp = await api.get(`/ftth/ctos/${forceCtoId}`);
          if (singleResp.data) {
            loadedCtos = [singleResp.data, ...loadedCtos];
          }
        } catch (err) {
          console.error("Erro ao carregar CTO por ID:", err);
        }
      }
      setCtos(loadedCtos);
    } catch (error) {
      console.error("Erro ao carregar CTOs:", error);
    } finally {
      setCtosLoading(false);
    }
  }, []);

  // Load OLTs when form opens
  useEffect(() => {
    if (openForm && activeCompany) {
      loadOLTs('', form.olt_id);
    }
  }, [openForm, activeCompany, form.olt_id]);

  // Load CTOs reactively when form opens, OLT changes, or coordinates change
  useEffect(() => {
    if (openForm && activeCompany) {
      const timer = setTimeout(() => {
        loadCTOs('', form.olt_id, form.coordenadas_gps, form.cto_id);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [openForm, form.olt_id, form.coordenadas_gps, activeCompany, form.cto_id]);

  // Load available IPs when IP class changes
  const loadAvailableIPs = useCallback(async (ipClass: IPClass | undefined) => {
    if (ipClass) {
      try {
        // Busca IPs já em uso para esta classe IP
        const usedIPsResponse = await api.get(`/network/ip-classes/${ipClass.id}/used-ips/`);

        if (usedIPsResponse.data) {
          let usedIPs: string[] = usedIPsResponse.data;

          // Se o formulário tiver um IP (caso de edição), removemos ele da lista de 'usados' 
          // para que ele apareça como disponível na lista de opções do Select
          if (form.assigned_ip) {
            usedIPs = usedIPs.filter(ip => ip !== form.assigned_ip);
          }

          // Gera IPs disponíveis excluindo os já em uso
          const ips = generateAvailableIPs(ipClass, usedIPs);
          setAvailableIPs(ips);
        } else {
          // Fallback: gera todos os IPs se não conseguir buscar os usados
          const ips = generateAvailableIPs(ipClass);
          setAvailableIPs(ips);
        }
      } catch (error) {
        console.error('Erro ao buscar IPs em uso:', error);
        // Fallback: gera todos os IPs em caso de erro
        const ips = generateAvailableIPs(ipClass);
        setAvailableIPs(ips);
      }
    } else {
      setAvailableIPs([]);
    }
  }, [form.assigned_ip]);

  // Get IP classes for selected interface
  const getIPClassesForSelectedInterface = useMemo(() => {
    if (!form.interface_id) return [];
    const selectedInterface = interfaces.find(intf => intf.id === form.interface_id);
    return selectedInterface?.ip_classes || [];
  }, [form.interface_id, interfaces]);

  // Auto-select network settings for IP_MAC authentication
  useEffect(() => {
    if (openForm && form.metodo_autenticacao === 'IP_MAC') {
      // 1. Auto-select first IP class if interface is selected but class is not
      if (form.interface_id && !form.ip_class_id) {
        const classes = getIPClassesForSelectedInterface;
        if (classes.length > 0) {
          handleInputChange('ip_class_id', classes[0].id);
        }
      }

      // 2. Auto-select first available IP if class is set and IP is empty
      if (form.ip_class_id && availableIPs.length > 0 && !form.assigned_ip) {
        handleInputChange('assigned_ip', availableIPs[0]);
      }
    }
  }, [form.metodo_autenticacao, form.interface_id, form.ip_class_id, availableIPs.length, form.assigned_ip, openForm, getIPClassesForSelectedInterface]);

  // Load available IPs automatically when IP class changes
  useEffect(() => {
    if (openForm && form.ip_class_id) {
      const selectedIpClass = getIPClassesForSelectedInterface.find(c => c.id === form.ip_class_id);
      if (selectedIpClass) {
        loadAvailableIPs(selectedIpClass);
      } else {
        // Se não achar na interface atual (ex: mudou interface), limpa IPs
        setAvailableIPs([]);
      }
    } else {
      setAvailableIPs([]);
    }
  }, [form.ip_class_id, openForm, loadAvailableIPs, getIPClassesForSelectedInterface]);


  const renderContractCards = () => (
    <Box sx={{ display: 'grid', gap: 2 }}>
      {contratos.map(c => {
        const isActive = c.is_active;
        const autoEmit = c.auto_emit;
        const isExpired = isContractExpired(c);
        return (
          <Card
            key={c.id}
            variant="outlined"
            sx={{
              borderColor: isExpired ? '#f44336' : undefined,
              borderWidth: isExpired ? 2 : 1,
              backgroundColor: isExpired ? '#ffebee' : undefined
            }}
          >
            <CardContent sx={{ padding: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                <Box sx={{ flex: 1 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {c.numero_contrato || `Contrato #${c.id}`}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
                      <Checkbox
                        checked={selectedContracts.includes(c.id)}
                        onChange={(e) => handleContractSelect(c.id, e.target.checked)}
                        size="small"
                      />
                      {isExpired ? (
                        <Chip label="VENCIDO" color="error" size="small" variant="filled" />
                      ) : (
                        <>
                          {c.status === 'AGUARDANDO_ASSINATURA' && <Chip label="Aguardando Assinatura" color="warning" size="small" variant="outlined" />}
                          {c.assinado_em && <Chip label="Assinado" color="success" size="small" variant="filled" icon={<CheckCircleIcon className="w-3.5 h-3.5" />} />}
                          {isActive && c.status !== 'AGUARDANDO_ASSINATURA' && <Chip label="Ativo" color="success" size="small" />}
                          {!isActive && <Chip label="Inativo" color="default" size="small" />}
                        </>
                      )}
                      {autoEmit && <Chip label="Auto" color="info" size="small" />}
                    </Box>
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2, width: '100%' }}>
                    Cliente: {c.cliente_razao_social || c.cliente_nome || `Cliente #${c.cliente_id}`}
                    {c.cliente_cpf_cnpj && (
                      <><br /><small>CPF/CNPJ: {clientService.formatCpfCnpj(c.cliente_cpf_cnpj)}</small></>
                    )}
                    {c.cliente_telefone && (
                      <><br /><small>Tel: {c.cliente_telefone}</small></>
                    )}
                    {(c.cliente_municipio || c.cliente_uf) && (
                      <><br /><small>{c.cliente_municipio ? c.cliente_municipio : ''}{c.cliente_municipio && c.cliente_uf ? '/' : ''}{c.cliente_uf ? c.cliente_uf : ''}</small></>
                    )}
                  </Typography>
                </Box>
              </Box>
              <Divider sx={{ my: 2 }} />
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mb: 2 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">Periodicidade</Typography>
                  <Typography variant="body2">{c.periodicidade || 'MENSAL'}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Dia Emissão</Typography>
                  <Typography variant="body2">{c.dia_emissao || '-'}</Typography>
                </Box>
                <Box sx={{ gridColumn: 'span 2' }}>
                  <Typography variant="caption" color="text.secondary">Dia Vencimento</Typography>
                  <Typography variant="body2">{c.dia_vencimento ?? (c.vencimento ? (() => { const m = (String(c.vencimento)).match(/^(\d{4})-(\d{2})-(\d{2})/); return m ? m[3] : '-'; })() : '-')}</Typography>
                </Box>
              </Box>
              <Box sx={{ textAlign: 'center', mb: 2 }}>
                <Typography variant="caption" color="text.secondary">Valor Unitário</Typography>
                <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                  {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(c.valor_unitario || 0)}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end', mt: 2 }}>
                {hasPermission('contract_manage') ? (
                  <>
                    <Tooltip title="Imprimir Contrato">
                      <IconButton size="small" onClick={() => handlePrintContract(c.id)} color="primary">
                        <PrinterIcon className="w-5 h-5" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Editar">
                      <IconButton size="small" onClick={() => handleOpenForm(c)}>
                        <PencilIcon className="w-5 h-5" />
                      </IconButton>
                    </Tooltip>
                    {c.status === 'PENDENTE_INSTALACAO' && (
                      <Tooltip title="Ativar Serviço">
                        <IconButton size="small" onClick={() => ativarServico(c)} color="success">
                          <PlayIcon className="w-5 h-5" />
                        </IconButton>
                      </Tooltip>
                    )}
                    {c.status === 'ATIVO' && (
                      <>
                        <Tooltip title="Resetar Conexão">
                          <IconButton size="small" onClick={() => resetConnection(c)} color="warning">
                            <ArrowPathIcon className="w-5 h-5" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Sincronizar com Router (Full Sync)">
                          <IconButton size="small" onClick={() => syncRouter(c)} color="primary">
                            <CloudArrowUpIcon className="w-5 h-5" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Bloquear/Suspender">
                          <IconButton size="small" onClick={() => suspenderServico(c)} color="error">
                            <PauseIcon className="w-5 h-5" />
                          </IconButton>
                        </Tooltip>
                      </>
                    )}

                    {c.status === 'SUSPENSO' && (
                      <Tooltip title="Desbloquear/Ativar">
                        <IconButton size="small" onClick={() => ativarServico(c)} color="success">
                          <PlayIcon className="w-5 h-5" />
                        </IconButton>
                      </Tooltip>
                    )}
                    <Tooltip title="Excluir">
                      <IconButton size="small" onClick={() => remove(c)}>
                        <TrashIconMUI className="w-5 h-5 text-red-500" />
                      </IconButton>
                    </Tooltip>
                  </>
                ) : hasPermission('contract_view') ? (
                  <Tooltip title="Visualizar">
                    <IconButton size="small" onClick={() => handleOpenForm(c, true)}>
                      <EyeIcon className="w-5 h-5" />
                    </IconButton>
                  </Tooltip>
                ) : null}
              </Box>
            </CardContent>
          </Card>
        );
      })}
    </Box>
  );

  const renderContractMap = () => {
    // Filtrar apenas contratos que possuem coordenadas GPS válidas
    const contractsWithGPS = contratos.filter(c => {
      if (!c.coordenadas_gps) return false;
      const parts = c.coordenadas_gps.split(',');
      if (parts.length !== 2) return false;
      const lat = parseFloat(parts[0]);
      const lon = parseFloat(parts[1]);
      return !isNaN(lat) && !isNaN(lon);
    });

    if (contractsWithGPS.length === 0) {
      return (
        <Box sx={{ textAlign: 'center', p: 6, backgroundColor: '#fff', borderRadius: 2, border: '1px solid', borderColor: 'grey.200' }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            🗺️ Nenhum contrato com coordenadas válidas
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Para visualizar contratos no mapa, certifique-se de preencher o campo "Coordenadas GPS" nos dados da instalação.
          </Typography>
        </Box>
      );
    }

    // Calcular o centro médio de todos os pontos para centralizar o mapa
    let sumLat = 0;
    let sumLon = 0;
    contractsWithGPS.forEach(c => {
      const [lat, lon] = c.coordenadas_gps!.split(',').map(parseFloat);
      sumLat += lat;
      sumLon += lon;
    });
    const centerLat = sumLat / contractsWithGPS.length;
    const centerLon = sumLon / contractsWithGPS.length;

    const getStatusColor = (status?: string) => {
      switch (status) {
        case 'ATIVO':
          return '#10B981'; // Emerald
        case 'AGUARDANDO_ASSINATURA':
          return '#F59E0B'; // Amber
        case 'BLOQUEADO':
          return '#EF4444'; // Red
        default:
          return '#6B7280'; // Gray
      }
    };

    const getStatusLabel = (status?: string) => {
      switch (status) {
        case 'ATIVO':
          return 'Ativo';
        case 'AGUARDANDO_ASSINATURA':
          return 'Aguardando Assinatura';
        case 'BLOQUEADO':
          return 'Bloqueado';
        default:
          return status || 'Desconhecido';
      }
    };

    return (
      <Box sx={{ height: 'calc(100vh - 280px)', width: '100%', borderRadius: 2, overflow: 'hidden', border: '1px solid', borderColor: 'grey.300', position: 'relative' }}>
        <MapContainer
          center={[centerLat, centerLon]}
          zoom={13}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
          />

          {contractsWithGPS.map(c => {
            const [lat, lon] = c.coordenadas_gps!.split(',').map(parseFloat);
            const statusColor = getStatusColor(c.status);

            const customIcon = L.divIcon({
              html: `<div style="display: flex; justify-content: center; align-items: center; width: 28px; height: 28px; background-color: ${statusColor}; border-radius: 50% 50% 50% 0; transform: rotate(-45deg); border: 2.5px solid white; box-shadow: 0 3px 6px rgba(0,0,0,0.35);">
                      <div style="width: 8px; height: 8px; background-color: white; border-radius: 50%; transform: rotate(45deg);"></div>
                    </div>`,
              className: 'custom-gps-pin',
              iconSize: [28, 28],
              iconAnchor: [14, 28],
              popupAnchor: [0, -28]
            });

            return (
              <Marker
                key={c.id}
                position={[lat, lon]}
                icon={customIcon}
              >
                <LeafletTooltip direction="top" offset={[0, -28]} opacity={0.9}>
                  <strong>{c.cliente_razao_social || c.cliente_nome || 'Cliente'}</strong>
                </LeafletTooltip>
                <Popup maxWidth={300}>
                  <Box sx={{ p: 0.5 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: 'indigo.900', mb: 0.5 }}>
                      👤 {c.cliente_razao_social || c.cliente_nome || 'Cliente'}
                    </Typography>
                    <Box sx={{ mb: 1 }}>
                      <Chip
                        label={getStatusLabel(c.status)}
                        size="small"
                        sx={{
                          height: 18,
                          fontSize: '0.675rem',
                          fontWeight: 'bold',
                          color: '#fff',
                          bgcolor: statusColor,
                          mb: 0.5
                        }}
                      />
                    </Box>
                    <Divider sx={{ my: 1 }} />
                    <Typography variant="body2" sx={{ fontSize: '0.8rem', color: 'text.primary', mb: 0.5 }}>
                      <strong>Plano:</strong> {c.servico_descricao || 'Sem plano'} - R$ {Number(c.valor_unitario || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </Typography>
                    {c.tipo_conexao && (
                      <Typography variant="body2" sx={{ fontSize: '0.8rem', color: 'text.secondary', mb: 0.5 }}>
                        <strong>Conexão:</strong> {c.tipo_conexao}
                      </Typography>
                    )}
                    {c.cto_nome && (
                      <Typography variant="body2" sx={{ fontSize: '0.8rem', color: 'text.secondary', mb: 0.5 }}>
                        <strong>Caixa CTO:</strong> {c.cto_nome} {c.cto_porta ? `(Porta ${c.cto_porta})` : ''}
                      </Typography>
                    )}
                    {c.onu_serial && (
                      <Typography variant="body2" sx={{ fontSize: '0.8rem', color: 'text.secondary', mb: 1 }}>
                        <strong>ONU Serial:</strong> {c.onu_serial}
                      </Typography>
                    )}
                    <Box sx={{ display: 'flex', gap: 1, mt: 1.5 }}>
                      <Button
                        size="small"
                        variant="contained"
                        color="primary"
                        fullWidth
                        sx={{ fontSize: '0.75rem', py: 0.5, textTransform: 'none' }}
                        onClick={() => handleOpenForm(c, true)}
                      >
                        Visualizar
                      </Button>
                      {hasPermission('contract_manage') && (
                        <Button
                          size="small"
                          variant="outlined"
                          color="secondary"
                          fullWidth
                          sx={{ fontSize: '0.75rem', py: 0.5, textTransform: 'none' }}
                          onClick={() => handleOpenForm(c, false)}
                        >
                          Editar
                        </Button>
                      )}
                    </Box>
                  </Box>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </Box>
    );
  };

  const renderContractTable = () => (
    <TableContainer component={Paper} sx={{ maxHeight: '70vh', overflow: 'auto' }}>
      <Table stickyHeader>
        <TableHead>
          <TableRow>
            <TableCell sx={{ fontWeight: 600, width: 50 }}>
              <Checkbox
                checked={isAllSelected}
                indeterminate={isIndeterminate}
                onChange={(e) => handleSelectAll(e.target.checked)}
                size="small"
              />
            </TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Nº</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Cliente</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Cidade/UF</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>CPF/CNPJ</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Plano</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Emissão</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Venc.</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Valor</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
            <TableCell sx={{ fontWeight: 600, width: 120 }}>Ações</TableCell>
          </TableRow>
        </TableHead>
        <TableBody sx={{ whiteSpace: 'nowrap' }}>
          {contratos.map((c) => {
            const isExpired = isContractExpired(c);
            return (
              <TableRow
                key={c.id}
                hover
                sx={{
                  backgroundColor: isExpired ? '#ffebee' : undefined,
                  '&:hover': {
                    backgroundColor: isExpired ? '#ffcdd2' : undefined
                  }
                }}
              >
                <TableCell>
                  <Checkbox
                    checked={selectedContracts.includes(c.id)}
                    onChange={(e) => handleContractSelect(c.id, e.target.checked)}
                    size="small"
                  />
                </TableCell>
                <TableCell>{c.numero_contrato || `Contrato #${c.id}`}</TableCell>
                <TableCell>{c.cliente_razao_social || c.cliente_nome || `Cliente #${c.cliente_id}`}</TableCell>
                <TableCell>{c.cliente_municipio ? `${c.cliente_municipio}${c.cliente_uf ? '/' + c.cliente_uf : ''}` : '-'}</TableCell>
                <TableCell>{c.cliente_cpf_cnpj ? clientService.formatCpfCnpj(c.cliente_cpf_cnpj) : '-'}</TableCell>
                <TableCell>{c.servico_descricao || `Serviço #${c.servico_id}`}</TableCell>
                <TableCell>{c.dia_emissao || '-'}</TableCell>
                <TableCell>{c.dia_vencimento ?? (c.vencimento ? (() => { const m = (String(c.vencimento)).match(/^(\d{4})-(\d{2})-(\d{2})/); return m ? m[3] : '-'; })() : '-')}</TableCell>
                <TableCell>
                  {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(c.valor_unitario || 0)}
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', alignItems: 'center' }}>
                    {c.status && (
                      <Chip
                        label={c.status === 'ATIVO' ? 'Ativo' :
                          c.status === 'SUSPENSO' ? 'Suspenso' :
                            c.status === 'CANCELADO' ? 'Cancelado' :
                              c.status === 'PENDENTE_INSTALACAO' ? 'Pendente Instalação' :
                                c.status === 'AGUARDANDO_ASSINATURA' ? 'Aguardando Assinatura' : c.status}
                        color={c.status === 'ATIVO' ? 'success' :
                          c.status === 'SUSPENSO' ? 'warning' :
                            c.status === 'CANCELADO' ? 'error' :
                              c.status === 'PENDENTE_INSTALACAO' ? 'info' :
                                c.status === 'AGUARDANDO_ASSINATURA' ? 'warning' : 'default'}
                        size="small"
                        variant="outlined"
                      />
                    )}
                    {c.assinado_em && (
                      <Tooltip title={`Assinado em ${new Date(c.assinado_em).toLocaleString()}`}>
                        <Chip
                          label="Assinado"
                          color="success"
                          size="small"
                          icon={<CheckCircleIcon className="w-3.5 h-3.5" />}
                        />
                      </Tooltip>
                    )}
                    {(c.taxa_instalacao ?? 0) > 0 && (
                      <Chip
                        label={c.taxa_instalacao_paga ? 'Instalação Paga' : 'Taxa Pendente'}
                        color={c.taxa_instalacao_paga ? 'success' : 'warning'}
                        size="small"
                        variant="outlined"
                      />
                    )}
                  </Box>
                </TableCell>
                <TableCell align="right">
                  <IconButton
                    size="small"
                    onClick={(e) => handleOpenMenu(e, c.id)}
                  >
                    <EllipsisVerticalIcon className="w-5 h-5" />
                  </IconButton>
                  <Menu
                    anchorEl={anchorEl}
                    open={activeMenuContractId === c.id}
                    onClose={handleCloseMenu}
                    transformOrigin={{ horizontal: 'right', vertical: 'top' }}
                    anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
                  >
                    <MenuItem onClick={() => { handleOpenForm(c, true); handleCloseMenu(); }}>
                      <EyeIcon className="w-4 h-4 mr-2" />
                      Visualizar
                    </MenuItem>

                    <MenuItem onClick={() => { handlePrintContract(c.id); handleCloseMenu(); }}>
                      <PrinterIcon className="w-4 h-4 mr-2" />
                      Imprimir Contrato
                    </MenuItem>

                    {hasPermission('contract_manage') && (
                      <MenuItem onClick={() => { handleOpenForm(c); handleCloseMenu(); }}>
                        <PencilIcon className="w-4 h-4 mr-2" />
                        Editar
                      </MenuItem>
                    )}

                    {hasPermission('contract_manage') && c.status === 'PENDENTE_INSTALACAO' && (
                      <MenuItem onClick={() => { ativarServico(c); handleCloseMenu(); }} sx={{ color: 'success.main' }}>
                        <PlayIcon className="w-4 h-4 mr-2" />
                        Ativar Serviço
                      </MenuItem>
                    )}

                    {hasPermission('contract_manage') && c.status === 'ATIVO' && (
                      <>
                        <MenuItem onClick={() => { resetConnection(c); handleCloseMenu(); }} sx={{ color: 'warning.main' }}>
                          <ArrowPathIcon className="w-4 h-4 mr-2" />
                          Resetar Conexão
                        </MenuItem>
                        <MenuItem onClick={() => { syncRouter(c); handleCloseMenu(); }}>
                          <CloudArrowUpIcon className="w-4 h-4 mr-2" />
                          Sincronizar Router
                        </MenuItem>
                        <MenuItem onClick={() => { suspenderServico(c); handleCloseMenu(); }} sx={{ color: 'error.main' }}>
                          <PauseIcon className="w-4 h-4 mr-2" />
                          Bloquear
                        </MenuItem>
                      </>
                    )}

                    {hasPermission('contract_manage') && c.status === 'SUSPENSO' && (
                      <MenuItem onClick={() => { ativarServico(c); handleCloseMenu(); }} sx={{ color: 'success.main' }}>
                        <PlayIcon className="w-4 h-4 mr-2" />
                        Desbloquear
                      </MenuItem>
                    )}

                    {hasPermission('contract_manage') && (
                      <>
                        <Divider />
                        <MenuItem onClick={() => { remove(c); handleCloseMenu(); }} sx={{ color: 'error.main' }}>
                          <TrashIconMUI className="w-4 h-4 mr-2" />
                          Excluir
                        </MenuItem>
                      </>
                    )}
                  </Menu>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );

  const renderPagination = () => {
    if (isMobile) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2, flexWrap: 'wrap', gap: 1 }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
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
          <Pagination
            count={Math.ceil(totalRows / rowsPerPage)}
            page={page + 1}
            onChange={handleChangePage}
            color="primary"
            size="small"
          />
        </Box>
      );
    }

    return (
      <TablePagination
        component="div"
        count={totalRows}
        page={page}
        onPageChange={handleChangePage}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={handleTableRowsPerPageChange}
        labelRowsPerPage="Itens por página"
        labelDisplayedRows={({ from, to, count }) => `${from}-${to} de ${count}`}
      />
    );
  };

  const handleOpenForm = async (c?: Contrato, view: boolean = false, preselectedClient?: { id: number; nome_razao_social: string; cpf_cnpj?: string; enderecos?: any[] }) => {
    setViewOnly(!!view);
    if (c) {
      let fullContract = c;
      // Fetch full contract to get assets and other details not in the list
      try {
        setLoading(true);
        fullContract = await contratoService.getContratoById(c.id);
      } catch (error) {
        console.error('Erro ao buscar detalhes do contrato:', error);
        // Fallback to the object we have if fetch fails
      } finally {
        setLoading(false);
      }

      setEditing(fullContract);
      // Normalize date fields to YYYY-MM-DD for date inputs to avoid timezone shifts
      const normalized: any = { ...fullContract };
      // Prefer direct string slice for strings to avoid any Date parsing differences
      // Prefer dia_vencimento numeric (new field). If not present, try to extract day from legacy vencimento date.
      if (c.dia_vencimento !== undefined && c.dia_vencimento !== null) {
        normalized.dia_vencimento = Number(c.dia_vencimento);
      } else if (typeof c.vencimento === 'string' && /^\d{4}-\d{2}-\d{2}/.test(c.vencimento)) {
        const mm = c.vencimento.match(/^(\d{4})-(\d{2})-(\d{2})/);
        normalized.dia_vencimento = mm ? Number(mm[3]) : undefined;
      } else if (c.vencimento) {
        // fallback: parse date and extract UTC day to avoid TZ shifts
        const parsed = toLocalDateInputString(c.vencimento);
        if (parsed) {
          const mm = parsed.match(/^(\d{4})-(\d{2})-(\d{2})/);
          normalized.dia_vencimento = mm ? Number(mm[3]) : undefined;
        }
      }
      normalized.d_contrato_ini = toLocalDateInputString(c.d_contrato_ini);
      normalized.d_contrato_fim = toLocalDateInputString(c.d_contrato_fim);
      normalized.data_inicio_cobranca = toLocalDateInputString(c.data_inicio_cobranca);
      // Debugging: log raw + normalized to help diagnose TZ/format issues
      // eslint-disable-next-line no-console
      console.log('handleOpenForm - vencimento raw:', c.vencimento, 'normalized:', normalized.vencimento);
      setForm(normalized);

      // Carregar dados do cliente selecionado
      if (c.cliente_id && activeCompany) {
        try {
          const clientResponse = await clientService.getClientById(c.cliente_id, activeCompany.id);
          setClients([clientResponse]);
          if (clientResponse.enderecos && clientResponse.enderecos.length > 0) {
            setClientAddresses(clientResponse.enderecos);
          } else {
            setClientAddresses([]);
          }
          setClientSearch(clientResponse.nome_razao_social || '');
        } catch (error) {
          console.error('Erro ao carregar cliente:', error);
        }
      }

      // Carregar dados do serviço selecionado
      if (c.servico_id && activeCompany) {
        try {
          // Por enquanto, buscar todos os serviços e filtrar pelo ID
          const servicoResponse = await servicoService.getServicosByEmpresaPaginated(activeCompany.id, 1, 1000);
          const servico = servicoResponse.servicos.find(s => s.id === c.servico_id);
          if (servico) {
            setServicos([servico]);
            setServicoSearch(servico.descricao || '');
          }
        } catch (error) {
          console.error('Erro ao carregar serviço:', error);
        }
      }

      // Carregar dados de rede se houver configuração
      if (activeCompany) {
        loadRouters();
        if (c.router_id) {
          loadInterfaces(c.router_id);
        }
        if (c.assigned_ip) {
          setAvailableIPs([c.assigned_ip]);
        }
      }
    } else {
      setViewOnly(false);
      const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
      const oneYearFromNow = new Date();
      oneYearFromNow.setFullYear(oneYearFromNow.getFullYear() + 1);
      const oneYearFromNowStr = oneYearFromNow.toISOString().split('T')[0];
      setEditing(null);

      // Tentar carregar dados do último contrato salvo no localStorage
      let initialForm: Partial<Contrato> = {
        empresa_id: activeCompany?.id,
        cliente_id: undefined,
        servico_id: undefined,
        bank_account_id: activeCompany?.default_bank_account_id,
        quantidade: 1,
        periodicidade: 'MENSAL',
        valor_unitario: 0,
        auto_emit: true,
        auto_emit_nfcom: true,
        is_active: true,
        dia_emissao: 1,
        status: 'AGUARDANDO_ASSINATURA',
        periodo_carencia: 0,
        multa_atraso_percentual: 0.0,
        taxa_instalacao: 0.0,
        taxa_instalacao_paga: false,
        tipo_conexao: 'FIBRA',
        sla_garantido: undefined,
        velocidade_garantida: '',
        subscription_id: undefined,
        d_contrato_ini: today,
        d_contrato_fim: oneYearFromNowStr,
        data_inicio_cobranca: today,
        data_instalacao: today,
        router_id: undefined,
        interface_id: undefined,
        ip_class_id: undefined,
        mac_address: '',
        assigned_ip: '',
        metodo_autenticacao: undefined,
        pppoe_username: '',
        pppoe_password: '',
        onu_serial: '',
        onu_modelo: '',
        onu_sinal: '',
        olt_nome: '',
        olt_pon: '',
        cto_nome: '',
        cto_porta: '',
        metragem_drop: undefined,
        vlan_id: undefined,
        olt_id: undefined,
        cto_id: undefined,
        ativos: []
      };

      const savedData = localStorage.getItem('last_contract_tech_data');
      if (savedData) {
        try {
          const techData = JSON.parse(savedData) as Partial<Contrato>;
          initialForm = { ...initialForm, ...techData };

          // Se houver um router salvo, carregar as interfaces
          if (techData.router_id) {
            loadInterfaces(techData.router_id);
          }

          // NUNCA copiar IP, MAC ou usuários PPPoE de um contrato para outro
          initialForm.assigned_ip = '';
          initialForm.mac_address = '';
          initialForm.pppoe_username = '';
          initialForm.pppoe_password = '';
          initialForm.onu_serial = '';
          initialForm.onu_sinal = '';
          initialForm.cto_porta = '';
          initialForm.metragem_drop = undefined;
        } catch (e) {
          console.error('Erro ao processar dados salvos do localStorage:', e);
        }
      }

      if (preselectedClient) {
        initialForm.cliente_id = preselectedClient.id;
      }

      setForm(initialForm);
      // Reset input values and prefetch the first 10 clients and services
      if (preselectedClient) {
        setClientSearch(preselectedClient.nome_razao_social || '');
        setClientAddresses(preselectedClient.enderecos || []);
      } else {
        setClientSearch('');
        setClientAddresses([]);
      }
      setServicoSearch('');

      // Prefetch defaults (do not await)
      if (activeCompany) {
        if (preselectedClient) {
          setClients([preselectedClient as any]);
        } else {
          loadClients('');
        }
        loadServicos('');
        loadBankAccounts();
        loadRouters();
      }
    }

    // Prefetch defaults (do not await)
    // Nota: no modo edição (c !== undefined), o cliente já foi carregado individualmente acima.
    // NÃO chamar loadClients('') neste caso, pois sobrescreveria o array clients com os primeiros
    // 20 clientes paginados, fazendo o cliente selecionado "desaparecer" do Autocomplete.
    if (activeCompany) {
      if (!c && !clientSearch && !preselectedClient) loadClients('');
      if (!servicoSearch) loadServicos('');
    }
    setOpenForm(true);
  };

  useEffect(() => {
    if (location.state && location.state.preselectClientId && activeCompany) {
      const { preselectClientId, preselectClientName, preselectClientCpfCnpj, preselectClientAddresses } = location.state;
      handleOpenForm(undefined, false, {
        id: preselectClientId,
        nome_razao_social: preselectClientName,
        cpf_cnpj: preselectClientCpfCnpj || '',
        enderecos: preselectClientAddresses || []
      });
      // Clear location state to avoid re-opening the form on page refresh/navigation back
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location.state, activeCompany, navigate, location.pathname]);

  const handleCloseForm = () => {
    setOpenForm(false);
    setEditing(null);
    setErrors({});
  };

  // Function to format MAC address input
  const formatMacAddress = (value: string): string => {
    // Remove all non-hex characters
    const cleaned = value.replace(/[^0-9A-Fa-f]/g, '');
    // Limit to 12 characters (6 bytes)
    const limited = cleaned.slice(0, 12);
    // Add colons every 2 characters and convert to uppercase
    return limited.replace(/(.{2})(?=.)/g, '$1:').toUpperCase();
  };

  const fetchCoordinatesForAddress = async (enderecoId: number, addressesList?: any[]) => {
    const listToSearch = addressesList || clientAddresses;
    const selectedAddress = listToSearch.find(end => end.id === Number(enderecoId));
    if (!selectedAddress) return;

    // Queries com níveis de fallbacks crescentes (Completo -> Sem bairro -> Apenas rua e cidade)
    const queries = [
      `${selectedAddress.endereco}, ${selectedAddress.numero}, ${selectedAddress.bairro || ''}, ${selectedAddress.municipio} - ${selectedAddress.uf}, Brasil`,
      `${selectedAddress.endereco}, ${selectedAddress.numero}, ${selectedAddress.municipio} - ${selectedAddress.uf}, Brasil`,
      `${selectedAddress.endereco}, ${selectedAddress.municipio} - ${selectedAddress.uf}, Brasil`
    ];

    for (const query of queries) {
      try {
        const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`, {
          headers: {
            'Accept-Language': 'pt-BR,pt;q=0.9'
          }
        });
        if (response.ok) {
          const data = await response.json();
          if (data && data.length > 0) {
            const { lat, lon } = data[0];
            const coords = `${lat},${lon}`;
            setForm(prev => ({ ...prev, coordenadas_gps: coords }));
            setSnackbar({
              open: true,
              message: '📍 Coordenadas GPS localizadas e preenchidas automaticamente para o endereço selecionado!',
              severity: 'success'
            });
            break; // Encontrou as coordenadas, interrompe as tentativas
          }
        }
      } catch (error) {
        console.error('Erro ao buscar coordenadas via Nominatim:', error);
      }
    }
  };

  const handleOpenGoogleMaps = () => {
    if (form.coordenadas_gps && form.coordenadas_gps.trim() !== '') {
      window.open(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(form.coordenadas_gps.trim())}`, '_blank');
      return;
    }

    if (form.endereco_id) {
      const selectedAddress = clientAddresses.find(end => end.id === Number(form.endereco_id));
      if (selectedAddress) {
        const addressStr = `${selectedAddress.endereco}, ${selectedAddress.numero}, ${selectedAddress.bairro || ''}, ${selectedAddress.municipio} - ${selectedAddress.uf}, Brasil`;
        window.open(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(addressStr)}`, '_blank');
      }
    }
  };

  const handleInputChange = (field: string, value: any) => {
    let processedValue = value;

    if (field === 'mac_address') {
      processedValue = formatMacAddress(value);
    }

    setForm(prev => {
      const newForm = { ...prev, [field]: processedValue };

      if (field === 'metodo_autenticacao') {
        if (value !== 'IP_MAC') {
          // Limpar MAC e IP se não for IP_MAC
          newForm.mac_address = '';
          newForm.assigned_ip = '';
        }
      }

      // Se mudar a interface ou classe IP, limpar o IP atribuído para forçar nova seleção automática
      if (field === 'interface_id' || field === 'ip_class_id' || field === 'router_id') {
        newForm.assigned_ip = '';
        if (field === 'router_id') {
          newForm.interface_id = undefined;
          newForm.ip_class_id = undefined;
        }
        if (field === 'interface_id') {
          newForm.ip_class_id = undefined;
        }
      }

      return newForm;
    });

    // Quando a data de início do contrato for alterada, preencher automaticamente a data de instalação se estiver vazia,
    // e também a data de início da cobrança se estiver vazia ou se era igual à data de início anterior.
    if (field === 'd_contrato_ini' && value) {
      setForm(prev => {
        const updates: any = {};
        if (!prev.data_instalacao) {
          updates.data_instalacao = value;
        }
        if (!prev.data_inicio_cobranca || prev.data_inicio_cobranca === prev.d_contrato_ini) {
          updates.data_inicio_cobranca = value;
        }
        return { ...prev, ...updates };
      });
    }

    // Buscar coordenadas se o endereço mudar
    if (field === 'endereco_id' && value) {
      fetchCoordinatesForAddress(value);
    }

    if (errors[field]) setErrors(prev => ({ ...prev, [field]: '' }));

    // Validar campos obrigatórios em tempo real
    setForm(currentForm => {
      validateRequiredFields({ ...currentForm, [field]: processedValue });
      return currentForm;
    });
  };


  const addAtivo = () => {
    setForm(prev => ({
      ...prev,
      ativos: [
        ...(prev.ativos || []),
        { tipo_equipamento: 'ROTEADOR', modelo: '', patrimonio: '', serial_number: '', login_acesso: 'admin', senha_acesso: '', is_comodato: true, observacoes: '' }
      ]
    }));
  };

  const removeAtivo = (index: number) => {
    setForm(prev => ({
      ...prev,
      ativos: (prev.ativos || []).filter((_, i) => i !== index)
    }));
  };

  const handleAtivoChange = (index: number, field: keyof AtivoContrato, value: any) => {
    setForm(prev => {
      const newAtivos = [...(prev.ativos || [])];
      newAtivos[index] = { ...newAtivos[index], [field]: value };
      return { ...prev, ativos: newAtivos };
    });
  };

  const validateRequiredFields = (currentForm: any) => {
    const newErrors: Record<string, string> = { ...errors };

    // Campos sempre obrigatórios
    if (!currentForm.endereco_id) {
      newErrors.endereco_id = 'Endereço de instalação é obrigatório';
    } else {
      delete newErrors.endereco_id;
    }

    if (!currentForm.tipo_conexao) {
      newErrors.tipo_conexao = 'Tipo de conexão é obrigatório';
    } else {
      delete newErrors.tipo_conexao;
    }

    if (!currentForm.responsavel_tecnico || currentForm.responsavel_tecnico.trim() === '') {
      newErrors.responsavel_tecnico = 'Responsável técnico é obrigatório';
    } else {
      delete newErrors.responsavel_tecnico;
    }

    // CTO obrigatória para fibra
    if (currentForm.tipo_conexao === 'FIBRA') {
      if (!currentForm.cto_nome || currentForm.cto_nome.trim() === '') {
        newErrors.cto_nome = 'Caixa de Atendimento (CTO) é obrigatória para conexões de Fibra';
      } else {
        delete newErrors.cto_nome;
      }
    } else {
      delete newErrors.cto_nome;
    }

    // Campos condicionais para rede
    if (currentForm.router_id) {
      if (currentForm.metodo_autenticacao === 'RADIUS') {
        // Para RADIUS, interface_id e ip_class_id são opcionais e não serão validados
        delete newErrors.interface_id;
        delete newErrors.ip_class_id;
        delete newErrors.mac_address;
        delete newErrors.assigned_ip;

        if (!currentForm.pppoe_username || currentForm.pppoe_username.trim() === '') {
          newErrors.pppoe_username = 'Username PPPoE é obrigatório para autenticação RADIUS';
        } else {
          delete newErrors.pppoe_username;
        }

        if (!currentForm.pppoe_password || currentForm.pppoe_password.trim() === '') {
          newErrors.pppoe_password = 'Password PPPoE é obrigatório para autenticação RADIUS';
        } else {
          delete newErrors.pppoe_password;
        }
      } else {
        // Limpar possíveis erros de username/password se mudar do método PPPOE/RADIUS
        if (currentForm.metodo_autenticacao !== 'PPPOE') {
          delete newErrors.pppoe_username;
          delete newErrors.pppoe_password;
        }

        if (!currentForm.interface_id) {
          newErrors.interface_id = 'Interface é obrigatória';
        } else {
          delete newErrors.interface_id;
        }

        // Validação condicional baseada no método de autenticação
        if (currentForm.metodo_autenticacao === 'IP_MAC') {
          if (!currentForm.interface_id) {
            newErrors.interface_id = 'Interface é obrigatória quando IP + MAC é selecionado';
          } else {
            delete newErrors.interface_id;
          }

          if (!currentForm.ip_class_id) {
            newErrors.ip_class_id = 'Classe IP é obrigatória quando IP + MAC é selecionado';
          } else {
            delete newErrors.ip_class_id;
          }

          if (!currentForm.mac_address || currentForm.mac_address.trim() === '') {
            newErrors.mac_address = 'Endereço MAC é obrigatório quando IP + MAC é selecionado';
          } else {
            delete newErrors.mac_address;
          }

          // Só validar IP se houver IPs disponíveis (campo habilitado)
          if (currentForm.ip_class_id && availableIPs.length > 0) {
            if (!currentForm.assigned_ip || currentForm.assigned_ip.trim() === '' || currentForm.assigned_ip === undefined || currentForm.assigned_ip === null) {
              newErrors.assigned_ip = 'IP Atribuído é obrigatório quando IP + MAC é selecionado';
            } else {
              delete newErrors.assigned_ip;
            }
          } else {
            // Se não há IPs disponíveis, limpar erro
            delete newErrors.assigned_ip;
          }
        } else if (currentForm.metodo_autenticacao === 'PPPOE') {
          if (!currentForm.interface_id) {
            newErrors.interface_id = 'Interface é obrigatória quando PPPoE é selecionado';
          } else {
            delete newErrors.interface_id;
          }

          if (!currentForm.pppoe_username || currentForm.pppoe_username.trim() === '') {
            newErrors.pppoe_username = 'Username PPPoE é obrigatório quando PPPoE é selecionado';
          } else {
            delete newErrors.pppoe_username;
          }

          if (!currentForm.pppoe_password || currentForm.pppoe_password.trim() === '') {
            newErrors.pppoe_password = 'Password PPPoE é obrigatório quando PPPoE é selecionado';
          } else {
            delete newErrors.pppoe_password;
          }

          // Para PPPoE, classe IP, MAC e IP atribuído não são necessários
          delete newErrors.ip_class_id;
          delete newErrors.mac_address;
          delete newErrors.assigned_ip;
        } else {
          // Para outros métodos, apenas interface pode ser necessária
          if (!currentForm.interface_id) {
            newErrors.interface_id = 'Interface é obrigatória';
          } else {
            delete newErrors.interface_id;
          }

          delete newErrors.ip_class_id;
          delete newErrors.mac_address;
          delete newErrors.assigned_ip;
        }
      }
    } else {
      // Limpar erros se router não estiver selecionado
      delete newErrors.interface_id;
      delete newErrors.ip_class_id;
      delete newErrors.mac_address;
      delete newErrors.assigned_ip;
      delete newErrors.pppoe_username;
      delete newErrors.pppoe_password;
    }

    setErrors(newErrors);
  };

  // Validar campos obrigatórios quando o form muda
  useEffect(() => {
    if (openForm) {
      validateRequiredFields(form);
    }
  }, [form, openForm]);

  const validateForm = (): Record<string, string> => {
    const newErrors: Record<string, string> = {};

    // Número do contrato (opcional, mas se informado deve ter pelo menos 1 caractere)
    if (form.numero_contrato && String(form.numero_contrato).trim().length < 1) {
      newErrors.numero_contrato = 'Número do contrato deve ter pelo menos 1 caractere';
    }

    // Cliente obrigatório
    if (!form.cliente_id) {
      newErrors.cliente_id = 'Cliente é obrigatório';
    }

    // Serviço obrigatório
    if (!form.servico_id) {
      newErrors.servico_id = 'Plano de internet é obrigatório';
    }

    // Valor unitário obrigatório e positivo
    if (form.valor_unitario === undefined || form.valor_unitario === null || form.valor_unitario <= 0) {
      newErrors.valor_unitario = 'Valor unitário é obrigatório e deve ser maior que zero';
    }

    // Quantidade obrigatória e positiva
    if (form.quantidade === undefined || form.quantidade === null || form.quantidade <= 0) {
      newErrors.quantidade = 'Quantidade é obrigatória e deve ser maior que zero';
    }

    // Dia de vencimento obrigatório
    if (form.dia_vencimento === undefined || form.dia_vencimento === null) {
      newErrors.dia_vencimento = 'Dia de vencimento é obrigatório';
    } else {
      const dia = Number(form.dia_vencimento);
      if (dia < 1 || dia > 31) {
        newErrors.dia_vencimento = 'Dia de vencimento deve estar entre 1 e 31';
      }
    }

    // Data de início do contrato obrigatória
    if (!form.d_contrato_ini) {
      newErrors.d_contrato_ini = 'Data de início do contrato é obrigatória';
    }

    // Data de fim do contrato obrigatória
    if (!form.d_contrato_fim) {
      newErrors.d_contrato_fim = 'Data de fim do contrato é obrigatória';
    }

    // Data de início da cobrança obrigatória
    if (!form.data_inicio_cobranca) {
      newErrors.data_inicio_cobranca = 'Data de início da cobrança é obrigatória';
    }

    // Data de instalação obrigatória
    if (!form.data_instalacao) {
      newErrors.data_instalacao = 'Data de instalação é obrigatória';
    }

    // Endereço de instalação obrigatório
    if (!form.endereco_id) {
      newErrors.endereco_id = 'Endereço de instalação é obrigatório';
    }

    // Tipo de conexão obrigatório
    if (!form.tipo_conexao) {
      newErrors.tipo_conexao = 'Tipo de conexão é obrigatório';
    }

    // Responsável técnico obrigatório
    if (!form.responsavel_tecnico || form.responsavel_tecnico.trim() === '') {
      newErrors.responsavel_tecnico = 'Responsável técnico é obrigatório';
    }

    // CTO obrigatória para fibra
    if (form.tipo_conexao === 'FIBRA') {
      if (!form.cto_nome || form.cto_nome.trim() === '') {
        newErrors.cto_nome = 'Caixa de Atendimento (CTO) é obrigatória para conexões de Fibra';
      }
    }

    // Validação condicional para rede
    if (form.router_id) {
      // Para RADIUS, interface e classe IP são opcionais
      if (form.metodo_autenticacao === 'RADIUS') {
        delete newErrors.interface_id;
        delete newErrors.ip_class_id;
        delete newErrors.mac_address;
        // assigned_ip (IP Fixo) é opcional para RADIUS, não validar
      }
      // Para IP_MAC, interface e classe IP são obrigatórios
      else if (form.metodo_autenticacao === 'IP_MAC') {
        if (!form.interface_id) {
          newErrors.interface_id = 'Interface é obrigatória quando IP + MAC é selecionado';
        }
        if (!form.ip_class_id) {
          newErrors.ip_class_id = 'Classe IP é obrigatória quando IP + MAC é selecionado';
        }
        if (!form.mac_address || form.mac_address.trim() === '') {
          newErrors.mac_address = 'Endereço MAC é obrigatório quando IP + MAC é selecionado';
        }
        // Só validar IP se houver IPs disponíveis (campo habilitado)
        if (form.ip_class_id && availableIPs.length > 0) {
          if (!form.assigned_ip || form.assigned_ip.trim() === '' || form.assigned_ip === undefined || form.assigned_ip === null) {
            newErrors.assigned_ip = 'IP Atribuído é obrigatório quando IP + MAC é selecionado';
          }
        }
      }
      // Para PPPoE, apenas interface é obrigatória (para saber onde está o servidor PPPoE)
      else if (form.metodo_autenticacao === 'PPPOE') {
        if (!form.interface_id) {
          newErrors.interface_id = 'Interface é obrigatória quando PPPoE é selecionado';
        }
        // Classe IP, MAC e IP atribuído não são necessários para PPPoE
        delete newErrors.ip_class_id;
        delete newErrors.mac_address;
        delete newErrors.assigned_ip;
      }
      // Para outros métodos, manter validação básica se necessário
      else {
        if (!form.interface_id) {
          newErrors.interface_id = 'Interface é obrigatória';
        }
        delete newErrors.ip_class_id;
        delete newErrors.mac_address;
        delete newErrors.assigned_ip;
      }
    }

    // Validar campos PPPoE se o método for PPPOE ou RADIUS
    if (form.metodo_autenticacao === 'PPPOE' || form.metodo_autenticacao === 'RADIUS') {
      if (!form.pppoe_username || form.pppoe_username.trim() === '') {
        newErrors.pppoe_username = `Username PPPoE é obrigatório quando ${form.metodo_autenticacao} é selecionado`;
      }

      if (!form.pppoe_password || form.pppoe_password.trim() === '') {
        newErrors.pppoe_password = `Password PPPoE é obrigatório quando ${form.metodo_autenticacao} é selecionado`;
      }
    } else {
      delete newErrors.pppoe_username;
      delete newErrors.pppoe_password;
    }

    // Validação de datas: d_contrato_fim deve ser maior ou igual a d_contrato_ini
    if (form.d_contrato_ini && form.d_contrato_fim) {
      const dataIni = new Date(form.d_contrato_ini);
      const dataFim = new Date(form.d_contrato_fim);
      if (dataFim < dataIni) {
        newErrors.d_contrato_fim = 'Data fim deve ser maior ou igual à data início';
      }
    }

    setErrors(newErrors);

    // Navegar para a aba com erro
    if (Object.keys(newErrors).length > 0) {
      const errorFields = Object.keys(newErrors);

      // Campos por aba
      const dadosPlanoFields = [
        'numero_contrato', 'cliente_id', 'servico_id', 'periodicidade', 'dia_emissao',
        'd_contrato_ini', 'd_contrato_fim', 'data_inicio_cobranca', 'dia_vencimento', 'quantidade', 'valor_unitario',
        'auto_emit', 'auto_emit_nfcom', 'is_active', 'status'
      ];

      const redeFields = ['router_id', 'interface_id', 'ip_class_id', 'mac_address', 'assigned_ip', 'metodo_autenticacao', 'pppoe_username', 'pppoe_password'];

      const cobrancaFields = [
        'periodo_carencia', 'multa_atraso_percentual', 'taxa_instalacao',
        'taxa_instalacao_paga', 'sla_garantido', 'subscription_id'
      ];

      const instalacaoFields = [
        'endereco_id', 'tipo_conexao', 'coordenadas_gps', 'data_instalacao', 'responsavel_tecnico',
        'velocidade_garantida', 'onu_serial', 'onu_modelo', 'onu_sinal', 'olt_nome', 'olt_pon',
        'cto_nome', 'cto_porta', 'metragem_drop', 'vlan_id'
      ];

      if (errorFields.some(field => dadosPlanoFields.includes(field))) {
        setTabValue(0);
      } else if (errorFields.some(field => redeFields.includes(field))) {
        setTabValue(1);
      } else if (errorFields.some(field => cobrancaFields.includes(field))) {
        setTabValue(2);
      } else if (errorFields.some(field => instalacaoFields.includes(field))) {
        setTabValue(3);
      }
    }

    return newErrors;
  };

  const submit = async () => {
    const validationErrors = validateForm();
    if (Object.keys(validationErrors).length > 0) {
      const errorMessages = Object.values(validationErrors).filter(msg => msg);
      const errorMessage = errorMessages.length > 0
        ? `Por favor, corrija os seguintes erros: ${errorMessages.join('; ')}`
        : 'Por favor, corrija os erros do formulário antes de continuar.';
      setSnackbar({ open: true, message: errorMessage, severity: 'warning' });
      return;
    }
    if (!activeCompany) return;
    try {
      console.log('Form data before filtering:', form);
      console.log('Form entries:', Object.entries(form));
      if (editing) {
        // Filtrar apenas campos com valores válidos para evitar erros do Pydantic
        const contractData = Object.fromEntries(
          Object.entries(form).filter(([key, value]) => {
            const requiredFields = ['cliente_id', 'servico_id', 'valor_unitario', 'quantidade', 'dia_emissao', 'd_contrato_ini', 'd_contrato_fim', 'data_inicio_cobranca', 'data_instalacao'];
            if (requiredFields.includes(key)) {
              return true; // Sempre incluir campos obrigatórios
            }

            // Para outros campos, filtrar valores vazios/inválidos
            if (value === undefined || value === null || value === '') return false;
            if (typeof value === 'string' && value.trim() === '') return false;
            if (typeof value === 'number' && isNaN(value)) return false;

            return true;
          })
        );
        console.log('Contract data after filtering (update):', contractData);
        console.log('Contract data JSON:', JSON.stringify(contractData));
        await contratoService.updateContrato(activeCompany.id, editing.id, contractData);
        setSnackbar({ open: true, message: 'Contrato atualizado com sucesso!', severity: 'success' });
      } else {
        // Filtrar apenas campos com valores válidos para evitar erros do Pydantic
        const contractData = Object.fromEntries(
          Object.entries(form).filter(([key, value]) => {
            const requiredFields = ['cliente_id', 'servico_id', 'valor_unitario', 'quantidade', 'dia_emissao', 'd_contrato_ini', 'd_contrato_fim', 'data_inicio_cobranca', 'data_instalacao'];
            if (requiredFields.includes(key)) {
              return true; // Sempre incluir campos obrigatórios
            }

            // Para outros campos, filtrar valores vazios/inválidos
            if (value === undefined || value === null || value === '') return false;
            if (typeof value === 'string' && value.trim() === '') return false;
            if (typeof value === 'number' && isNaN(value)) return false;

            return true;
          })
        );
        console.log('Contract data after filtering (create):', contractData);
        console.log('Contract data JSON:', JSON.stringify(contractData));
        const createdContrato = await contratoService.createContrato(activeCompany.id, contractData);

        setSnackbar({ open: true, message: 'Contrato criado com sucesso!', severity: 'success' });
      }

      // Salvar dados técnicos no localStorage para facilitar o próximo contrato
      const technicalData = {
        dia_emissao: form.dia_emissao,
        dia_vencimento: form.dia_vencimento,
        periodicidade: form.periodicidade,
        valor_unitario: form.valor_unitario,
        quantidade: form.quantidade,
        auto_emit: form.auto_emit,
        auto_emit_nfcom: form.auto_emit_nfcom,
        tipo_conexao: form.tipo_conexao,
        metodo_autenticacao: form.metodo_autenticacao,
        router_id: form.router_id,
        interface_id: form.interface_id,
        ip_class_id: form.ip_class_id,
        status: form.status,
        is_active: form.is_active,
        velocidade_garantida: form.velocidade_garantida,
        sla_garantido: form.sla_garantido,
        responsavel_tecnico: form.responsavel_tecnico,
        olt_nome: form.olt_nome,
        olt_pon: form.olt_pon,
        cto_nome: form.cto_nome,
        vlan_id: form.vlan_id,
        onu_modelo: form.onu_modelo
      };
      localStorage.setItem('last_contract_tech_data', JSON.stringify(technicalData));

      handleCloseForm();
      load();
    } catch (e: any) {
      const msg = stringifyError(e) || 'Erro ao salvar contrato.';
      setSnackbar({ open: true, message: msg, severity: 'error' });
    }
  };

  const remove = async (c: Contrato) => {
    if (!activeCompany || !window.confirm('Tem certeza que deseja excluir este contrato?')) return;
    try {
      await contratoService.deleteContrato(activeCompany.id, c.id);
      setSnackbar({ open: true, message: 'Contrato excluído com sucesso!', severity: 'success' });
      load();
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao excluir contrato', severity: 'error' });
    }
  };

  const ativarServico = async (c: Contrato) => {
    if (!window.confirm('Tem certeza que deseja ativar este serviço? As regras serão enviadas para o router.')) return;
    try {
      await contratoService.ativarServico(c.id);
      setSnackbar({ open: true, message: 'Serviço ativado com sucesso!', severity: 'success' });
      load();
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao ativar serviço', severity: 'error' });
    }
  };

  const resetConnection = async (c: Contrato) => {
    if (!window.confirm('Tem certeza que deseja resetar a conexão deste cliente?')) return;
    try {
      await contratoService.resetConnection(c.id);
      setSnackbar({ open: true, message: 'Conexão resetada com sucesso!', severity: 'success' });
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao resetar conexão', severity: 'error' });
    }
  };

  const syncRouter = async (c: Contrato) => {
    if (!window.confirm('Deseja realizar uma sincronização completa com o roteador? Isso irá remover configurações antigas e re-aplicar as atuais.')) return;
    try {
      await contratoService.syncRouter(c.id);
      setSnackbar({ open: true, message: 'Configurações sincronizadas com sucesso!', severity: 'success' });
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao sincronizar com roteador', severity: 'error' });
    }
  };

  const suspenderServico = async (c: Contrato) => {
    if (!window.confirm('Tem certeza que deseja bloquear/suspender este serviço? O cliente será redirecionado para a página de aviso.')) return;
    try {
      await contratoService.suspenderServico(c.id);
      setSnackbar({ open: true, message: 'Serviço bloqueado com sucesso!', severity: 'warning' });
      load();
    } catch (e) {
      setSnackbar({ open: true, message: 'Erro ao bloquear serviço', severity: 'error' });
    }
  };

  const handleReiniciarAssinatura = async (id: number) => {
    if (!window.confirm('Tem certeza que deseja REINICIAR a assinatura deste contrato? O link anterior será invalidado e os dados da assinatura atual serão apagados.')) return;
    try {
      setLoading(true);
      await contratoService.reiniciarAssinatura(id);
      setSnackbar({
        open: true,
        message: 'Assinatura reiniciada! Agora você pode enviar o novo link por e-mail para o cliente.',
        severity: 'success'
      });
      load();
    } catch (e: any) {
      setSnackbar({
        open: true,
        message: e.response?.data?.detail || 'Erro ao reiniciar assinatura',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  if (!activeCompany) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6">Nenhuma empresa ativa</Typography>
        <Typography variant="body2" color="text.secondary">Selecione uma empresa para gerenciar contratos.</Typography>
      </Paper>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4, flexWrap: 'wrap' }}>
        <Typography
          component="h1"
          variant="h4"
          sx={{
            fontWeight: 'bold',
            mr: 2,
            mb: { xs: 2, sm: 0 },
            fontSize: { xs: '1.5rem', sm: '2.125rem' }
          }}
        >
          Contratos de Internet
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {hasPermission('contract_manage') && (
            <Button
              variant="contained"
              startIcon={<PlusIcon className="w-5 h-5" />}
              sx={{ py: 1.5, width: { xs: '100%', sm: 'auto' } }}
              onClick={() => handleOpenForm()}
            >
              Novo Contrato
            </Button>
          )}
          {hasPermission('contract_manage') && selectedContracts.length > 0 && (
            <Button
              variant="contained"
              color="success"
              startIcon={bulkEmitLoading ? <CircularProgress size={16} color="inherit" /> : <DocumentTextIcon className="w-5 h-5" />}
              sx={{ py: 1.5, width: { xs: '100%', sm: 'auto' } }}
              onClick={handleBulkEmitNFCom}
              disabled={bulkEmitLoading}
            >
              {bulkEmitLoading ? 'Emitindo...' : `Emitir NFCom (${selectedContracts.length}) - R$ ${selectedContractsTotalValue.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            </Button>
          )}
          {hasPermission('contract_manage') && selectedContracts.some(id => contratos.find(c => c.id === id)?.status === 'SUSPENSO') && (
            <Button
              variant="contained"
              color="warning"
              startIcon={bulkUnlockLoading ? <CircularProgress size={16} color="inherit" /> : <PlayIcon className="w-5 h-5" />}
              sx={{ py: 1.5, width: { xs: '100%', sm: 'auto' } }}
              onClick={handleBulkUnlock}
              disabled={bulkUnlockLoading}
            >
              {bulkUnlockLoading ? 'Desbloqueando...' : `Desbloquear (${selectedContracts.filter(id => contratos.find(c => c.id === id)?.status === 'SUSPENSO').length})`}
            </Button>
          )}
        </Box>
      </Box>

      <Paper sx={{ p: { xs: 1, sm: 2 }, backgroundColor: 'grey.50', minHeight: 'calc(100vh - 250px)' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
          <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center', flexWrap: 'wrap' }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', color: 'text.primary' }}>Contratos Cadastrados</Typography>
            <Box sx={{ display: 'inline-flex', borderRadius: 2, p: 0.5, bgcolor: 'grey.200' }}>
              <Button
                size="small"
                variant={viewMode === 'table' ? 'contained' : 'text'}
                color="inherit"
                sx={{
                  borderRadius: 1.5,
                  textTransform: 'none',
                  fontWeight: 'bold',
                  py: 0.5,
                  px: 1.5,
                  fontSize: '0.75rem',
                  boxShadow: viewMode === 'table' ? '0px 1px 3px rgba(0,0,0,0.1)' : 'none',
                  bgcolor: viewMode === 'table' ? '#fff' : 'transparent',
                  '&:hover': { bgcolor: viewMode === 'table' ? '#fff' : 'grey.300' }
                }}
                onClick={() => setViewMode('table')}
                startIcon={<span style={{ fontSize: '0.9rem' }}>📋</span>}
              >
                Lista
              </Button>
              <Button
                size="small"
                variant={viewMode === 'map' ? 'contained' : 'text'}
                color="inherit"
                sx={{
                  borderRadius: 1.5,
                  textTransform: 'none',
                  fontWeight: 'bold',
                  py: 0.5,
                  px: 1.5,
                  fontSize: '0.75rem',
                  boxShadow: viewMode === 'map' ? '0px 1px 3px rgba(0,0,0,0.1)' : 'none',
                  bgcolor: viewMode === 'map' ? '#fff' : 'transparent',
                  '&:hover': { bgcolor: viewMode === 'map' ? '#fff' : 'grey.300' }
                }}
                onClick={() => setViewMode('map')}
                startIcon={<span style={{ fontSize: '0.9rem' }}>🗺️</span>}
              >
                Mapa
              </Button>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
            <TextField
              size="small"
              placeholder="Buscar contratos..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <MagnifyingGlassIcon className="w-4 h-4 text-gray-400 mr-2" />
                ),
              }}
              sx={{ minWidth: 200 }}
            />
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
              <TextField
                size="small"
                type="number"
                placeholder="Dia venc. min"
                value={diaVencimentoMin}
                onChange={(e) => setDiaVencimentoMin(e.target.value === '' ? '' : Number(e.target.value))}
                inputProps={{ min: 1, max: 31 }}
                sx={{ minWidth: { xs: 90, sm: 150 } }}
              />
              <TextField
                size="small"
                type="number"
                placeholder="Dia venc. max"
                value={diaVencimentoMax}
                onChange={(e) => setDiaVencimentoMax(e.target.value === '' ? '' : Number(e.target.value))}
                inputProps={{ min: 1, max: 31 }}
                sx={{ minWidth: { xs: 90, sm: 150 } }}
              />
              <TextField
                select
                size="small"
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                sx={{ minWidth: 150 }}
                SelectProps={{ displayEmpty: true }}
              >
                <MenuItem value="">Todos os Status</MenuItem>
                <MenuItem value="ATIVO">Ativo</MenuItem>
                <MenuItem value="SUSPENSO">Suspenso</MenuItem>
                <MenuItem value="CANCELADO">Cancelado</MenuItem>
                <MenuItem value="PENDENTE_INSTALACAO">Pend. Instalação</MenuItem>
                <MenuItem value="AGUARDANDO_ASSINATURA">Aguard. Assinatura</MenuItem>
              </TextField>
            </Box>
          </Box>
        </Box>
        {loading ? (
          <Box sx={{ textAlign: 'center', p: 4 }}><CircularProgress /></Box>
        ) : contratos.length === 0 ? (
          <Box sx={{ textAlign: 'center', p: 4, backgroundColor: '#fff', borderRadius: 2 }}>
            <DocumentTextIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <Typography variant="h6" gutterBottom>
              {searchTerm ? 'Nenhum contrato encontrado' : 'Nenhum contrato cadastrado'}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {searchTerm ? 'Tente ajustar os termos da busca' : 'Comece cadastrando seu primeiro contrato de internet.'}
            </Typography>
            {!searchTerm && (
              <Button variant="outlined" startIcon={<PlusIcon className="w-5 h-5" />} onClick={() => handleOpenForm()}>
                Cadastrar Primeiro Contrato
              </Button>
            )}
          </Box>
        ) : viewMode === 'map' ? (
          renderContractMap()
        ) : isMobile ? (
          renderContractCards()
        ) : (
          renderContractTable()
        )}

        {!loading && contratos.length > 0 && viewMode === 'table' && renderPagination()}
      </Paper>

      {openForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-0 sm:p-4">
          <div
            className="absolute inset-0 bg-gradient-to-br from-black/60 via-black/50 to-black/70 backdrop-blur-md"
            onClick={handleCloseForm}
          />
          <div className={`relative bg-gradient-to-br from-white via-gray-50 to-blue-50 border border-borderLight shadow-modern-hover w-full max-w-sm sm:max-w-md lg:max-w-4xl h-full sm:h-auto max-h-screen sm:max-h-[90vh] flex flex-col overflow-hidden ${isMobile ? 'rounded-none' : 'rounded-2xl sm:rounded-3xl'}`}>
            <div className="flex items-center justify-between p-3 sm:p-6 border-b border-borderLight bg-gradient-to-r from-white to-blue-50/30 flex-shrink-0">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-lg sm:rounded-xl flex items-center justify-center shadow">
                  <DocumentTextIcon className="w-4 h-4 text-white" />
                </div>
                <div>
                  <h2 className="text-base sm:text-xl font-bold text-text bg-gradient-to-r from-indigo-700 to-indigo-600 bg-clip-text text-transparent">
                    {viewOnly ? 'Visualizar Contrato' : (editing ? 'Editar Contrato' : 'Novo Contrato')}
                  </h2>
                  <p className="text-xs sm:text-sm text-textLight hidden sm:block">Configure as informações e os termos do contrato de internet do cliente.</p>
                </div>
              </div>
              <button
                onClick={handleCloseForm}
                className="p-2 hover:bg-red-50 rounded-xl transition-all duration-200 flex items-center justify-center flex-shrink-0 shadow-sm hover:shadow-md group"
                style={{ minWidth: 40, minHeight: 40 }}
                aria-label="Fechar"
              >
                <XMarkIcon className="w-5 h-5 sm:w-6 sm:h-6 text-red-400 group-hover:text-red-600 transition-colors" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-3 sm:p-6 min-h-0 bg-gradient-to-b from-white to-gray-50/30">
              {/* Tabs for better organization */}
              <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
                <Tabs
                  value={tabValue}
                  onChange={(_, newValue) => setTabValue(newValue)}
                  aria-label="contrato tabs"
                  variant="scrollable"
                  scrollButtons="auto"
                  allowScrollButtonsMobile={isMobile}
                  sx={isMobile ? {
                    minHeight: 48,
                    '& .MuiTabs-flexContainer': {
                      gap: 0.5,
                    },
                    '& .MuiTab-root': {
                      minWidth: 'auto',
                      px: 1.5,
                      fontSize: '0.8rem',
                    }
                  } : undefined}
                >
                  <Tab label={isMobile ? "📋 Contrato" : "📋 Dados do Contrato"} />
                  <Tab label={isMobile ? "🌐 Rede" : "🌐 Configuração de Rede"} />
                  <Tab label={isMobile ? "💰 Cobrança" : "💰 Cobrança e SLA"} />
                  <Tab label={isMobile ? "🛠️ Instalação" : "🛠️ Instalação e Ativos"} />
                </Tabs>
              </Box>

              {/* Tab Content */}
              {tabValue === 0 && (
                <div className="space-y-4 sm:space-y-6">
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-blue-100">
                    <h3 className="text-lg sm:text-xl font-bold text-blue-800 mb-1 sm:mb-2 flex items-center">
                      <span className="mr-2 text-base sm:text-lg">📋</span>
                      <span className="text-sm sm:text-base">Identificação</span>
                    </h3>
                    <p className="text-xs sm:text-sm text-blue-600 hidden sm:block">
                      Informações básicas do contrato de internet.
                    </p>
                    <div className="mt-3 sm:mt-4">
                      <TextField
                        label="Número do Contrato"
                        value={form.numero_contrato || ''}
                        onChange={e => handleInputChange('numero_contrato', e.target.value)}
                        fullWidth
                        size="small"
                        placeholder={!editing ? "Deixe em branco para gerar automaticamente" : undefined}
                        error={!!errors.numero_contrato}
                        helperText={errors.numero_contrato || (!editing && !form.numero_contrato ? "Será gerado automaticamente se deixado em branco" : undefined)}
                      />
                    </div>
                  </div>

                  <div className="bg-gradient-to-r from-cyan-50 to-blue-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-cyan-100">
                    <h3 className="text-lg sm:text-xl font-bold text-cyan-800 mb-1 sm:mb-2 flex items-center">
                      <span className="mr-2 text-base sm:text-lg">👤</span>
                      <span className="text-sm sm:text-base">Cliente e Plano</span>
                    </h3>
                    <p className="text-xs sm:text-sm text-cyan-600 hidden sm:block">
                      Selecione o cliente e o plano de internet contratado.
                    </p>
                    <div className="mt-3 sm:mt-4 space-y-3 sm:space-y-4">
                      <Autocomplete
                        options={clients}
                        getOptionLabel={(option) => option.nome_razao_social || ''}
                        isOptionEqualToValue={(option, value) => option.id === value.id}
                        renderOption={(props, option) => (
                          <Box component="li" {...props} sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', textAlign: 'left', py: 1, width: '100%' }}>
                            <Typography variant="body1" sx={{ width: '100%', textAlign: 'left' }}>{option.nome_razao_social}</Typography>
                            <Typography variant="caption" color="text.secondary" sx={{ width: '100%', textAlign: 'left' }}>
                              {clientService.formatCpfCnpj(option.cpf_cnpj)}
                            </Typography>
                          </Box>
                        )}
                        value={clients.find(cl => cl.id === form.cliente_id) || null}
                        onChange={async (_, value) => {
                          handleInputChange('cliente_id', value?.id || undefined);

                          if (value) {
                            // Garantir que o cliente selecionado permaneça na lista de opções
                            setClients(prev => {
                              const exists = prev.some(c => c.id === value.id);
                              if (exists) return prev;
                              return [value, ...prev];
                            });

                            if (activeCompany) {
                              try {
                                const clientDetails = await clientService.getClientById(value.id, activeCompany.id);
                                if (clientDetails.enderecos && clientDetails.enderecos.length > 0) {
                                  setClientAddresses(clientDetails.enderecos);

                                  if (!form.endereco_id) {
                                    const primary = clientDetails.enderecos.find((e: any) => e.is_principal) || clientDetails.enderecos[0];
                                    handleInputChange('endereco_id', primary.id);
                                    fetchCoordinatesForAddress(primary.id, clientDetails.enderecos);
                                  }
                                } else {
                                  setClientAddresses([]);
                                }
                              } catch (error) {
                                console.error('Erro ao buscar endereços do cliente:', error);
                                setClientAddresses([]);
                              }
                            }
                          } else {
                            // Limpar o endereço se nenhum cliente foi selecionado
                            handleInputChange('endereco_id', undefined);
                            setClientAddresses([]);
                          }
                        }}
                        inputValue={clientSearch}
                        onInputChange={(_, value, reason) => {
                          setClientSearch(value);
                          if (reason === 'input') {
                            if (clientSearchTimer.current) clearTimeout(clientSearchTimer.current);

                            clientSearchTimer.current = setTimeout(() => {
                              if (value.length >= 2) {
                                loadClients(value);
                              } else if (value.length === 0) {
                                loadClients('');
                              }
                            }, 400);
                          }
                        }}
                        loading={clientLoading}
                        renderInput={(params) => {
                          const selectedClient = clients.find(cl => cl.id === form.cliente_id);
                          const dynamicLabel = selectedClient
                            ? `Cliente (${clientService.formatCpfCnpj(selectedClient.cpf_cnpj)}) *`
                            : "Cliente *";

                          return (
                            <TextField
                              {...params}
                              label={dynamicLabel}
                              error={!!errors.cliente_id}
                              helperText={errors.cliente_id || 'Digite ao menos 2 caracteres para buscar'}
                              size="small"
                            />
                          );
                        }}
                      />
                      <Autocomplete
                        openOnFocus
                        options={servicos}
                        getOptionLabel={(option) => `${option.codigo || ''} - ${option.descricao || ''}`}
                        value={servicos.find(s => s.id === form.servico_id) || null}
                        onChange={(_, value) => {
                          handleInputChange('servico_id', value?.id || undefined);

                          if (value) {
                            // Garantir que o serviço selecionado permaneça na lista de opções
                            setServicos(prev => {
                              const exists = prev.some(s => s.id === value.id);
                              if (exists) return prev;
                              return [value, ...prev];
                            });

                            // Preencher campos automaticamente com dados do serviço
                            handleInputChange('valor_unitario', value.valor_unitario !== undefined ? Number(value.valor_unitario) : 0);

                            // Preencher velocidade garantida baseada nas velocidades do plano
                            if (value.upload_speed || value.download_speed) {
                              const velocidade = [];
                              if (value.download_speed) velocidade.push(`${value.download_speed} Mbps ↓`);
                              if (value.upload_speed) velocidade.push(`${value.upload_speed} Mbps ↑`);
                              handleInputChange('velocidade_garantida', velocidade.join(' / '));
                            }

                            // Preencher periodicidade baseada no ciclo de cobrança do serviço
                            if (value.billing_cycle) {
                              const periodicidadeMap: { [key: string]: string } = {
                                'MENSAL': 'MENSAL',
                                'TRIMESTRAL': 'TRIMESTRAL',
                                'SEMESTRAL': 'SEMESTRAL',
                                'ANUAL': 'ANUAL',
                                'UNICA': 'UNICA'
                              };
                              handleInputChange('periodicidade', periodicidadeMap[value.billing_cycle] || 'MENSAL');
                            }

                            // Preencher período de carência baseado nos meses de fidelidade
                            if (value.fidelity_months) {
                              handleInputChange('periodo_carencia', value.fidelity_months);
                            }

                            // Preencher SLA garantido para planos de internet (padrão 99.9%)
                            if (value.tipo === 'PLANO_INTERNET') {
                              handleInputChange('sla_garantido', 99.9);
                            }

                            // Usar preço promocional se estiver ativo
                            if (value.promotional_active && value.promotional_price) {
                              handleInputChange('valor_unitario', value.promotional_price);
                            }

                            // Preencher data de início com hoje
                            if (!form.d_contrato_ini) {
                              const today = new Date().toISOString().split('T')[0];
                              handleInputChange('d_contrato_ini', today);
                            }

                            // Preencher data de fim baseada na fidelidade do plano
                            if (value.fidelity_months && value.fidelity_months > 0 && !form.d_contrato_fim) {
                              const startDate = form.d_contrato_ini ? new Date(form.d_contrato_ini) : new Date();
                              const endDate = new Date(startDate);
                              endDate.setMonth(endDate.getMonth() + value.fidelity_months);
                              handleInputChange('d_contrato_fim', endDate.toISOString().split('T')[0]);
                            }
                          }
                        }}
                        onInputChange={(_, value, reason) => {
                          if (reason === 'input') {
                            if (servicoSearchTimer.current) clearTimeout(servicoSearchTimer.current);

                            servicoSearchTimer.current = setTimeout(() => {
                              if (value.length >= 1) {
                                loadServicos(value);
                              } else if (value.length === 0) {
                                loadServicos('');
                              }
                            }, 400);
                          } else if (reason === 'clear') {
                            loadServicos('');
                          }
                        }}
                        loading={servicoLoading}
                        renderInput={(params) => (
                          <TextField
                            {...params}
                            label="Plano de Internet *"
                            error={!!errors.servico_id}
                            helperText={errors.servico_id || 'Selecione um plano'}
                            size="small"
                            inputProps={{
                              ...params.inputProps,
                              autoComplete: 'new-password', // Evita o autofill do navegador (ex: Chrome)
                            }}
                          />
                        )}
                      />
                    </div>
                  </div>

                  <div className="bg-gradient-to-r from-green-50 to-emerald-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-green-100">
                    <h3 className="text-lg sm:text-xl font-bold text-green-800 mb-1 sm:mb-2 flex items-center">
                      <span className="mr-2 text-base sm:text-lg">📅</span>
                      <span className="text-sm sm:text-base">Periodicidade</span>
                    </h3>
                    <p className="text-xs sm:text-sm text-green-600 hidden sm:block">
                      Configure a periodicidade e datas do contrato.
                    </p>
                    <div className="mt-3 sm:mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                      <FormControl fullWidth size="small">
                        <InputLabel>Periodicidade</InputLabel>
                        <Select
                          value={form.periodicidade || 'MENSAL'}
                          label="Periodicidade"
                          onChange={(e: SelectChangeEvent) => handleInputChange('periodicidade', e.target.value)}
                        >
                          <MenuItem value="MENSAL">Mensal</MenuItem>
                          <MenuItem value="SEMESTRAL">Semestral</MenuItem>
                          <MenuItem value="UNICA">Única</MenuItem>
                        </Select>
                      </FormControl>
                      <TextField
                        label="Dia de Emissão (1-31) *"
                        type="number"
                        value={form.dia_emissao || ''}
                        onChange={e => handleInputChange('dia_emissao', parseInt(e.target.value || '0') || undefined)}
                        fullWidth
                        size="small"
                        error={!!errors.dia_emissao}
                        helperText={errors.dia_emissao}
                        inputProps={{ min: 1, max: 31 }}
                      />
                      <TextField
                        label="Data Início Contrato"
                        type="date"
                        value={form.d_contrato_ini || ''}
                        onChange={e => handleInputChange('d_contrato_ini', e.target.value)}
                        fullWidth
                        size="small"
                        error={!!errors.d_contrato_ini}
                        helperText={errors.d_contrato_ini}
                        InputLabelProps={{ shrink: true }}
                      />
                      <TextField
                        label="Data Início Cobrança"
                        type="date"
                        value={form.data_inicio_cobranca || ''}
                        onChange={e => handleInputChange('data_inicio_cobranca', e.target.value)}
                        fullWidth
                        size="small"
                        error={!!errors.data_inicio_cobranca}
                        helperText={errors.data_inicio_cobranca}
                        InputLabelProps={{ shrink: true }}
                      />
                      <TextField
                        label="Data Fim Contrato"
                        type="date"
                        value={form.d_contrato_fim || ''}
                        onChange={e => handleInputChange('d_contrato_fim', e.target.value)}
                        fullWidth
                        size="small"
                        error={!!errors.d_contrato_fim}
                        helperText={errors.d_contrato_fim}
                        InputLabelProps={{ shrink: true }}
                      />
                      <TextField
                        label="Dia de Vencimento (1-31) *"
                        type="number"
                        value={form.dia_vencimento ?? ''}
                        onChange={e => handleInputChange('dia_vencimento', e.target.value === '' ? undefined : Number(e.target.value))}
                        fullWidth
                        size="small"
                        error={!!errors.dia_vencimento}
                        helperText={errors.dia_vencimento || "Dia do mês para vencimento da fatura. Usado na geração automática de faturas."}
                        inputProps={{ min: 1, max: 31 }}
                      />
                    </div>
                  </div>

                  <div className="bg-gradient-to-r from-amber-50 to-orange-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-amber-100">
                    <h3 className="text-lg sm:text-xl font-bold text-amber-800 mb-1 sm:mb-2 flex items-center">
                      <span className="mr-2 text-base sm:text-lg">💰</span>
                      <span className="text-sm sm:text-base">Valores</span>
                    </h3>
                    <p className="text-xs sm:text-sm text-amber-600 hidden sm:block">
                      Informe a quantidade e valor unitário do plano.
                    </p>
                    <div className="mt-3 sm:mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                      <TextField
                        label="Quantidade"
                        type="number"
                        value={form.quantidade || 1}
                        onChange={e => handleInputChange('quantidade', parseFloat(e.target.value || '1'))}
                        fullWidth
                        size="small"
                        error={!!errors.quantidade}
                        helperText={errors.quantidade}
                      />
                      <TextField
                        label="Valor Unitário *"
                        value={maskCurrency((form.valor_unitario || 0).toFixed(2))}
                        onChange={e => handleInputChange('valor_unitario', unmaskCurrency(e.target.value))}
                        fullWidth
                        size="small"
                        error={!!errors.valor_unitario}
                      />
                    </div>
                  </div>

                  <div className="bg-gradient-to-r from-purple-50 to-violet-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-purple-100">
                    <h3 className="text-lg sm:text-xl font-bold text-purple-800 mb-1 sm:mb-2 flex items-center">
                      <span className="mr-2 text-base sm:text-lg">⚙️</span>
                      <span className="text-sm sm:text-base">Configurações</span>
                    </h3>
                    <p className="text-xs sm:text-sm text-purple-600 hidden sm:block">
                      Configure as opções de emissão automática e status.
                    </p>
                    <div className="mt-3 sm:mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
                      <FormControl fullWidth size="small">
                        <InputLabel>Emissão Automática (Cobrança)</InputLabel>
                        <Select
                          value={form.auto_emit ? 'true' : 'false'}
                          label="Emissão Automática (Cobrança)"
                          onChange={(e: SelectChangeEvent) => handleInputChange('auto_emit', e.target.value === 'true')}
                        >
                          <MenuItem value="true">Sim</MenuItem>
                          <MenuItem value="false">Não</MenuItem>
                        </Select>
                      </FormControl>
                      <FormControl fullWidth size="small">
                        <InputLabel>Emissão Auto NFCom</InputLabel>
                        <Select
                          value={form.auto_emit_nfcom ? 'true' : 'false'}
                          label="Emissão Auto NFCom"
                          onChange={(e: SelectChangeEvent) => handleInputChange('auto_emit_nfcom', e.target.value === 'true')}
                        >
                          <MenuItem value="true">Sim</MenuItem>
                          <MenuItem value="false">Não</MenuItem>
                        </Select>
                      </FormControl>
                      <FormControl fullWidth size="small">
                        <InputLabel>Status</InputLabel>
                        <Select
                          value={form.is_active ? 'true' : 'false'}
                          label="Status"
                          onChange={(e: SelectChangeEvent) => handleInputChange('is_active', e.target.value === 'true')}
                        >
                          <MenuItem value="true">Ativo</MenuItem>
                          <MenuItem value="false">Inativo</MenuItem>
                        </Select>
                      </FormControl>
                    </div>
                  </div>

                  <div className="bg-gradient-to-r from-teal-50 to-cyan-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-teal-100">
                    <h3 className="text-lg sm:text-xl font-bold text-teal-800 mb-1 sm:mb-2 flex items-center">
                      <span className="mr-2 text-base sm:text-lg">🏢</span>
                      <span className="text-sm sm:text-base">Status do Contrato (ISP)</span>
                    </h3>
                    <p className="text-xs sm:text-sm text-teal-600 hidden sm:block">
                      Status específico para contratos de internet.
                    </p>
                    <div className="mt-3 sm:mt-4">
                      <FormControl fullWidth size="small">
                        <InputLabel>Status do Contrato</InputLabel>
                        <Select
                          value={form.status || 'ATIVO'}
                          label="Status do Contrato"
                          onChange={(e: SelectChangeEvent) => handleInputChange('status', e.target.value)}
                        >
                          <MenuItem value="ATIVO">Ativo</MenuItem>
                          <MenuItem value="SUSPENSO">Suspenso</MenuItem>
                          <MenuItem value="CANCELADO">Cancelado</MenuItem>
                          <MenuItem value="PENDENTE_INSTALACAO">Pendente de Instalação</MenuItem>
                          <MenuItem value="AGUARDANDO_ASSINATURA">Aguardando Assinatura</MenuItem>
                        </Select>
                      </FormControl>
                    </div>
                  </div>

                </div>
              )}

              {/* Fourth Tab - Installation and Assets */}
              {tabValue === 3 && (
                <div className="space-y-4 sm:space-y-6">
                  <div className="bg-gradient-to-r from-emerald-50 to-green-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-emerald-100">
                    <h3 className="text-lg sm:text-xl font-bold text-emerald-800 mb-1 sm:mb-2 flex items-center">
                      <span className="mr-2 text-base sm:text-lg">📍</span>
                      <span className="text-sm sm:text-base">Dados da Instalação</span>
                    </h3>
                    <p className="text-xs sm:text-sm text-emerald-600 hidden sm:block">
                      Dados específicos da instalação do serviço de internet no endereço do cliente.
                    </p>
                    <div className="mt-3 sm:mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                      <FormControl fullWidth size="small" error={!!errors.endereco_id}>
                        <InputLabel>Endereço de Instalação *</InputLabel>
                        <Select
                          value={form.endereco_id || ''}
                          label="Endereço de Instalação *"
                          onChange={(e: SelectChangeEvent<any>) => handleInputChange('endereco_id', e.target.value)}
                        >
                          {clientAddresses.map((end: any) => (
                            <MenuItem key={end.id} value={end.id}>
                              {`${end.endereco}, ${end.numero}${end.complemento ? ' - ' + end.complemento : ''} - ${end.bairro}, ${end.municipio}/${end.uf}`}
                            </MenuItem>
                          ))}
                        </Select>
                        {errors.endereco_id && <p className="text-sm text-red-600 mt-1">{errors.endereco_id}</p>}
                      </FormControl>
                      <FormControl fullWidth size="small" error={!!errors.tipo_conexao}>
                        <InputLabel>Tipo de Conexão</InputLabel>
                        <Select
                          value={form.tipo_conexao || ''}
                          label="Tipo de Conexão"
                          onChange={(e: SelectChangeEvent) => handleInputChange('tipo_conexao', e.target.value)}
                        >
                          <MenuItem value="FIBRA">Fibra Óptica</MenuItem>
                          <MenuItem value="RADIO">Rádio</MenuItem>
                          <MenuItem value="CABO">Cabo</MenuItem>
                          <MenuItem value="SATELITE">Satélite</MenuItem>
                          <MenuItem value="ADSL">ADSL</MenuItem>
                          <MenuItem value="OUTRO">Outro</MenuItem>
                        </Select>
                        {errors.tipo_conexao && <FormHelperText>{errors.tipo_conexao}</FormHelperText>}
                      </FormControl>
                      <TextField
                        label="Coordenadas GPS"
                        value={form.coordenadas_gps || ''}
                        onChange={e => handleInputChange('coordenadas_gps', e.target.value)}
                        fullWidth
                        size="small"
                        placeholder="latitude,longitude"
                        helperText="Ex: -23.550520,-46.633308"
                        disabled={viewOnly}
                        InputProps={{
                          endAdornment: (
                            <InputAdornment position="end">
                              {form.endereco_id && (
                                <Tooltip title="Buscar coordenadas automaticamente via API">
                                  <span>
                                    <IconButton
                                      size="small"
                                      onClick={() => fetchCoordinatesForAddress(form.endereco_id!)}
                                      disabled={viewOnly}
                                      color="secondary"
                                      sx={{ mr: 0.5 }}
                                    >
                                      ⚡
                                    </IconButton>
                                  </span>
                                </Tooltip>
                              )}
                              <Tooltip title={form.coordenadas_gps ? "Visualizar no Google Maps" : "Buscar endereço no Google Maps"}>
                                <span>
                                  <IconButton
                                    size="small"
                                    onClick={handleOpenGoogleMaps}
                                    disabled={!form.endereco_id && (!form.coordenadas_gps || form.coordenadas_gps.trim() === '')}
                                    color="primary"
                                  >
                                    📍
                                  </IconButton>
                                </span>
                              </Tooltip>
                            </InputAdornment>
                          )
                        }}
                      />
                      <TextField
                        label="Data de Instalação"
                        type="date"
                        value={form.data_instalacao || ''}
                        onChange={e => handleInputChange('data_instalacao', e.target.value)}
                        fullWidth
                        size="small"
                        error={!!errors.data_instalacao}
                        helperText={errors.data_instalacao}
                        InputLabelProps={{ shrink: true }}
                      />
                      <TextField
                        label="Responsável Técnico"
                        value={form.responsavel_tecnico || ''}
                        onChange={e => handleInputChange('responsavel_tecnico', e.target.value)}
                        fullWidth
                        size="small"
                        error={!!errors.responsavel_tecnico}
                        helperText={errors.responsavel_tecnico || "Nome do técnico responsável pela instalação"}
                      />
                      <TextField
                        label="Velocidade Garantida"
                        value={form.velocidade_garantida || ''}
                        onChange={e => handleInputChange('velocidade_garantida', e.target.value)}
                        fullWidth
                        size="small"
                        placeholder="Ex: 10M/10M"
                        helperText="Velocidade de download/upload garantida"
                        disabled={viewOnly}
                      />

                      {form.tipo_conexao === 'FIBRA' && (
                        <div className="col-span-1 sm:col-span-2 grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 mt-2 p-3 sm:p-4 bg-white/75 rounded-xl border border-emerald-100 shadow-sm">
                          <h4 className="col-span-1 sm:col-span-3 text-xs sm:text-sm font-bold text-emerald-800 border-b border-emerald-100/60 pb-1.5 flex items-center">
                            <span className="mr-1.5">🔌</span> Instalação da Fibra (FTTH)
                          </h4>
                          <TextField
                            label="Serial da ONU"
                            value={form.onu_serial || ''}
                            onChange={e => handleInputChange('onu_serial', e.target.value)}
                            fullWidth
                            size="small"
                            placeholder="Ex: FHTT12345678"
                            helperText="Número de série/MAC da ONU do cliente"
                            disabled={viewOnly}
                          />
                          <TextField
                            label="Modelo da ONU"
                            value={form.onu_modelo || ''}
                            onChange={e => handleInputChange('onu_modelo', e.target.value)}
                            fullWidth
                            size="small"
                            placeholder="Ex: Huawei EG8145V5"
                            helperText="Fabricante/modelo da ONU"
                            disabled={viewOnly}
                          />
                          <TextField
                            label="Sinal Óptico (dBm)"
                            value={form.onu_sinal || ''}
                            onChange={e => handleInputChange('onu_sinal', e.target.value)}
                            fullWidth
                            size="small"
                            placeholder="Ex: -22.5"
                            helperText="Potência óptica medida no cliente"
                            disabled={viewOnly}
                          />
                          <Autocomplete
                            freeSolo
                            options={olts}
                            getOptionLabel={(option) => typeof option === 'string' ? option : option.nome}
                            isOptionEqualToValue={(option, value) => {
                              if (typeof option === 'string' || typeof value === 'string') return option === value;
                              return option.id === value.id;
                            }}
                            value={olts.find(o => o.id === form.olt_id) || form.olt_nome || null}
                            onChange={(_event, newValue) => {
                              if (typeof newValue === 'string') {
                                setForm(prev => ({ ...prev, olt_nome: newValue, olt_id: undefined }));
                              } else if (newValue && newValue.id) {
                                setForm(prev => ({ ...prev, olt_nome: newValue.nome, olt_id: newValue.id, cto_id: undefined, cto_nome: '' }));
                              } else {
                                setForm(prev => ({ ...prev, olt_nome: '', olt_id: undefined }));
                              }
                            }}
                            inputValue={oltSearch}
                            onInputChange={(_, value, reason) => {
                              setOltSearch(value);
                              if (reason === 'input') {
                                if (oltSearchTimer.current) clearTimeout(oltSearchTimer.current);
                                oltSearchTimer.current = setTimeout(() => {
                                  loadOLTs(value);
                                }, 400);
                              }
                            }}
                            loading={oltsLoading}
                            disabled={viewOnly}
                            slotProps={{
                              paper: {
                                sx: { width: { xs: '280px', sm: '450px', md: '550px' } }
                              }
                            }}
                            renderInput={(params) => (
                              <TextField
                                {...params}
                                label="Nome da OLT"
                                size="small"
                                placeholder="Selecione ou digite"
                                helperText="Identificação da OLT de origem"
                                InputProps={{
                                  ...params.InputProps,
                                  endAdornment: (
                                    <React.Fragment>
                                      {oltsLoading ? <CircularProgress color="inherit" size={20} /> : null}
                                      {params.InputProps.endAdornment}
                                    </React.Fragment>
                                  ),
                                }}
                              />
                            )}
                          />
                          <TextField
                            label="Porta PON da OLT"
                            value={form.olt_pon || ''}
                            onChange={e => handleInputChange('olt_pon', e.target.value)}
                            fullWidth
                            size="small"
                            placeholder="Ex: GPON 0/1/2"
                            helperText="Porta PON do slot da OLT"
                            disabled={viewOnly}
                          />
                          <TextField
                            label="VLAN ID"
                            type="number"
                            value={form.vlan_id || ''}
                            onChange={e => handleInputChange('vlan_id', e.target.value ? Number(e.target.value) : undefined)}
                            fullWidth
                            size="small"
                            placeholder="Ex: 100"
                            helperText="VLAN do serviço de internet"
                            disabled={viewOnly}
                          />
                          <Box className="col-span-1 sm:col-span-3">
                            <Autocomplete
                              freeSolo
                              options={ctos}
                              getOptionLabel={(option) => typeof option === 'string' ? option : option.nome}
                              isOptionEqualToValue={(option, value) => {
                                if (typeof option === 'string' || typeof value === 'string') return option === value;
                                return option.id === value.id;
                              }}
                              renderOption={(props, option) => {
                                if (typeof option === 'string') {
                                  return <li {...props}>{option}</li>;
                                }
                                return (
                                  <Box component="li" {...props} sx={{ display: 'flex !important', flexDirection: 'column !important', alignItems: 'flex-start !important', py: 0.75, px: 1.5, width: '100%' }}>
                                    {/* Linha 1: Nome e Distância */}
                                    <Box sx={{ display: 'flex', justifyContent: 'flex-start', alignItems: 'center', gap: 1.5, mb: 0.25 }}>
                                      <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#1f2937' }}>
                                        {option.nome}
                                      </Typography>
                                      {option.distancia_metros !== undefined && option.distancia_metros !== null && (
                                        <Chip
                                          size="small"
                                          color={option.distancia_metros < 200 ? "success" : "default"}
                                          label={option.distancia_metros < 1000
                                            ? `📍 ${Math.round(option.distancia_metros)}m`
                                            : `📍 ${(option.distancia_metros / 1000).toFixed(1)}km`
                                          }
                                          sx={{ height: 18, fontSize: '0.7rem', flexShrink: 0 }}
                                        />
                                      )}
                                    </Box>
                                    {/* Linha 2: OLT, PON e Splitter */}
                                    <Typography variant="caption" color="text.secondary" sx={{ mb: 0.25 }}>
                                      {option.olt_nome ? `OLT: ${option.olt_nome}` : ''}
                                      {option.porta_pon ? ` | Porta PON: ${option.porta_pon}` : ''}
                                      {option.splitter_ratio ? ` | Splitter: ${option.splitter_ratio}` : ''}
                                    </Typography>
                                    {/* Linha 3: Endereço */}
                                    {option.endereco && (
                                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '100%' }}>
                                        🏠 {option.endereco}
                                      </Typography>
                                    )}
                                  </Box>
                                );
                              }}
                              value={ctos.find(c => c.id === form.cto_id) || form.cto_nome || null}
                              onChange={(_event, newValue) => {
                                if (typeof newValue === 'string') {
                                  setForm(prev => ({ ...prev, cto_nome: newValue, cto_id: undefined }));
                                } else if (newValue && newValue.id) {
                                  setForm(prev => {
                                    const updatedForm: any = {
                                      ...prev,
                                      cto_nome: newValue.nome,
                                      cto_id: newValue.id,
                                      olt_pon: newValue.olt_pon || prev.olt_pon,
                                    };
                                    if (newValue.olt_id) {
                                      updatedForm.olt_id = newValue.olt_id;
                                      updatedForm.olt_nome = newValue.olt_nome || prev.olt_nome;
                                    }
                                    return updatedForm;
                                  });
                                } else {
                                  setForm(prev => ({ ...prev, cto_nome: '', cto_id: undefined }));
                                }
                              }}
                              inputValue={ctoSearch}
                              onInputChange={(_, value, reason) => {
                                setCtoSearch(value);
                                if (reason === 'input') {
                                  if (ctoSearchTimer.current) clearTimeout(ctoSearchTimer.current);
                                  ctoSearchTimer.current = setTimeout(() => {
                                    loadCTOs(value, form.olt_id, form.coordenadas_gps);
                                  }, 400);
                                }
                              }}
                              loading={ctosLoading}
                              disabled={viewOnly}
                              slotProps={{
                                paper: {
                                  sx: { width: { xs: '280px', sm: '500px', md: '600px' } }
                                }
                              }}
                              renderInput={(params) => (
                                <TextField
                                  {...params}
                                  label="Caixa de Atendimento (CTO) *"
                                  size="small"
                                  placeholder="Selecione ou digite"
                                  helperText={errors.cto_nome || "Identificação da caixa (CTO) no poste"}
                                  error={!!errors.cto_nome}
                                  InputProps={{
                                    ...params.InputProps,
                                    endAdornment: (
                                      <React.Fragment>
                                        {ctosLoading ? <CircularProgress color="inherit" size={20} /> : null}
                                        {params.InputProps.endAdornment}
                                      </React.Fragment>
                                    ),
                                  }}
                                />
                              )}
                            />
                          </Box>
                          <TextField
                            label="Porta na CTO"
                            value={form.cto_porta || ''}
                            onChange={e => handleInputChange('cto_porta', e.target.value)}
                            fullWidth
                            size="small"
                            placeholder="Ex: 8"
                            helperText="Número da porta de atendimento"
                            disabled={viewOnly}
                          />
                          <TextField
                            label="Metragem Drop (Metros)"
                            type="number"
                            value={form.metragem_drop || ''}
                            onChange={e => handleInputChange('metragem_drop', e.target.value ? Number(e.target.value) : undefined)}
                            fullWidth
                            size="small"
                            placeholder="Ex: 120"
                            helperText="Comprimento do cabo drop de fibra usado"
                            disabled={viewOnly}
                          />
                        </div>
                      )}

                      <div className="col-span-1 sm:col-span-2 mt-2">
                        <TextField
                          label="Observações da Instalação"
                          value={form.observacoes_instalacao || ''}
                          onChange={e => handleInputChange('observacoes_instalacao', e.target.value)}
                          fullWidth
                          size="small"
                          multiline
                          rows={3}
                          placeholder="Detalhes sobre a instalação, fiação, local do roteador, etc."
                          disabled={viewOnly}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="bg-gradient-to-r from-orange-50 to-amber-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-orange-100">
                    <div className={isMobile ? "flex flex-col justify-between items-stretch gap-3 mb-4" : "flex justify-between items-center mb-4"}>
                      <h3 className="text-lg sm:text-xl font-bold text-orange-800 flex items-center">
                        <span className="mr-2 text-base sm:text-lg">📟</span>
                        <span className="text-sm sm:text-base">Equipamentos e Ativos</span>
                      </h3>
                      <Button
                        variant="contained"
                        size="small"
                        color="warning"
                        onClick={addAtivo}
                        startIcon={<span className="text-lg">+</span>}
                        className="rounded-full shadow-sm"
                        sx={isMobile ? { width: '100%' } : undefined}
                      >
                        Adicionar Equipamento
                      </Button>
                    </div>

                    <div className="space-y-4">
                      {(!form.ativos || form.ativos.length === 0) && (
                        <div className="text-center py-6 border-2 border-dashed border-orange-200 rounded-xl bg-white/50">
                          <p className="text-orange-400 text-sm italic">Nenhum equipamento vinculado. Clique em "Adicionar Equipamento" para registrar.</p>
                        </div>
                      )}

                      {(form.ativos || []).map((ativo, index) => (
                        <div key={index} className="bg-white p-4 rounded-xl border border-orange-100 shadow-sm relative">
                          <div className="flex justify-end mb-2">
                            <Button
                              size="small"
                              color="error"
                              variant="text"
                              onClick={() => removeAtivo(index)}
                              startIcon={<TrashIconMUI className="w-4 h-4" />}
                              sx={{
                                textTransform: 'none',
                                fontSize: '0.75rem',
                                backgroundColor: 'rgba(239, 68, 68, 0.08)',
                                '&:hover': { backgroundColor: 'rgba(239, 68, 68, 0.15)' }
                              }}
                            >
                              Remover Equipamento
                            </Button>
                          </div>

                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            <FormControl fullWidth size="small">
                              <InputLabel>Tipo</InputLabel>
                              <Select
                                value={ativo.tipo_equipamento}
                                label="Tipo"
                                onChange={(e) => handleAtivoChange(index, 'tipo_equipamento', e.target.value)}
                              >
                                <MenuItem value="ROTEADOR">Roteador</MenuItem>
                                <MenuItem value="ONT">ONT / ONU</MenuItem>
                                <MenuItem value="BRIDGE">Bridge</MenuItem>
                                <MenuItem value="RADIO">Rádio / Antena</MenuItem>
                                <MenuItem value="OUTRO">Outro</MenuItem>
                              </Select>
                            </FormControl>

                            <TextField
                              label="Modelo"
                              value={ativo.modelo || ''}
                              onChange={e => handleAtivoChange(index, 'modelo', e.target.value)}
                              fullWidth
                              size="small"
                              placeholder="Ex: Huawei HG8245H"
                            />

                            <TextField
                              label="Patrimônio"
                              value={ativo.patrimonio || ''}
                              onChange={e => handleAtivoChange(index, 'patrimonio', e.target.value)}
                              fullWidth
                              size="small"
                              placeholder="Nº Patrimônio"
                            />

                            <TextField
                              label="Número de Série"
                              value={ativo.serial_number || ''}
                              onChange={e => handleAtivoChange(index, 'serial_number', e.target.value)}
                              fullWidth
                              size="small"
                              placeholder="S/N"
                            />

                            <TextField
                              label="Login de Acesso"
                              value={ativo.login_acesso || ''}
                              onChange={e => handleAtivoChange(index, 'login_acesso', e.target.value)}
                              fullWidth
                              size="small"
                              placeholder="Usuário técnico"
                            />

                            <TextField
                              label="Senha de Acesso"
                              value={ativo.senha_acesso || ''}
                              onChange={e => handleAtivoChange(index, 'senha_acesso', e.target.value)}
                              fullWidth
                              size="small"
                              type="text"
                              placeholder="Senha técnica"
                            />

                            <FormControl fullWidth size="small">
                              <InputLabel>Regime</InputLabel>
                              <Select
                                value={String(ativo.is_comodato)}
                                label="Regime"
                                onChange={(e) => handleAtivoChange(index, 'is_comodato', e.target.value === 'true')}
                              >
                                <MenuItem value="true">Comodato</MenuItem>
                                <MenuItem value="false">Próprio do Cliente</MenuItem>
                              </Select>
                            </FormControl>

                            <TextField
                              label="Observações Técnicas"
                              value={ativo.observacoes || ''}
                              onChange={e => handleAtivoChange(index, 'observacoes', e.target.value)}
                              fullWidth
                              size="small"
                              className="sm:col-span-2"
                              placeholder="Ex: Localizado no forro, IP fixo 192.168.1.1, etc."
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                </div>
              )}

              {/* Second Tab - Network Configuration */}
              {tabValue === 1 && (
                <div className="space-y-4 sm:space-y-6">
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-blue-100">
                    <h3 className="text-lg sm:text-xl font-bold text-blue-800 mb-1 sm:mb-2 flex items-center">
                      <span className="mr-2 text-base sm:text-lg">🌐</span>
                      <span className="text-sm sm:text-base">Configuração de Rede</span>
                    </h3>
                    <p className="text-xs sm:text-sm text-blue-600 hidden sm:block">
                      Configurações de rede para provisionamento automático do plano de internet.
                    </p>
                    <div className="mt-3 sm:mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                      <FormControl fullWidth size="small">
                        <InputLabel>Router</InputLabel>
                        <Select
                          value={form.router_id?.toString() || ''}
                          label="Router"
                          onChange={(e: SelectChangeEvent) => {
                            const routerId = e.target.value ? parseInt(e.target.value) : undefined;
                            handleInputChange('router_id', routerId);
                            handleInputChange('interface_id', undefined);
                            handleInputChange('ip_class_id', undefined);
                            if (routerId) {
                              loadInterfaces(routerId);
                              const selectedRouter = routers.find(r => r.id === routerId);
                              if (selectedRouter) {
                                const allowedMethods = selectedRouter.metodos_autenticacao && selectedRouter.metodos_autenticacao.length > 0
                                  ? selectedRouter.metodos_autenticacao
                                  : ['IP_MAC', 'PPPOE', 'HOTSPOT', 'RADIUS'];
                                const defaultMethod = selectedRouter.metodo_autenticacao_padrao;
                                if (defaultMethod && allowedMethods.includes(defaultMethod)) {
                                  handleInputChange('metodo_autenticacao', defaultMethod);
                                } else if (form.metodo_autenticacao && !allowedMethods.includes(form.metodo_autenticacao)) {
                                  handleInputChange('metodo_autenticacao', '');
                                }
                              }
                            } else {
                              setInterfaces([]);
                              handleInputChange('metodo_autenticacao', '');
                            }
                          }}
                          disabled={networkLoading}
                        >
                          <MenuItem value="">
                            <em>Selecione um router</em>
                          </MenuItem>
                          {routers.map((router) => (
                            <MenuItem key={router.id} value={router.id}>
                              {router.nome} ({router.ip})
                            </MenuItem>
                          ))}
                        </Select>
                        {networkLoading && <CircularProgress size={20} sx={{ mt: 1 }} />}
                      </FormControl>

                      {(() => {
                        const selectedRouter = routers.find(r => r.id === form.router_id);
                        const allowedMethods = selectedRouter?.metodos_autenticacao && selectedRouter.metodos_autenticacao.length > 0
                          ? selectedRouter.metodos_autenticacao
                          : ['IP_MAC', 'PPPOE', 'HOTSPOT', 'RADIUS'];
                        return (
                          <FormControl fullWidth size="small">
                            <InputLabel>Método de Autenticação</InputLabel>
                            <Select
                              value={form.metodo_autenticacao || ''}
                              label="Método de Autenticação"
                              onChange={(e: SelectChangeEvent) => handleInputChange('metodo_autenticacao', e.target.value)}
                              disabled={!form.router_id}
                            >
                              <MenuItem value="">
                                <em>Selecione um método</em>
                              </MenuItem>
                              {allowedMethods.includes('IP_MAC') && <MenuItem value="IP_MAC">IP + MAC</MenuItem>}
                              {allowedMethods.includes('PPPOE') && <MenuItem value="PPPOE">PPPoE</MenuItem>}
                              {allowedMethods.includes('HOTSPOT') && <MenuItem value="HOTSPOT">Hotspot</MenuItem>}
                              {allowedMethods.includes('RADIUS') && <MenuItem value="RADIUS">RADIUS</MenuItem>}
                            </Select>
                          </FormControl>
                        );
                      })()}

                      {form.metodo_autenticacao !== 'RADIUS' && (
                        <>
                          <FormControl fullWidth size="small" error={!!errors.interface_id}>
                            <InputLabel>Interface</InputLabel>
                            <Select
                              value={form.interface_id?.toString() || ''}
                              label="Interface"
                              onChange={(e: SelectChangeEvent) => {
                                handleInputChange('interface_id', e.target.value ? parseInt(e.target.value) : undefined);
                                handleInputChange('ip_class_id', undefined); // Reset IP class when interface changes
                              }}
                              disabled={!form.router_id || networkLoading}
                            >
                              <MenuItem value="">
                                <em>Selecione uma interface</em>
                              </MenuItem>
                              {interfaces.map((interface_) => (
                                <MenuItem key={interface_.id} value={interface_.id}>
                                  <div>
                                    <div className="font-medium">{interface_.nome}</div>
                                    {interface_.comentario && (
                                      <div className="text-xs text-gray-500 mt-1">{interface_.comentario}</div>
                                    )}
                                  </div>
                                </MenuItem>
                              ))}
                            </Select>
                            {errors.interface_id && <FormHelperText>{errors.interface_id}</FormHelperText>}
                          </FormControl>

                          <FormControl fullWidth size="small" error={!!errors.ip_class_id}>
                            <InputLabel>Classe IP</InputLabel>
                            <Select
                              value={form.ip_class_id?.toString() || ''}
                              label="Classe IP"
                              onChange={(e: SelectChangeEvent) => {
                                const selectedClassId = e.target.value ? parseInt(e.target.value) : undefined;
                                handleInputChange('ip_class_id', selectedClassId);
                              }}
                              disabled={!form.interface_id || networkLoading}
                            >
                              <MenuItem value="">
                                <em>Selecione uma classe IP</em>
                              </MenuItem>
                              {getIPClassesForSelectedInterface.map((ipClass) => (
                                <MenuItem key={ipClass.id} value={ipClass.id}>
                                  {ipClass.nome} ({ipClass.rede})
                                </MenuItem>
                              ))}
                            </Select>
                            {errors.ip_class_id && <FormHelperText>{errors.ip_class_id}</FormHelperText>}
                          </FormControl>
                        </>
                      )}

                      {form.metodo_autenticacao === 'RADIUS' ? (
                        <>
                          <TextField
                            label="IP Fixo (Opcional)"
                            value={form.assigned_ip || ''}
                            onChange={e => handleInputChange('assigned_ip', e.target.value)}
                            fullWidth
                            size="small"
                            placeholder="Ex: 201.130.84.5"
                            error={!!errors.assigned_ip}
                            helperText={errors.assigned_ip || "Opcional: IP fixo entregue via RADIUS (deixe vazio para IP dinâmico)"}
                          />

                          <div className="flex items-center space-x-2 text-sm text-blue-600 sm:col-span-2">
                            <span>🔄</span>
                            <span>Opcional: Preencha um IP fixo para ser entregue via Radius, ou deixe em branco para dinâmico</span>
                          </div>
                        </>
                      ) : form.metodo_autenticacao === 'IP_MAC' ? (
                        <>
                          <TextField
                            label="Endereço MAC"
                            value={form.mac_address || ''}
                            onChange={e => handleInputChange('mac_address', e.target.value)}
                            fullWidth
                            size="small"
                            placeholder="Ex: AA:BB:CC:DD:EE:FF"
                            error={!!errors.mac_address}
                            helperText={errors.mac_address || "MAC address do dispositivo do cliente"}
                          />

                          <FormControl fullWidth size="small" error={!!errors.assigned_ip}>
                            <InputLabel>IP Atribuído</InputLabel>
                            <Select
                              value={form.assigned_ip || ''}
                              label="IP Atribuído"
                              onChange={(e: SelectChangeEvent) => handleInputChange('assigned_ip', e.target.value)}
                              disabled={!form.ip_class_id || availableIPs.length === 0}
                            >
                              <MenuItem value="">
                                <em>Selecione um IP disponível</em>
                              </MenuItem>
                              {availableIPs.map((ip) => (
                                <MenuItem key={ip} value={ip}>
                                  {ip}
                                </MenuItem>
                              ))}
                            </Select>
                            {errors.assigned_ip && <FormHelperText>{errors.assigned_ip}</FormHelperText>}
                          </FormControl>

                          <div className="flex items-center space-x-2 text-sm text-blue-600">
                            <span>🔄</span>
                            <span>Selecione um IP disponível da lista quando a Classe IP for escolhida</span>
                          </div>
                        </>
                      ) : null}

                      {(form.metodo_autenticacao === 'PPPOE' || form.metodo_autenticacao === 'RADIUS') && (
                        <>
                          <TextField
                            label="Username PPPoE"
                            value={form.pppoe_username || ''}
                            onChange={e => handleInputChange('pppoe_username', e.target.value)}
                            fullWidth
                            size="small"
                            placeholder="Ex: cliente123"
                            error={!!errors.pppoe_username}
                            helperText={errors.pppoe_username || "Username para autenticação PPPoE"}
                          />

                          <TextField
                            label="Password PPPoE"
                            type={showPppoePassword ? 'text' : 'password'}
                            value={form.pppoe_password || ''}
                            onChange={e => handleInputChange('pppoe_password', e.target.value)}
                            fullWidth
                            size="small"
                            placeholder="Digite a senha PPPoE"
                            error={!!errors.pppoe_password}
                            helperText={errors.pppoe_password || "Password para autenticação PPPoE"}
                            InputProps={{
                              endAdornment: (
                                <InputAdornment position="end">
                                  <IconButton
                                    onClick={() => setShowPppoePassword(prev => !prev)}
                                    edge="end"
                                    size="small"
                                    tabIndex={-1}
                                    aria-label={showPppoePassword ? 'Ocultar senha' : 'Mostrar senha'}
                                  >
                                    <EyeIcon className="w-4 h-4" style={{ opacity: showPppoePassword ? 1 : 0.5 }} />
                                  </IconButton>
                                </InputAdornment>
                              )
                            }}
                          />

                          <div className="flex items-center space-x-2 text-sm text-green-600">
                            <span>🔐</span>
                            <span>Configure as credenciais PPPoE para autenticação do cliente</span>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Third Tab - Billing and SLA */}
              {tabValue === 2 && (
                <div className="space-y-4 sm:space-y-6">
                  <div className="bg-gradient-to-r from-rose-50 to-pink-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-rose-100">
                    <h3 className="text-lg sm:text-xl font-bold text-rose-800 mb-1 sm:mb-2 flex items-center">
                      <span className="mr-2 text-base sm:text-lg">💰</span>
                      <span className="text-sm sm:text-base">Cobrança e SLA</span>
                    </h3>
                    <p className="text-xs sm:text-sm text-rose-600 hidden sm:block">
                      Configurações de cobrança e qualidade do plano de internet.
                    </p>
                    <div className="mt-3 sm:mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                      <FormControl fullWidth size="small">
                        <InputLabel>Conta Bancária</InputLabel>
                        <Select
                          value={form.bank_account_id?.toString() || ''}
                          label="Conta Bancária"
                          onChange={(e: SelectChangeEvent) => handleInputChange('bank_account_id', e.target.value === '' ? undefined : parseInt(e.target.value))}
                          disabled={bankAccountLoading}
                        >
                          <MenuItem value="">
                            <em>Conta padrão da empresa</em>
                          </MenuItem>
                          {bankAccounts.map((bankAccount) => (
                            <MenuItem key={bankAccount.id} value={bankAccount.id}>
                              {bankAccount.bank} - Ag: {bankAccount.agencia} Conta: {bankAccount.conta}
                              {bankAccount.is_default && ' (Padrão)'}
                            </MenuItem>
                          ))}
                        </Select>
                        <FormHelperText>
                          Conta bancária para cobrança deste contrato. Se não selecionada, usa a conta padrão da empresa.
                        </FormHelperText>
                      </FormControl>
                      <TextField
                        label="Período de Carência (dias)"
                        type="number"
                        value={form.periodo_carencia || 0}
                        onChange={e => handleInputChange('periodo_carencia', parseInt(e.target.value || '0'))}
                        fullWidth
                        size="small"
                        inputProps={{ min: 0 }}
                        helperText="Dias de tolerância após vencimento"
                      />
                      <TextField
                        label="Multa por Atraso (%)"
                        type="number"
                        value={form.multa_atraso_percentual || 0}
                        onChange={e => handleInputChange('multa_atraso_percentual', parseFloat(e.target.value || '0'))}
                        fullWidth
                        size="small"
                        inputProps={{ min: 0, max: 100, step: 0.01 }}
                        helperText="Percentual de multa sobre valor devido"
                      />
                      <TextField
                        label="Taxa de Instalação (R$)"
                        type="number"
                        value={form.taxa_instalacao || 0}
                        onChange={e => handleInputChange('taxa_instalacao', parseFloat(e.target.value || '0'))}
                        fullWidth
                        size="small"
                        inputProps={{ min: 0, step: 0.01 }}
                        helperText="Taxa única cobrada na instalação"
                      />
                      <FormControl fullWidth size="small">
                        <InputLabel>Taxa de Instalação Paga</InputLabel>
                        <Select
                          value={form.taxa_instalacao_paga ? 'true' : 'false'}
                          label="Taxa de Instalação Paga"
                          onChange={(e: SelectChangeEvent) => handleInputChange('taxa_instalacao_paga', e.target.value === 'true')}
                        >
                          <MenuItem value="false">Não</MenuItem>
                          <MenuItem value="true">Sim</MenuItem>
                        </Select>
                      </FormControl>
                      <TextField
                        label="SLA Garantido (%)"
                        type="number"
                        value={form.sla_garantido || ''}
                        onChange={e => handleInputChange('sla_garantido', e.target.value === '' ? undefined : parseFloat(e.target.value))}
                        fullWidth
                        size="small"
                        inputProps={{ min: 0, max: 100, step: 0.01 }}
                        helperText="SLA de disponibilidade garantido"
                      />
                      <TextField
                        label="Subscription ID"
                        value={form.subscription_id || ''}
                        onChange={e => handleInputChange('subscription_id', e.target.value === '' ? undefined : parseInt(e.target.value))}
                        fullWidth
                        size="small"
                        type="number"
                        disabled={true}
                        helperText="ID da subscription relacionada (somente leitura)"
                      />
                      <FormControl fullWidth size="small">
                        <InputLabel>Método de Pagamento</InputLabel>
                        <Select
                          value={form.payment_method || 'BOLETO'}
                          label="Método de Pagamento"
                          onChange={(e: SelectChangeEvent) => handleInputChange('payment_method', e.target.value)}
                        >
                          <MenuItem value="BOLETO">Boleto Bancário (Tradicional)</MenuItem>
                          <MenuItem value="MERCADO_PAGO">Mercado Pago (Cartão/Pix/Boleto Online)</MenuItem>
                        </Select>
                        <FormHelperText>
                          Selecione como este contrato será cobrado. Mercado Pago permite pagamento online via link.
                        </FormHelperText>
                      </FormControl>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-2 sm:gap-3 p-3 sm:p-6 border-t border-borderLight bg-gradient-to-r from-gray-50 to-blue-50/30 flex-shrink-0 shadow-modern">
              <div className="hidden sm:flex items-center space-x-2 text-xs sm:text-sm text-indigo-600 text-center sm:text-left">
                <span className="text-xs sm:text-lg">💡</span>
                <p className="leading-tight font-normal text-xs">Preencha os dados do contrato corretamente.</p>
              </div>
              <div className="flex gap-2 sm:gap-3 justify-center sm:justify-end">
                <button onClick={handleCloseForm} className="px-4 sm:px-5 py-2 sm:py-2.5 btn-secondary rounded-lg sm:rounded-xl shadow-sm hover:shadow-md transition-all duration-200 font-semibold flex-shrink-0 text-sm sm:text-sm">Cancelar</button>
                {!viewOnly && (
                  <button onClick={submit} className="px-4 sm:px-5 py-2 sm:py-2.5 btn-primary rounded-lg sm:rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 font-semibold flex-shrink-0 text-sm sm:text-sm bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700">{editing ? 'Atualizar' : 'Criar'}</button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Bulk emit dialog */}
      <Dialog open={bulkDialogOpen} onClose={() => setBulkDialogOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>Emitir NFCom em Lote</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Selecionados: {selectedContracts.length} contrato(s).
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 2 }}>
            <Checkbox checked={bulkExecuteFlag} onChange={(e) => setBulkExecuteFlag(e.target.checked)} />
            <Typography>Executar (criar NFComs no banco)</Typography>
            <Checkbox checked={bulkTransmitFlag} onChange={(e) => setBulkTransmitFlag(e.target.checked)} />
            <Typography>Transmitir após criação (atenção: requer certificado configurado)</Typography>
          </Box>

          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            <Button variant="outlined" onClick={previewBulkEmit} disabled={bulkPreviewLoading || selectedContracts.length === 0}>
              {bulkPreviewLoading ? <CircularProgress size={16} /> : 'Pré-visualizar (Dry-run)'}
            </Button>
            <Button variant="contained" color="primary" onClick={confirmBulkEmit} disabled={bulkExecuteLoading || selectedContracts.length === 0}>
              {bulkExecuteLoading ? <CircularProgress size={16} color="inherit" /> : (bulkExecuteFlag ? (bulkTransmitFlag ? 'Executar e Transmitir' : 'Executar (Criar)') : 'Executar (Dry-run)')}
            </Button>
            <Button variant="text" onClick={() => setBulkDialogOpen(false)}>Cancelar</Button>
          </Box>

          {bulkPreviewResult && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2">Resultado da Pré-visualização</Typography>
              <Typography variant="body2">Processados: {bulkPreviewResult.total_processed ?? selectedContracts.length}</Typography>
              <Typography variant="body2">Sucessos: {bulkPreviewResult.total_success ?? (bulkPreviewResult.successes ? bulkPreviewResult.successes.length : 0)}</Typography>
              <Typography variant="body2">Falhas: {bulkPreviewResult.total_failed ?? (bulkPreviewResult.failures ? bulkPreviewResult.failures.length : 0)}</Typography>
              {bulkPreviewResult.failures && bulkPreviewResult.failures.length > 0 && (
                <Box sx={{ mt: 1, maxHeight: 240, overflow: 'auto', bgcolor: 'background.paper', p: 1, borderRadius: 1 }}>
                  {bulkPreviewResult.failures.map((f: any, idx: number) => (
                    <Box key={idx} sx={{ mb: 1, borderBottom: '1px solid #eee', pb: 1 }}>
                      <Typography variant="body2"><strong>Contrato:</strong> {f.contract_id ?? f.id}</Typography>
                      <Typography variant="caption">{f.error || JSON.stringify(f)}</Typography>
                    </Box>
                  ))}
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
      </Dialog>

      {/* Modal Visualização de Contrato */}
      <Dialog
        open={openContractModal}
        onClose={() => { setOpenContractModal(false); setContractHtmlUrl(null); }}
        maxWidth="lg"
        fullWidth
        fullScreen={isMobile}
      >
        <DialogTitle sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          bgcolor: 'primary.main',
          color: 'white',
          px: isMobile ? 2 : undefined,
          py: isMobile ? 1.5 : undefined
        }}>
          {isMobile ? (
            <Typography variant="h6" sx={{ fontSize: '1.05rem', fontWeight: 'bold', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              Termo de Adesão
            </Typography>
          ) : (
            "Visualização do Termo de Adesão"
          )}
          <IconButton onClick={() => { setOpenContractModal(false); setContractHtmlUrl(null); }} sx={{ color: 'white', p: isMobile ? 0.5 : undefined }}><XMarkIcon className="w-6 h-6" /></IconButton>
        </DialogTitle>
        <DialogContent sx={isMobile ? { p: 0, flex: 1, display: 'flex', flexDirection: 'column', height: '100%', bgcolor: '#f5f5f5', overflow: 'hidden' } : { p: 0, height: '85vh', bgcolor: '#f5f5f5' }}>
          {contractHtmlUrl ? (
            <iframe src={contractHtmlUrl} width="100%" height="100%" style={isMobile ? { border: 'none', flexGrow: 1, width: '100%', height: '100%' } : { border: 'none' }} title="Termo de Adesão" />
          ) : (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}><CircularProgress /></Box>
          )}
        </DialogContent>
        <DialogActions sx={isMobile ? {
          p: 2,
          bgcolor: '#f5f5f5',
          gap: 1.5,
          justifyContent: 'center',
          flexDirection: 'row'
        } : { p: 2, bgcolor: '#f5f5f5', gap: 1 }}>
          {isMobile ? (
            <>
              <Button
                onClick={() => { setOpenContractModal(false); setContractHtmlUrl(null); setViewingContractId(null); }}
                variant="outlined"
                color="inherit"
                sx={{ minWidth: '48px', px: 0 }}
              >
                <XMarkIcon className="w-5 h-5" />
              </Button>

              {viewingContractId && contratos.find(c => c.id === viewingContractId)?.assinado_em && (
                <Button
                  variant="outlined"
                  color="secondary"
                  onClick={() => handleReiniciarAssinatura(viewingContractId)}
                  disabled={loading}
                  sx={{ minWidth: '48px', px: 0 }}
                >
                  <ArrowPathIcon className="w-5 h-5" />
                </Button>
              )}

              <Button
                variant="outlined"
                color="info"
                onClick={() => viewingContractId && handleSendContractNotification(viewingContractId)}
                disabled={!viewingContractId || loading}
                sx={{ minWidth: '48px', px: 0 }}
              >
                <EnvelopeIcon className="w-5 h-5" />
              </Button>
              <Button
                variant="contained"
                onClick={() => {
                  const iframe = document.querySelector('iframe[title="Termo de Adesão"]') as HTMLIFrameElement;
                  if (iframe && iframe.contentWindow) {
                    iframe.contentWindow.print();
                  }
                }}
                sx={{ minWidth: '48px', px: 0 }}
              >
                <PrinterIcon className="w-5 h-5" />
              </Button>
            </>
          ) : (
            <>
              <Button onClick={() => { setOpenContractModal(false); setContractHtmlUrl(null); setViewingContractId(null); }}>Fechar</Button>

              {viewingContractId && contratos.find(c => c.id === viewingContractId)?.assinado_em && (
                <Button
                  variant="outlined"
                  color="secondary"
                  startIcon={<ArrowPathIcon className="w-5 h-5" />}
                  onClick={() => handleReiniciarAssinatura(viewingContractId)}
                  disabled={loading}
                >
                  Reiniciar Assinatura
                </Button>
              )}

              <Button
                variant="outlined"
                color="info"
                startIcon={<EnvelopeIcon className="w-5 h-5" />}
                onClick={() => viewingContractId && handleSendContractNotification(viewingContractId)}
                disabled={!viewingContractId || loading}
              >
                Enviar Notificação
              </Button>
              <Button
                variant="contained"
                startIcon={<PrinterIcon className="w-5 h-5" />}
                onClick={() => {
                  const iframe = document.querySelector('iframe[title="Termo de Adesão"]') as HTMLIFrameElement;
                  if (iframe && iframe.contentWindow) {
                    iframe.contentWindow.print();
                  }
                }}
              >
                Imprimir
              </Button>
            </>
          )}
        </DialogActions>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={6000} onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}>
        <Alert onClose={() => setSnackbar(prev => ({ ...prev, open: false }))} severity={snackbar.severity} sx={{ width: '100%' }}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default Contracts;
