import React, { useState, useEffect, useCallback, useRef } from 'react';
import useFitText from '../hooks/useFitText';
import { useLocation } from 'react-router-dom';
import {
  Typography,
  Box,
  Paper,
  Button,
  TextField,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
  Alert,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  IconButton,
  Autocomplete,
  Card,
  CardContent,
  Divider,
  Chip,
  Checkbox,
  SelectChangeEvent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Pagination,
  TablePagination,
  InputAdornment,
} from '@mui/material';
import Menu from '@mui/material/Menu';
import FirstPageIcon from '@mui/icons-material/FirstPage';
import LastPageIcon from '@mui/icons-material/LastPage';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import { PlusIcon, DocumentTextIcon, TrashIcon, PencilIcon, DocumentArrowDownIcon, MagnifyingGlassIcon, XMarkIcon, CodeBracketIcon, PaperAirplaneIcon } from '@heroicons/react/24/outline';
import { useCompany } from '../contexts/CompanyContext';
import api, { API_BASE_URL } from '../services/api';
import clientService from '../services/clientService';
import { stringifyError } from '../utils/error';
// Renomeia o tipo importado para evitar conflito com o nome do componente
import nfcomService, { NFComCreate, NFComItemCreate, NFCom as NFComBaseType } from '../services/nfcomService';
import servicoService, { Servico } from '../services/servicoService';
import { Cliente } from '../types';

type FrontendNFComCreate = NFComCreate & {
  cliente_endereco_id?: number | null;
};

// Cria um novo tipo local que estende o tipo base importado
type NFComType = NFComBaseType & {
  xml_gerado?: string | null;
  email_status?: string | null;
  email_sent_at?: string | null;
  email_error_message?: string | null;
  email_error?: string | null;
};

const NFCom: React.FC = () => {
  const { activeCompany } = useCompany();
  const [nfcoms, setNfcoms] = useState<NFComType[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [clients, setClients] = useState<Cliente[]>([]);
  const [clientSearch, setClientSearch] = useState('');
  const [clientLoading, setClientLoading] = useState(false);
  const [clientAddresses, setClientAddresses] = useState<any[]>([]);
  const [servicos, setServicos] = useState<Servico[]>([]);
  const [servicosOptions, setServicosOptions] = useState<Record<number, Servico[]>>({});
  const [selectedServicos, setSelectedServicos] = useState<Record<number, Servico | null>>({});
  const searchTimeouts = React.useRef<Record<number, any>>({});
  const searchControllers = React.useRef<Record<number, AbortController>>({});
  const [openForm, setOpenForm] = useState(false);
  const [editingNfcom, setEditingNfcom] = useState<NFComType | null>(null);
  const [activeTab, setActiveTab] = useState('general');
  const [searchTerm, setSearchTerm] = useState('');
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'authorized' | 'pending'>('all');
  const [minValue, setMinValue] = useState('');
  const [maxValue, setMaxValue] = useState('');

  // Pagination and Total State
  const [page, setPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [totalRows, setTotalRows] = useState(0);
  const [totalGeralValor, setTotalGeralValor] = useState(0);
    const computeFontSizes = (value: string | number) => {
      const s = String(value);
      const len = s.length;
      if (len <= 3) return { xs: '1.5rem', sm: '1.75rem', md: '2rem' };
      if (len <= 6) return { xs: '1.25rem', sm: '1.5rem', md: '1.75rem' };
      if (len <= 10) return { xs: '1rem', sm: '1.125rem', md: '1.25rem' };
      return { xs: '0.9rem', sm: '1rem', md: '1.125rem' };
    };
  const [totalAutorizadas, setTotalAutorizadas] = useState(0);
  const [totalPendentes, setTotalPendentes] = useState(0);

  // Estados para exclusão de notas
  const [selectedNfcoms, setSelectedNfcoms] = useState<Set<number>>(new Set());
  const [deletingNfcoms, setDeletingNfcoms] = useState(false);
  const [sendingEmails, setSendingEmails] = useState(false);
  // Menu compacto para ações (economiza espaço)
  const [menuAnchorEl, setMenuAnchorEl] = useState<null | HTMLElement>(null);
  const menuOpen = Boolean(menuAnchorEl);
  const [confirmDeleteDialog, setConfirmDeleteDialog] = useState(false);

  const [formData, setFormData] = useState<FrontendNFComCreate>({
    cliente_id: null,
    cliente_endereco_id: null,
    // Campos contratuais do nível NFCom
    numero_contrato: undefined,
    d_contrato_ini: undefined,
    d_contrato_fim: undefined,
    cMunFG: activeCompany?.codigo_ibge || '',
    finalidade_emissao: '0',
    tpFat: '0',
    data_emissao: new Date().toISOString().split('T')[0],
    itens: [],
  faturas: [],
    valor_total: 0,
    informacoes_adicionais: '',
    dest_endereco: '',
    dest_numero: '',
    dest_complemento: '',
    dest_bairro: '',
    dest_municipio: '',
    dest_uf: '',
    dest_cep: '',
    dest_codigo_ibge: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' | 'warning' | 'info', persist: false });
  // Estado para modal de rejeição da SEFAZ
  const [rejectionModal, setRejectionModal] = useState({ open: false, cStat: '', xMotivo: '', resultado: null as any, nfId: null as number | null, empresaId: null as number | null, resending: false });
  const [transmittingId, setTransmittingId] = useState<number | null>(null);
  const [transmittingBulk, setTransmittingBulk] = useState(false);
  const [cancelDialog, setCancelDialog] = useState({ open: false, nfId: null as number | null, nProt: '', justificativa: '' });
  const [cancelSubmitting, setCancelSubmitting] = useState(false);

  const loadNfcoms = useCallback(async (currentPage = page) => {
    if (!activeCompany) return;
    setLoading(true);
    try {
      const filters: any = {};

      if (searchTerm) filters.search = searchTerm;
      if (dateFrom) filters.date_from = dateFrom;
      if (dateTo) filters.date_to = dateTo;
      if (statusFilter !== 'all') filters.status = statusFilter;
      // Only apply value filters if they have at least 3 characters (to avoid partial filtering)
      if (minValue && minValue.length >= 3) filters.min_value = parseFloat(minValue);
      if (maxValue && maxValue.length >= 3) filters.max_value = parseFloat(maxValue);

      // Ordenar por número da nota em ordem decrescente (última primeiro)
      filters.order_by = 'numero_nf';
      filters.order_direction = 'desc';

      const data = await nfcomService.getNFComsByCompany(activeCompany.id, currentPage, rowsPerPage, filters);
      setNfcoms(data.nfcoms || []);
      // Fetch email statuses for current page NFComs
      try {
        const ids = (data.nfcoms || []).map((n: any) => n.id);
        if (ids.length > 0) {
          const statuses = await nfcomService.getEmailStatuses(activeCompany.id, ids);
          // Preserve any email status already present on the NFCom object (e.g. from sync send),
          // otherwise fall back to the per-job status endpoint result, and finally to 'unknown'.
          setNfcoms((prev) => (data.nfcoms || []).map((n: any) => ({
            ...n,
            email_status: n.email_status || statuses[n.id]?.status || 'unknown',
            email_sent_at: n.email_sent_at || statuses[n.id]?.sent_at || null,
            email_error_message: n.email_error_message || n.email_error || statuses[n.id]?.error_message || null,
          })));
        }
      } catch (e) {
        // não bloquear o carregamento se falhar a busca de status
        console.warn('Não foi possível recuperar status de email das NFComs', e);
      }
      setTotalRows(data.total || 0);
      setTotalGeralValor(data.total_geral_valor || 0);
      setTotalAutorizadas(data.total_autorizadas || 0);
      setTotalPendentes(data.total_pendentes || 0);
    } catch (err) {
      console.error('Erro ao carregar NFComs:', err);
      setSnackbar({ open: true, message: 'Erro ao carregar NFComs', severity: 'error', persist: false });
    } finally {
      setLoading(false);
    }
  }, [activeCompany, page, rowsPerPage, searchTerm, dateFrom, dateTo, statusFilter, minValue, maxValue]);

  const location = useLocation();

  useEffect(() => {
    if (activeCompany) {
      setFormData(prev => ({ ...prev, cMunFG: activeCompany.codigo_ibge || '' }));
      // Prefetch a small set of services for autocomplete defaults
      loadServicos();
      loadNfcoms(1); // Load first page on company change
      setClients([]); // Limpa clientes ao abrir nova empresa
      setClientSearch('');
    }
    // Se a rota tiver ?new=true, abrir formulário para nova NFCom
    try {
      const params = new URLSearchParams(location.search);
      if (params.get('new') === 'true') {
        handleOpenForm();
      }
    } catch (e) {}
  }, [activeCompany, location]);

  // Auto-reload when filters change (but not during initial load)
  useEffect(() => {
    if (activeCompany && !loading) {
      const timeoutId = setTimeout(() => {
        setPage(1);
        loadNfcoms(1);
      }, 500); // Debounce for 500ms

      return () => clearTimeout(timeoutId);
    }
  }, [searchTerm, dateFrom, dateTo, statusFilter]); // Removed minValue, maxValue from here

  // Separate debounce for value filters (longer delay to allow user to finish typing)
  useEffect(() => {
    if (activeCompany && !loading && (minValue.length >= 3 || maxValue.length >= 3 || minValue === '' || maxValue === '')) {
      const timeoutId = setTimeout(() => {
        setPage(1);
        loadNfcoms(1);
      }, 2000); // Longer debounce for value filters (2 seconds)

      return () => clearTimeout(timeoutId);
    }
  }, [minValue, maxValue]); // Only trigger on value filter changes

  // Reload when rowsPerPage changes
  useEffect(() => {
    if (activeCompany && !loading) {
      loadNfcoms(1);
    }
  }, [rowsPerPage, activeCompany]);

  // Check if any filters are applied
  const hasFiltersApplied = () => {
    return !!(searchTerm || dateFrom || dateTo || statusFilter !== 'all' || (minValue && minValue.length >= 3) || (maxValue && maxValue.length >= 3));
  };

  // Download single XML (direct) for one NFCom
  const handleDownloadSingleXml = async (nf: any) => {
    if (!activeCompany) return;
    if (!nf || !nf.xml_url) {
      setSnackbar({ open: true, message: 'XML não disponível para esta NFCom', severity: 'warning', persist: false });
      return;
    }
    try {
      const response = await api.get(nf.xml_url, { responseType: 'blob' });
      const blob = new Blob([response.data], { type: 'application/xml' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `nfcom_${nf.numero_nf}_${nf.serie}.xml`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      setSnackbar({ open: true, message: 'XML baixado com sucesso!', severity: 'success', persist: false });
    } catch (error: any) {
      console.error('Erro ao baixar XML:', error);
      setSnackbar({ open: true, message: stringifyError(error) || 'Erro ao baixar XML', severity: 'error', persist: false });
    }
  };

  // Download single DANFE (direct PDF) for one NFCom
  const handleDownloadSingleDanfe = async (nf: any) => {
    if (!activeCompany) return;
    try {
      const response = await api.get(`/empresas/${activeCompany.id}/nfcom/${nf.id}/danfe?download=true`, { responseType: 'blob' });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `danfe_nfcom_${nf.numero_nf}_${nf.serie}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      setSnackbar({ open: true, message: 'DANFE baixado com sucesso!', severity: 'success', persist: false });
    } catch (error: any) {
      console.error('Erro ao baixar DANFE:', error);
      setSnackbar({ open: true, message: stringifyError(error) || 'Erro ao baixar DANFE', severity: 'error', persist: false });
    }
  };

  const handleDownloadSelectedXmls = async () => {
    if (selectedNfcoms.size === 0) return;
    if (!activeCompany) return;
    // If only one selected, download the XML directly (no zip)
    if (selectedNfcoms.size === 1) {
      const id = Array.from(selectedNfcoms)[0];
      const nf = nfcoms.find(n => n.id === id);
      if (nf) {
        return handleDownloadSingleXml(nf);
      }
    }

    const ids = Array.from(selectedNfcoms);
    try {
      const resp = await nfcomService.downloadZip(activeCompany.id, ids, 'xml');
      const blob = new Blob([resp.data], { type: 'application/zip' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `nfcom_xmls_${Date.now()}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      setSnackbar({ open: true, message: 'Download iniciado', severity: 'success', persist: false });
      setSelectedNfcoms(new Set());
    } catch (error: any) {
      console.error('Erro ao baixar XMLs:', error);
      setSnackbar({ open: true, message: stringifyError(error) || 'Erro ao baixar XMLs', severity: 'error', persist: false });
    }
  };

  const handleDownloadSelectedDanfes = async () => {
    if (selectedNfcoms.size === 0) return;
    if (!activeCompany) return;
    // If only one selected, download single PDF directly
    if (selectedNfcoms.size === 1) {
      const id = Array.from(selectedNfcoms)[0];
      const nf = nfcoms.find(n => n.id === id);
      if (nf) {
        return handleDownloadSingleDanfe(nf);
      }
    }

    const ids = Array.from(selectedNfcoms);
    try {
      const resp = await nfcomService.downloadZip(activeCompany.id, ids, 'danfe');
      const blob = new Blob([resp.data], { type: 'application/zip' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `nfcom_danfes_${Date.now()}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      setSnackbar({ open: true, message: 'Download iniciado', severity: 'success', persist: false });
      setSelectedNfcoms(new Set());
    } catch (error: any) {
      console.error('Erro ao baixar DANFEs:', error);
      setSnackbar({ open: true, message: stringifyError(error) || 'Erro ao baixar DANFEs', severity: 'error', persist: false });
    }
  };

  // Small component to auto-fit numbers in the summary cards
  const StatNumber: React.FC<{ value: string | number; color?: string }> = ({ value, color }) => {
    const ref = useRef<HTMLElement | null>(null);
    const fitPx = useFitText(ref, { min: 12, max: 36 });
    return (
      <Typography ref={ref as any} variant="h4" sx={{ color: color || 'text.primary', fontWeight: 'bold' }} style={{ fontSize: `${Math.round(fitPx)}px` }}>
        {value}
      </Typography>
    );
  };

  // Clear all filters
  const clearFilters = () => {
    setSearchTerm('');
    setDateFrom('');
    setDateTo('');
    setStatusFilter('all');
    setMinValue('');
    setMaxValue('');
    setPage(1);
  };

  const handlePageChange = (event: React.ChangeEvent<unknown>, newPage: number) => {
    setPage(newPage);
    loadNfcoms(newPage);
  };

  const handleRowsPerPageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newRowsPerPage = parseInt(event.target.value, 10);
    setRowsPerPage(newRowsPerPage);
    // Don't call loadNfcoms here - the useEffect will handle it
  };

  const handleDownloadPdf = (nf: any) => {
    if (nf.pdf_url) {
      window.open(nf.pdf_url, '_blank');
    } else {
      setSnackbar({ open: true, message: 'PDF não disponível para esta NFCom', severity: 'warning', persist: false });
    }
  };

  const handleDownloadXml = async (nf: any) => {
    // Single XML download (no zip)
    return handleDownloadSingleXml(nf);
  };

  const handleViewDanfe = async (nf: any) => {
    if (!activeCompany) return;
    
    try {
      // Busca o DANFE com autenticação usando a instância axios configurada
      const response = await api.get(`/empresas/${activeCompany.id}/nfcom/${nf.id}/danfe`, {
        responseType: 'blob' // Importante para downloads binários
      });

      // Cria um blob e abre em nova aba
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      window.open(url, '_blank');
      
      // Limpa o URL após um tempo (o navegador já tem o blob)
      setTimeout(() => window.URL.revokeObjectURL(url), 100);
    } catch (error: any) {
      console.error('Erro ao visualizar DANFE:', error);
      const errorMessage = stringifyError(error) || 'Erro ao visualizar DANFE';
      setSnackbar({ open: true, message: errorMessage, severity: 'error', persist: false });
    }
  };

  const handleDownloadDanfe = async (nf: any) => {
    // Single DANFE download (no zip)
    return handleDownloadSingleDanfe(nf);
  };

  const handleTransmit = async (nf: NFComType) => {
    if (!activeCompany) return;
    setTransmittingId(nf.id);
  setSnackbar({ open: true, message: `Transmitindo NFCom #${nf.numero_nf}...`, severity: 'info', persist: false });

    try {
        // Esta lógica idealmente ficaria em nfcomService.ts
        const response = await api.post(`/empresas/${activeCompany.id}/nfcom/${nf.id}/transmitir`, {});

        console.log("Resposta da SEFAZ:", response.data.sefaz_response);
        setSnackbar({ open: true, message: `NFCom #${nf.numero_nf} transmitida! Verifique a resposta no console.`, severity: 'success', persist: false });
        
        // Atualiza a lista para refletir o novo status (se houver mudança)
        loadNfcoms(page);

  } catch (error: any) {
    const errorMessage = stringifyError(error) || 'Erro ao transmitir NFCom.';
        console.error("Erro na transmissão:", error);
        // Se a resposta da API indicar rejeição pela SEFAZ (cStat presente), abrir modal com detalhes
        const isSefazRejection = !!(error.response && error.response.status === 400 && error.response.data && error.response.data.cStat);
        if (isSefazRejection) {
          // esconder snackbar (caso tenha sido aberto) e abrir modal detalhado com informações de rejeição
          setSnackbar(prev => ({ ...prev, open: false }));
          setRejectionModal({
            open: true,
            cStat: error.response.data.cStat,
            xMotivo: error.response.data.xMotivo || (typeof error.response.data.detail === 'string' ? error.response.data.detail : ''),
            resultado: error.response.data.resultado || null,
            nfId: nf.id,
            empresaId: activeCompany?.id || null,
            resending: false,
          });
          // Atualiza lista para refletir possíveis mudanças de status (ex: duplicidade -> já cancelado)
          loadNfcoms(page);
        } else {
          setSnackbar({ open: true, message: `Falha na transmissão: ${errorMessage}`, severity: 'error', persist: false });
        }
    } finally {
        setTransmittingId(null);
    }
  };

  const handleOpenCancel = (nf: NFComType) => {
    setCancelDialog({ open: true, nfId: nf.id, nProt: nf.protocolo_autorizacao || '', justificativa: '' });
  };

  const handleCloseCancel = () => {
    setCancelDialog(prev => ({ ...prev, open: false }));
  };

  const handleSubmitCancel = async () => {
    if (!activeCompany || !cancelDialog.nfId) return;
    
    // Validação conforme MOC/XSD: xJust (TJust) deve ter de 15 a 255 caracteres
    const justificativaLimpa = cancelDialog.justificativa.trim();
    if (!justificativaLimpa || justificativaLimpa.length < 15) {
      setSnackbar({ open: true, message: 'Justificativa é obrigatória e deve ter no mínimo 15 caracteres', severity: 'error', persist: false });
      setCancelSubmitting(false);
      return;
    }
    if (justificativaLimpa.length > 255) {
      setSnackbar({ open: true, message: 'Justificativa deve ter no máximo 255 caracteres', severity: 'error', persist: false });
      setCancelSubmitting(false);
      return;
    }
    if (!cancelDialog.nProt || cancelDialog.nProt.trim().length === 0) {
      setSnackbar({ open: true, message: 'Protocolo de autorização (nProt) é obrigatório', severity: 'error', persist: false });
      setCancelSubmitting(false);
      return;
    }
    
    setCancelSubmitting(true);
    try {
      const payload = { nProt: cancelDialog.nProt.trim(), xJust: justificativaLimpa };
      const result = await nfcomService.cancelNFCom(activeCompany.id, cancelDialog.nfId, payload);

      // If backend returned cStat indicating rejection, it usually responds with HTTP 400
      // But if the backend returns success, show snackbar and reload.
      // Se o backend retornou detalhes da SEFAZ (resultado.cStat), mostramos o modal
      if (result && (result.cStat || (result.resultado && result.resultado.cStat))) {
        const cStat = result.cStat || (result.resultado && result.resultado.cStat);
        const xMotivo = result.xMotivo || (result.resultado && result.resultado.xMotivo) || (typeof result.detail === 'string' ? result.detail : '');
        setRejectionModal({
          open: true,
          cStat: cStat || '',
          xMotivo: xMotivo || '',
          resultado: result.resultado || result,
          nfId: cancelDialog.nfId,
          empresaId: activeCompany?.id || null,
          resending: false,
        });
        handleCloseCancel();
        loadNfcoms(page);
      } else {
        setSnackbar({ open: true, message: `Evento de cancelamento enviado para NFCom #${cancelDialog.nfId}`, severity: 'success', persist: false });
        handleCloseCancel();
        loadNfcoms(page);
      }
    } catch (error: any) {
      const isSefazRejection = !!(error.response && error.response.status === 400 && error.response.data && error.response.data.cStat);
      if (isSefazRejection) {
        setSnackbar(prev => ({ ...prev, open: false }));
        setRejectionModal({
          open: true,
          cStat: error.response.data.cStat,
          xMotivo: error.response.data.xMotivo || (typeof error.response.data.detail === 'string' ? error.response.data.detail : ''),
          resultado: error.response.data.resultado || null,
          nfId: cancelDialog.nfId,
          empresaId: activeCompany?.id || null,
          resending: false,
        });
        handleCloseCancel();
      } else {
        const errorMessage = stringifyError(error) || 'Erro ao enviar evento de cancelamento.';
        setSnackbar({ open: true, message: errorMessage, severity: 'error', persist: false });
      }
    } finally {
      setCancelSubmitting(false);
    }
  };

  const handleDownloadDebug = async (filePath: string, filename?: string) => {
    if (!rejectionModal.empresaId || !rejectionModal.nfId) return;
    try {
      const token = localStorage.getItem('token');
      // Usa a instância axios configurada que já tem a baseURL correta
      const resp = await api.post(`/empresas/${rejectionModal.empresaId}/nfcom/${rejectionModal.nfId}/download_debug`, { path: filePath }, { responseType: 'blob' });
      const blob = new Blob([resp.data], { type: resp.headers['content-type'] || 'application/octet-stream' });
      const link = document.createElement('a');
      link.href = window.URL.createObjectURL(blob);
      link.download = filename || (filePath.split('/').pop() || 'file.bin');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error: any) {
      console.error('Erro ao baixar arquivo de debug:', error);
      setSnackbar({ open: true, message: 'Falha ao baixar arquivo de debug', severity: 'error', persist: false });
    }
  };

  const handleViewTextContent = (title: string, content: string) => {
    // Abre nova janela com conteúdo em texto pré formatado
    const w = window.open('', '_blank');
    if (!w) {
      setSnackbar({ open: true, message: 'Não foi possível abrir a janela de visualização', severity: 'warning', persist: false });
      return;
    }
    w.document.title = title;
    const pre = w.document.createElement('pre');
    pre.style.whiteSpace = 'pre-wrap';
    pre.style.wordBreak = 'break-word';
    pre.textContent = content;
    w.document.body.appendChild(pre);
  };

  const loadServicos = async (search: string = '') => {
    if (!activeCompany) return;
    try {
      // Load a small page of services (first 10) to be used as default options
      const resp = await servicoService.getServicosByEmpresaPaginated(activeCompany.id, 1, 10, search || undefined);
      setServicos(resp.servicos || []);
    } catch (error) {
      console.error('Erro ao carregar serviços:', error);
      setServicos([]);
    }
  };

  const searchServicosForItem = (index: number, q: string) => {
    if (!activeCompany) return;
    if (searchTimeouts.current[index]) {
      clearTimeout(searchTimeouts.current[index]);
    }
    searchTimeouts.current[index] = setTimeout(async () => {
      try {
        if (searchControllers.current[index]) {
          try {
            searchControllers.current[index].abort();
          } catch (e) {}
        }
        const controller = new AbortController();
        searchControllers.current[index] = controller;
        const results = await servicoService.searchServicos(activeCompany.id, q, 20, controller.signal);
        setServicosOptions(prev => ({ ...prev, [index]: results || [] }));
      } catch (err: any) {
        if (err.name === 'CanceledError' || err.name === 'AbortError') {
          return;
        }
        console.error('Erro ao buscar serviços:', err);
      }
    }, 300);
  };

  useEffect(() => {
    return () => {
      Object.values(searchTimeouts.current).forEach((t) => clearTimeout(t));
      Object.values(searchControllers.current).forEach((c) => {
        try { c.abort(); } catch (e) {}
      });
    };
  }, []);

  const loadClients = async (search: string = '') => {
    if (!activeCompany) return;
    setClientLoading(true);
    try {
      // When search is empty, this returns the first page (limit 10)
      const response = await clientService.getClientsByCompany(activeCompany.id, 1, 10, search || undefined);
      setClients(response.clientes || []);
    } catch (error) {
      console.error("Erro ao carregar clientes:", error);
      setClients([]);
    } finally {
      setClientLoading(false);
    }
  };

  const loadContratosByCliente = async (clienteId: number) => {
    if (!activeCompany) return;
    try {
      const response = await api.get(`/servicos-contratados/cliente/${clienteId}?empresa_id=${activeCompany.id}`);
      console.log('loadContratosByCliente response:', response.data);
      return response.data;
    } catch (error) {
      console.error("Erro ao carregar contratos do cliente:", error);
      return [];
    }
  };

  const addContratosToNfcom = async (contratos: any[]) => {
    if (contratos.length === 0) return;

    // Filtrar apenas contratos ativos
    const contratosAtivos = contratos.filter((contrato: any) => contrato.is_active);

    if (contratosAtivos.length === 0) {
      setSnackbar({ open: true, message: 'Cliente não possui contratos ativos', severity: 'info', persist: false });
      return;
    }

    // Adicionar itens automaticamente baseados nos contratos
    const newItens = [...formData.itens];
    let addedCount = 0;
    const newSelectedServicos = { ...selectedServicos };

    for (const contrato of contratosAtivos) {
      console.log('Contrato (addContratosToNfcom):', contrato);
      // Se o contrato não traz defaults fiscais, buscar o serviço para preencher
      let servicoFallback: any = null;
      try {
        const needsFallback = (
          (!contrato.servico_cfop && !contrato.servico?.cfop) ||
          (contrato.servico_base_calculo_icms_default == null && contrato.servico?.base_calculo_icms_default == null) ||
          (contrato.servico_aliquota_icms_default == null && contrato.servico?.aliquota_icms_default == null) ||
          (contrato.servico_valor_desconto_default == null && contrato.servico?.valor_desconto_default == null)
        );
        if (needsFallback && contrato.servico_id) {
          try {
            servicoFallback = await servicoService.getServicoById(contrato.servico_id);
            console.log('servicoFallback:', servicoFallback);
          } catch (err) {
            console.warn('Erro ao buscar serviço fallback para contrato', contrato.servico_id, err);
            servicoFallback = null;
          }
        }
      } catch (e) {
        console.warn('Erro ao avaliar necessidade de fallback do contrato', e);
      }
      // Compatibilidade: alguns contratos podem retornar campos com prefixo servico_* ou um objeto nested 'servico'
      const svc_cfop = contrato.servico_cfop ?? contrato.servico?.cfop ?? '';
      const svc_ncm = contrato.servico_ncm ?? contrato.servico?.ncm ?? '';
      const svc_base_icms = contrato.servico_base_calculo_icms_default ?? contrato.servico?.base_calculo_icms_default ?? 0;
      const svc_aliquota_icms = contrato.servico_aliquota_icms_default ?? contrato.servico?.aliquota_icms_default ?? 0;
      const svc_valor_desconto = contrato.servico_valor_desconto_default ?? contrato.servico?.valor_desconto_default ?? 0;
      const svc_valor_outros = contrato.servico_valor_outros_default ?? contrato.servico?.valor_outros_default ?? 0;

      // Preparar objeto de serviço para o Autocomplete (mantém mesmos campos usados no search)
      const svcSource = servicoFallback || contrato.servico || {};

      // Criar item baseado no contrato, mapeando todos os campos disponíveis
      const newItem: NFComItemCreate = {
        servico_id: contrato.servico_id,
        // Preferir o campo cClass do serviço; se não existir, usar servico_codigo ou código
        cClass: (svcSource as any).cClass || contrato.servico_codigo || (svcSource as any).codigo || '',
        codigo_servico: contrato.servico_codigo || (svcSource as any).codigo || '',
        descricao_servico: contrato.servico_descricao || (svcSource as any).descricao || '',
        quantidade: contrato.quantidade || 1,
        unidade_medida: contrato.servico_unidade || (svcSource as any).unidade_medida || 'U',
        valor_unitario: contrato.valor_unitario != null ? contrato.valor_unitario : ((svcSource as any).valor_unitario ?? 0),
        valor_desconto: svc_valor_desconto || 0,
        valor_outros: svc_valor_outros || 0,
        valor_total: (contrato.quantidade || 1) * (contrato.valor_unitario || 0),
        cfop: svc_cfop || '',
        ncm: svc_ncm || '',
        base_calculo_icms: svc_base_icms || 0,
        aliquota_icms: svc_aliquota_icms || 0,
        base_calculo_pis: contrato.servico_base_calculo_pis_default ?? (svcSource as any).base_calculo_pis_default ?? 0,
        aliquota_pis: contrato.servico_aliquota_pis_default ?? (svcSource as any).aliquota_pis_default ?? 0,
        base_calculo_cofins: contrato.servico_base_calculo_cofins_default ?? (svcSource as any).base_calculo_cofins_default ?? 0,
        aliquota_cofins: contrato.servico_aliquota_cofins_default ?? (svcSource as any).aliquota_cofins_default ?? 0,
      };

      const svcObj: Servico = {
        id: contrato.servico_id,
        codigo: contrato.servico_codigo || (svcSource as any).codigo || '',
        descricao: contrato.servico_descricao || (svcSource as any).descricao || '',
        cClass: (svcSource as any).cClass || contrato.servico_codigo || (svcSource as any).codigo || '',
        unidade_medida: contrato.servico_unidade || (svcSource as any).unidade_medida || 'U',
        valor_unitario: contrato.valor_unitario != null ? contrato.valor_unitario : ((svcSource as any).valor_unitario ?? 0),
        cfop: svc_cfop || (svcSource as any).cfop || '',
        ncm: svc_ncm || (svcSource as any).ncm || '',
        base_calculo_icms_default: svc_base_icms || ((svcSource as any).base_calculo_icms_default ?? 0),
        aliquota_icms_default: svc_aliquota_icms || ((svcSource as any).aliquota_icms_default ?? 0),
        valor_desconto_default: svc_valor_desconto || ((svcSource as any).valor_desconto_default ?? 0),
        valor_outros_default: svc_valor_outros || ((svcSource as any).valor_outros_default ?? 0),
      } as any;

      // Index do novo item
      const newIndex = newItens.length;
      newItens.push(newItem);
  console.log('Novo item criado (addContratosToNfcom):', newItem, 'svcObj:', svcObj, 'index:', newIndex);
      newSelectedServicos[newIndex] = svcObj;
      addedCount++;
    }
    // Se pelo menos um contrato ativo foi usado, preencher os campos contratuais no nível da NFCom
    const primeiroContrato = contratosAtivos[0];
    // Também gerar faturas automaticamente a partir dos contratos
    const newFaturas: any[] = [];

    const computeVencimentoISO = (contr: any) => {
      try {
        // 1) se já tem vencimento explícito
        if (contr.vencimento) {
          const d = new Date(contr.vencimento);
          if (!isNaN(d.getTime())) return d.toISOString().split('T')[0];
        }

        // 2) derivar a partir de dia_emissao (próxima ocorrência)
        if (contr.dia_emissao) {
          const dia = Number(contr.dia_emissao);
          if (!isNaN(dia) && dia >= 1 && dia <= 31) {
            const today = new Date();
            let year = today.getFullYear();
            let month = today.getMonth(); // 0-based

            const lastDayOfMonth = (y: number, m: number) => new Date(y, m + 1, 0).getDate();
            const useDayCur = Math.min(dia, lastDayOfMonth(year, month));
            let candidate = new Date(year, month, useDayCur);
            if (candidate < new Date(new Date().setHours(0,0,0,0))) {
              // avançar para próximo mês
              if (month === 11) {
                year += 1;
                month = 0;
              } else {
                month += 1;
              }
              const useDayNext = Math.min(dia, lastDayOfMonth(year, month));
              candidate = new Date(year, month, useDayNext);
            }
            return candidate.toISOString().split('T')[0];
          }
        }

        // 3) fallback: d_contrato_fim ou d_contrato_ini
        if (contr.d_contrato_fim) {
          const d2 = new Date(contr.d_contrato_fim);
          if (!isNaN(d2.getTime())) return d2.toISOString().split('T')[0];
        }
        if (contr.d_contrato_ini) {
          const d3 = new Date(contr.d_contrato_ini);
          if (!isNaN(d3.getTime())) return d3.toISOString().split('T')[0];
        }

        return new Date().toISOString().split('T')[0];
      } catch (e) {
        return new Date().toISOString().split('T')[0];
      }
    };

    for (const contrato of contratosAtivos) {
      const valorFatura = (contrato.valor_total != null && contrato.valor_total !== '') ? Number(contrato.valor_total) : ((contrato.quantidade || 1) * (contrato.valor_unitario || 0));
      newFaturas.push({
        numero_fatura: contrato.numero_contrato ?? `CT${contrato.id}`,
        data_vencimento: computeVencimentoISO(contrato),
        valor_fatura: valorFatura || 0,
      });
    }

    // Atualiza o form com itens, faturas e campos contratuais
    const totalValor = newItens.reduce((s, it) => s + (it.valor_total || 0), 0);
    setFormData(prev => ({
      ...prev,
      itens: newItens,
      faturas: newFaturas,
      numero_contrato: primeiroContrato?.numero_contrato ?? prev.numero_contrato,
      d_contrato_ini: primeiroContrato?.d_contrato_ini ?? prev.d_contrato_ini,
      d_contrato_fim: primeiroContrato?.d_contrato_fim ?? prev.d_contrato_fim,
      valor_total: totalValor || prev.valor_total,
    }));
    setSelectedServicos(newSelectedServicos);

    if (addedCount > 0) {
      setSnackbar({
        open: true,
        message: `${addedCount} item(ns) adicionado(s) automaticamente dos contratos do cliente`,
        severity: 'success',
        persist: false
      });
    }
  };

  const resetForm = () => {
    setFormData({
      cliente_id: null,
      cliente_endereco_id: null,
      cMunFG: activeCompany?.codigo_ibge || '',
      finalidade_emissao: '0',
      tpFat: '0',
      data_emissao: new Date().toISOString().split('T')[0],
      itens: [],
      valor_total: 0,
      informacoes_adicionais: '',
      dest_endereco: '',
      dest_numero: '',
      dest_complemento: '',
      dest_bairro: '',
      dest_municipio: '',
      dest_uf: '',
      dest_cep: '',
      dest_codigo_ibge: '',
    });
    setErrors({});
    setSelectedServicos({});
    setClientAddresses([]);
    setEditingNfcom(null);
  };

  const handleOpenForm = () => {
    resetForm();
    // Prefetch defaults for autocompletes
    if (activeCompany) {
      void loadClients('');
      void loadServicos('');
    }
    setOpenForm(true);
    setActiveTab('general');
  };

  const handleEdit = async (nfcom: NFComType) => {
    const fullNfcom = await nfcomService.getNFComById(nfcom.empresa_id, nfcom.id);
    if (!fullNfcom || !fullNfcom.cliente) {
  setSnackbar({ open: true, message: 'Não foi possível carregar os dados completos da NFCom para edição.', severity: 'error', persist: false });
      return;
    }

    setEditingNfcom(fullNfcom);
    
    // Usar os endereços do cliente retornado pela API (que deve incluir endereços)
    let selectedAddressId = null;
    if (fullNfcom.cliente && fullNfcom.cliente.enderecos) {
      setClientAddresses(fullNfcom.cliente.enderecos);
      
      // Encontrar o endereço que corresponde aos dados da NFCom
      const matchingAddress = fullNfcom.cliente.enderecos.find(addr => 
        addr.endereco === fullNfcom.dest_endereco &&
        addr.numero === fullNfcom.dest_numero &&
        addr.bairro === fullNfcom.dest_bairro &&
        addr.municipio === fullNfcom.dest_municipio
      );
      if (matchingAddress) {
        selectedAddressId = matchingAddress.id;
      }
    } else {
      setClientAddresses([]);
    }

    setFormData({
      ...fullNfcom,
      data_emissao: new Date(fullNfcom.data_emissao).toISOString().split('T')[0],
      cliente_endereco_id: selectedAddressId,
    });
    
    const initialSelectedServicos: Record<number, Servico | null> = {};
    fullNfcom.itens.forEach((item, index) => {
        if(item.servico) {
            initialSelectedServicos[index] = item.servico;
        }
    });
    setSelectedServicos(initialSelectedServicos);
    // Ensure default services are loaded so item autocompletes can show defaults
    if (activeCompany) {
      await loadServicos('');
      // For each existing item, seed servicosOptions with the selected servico + defaults
      const seeded: Record<number, Servico[]> = {};
      Object.keys(initialSelectedServicos).forEach(k => {
        const idx = Number(k);
        const sel = initialSelectedServicos[idx];
        seeded[idx] = [ ...(sel ? [sel] : []), ...(servicos || []) ].filter((v, i, a) => a.findIndex(o => o?.id === v?.id) === i);
      });
      setServicosOptions(prev => ({ ...prev, ...seeded }));
    }

    setOpenForm(true);
    setActiveTab('general');
  };

  const handleCloseForm = () => {
    setOpenForm(false);
    resetForm();
  };

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const handleItemChange = (index: number, field: string, value: any) => {
    const newItens = [...formData.itens];
    const item = { ...newItens[index], [field]: value };
    const quant = typeof item.quantidade === 'number' ? item.quantidade : 0;
    const vlrUnit = typeof item.valor_unitario === 'number' ? item.valor_unitario : 0;
    const vlrDesc = typeof item.valor_desconto === 'number' ? item.valor_desconto : 0;
    const vlrOutro = typeof item.valor_outros === 'number' ? item.valor_outros : 0;
    item.valor_total = (quant * vlrUnit) - vlrDesc + vlrOutro;
    newItens[index] = item;
    setFormData(prev => ({ ...prev, itens: newItens }));
  };

  // Faturas handlers
  const handleAddFatura = () => {
    const newFaturas = [...(formData.faturas || [])];
    newFaturas.push({ numero_fatura: '', data_vencimento: '', valor_fatura: 0, codigo_barras: '' });
    setFormData(prev => ({ ...prev, faturas: newFaturas }));
  };

  const handleRemoveFatura = (index: number) => {
    const newFaturas = [...(formData.faturas || [])];
    newFaturas.splice(index, 1);
    setFormData(prev => ({ ...prev, faturas: newFaturas }));
  };

  const handleFaturaChange = (index: number, field: string, value: any) => {
    const newFaturas = [...(formData.faturas || [])];
    const f = { ...newFaturas[index], [field]: value };
    newFaturas[index] = f;
    setFormData(prev => ({ ...prev, faturas: newFaturas }));
  };

  const applyServiceToItem = (index: number, patch: Record<string, any>) => {
    const newItens = [...formData.itens];
    const existing = newItens[index] || {};
    const item = { ...existing, ...patch };
    const quant = typeof item.quantidade === 'number' ? item.quantidade : 0;
    const vlrUnit = typeof item.valor_unitario === 'number' ? item.valor_unitario : 0;
    const vlrDesc = typeof item.valor_desconto === 'number' ? item.valor_desconto : 0;
    const vlrOutro = typeof item.valor_outros === 'number' ? item.valor_outros : 0;
    item.valor_total = (quant * vlrUnit) - vlrDesc + vlrOutro;
    newItens[index] = item;
    setFormData(prev => ({ ...prev, itens: newItens }));
  };

  const handleAddItem = async () => {
    // Se há um cliente selecionado e não estamos editando, verificar contratos
    if (formData.cliente_id && !editingNfcom) {
      try {
        const contratos = await loadContratosByCliente(formData.cliente_id);
        const contratosAtivos = contratos.filter((contrato: any) => contrato.is_active);

        if (contratosAtivos.length > 0) {
          // Adicionar itens baseados nos contratos
          const newItens = [...formData.itens];
          let addedCount = 0;

          for (const contrato of contratosAtivos) {
            console.log('Contrato (handleAddItem):', contrato);
            // Se o contrato não traz defaults fiscais, buscar o serviço para preencher
            let servicoFallback: any = null;
            try {
              const needsFallback = (
                (!contrato.servico_cfop && !contrato.servico?.cfop) ||
                (contrato.servico_base_calculo_icms_default == null && contrato.servico?.base_calculo_icms_default == null) ||
                (contrato.servico_aliquota_icms_default == null && contrato.servico?.aliquota_icms_default == null) ||
                (contrato.servico_valor_desconto_default == null && contrato.servico?.valor_desconto_default == null)
              );
              if (needsFallback && contrato.servico_id) {
                try {
                  servicoFallback = await servicoService.getServicoById(contrato.servico_id);
                  console.log('servicoFallback:', servicoFallback);
                } catch (err) {
                  console.warn('Erro ao buscar serviço fallback para contrato', contrato.servico_id, err);
                  servicoFallback = null;
                }
              }
            } catch (e) {
              console.warn('Erro ao avaliar necessidade de fallback do contrato', e);
            }

            // Compatibilidade: alguns contratos podem retornar campos com prefixo servico_* ou um objeto nested 'servico'
            const svc_cfop = contrato.servico_cfop ?? contrato.servico?.cfop ?? servicoFallback?.cfop ?? '';
            const svc_ncm = contrato.servico_ncm ?? contrato.servico?.ncm ?? servicoFallback?.ncm ?? '';
            const svc_base_icms = contrato.servico_base_calculo_icms_default ?? contrato.servico?.base_calculo_icms_default ?? servicoFallback?.base_calculo_icms_default ?? 0;
            const svc_aliquota_icms = contrato.servico_aliquota_icms_default ?? contrato.servico?.aliquota_icms_default ?? servicoFallback?.aliquota_icms_default ?? 0;
            const svc_valor_desconto = contrato.servico_valor_desconto_default ?? contrato.servico?.valor_desconto_default ?? servicoFallback?.valor_desconto_default ?? 0;
            const svc_valor_outros = contrato.servico_valor_outros_default ?? contrato.servico?.valor_outros_default ?? servicoFallback?.valor_outros_default ?? 0;

            const svcSource = servicoFallback || contrato.servico || {};

            const newItem: NFComItemCreate = {
              servico_id: contrato.servico_id,
              cClass: (svcSource as any).cClass || contrato.servico_codigo || (svcSource as any).codigo || '',
              codigo_servico: contrato.servico_codigo || (svcSource as any).codigo || '',
              descricao_servico: contrato.servico_descricao || (svcSource as any).descricao || '',
              quantidade: contrato.quantidade || 1,
              unidade_medida: contrato.servico_unidade || (svcSource as any).unidade_medida || 'U',
              valor_unitario: contrato.valor_unitario != null ? contrato.valor_unitario : ((svcSource as any).valor_unitario ?? 0),
              valor_desconto: svc_valor_desconto || 0,
              valor_outros: svc_valor_outros || 0,
              valor_total: (contrato.quantidade || 1) * (contrato.valor_unitario || 0),
              cfop: svc_cfop || '',
              ncm: svc_ncm || '',
              base_calculo_icms: svc_base_icms || 0,
              aliquota_icms: svc_aliquota_icms || 0,
              base_calculo_pis: contrato.servico_base_calculo_pis_default ?? (svcSource as any).base_calculo_pis_default ?? 0,
              aliquota_pis: contrato.servico_aliquota_pis_default ?? (svcSource as any).aliquota_pis_default ?? 0,
              base_calculo_cofins: contrato.servico_base_calculo_cofins_default ?? (svcSource as any).base_calculo_cofins_default ?? 0,
              aliquota_cofins: contrato.servico_aliquota_cofins_default ?? (svcSource as any).aliquota_cofins_default ?? 0,
            };

            // NOTA: campos contratuais são mantidos no nível da NFCom (formData) — não devem ser adicionados aos itens

            // Preparar objeto de serviço para Autocomplete (usa fallback se disponível)
            const svcObj: Servico = {
              id: contrato.servico_id,
              codigo: contrato.servico_codigo || (svcSource as any).codigo || '',
              descricao: contrato.servico_descricao || (svcSource as any).descricao || '',
              cClass: (svcSource as any).cClass || contrato.servico_codigo || (svcSource as any).codigo || '',
              unidade_medida: contrato.servico_unidade || (svcSource as any).unidade_medida || 'U',
              valor_unitario: contrato.valor_unitario != null ? contrato.valor_unitario : ((svcSource as any).valor_unitario ?? 0),
              cfop: svc_cfop || (svcSource as any).cfop || '',
              ncm: svc_ncm || (svcSource as any).ncm || '',
              base_calculo_icms_default: svc_base_icms || ((svcSource as any).base_calculo_icms_default ?? 0),
              aliquota_icms_default: svc_aliquota_icms || ((svcSource as any).aliquota_icms_default ?? 0),
              valor_desconto_default: svc_valor_desconto || ((svcSource as any).valor_desconto_default ?? 0),
              valor_outros_default: svc_valor_outros || ((svcSource as any).valor_outros_default ?? 0),
            } as any;

            const newIndex = newItens.length;
            newItens.push(newItem);
            // Marcar serviço selecionado para que o Autocomplete exiba a descrição
            console.log('Novo item criado (handleAddItem):', newItem, 'svcObj:', svcObj, 'index:', newIndex);
            setSelectedServicos(prev => ({ ...prev, [newIndex]: svcObj }));
            addedCount++;
          }

          // Ao adicionar itens a partir de contratos via handleAddItem, também popular os campos contratuais na NFCom
          const primeiroContrato = contratosAtivos[0];

          // Calcular data de emissão da NFCom (usar data atual se não definida)
          const dataEmissao = formData.data_emissao ? new Date(formData.data_emissao) : new Date();

          // Criar faturas para cada item adicionado
          const novasFaturas = [...(formData.faturas || [])];

          for (const contrato of contratosAtivos) {
            // Calcular vencimento: dia do contrato + ano/mês da emissão da NFCom
            let dataVencimento: Date | null = null;
            if (contrato.dia_emissao) {
              // Usar o dia do vencimento do contrato
              const diaVencimento = contrato.dia_emissao;
              dataVencimento = new Date(dataEmissao.getFullYear(), dataEmissao.getMonth(), diaVencimento);

              // Se o dia já passou este mês, vencimento no próximo mês
              if (dataVencimento <= dataEmissao) {
                dataVencimento.setMonth(dataVencimento.getMonth() + 1);
              }
            }

            // Criar fatura para este item
            const novaFatura = {
              numero_fatura: contrato.numero_contrato || `FAT-${contrato.id}`,
              data_vencimento: dataVencimento ? dataVencimento.toISOString().split('T')[0] : '',
              valor_fatura: contrato.valor_total || (contrato.quantidade * contrato.valor_unitario) || 0,
              codigo_barras: contrato.codigo_barras || ''
            };

            novasFaturas.push(novaFatura);
          }

          setFormData(prev => ({
            ...prev,
            itens: newItens,
            numero_contrato: primeiroContrato?.numero_contrato ?? prev.numero_contrato,
            d_contrato_ini: primeiroContrato?.d_contrato_ini ?? prev.d_contrato_ini,
            d_contrato_fim: primeiroContrato?.d_contrato_fim ?? prev.d_contrato_fim,
            faturas: novasFaturas
          }));
          if (addedCount > 0) {
            setSnackbar({
              open: true,
              message: `${addedCount} item(ns) do contrato adicionado(s) automaticamente`,
              severity: 'success',
              persist: false
            });
          }
          return;
        }
      } catch (error) {
        console.error('Erro ao carregar contratos:', error);
        // Continua para adicionar item vazio se houver erro
      }
    }

    // Adicionar item vazio (comportamento padrão)
    const newItem: NFComItemCreate = {
      cClass: '',
      codigo_servico: '',
      descricao_servico: '',
      quantidade: 1,
      unidade_medida: 'U',
      valor_unitario: 0,
      valor_desconto: 0,
      valor_outros: 0,
      valor_total: 0,
      cfop: '',
      ncm: '',
      base_calculo_icms: 0,
      aliquota_icms: 0,
      base_calculo_pis: 0,
      aliquota_pis: 0,
      base_calculo_cofins: 0,
      aliquota_cofins: 0,
    };
    setFormData(prev => ({ ...prev, itens: [...prev.itens, newItem] }));
  };

  const handleRemoveItem = (index: number) => {
    const newItens = formData.itens.filter((_, i) => i !== index);
    setFormData(prev => ({ ...prev, itens: newItens }));
    setSelectedServicos(prev => {
      const newSelected = { ...prev };
      delete newSelected[index];
      return newSelected;
    });
  };
  
  useEffect(() => {
    const total = formData.itens.reduce((sum, item) => sum + (item.valor_total || 0), 0);
    setFormData(prev => ({ ...prev, valor_total: total }));
  }, [formData.itens]);

  const handleSubmit = async () => {
    // Validação dos campos obrigatórios
    const newErrors: Record<string, string> = {};

    if (!formData.data_emissao) {
      newErrors.data_emissao = 'Data de emissão é obrigatória';
    }

    if (!formData.cliente_id) {
      newErrors.cliente_id = 'Cliente é obrigatório';
    }

    if (!editingNfcom && !formData.cliente_endereco_id) {
      newErrors.cliente_endereco_id = 'Endereço do cliente é obrigatório';
    }

    if (formData.itens.length === 0) {
      newErrors.itens = 'Adicione pelo menos um item à nota';
    }

    // Verificar se há erros
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      setSnackbar({ open: true, message: 'Preencha todos os campos obrigatórios', severity: 'warning', persist: false });
      return;
    }

    if (!activeCompany) {
      setSnackbar({ open: true, message: 'Nenhuma empresa ativa selecionada.', severity: 'warning', persist: false });
      return;
    }

    const selectedAddress = editingNfcom 
      ? null // Na edição, o endereço já está nos campos dest_*
      : clientAddresses?.find(addr => addr.id === formData.cliente_endereco_id);
    
    if (!editingNfcom && !selectedAddress) {
      setSnackbar({ open: true, message: 'Endereço do cliente não encontrado.', severity: 'error', persist: false });
      return;
    }

    setSubmitting(true);

    const payload: NFComCreate = {
      ...formData,
      cliente_id: formData.cliente_id,
      dest_endereco: editingNfcom ? formData.dest_endereco : selectedAddress.endereco,
      dest_numero: editingNfcom ? formData.dest_numero : selectedAddress.numero,
      dest_complemento: editingNfcom ? formData.dest_complemento : selectedAddress.complemento,
      dest_bairro: editingNfcom ? formData.dest_bairro : selectedAddress.bairro,
      dest_municipio: editingNfcom ? formData.dest_municipio : selectedAddress.municipio,
      dest_uf: editingNfcom ? formData.dest_uf : selectedAddress.uf,
      dest_cep: editingNfcom ? formData.dest_cep : selectedAddress.cep,
      dest_codigo_ibge: editingNfcom ? formData.dest_codigo_ibge : selectedAddress.codigo_ibge,
    };
    delete (payload as any).cliente_endereco_id;

    try {
      if (editingNfcom) {
        await nfcomService.updateNFCom(editingNfcom.empresa_id, editingNfcom.id, payload);
  setSnackbar({ open: true, message: `NFCom #${editingNfcom.numero_nf} atualizada com sucesso!`, severity: 'success', persist: false });
      } else {
        await nfcomService.createNFCom(activeCompany.id, payload);
  setSnackbar({ open: true, message: `NFCom emitida com sucesso!`, severity: 'success', persist: false });
      }
      handleCloseForm();
      loadNfcoms(editingNfcom ? page : 1); // Refresh current page or go to first on create
      if (!editingNfcom) setPage(1);
    } catch (error: any) {
      console.error(`Erro ao ${editingNfcom ? 'atualizar' : 'emitir'} NFCom:`, error);
      const errorMsg = stringifyError(error) || 'Verifique os dados e tente novamente.';
  setSnackbar({ open: true, message: `Erro: ${errorMsg}`, severity: 'error', persist: false });
    } finally {
      setSubmitting(false);
    }
  };

  // Funções para exclusão de notas
  const handleSelectNfcom = (nfcomId: number, selected: boolean) => {
    setSelectedNfcoms(prev => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(nfcomId);
      } else {
        newSet.delete(nfcomId);
      }
      return newSet;
    });
  };

  const handleSelectAllNfcoms = (selected: boolean) => {
    if (selected) {
      // Selecionar notas que não estão canceladas (permitir autorisadas também)
      const nonCancelledNfcoms = nfcoms.filter(nf => (nf as any).status !== 'cancelada').map(nf => nf.id);
      setSelectedNfcoms(new Set(nonCancelledNfcoms));
    } else {
      setSelectedNfcoms(new Set());
    }
  };

  const handleDeleteSelectedNfcoms = async () => {
    if (selectedNfcoms.size === 0) {
      setSnackbar({ open: true, message: 'Nenhuma nota selecionada para exclusão', severity: 'warning', persist: false });
      return;
    }

    if (!activeCompany) return;

    // Obter todas as notas não autorizadas, ordenadas por número decrescente
    const nonAuthorizedNfcoms = nfcoms
      .filter(nf => !nf.protocolo_autorizacao)
      .sort((a, b) => b.numero_nf - a.numero_nf);

    // Verificar se alguma nota selecionada está autorizada ou cancelada
    const selectedNfcomsData = nfcoms.filter(nf => selectedNfcoms.has(nf.id));
    const authorizedNfcoms = selectedNfcomsData.filter(nf => !!nf.protocolo_autorizacao);
    const cancelledNfcoms = selectedNfcomsData.filter(nf => (nf as any).status === 'cancelada');

    if (authorizedNfcoms.length > 0 || cancelledNfcoms.length > 0) {
      const parts = [] as string[];
      if (authorizedNfcoms.length > 0) parts.push(`autorizadas: ${authorizedNfcoms.map(nf => `#${nf.numero_nf}`).join(', ')}`);
      if (cancelledNfcoms.length > 0) parts.push(`canceladas: ${cancelledNfcoms.map(nf => `#${nf.numero_nf}`).join(', ')}`);
      setSnackbar({
        open: true,
        message: `Não é possível excluir notas ${parts.join(' e ')}`,
        severity: 'error',
        persist: false
      });
      return;
    }

    // Validar sequência: as notas selecionadas devem ser as últimas N notas em sequência
    const selectedNumbers = selectedNfcomsData
      .map(nf => nf.numero_nf)
      .sort((a, b) => b - a); // Ordenar decrescente

    // Verificar se forma uma sequência contínua a partir da última nota
    const maxSelectedNumber = Math.max(...selectedNumbers);
    const minSelectedNumber = Math.min(...selectedNumbers);
    const expectedSequence = Array.from(
      { length: maxSelectedNumber - minSelectedNumber + 1 },
      (_, i) => maxSelectedNumber - i
    );

    const isValidSequence = selectedNumbers.length === expectedSequence.length &&
      selectedNumbers.every((num, index) => num === expectedSequence[index]);

    // Verificar se são as últimas notas da sequência geral
    const lastNonAuthorizedNumber = nonAuthorizedNfcoms[0]?.numero_nf || 0;
    const isFromEnd = maxSelectedNumber === lastNonAuthorizedNumber;

    if (!isValidSequence || !isFromEnd) {
      setSnackbar({
        open: true,
        message: 'Só é possível excluir as últimas notas em sequência contínua, sem deixar furos na numeração',
        severity: 'error',
        persist: false
      });
      return;
    }

    setDeletingNfcoms(true);
    let deletedCount = 0;
    let errors: string[] = [];

    try {
      for (const nfcom of selectedNfcomsData) {
        try {
          await nfcomService.deleteNFCom(activeCompany.id, nfcom.id);
          deletedCount++;
          setSnackbar({
            open: true,
            message: `Nota #${nfcom.numero_nf} excluída com sucesso`,
            severity: 'success',
            persist: false
          });
        } catch (error: any) {
          const errorMsg = stringifyError(error) || `Erro ao excluir nota #${nfcom.numero_nf}`;
          errors.push(errorMsg);
          setSnackbar({
            open: true,
            message: errorMsg,
            severity: 'error',
            persist: false
          });
        }
      }

      // Limpar seleção
      setSelectedNfcoms(new Set());

      // Recarregar lista
      loadNfcoms(page);

      // Resumo final
      if (deletedCount > 0) {
        setSnackbar({
          open: true,
          message: `${deletedCount} nota(s) excluída(s) com sucesso${errors.length > 0 ? `. ${errors.length} erro(s) encontrado(s)` : ''}`,
          severity: errors.length > 0 ? 'warning' : 'success',
          persist: false
        });
      }

    } catch (error) {
      console.error('Erro geral na exclusão:', error);
    } finally {
      setDeletingNfcoms(false);
    }
  };

  const handleSendSelectedEmails = async () => {
    if (selectedNfcoms.size === 0) {
      setSnackbar({ open: true, message: 'Nenhuma nota selecionada para envio', severity: 'warning' , persist: false });
      return;
    }

    if (!activeCompany) return;

    // Client-side validation: pendentes não podem ser enviados; canceladas não podem nenhuma ação
    const selectedNfcomsData = nfcoms.filter(nf => selectedNfcoms.has(nf.id));
    const pending = selectedNfcomsData.filter(nf => !nf.protocolo_autorizacao && (nf as any).status !== 'cancelada');
    const cancelled = selectedNfcomsData.filter(nf => (nf as any).status === 'cancelada');
    if (cancelled.length > 0) {
      setSnackbar({ open: true, message: `Notas canceladas não podem ser enviadas por email: ${cancelled.map(n => `#${n.numero_nf}`).join(', ')}`, severity: 'warning', persist: false });
      return;
    }
    if (pending.length > 0) {
      setSnackbar({ open: true, message: `Notas pendentes não podem ser enviadas por email: ${pending.map(n => `#${n.numero_nf}`).join(', ')}`, severity: 'warning', persist: false });
      return;
    }

    setSendingEmails(true);
    try {
      const ids = Array.from(selectedNfcoms);
      const result = await nfcomService.sendEmails(activeCompany.id, ids);
      // result.results is expected
      const successes = (result.results || []).filter((r: any) => r.sent).length;
      const failures = (result.results || []).filter((r: any) => !r.sent);
      setSnackbar({ open: true, message: `${successes} emails enviados, ${failures.length} falhas`, severity: failures.length === 0 ? 'success' : 'warning', persist: false });
      if (failures.length > 0) console.warn('Falhas no envio de email:', failures);
      // limpar seleção após envio
      setSelectedNfcoms(new Set());
      loadNfcoms(page);
    } catch (error: any) {
      console.error('Erro ao enviar emails:', error);
      // backend pode retornar 400 com detail.invalid list
      if (error?.response?.data?.invalid) {
        const invalid = error.response.data.invalid as any[];
        setSnackbar({ open: true, message: `Ação inválida para algumas notas: ${invalid.map(i => `${i.nfcom_id}:${i.reason}`).join(', ')}`, severity: 'error', persist: false });
      } else {
        setSnackbar({ open: true, message: stringifyError(error) || 'Erro ao enviar emails', severity: 'error', persist: false });
      }
    } finally {
      setSendingEmails(false);
    }
  };

  const handleTransmitSelectedNfcoms = async () => {
    if (selectedNfcoms.size === 0) {
      setSnackbar({ open: true, message: 'Nenhuma nota selecionada para transmissão', severity: 'warning' , persist: false });
      return;
    }

    if (!activeCompany) return;

    const selectedNfcomsData = nfcoms.filter(nf => selectedNfcoms.has(nf.id));
    // Consideramos 'pendente' quando não tem protocolo_autorizacao and status !== 'cancelada'
    const notPending = selectedNfcomsData.filter(nf => nf.protocolo_autorizacao || (nf as any).status === 'cancelada');
    if (notPending.length > 0) {
      const autorizadas = notPending.filter(nf => nf.protocolo_autorizacao).map(n => `#${n.numero_nf}`);
      const canceladas = notPending.filter(nf => (nf as any).status === 'cancelada').map(n => `#${n.numero_nf}`);
      const parts: string[] = [];
      if (autorizadas.length) parts.push(`Autorizadas: ${autorizadas.join(', ')}`);
      if (canceladas.length) parts.push(`Canceladas: ${canceladas.join(', ')}`);
      setSnackbar({ open: true, message: `Somente notas pendentes podem ser transmitidas. ${parts.join(' - ')}`, severity: 'warning', persist: false });
      return;
    }

    setTransmittingBulk(true);
    try {
      const ids = Array.from(selectedNfcoms);
      const result = await nfcomService.bulkTransmit(activeCompany.id, ids);
      // result is expected to contain successes and failures as implemented on backend
      const successes = result.successes || [];
      const failures = result.failures || [];
      if (failures.length === 0) {
        setSnackbar({ open: true, message: `Transmissão em lote concluída: ${successes.length} notas transmitidas`, severity: 'success', persist: false });
      } else {
        // show first failure in snackbar and log details
        const first = failures[0];
        setSnackbar({ open: true, message: `Falha na transmissão em lote. Nota ${first.nfcom_id} -> ${first.reason || first.message || 'Erro'}`, severity: 'error', persist: false });
        console.warn('Detalhes das falhas na transmissão em lote:', failures);
      }
      // refresh list and clear selection for those successfully transmitted
      setSelectedNfcoms(new Set());
      loadNfcoms(page);
    } catch (error: any) {
      console.error('Erro na transmissão em lote:', error);
      if (error?.response?.data?.invalid) {
        const invalid = error.response.data.invalid as any[];
        setSnackbar({ open: true, message: `Ação inválida para algumas notas: ${invalid.map(i => `${i.nfcom_id}:${i.reason}`).join(', ')}`, severity: 'error', persist: false });
      } else {
        setSnackbar({ open: true, message: stringifyError(error) || 'Erro na transmissão em lote', severity: 'error', persist: false });
      }
    } finally {
      setTransmittingBulk(false);
    }
  };

  if (!activeCompany) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6">Nenhuma empresa ativa</Typography>
        <Typography variant="body2" color="text.secondary">Selecione uma empresa para emitir NFCom.</Typography>
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
          Emissão de NFCom
        </Typography>
        <Button
          variant="contained"
          startIcon={<PlusIcon className="w-5 h-5" />}
          sx={{ py: 1.5, width: { xs: '100%', sm: 'auto' } }}
          onClick={handleOpenForm}
        >
          Nova NFCom
        </Button>
      </Box>

      {/* Dashboard Section */}
      <Box sx={{ mb: 4, display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(4, 1fr)' }, gap: 3 }}>
        <Card sx={{ background: 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)' }}>
          <CardContent sx={{ textAlign: 'center' }}>
            <StatNumber value={totalRows} color="#1976d2" />
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>Total de NFComs</Typography>
          </CardContent>
        </Card>
        <Card sx={{ background: 'linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%)' }}>
          <CardContent sx={{ textAlign: 'center' }}>
            <StatNumber value={totalAutorizadas} color="#388e3c" />
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>Autorizadas</Typography>
          </CardContent>
        </Card>
        <Card sx={{ background: 'linear-gradient(135deg, #fff3e0 0%, #ffcc80 100%)' }}>
          <CardContent sx={{ textAlign: 'center' }}>
            <StatNumber value={totalPendentes} color="#f57c00" />
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>Pendentes</Typography>
          </CardContent>
        </Card>
      </Box>

      <Paper sx={{ p: { xs: 1, sm: 2 }, backgroundColor: 'grey.50',  display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">NFComs emitidas</Typography>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <IconButton size="small" onClick={(e: any) => setMenuAnchorEl(e.currentTarget)} aria-label="Ações" aria-controls={menuOpen ? 'nfcom-actions-menu' : undefined} aria-haspopup="true" aria-expanded={menuOpen ? 'true' : undefined}>
              <MoreVertIcon />
            </IconButton>
            <Menu id="nfcom-actions-menu" anchorEl={menuAnchorEl} open={menuOpen} onClose={() => setMenuAnchorEl(null)}>
              <MenuItem onClick={() => { setMenuAnchorEl(null); setConfirmDeleteDialog(true); }} disabled={selectedNfcoms.size === 0 || deletingNfcoms}>
                {deletingNfcoms ? 'Excluindo...' : `Excluir ${selectedNfcoms.size} nota(s)`}
              </MenuItem>
              <MenuItem onClick={() => { setMenuAnchorEl(null); handleSendSelectedEmails(); }} disabled={selectedNfcoms.size === 0 || sendingEmails}>
                {sendingEmails ? 'Enviando...' : `Enviar por e-mail (${selectedNfcoms.size})`}
              </MenuItem>
              <MenuItem onClick={() => { setMenuAnchorEl(null); handleTransmitSelectedNfcoms(); }} disabled={selectedNfcoms.size === 0 || transmittingBulk || transmittingId !== null}>
                {transmittingBulk ? 'Transmitindo...' : `Transmitir selecionadas (${selectedNfcoms.size})`}
              </MenuItem>
              <MenuItem onClick={() => { setMenuAnchorEl(null); handleDownloadSelectedXmls(); }} disabled={selectedNfcoms.size === 0}>
                Baixar XMLs ({selectedNfcoms.size})
              </MenuItem>
              <MenuItem onClick={() => { setMenuAnchorEl(null); handleDownloadSelectedDanfes(); }} disabled={selectedNfcoms.size === 0}>
                Baixar DANFEs ({selectedNfcoms.size})
              </MenuItem>
              <MenuItem onClick={() => { setMenuAnchorEl(null); loadNfcoms(page); }}>
                Atualizar
              </MenuItem>
            </Menu>
          </Box>
        </Box>
        {loading ? (
          <Box sx={{ textAlign: 'center', p: 4 }}><CircularProgress /></Box>
        ) : nfcoms.length === 0 ? (
          <Box sx={{ textAlign: 'center', p: 4, backgroundColor: '#fff', borderRadius: 2 }}>
            <DocumentTextIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            {hasFiltersApplied() ? (
              <>
                <Typography variant="h6" gutterBottom>Nenhum resultado encontrado</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Não foram encontradas NFComs com os filtros aplicados.
                </Typography>
                <Button variant="outlined" onClick={clearFilters}>Limpar Filtros</Button>
              </>
            ) : (
              <>
                <Typography variant="h6" gutterBottom>Nenhuma NFCom emitida</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Comece emitindo sua primeira Nota Fiscal de Comunicação.</Typography>
                <Button variant="outlined" startIcon={<PlusIcon className="w-5 h-5" />} onClick={handleOpenForm}>Emitir Primeira NFCom</Button>
              </>
            )}
          </Box>
        ) : (
          <>
            {/* Search and Filters - Always visible at top */}
            <Box sx={{ mb: 2, flexShrink: 0 }}>
              {/* Main Search Bar */}
              <Box sx={{ mb: 1 }}>
                <TextField
                  fullWidth
                  variant="outlined"
                  placeholder="Buscar por número, cliente ou ID..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  size="small"
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <MagnifyingGlassIcon className="w-4 h-4 text-gray-400" />
                      </InputAdornment>
                    ),
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          size="small"
                          onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
                          sx={{
                            color: showAdvancedFilters ? 'primary.main' : 'text.secondary',
                            '&:hover': { color: 'primary.main' },
                            p: 0.5
                          }}
                        >
                          <svg
                            className={`w-3 h-3 transition-transform ${showAdvancedFilters ? 'rotate-180' : ''}`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </IconButton>
                        {searchTerm && (
                          <IconButton size="small" onClick={() => setSearchTerm('')} sx={{ p: 0.5 }}>
                            <XMarkIcon className="w-3 h-3" />
                          </IconButton>
                        )}
                      </InputAdornment>
                    )
                  }}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      borderRadius: 2,
                      backgroundColor: 'background.paper',
                      '&:hover': {
                        backgroundColor: 'action.hover',
                      },
                      '&.Mui-focused': {
                        backgroundColor: 'background.paper',
                      }
                    }
                  }}
                />
              </Box>

              {/* Advanced Filters */}
              {showAdvancedFilters && (
                <Paper
                  elevation={1}
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    background: 'linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%)',
                    border: '1px solid #e3f2fd',
                    mb: 2
                  }}
                >
                  <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 'bold', color: 'primary.main' }}>
                    🔍 Filtros Avançados
                  </Typography>

                  <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)' }, gap: 2 }}>
                    {/* Período de Datas */}
                    <Box>
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <TextField
                          type="date"
                          label="De"
                          value={dateFrom}
                          onChange={(e) => setDateFrom(e.target.value)}
                          size="small"
                          InputLabelProps={{ shrink: true }}
                          fullWidth
                        />
                        <TextField
                          type="date"
                          label="Até"
                          value={dateTo}
                          onChange={(e) => setDateTo(e.target.value)}
                          size="small"
                          InputLabelProps={{ shrink: true }}
                          fullWidth
                        />
                      </Box>
                    </Box>

                    {/* Status */}
                    <Box>
                      <FormControl fullWidth size="small">
                        <InputLabel>Status</InputLabel>
                        <Select
                          value={statusFilter}
                          onChange={(e) => setStatusFilter(e.target.value as 'all' | 'authorized' | 'pending')}
                          label="Status"
                        >
                          <MenuItem value="all">Todos</MenuItem>
                          <MenuItem value="authorized">Autorizadas</MenuItem>
                          <MenuItem value="pending">Pendentes</MenuItem>
                        </Select>
                      </FormControl>
                    </Box>
                  </Box>

                  {/* Botões de Ação */}
                  <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mt: 2 }}>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => {
                        setDateFrom('');
                        setDateTo('');
                        setStatusFilter('all');
                        setMinValue('');
                        setMaxValue('');
                        setSearchTerm('');
                        setPage(1);
                      }}
                      startIcon={<XMarkIcon className="w-3 h-3" />}
                      disabled={loading}
                    >
                      Limpar
                    </Button>
                  </Box>
                </Paper>
              )}
            </Box>

            {/* Mobile Card View - Scrollable */}
            <Box sx={{ display: { xs: 'block', md: 'none' }, flex: 1, overflow: 'auto' }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                {nfcoms.map((n) => {
                  const emissao = n.data_emissao ? new Date(n.data_emissao).toLocaleDateString('pt-BR') : 'N/A';
                  const numero = n.numero_nf ? `${n.numero_nf}` : 'N/A';
                  const serie = n.serie ? `Série ${n.serie}` : '';
                  const clienteNome = n.cliente?.nome_razao_social || 'Cliente não identificado';
                  const isAuthorized = !!n.protocolo_autorizacao;
                  const isCancelled = (n as any).status === 'cancelada';
                  const status = isCancelled ? 'Cancelada' : (isAuthorized ? 'Autorizada' : 'Pendente');
                  const statusColor = isCancelled ? 'error' : (isAuthorized ? 'success' : 'warning');
                  const protocolo = n.protocolo_autorizacao ? `Prot: ${n.protocolo_autorizacao}` : '';

                  return (
                    <Card key={n.id} variant="outlined" sx={{ borderRadius: 2 }}>
                      <CardContent sx={{ p: 2 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0, flex: 1 }}>
                            {!isCancelled && (
                              <Checkbox
                                size="small"
                                checked={selectedNfcoms.has(n.id)}
                                onChange={(e) => handleSelectNfcom(n.id, e.target.checked)}
                                sx={{ p: 0.5 }}
                              />
                            )}
                            <Box sx={{ minWidth: 0, flex: 1 }}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                                <Typography variant="h6" sx={{ fontWeight: 'bold', fontSize: '1rem' }}>
                                  NF #{numero}
                                </Typography>
                                {serie && (
                                  <Chip label={serie} size="small" variant="outlined" sx={{ fontSize: '0.7rem', height: 20 }} />
                                )}
                              </Box>
                              <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.85rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={clienteNome}>
                                {clienteNome}
                              </Typography>
                              {(n.dest_municipio || n.dest_uf) && (
                                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                                  {n.dest_municipio ? n.dest_municipio : ''}{n.dest_municipio && n.dest_uf ? '/' : ''}{n.dest_uf ? n.dest_uf : ''}
                                </Typography>
                              )}
                              {protocolo && (
                                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                                  {protocolo}
                                </Typography>
                              )}
                            </Box>
                          </Box>
                          <Chip label={status} color={statusColor} size="small" sx={{ flexShrink: 0, fontSize: '0.7rem' }} />
                        </Box>
                        
                        <Divider sx={{ my: 1 }} />

                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
                          <Box>
                            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>Emissão</Typography>
                            <Typography variant="body2" sx={{ fontSize: '0.85rem' }}>{emissao}</Typography>
                          </Box>
                          <Box sx={{ textAlign: 'right' }}>
                            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>Valor Total</Typography>
                            <Typography variant="h6" sx={{ fontWeight: 'bold', fontSize: '1rem' }}>
                              {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(n.valor_total || 0)}
                            </Typography>
                          </Box>
                        </Box>

                        <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                          {!isAuthorized && !isCancelled && n.xml_gerado && (
                            <Tooltip title="Transmitir para SEFAZ">
                              <span>
                                <IconButton size="small" onClick={() => handleTransmit(n)} disabled={transmittingId !== null} sx={{ p: 0.5 }}>
                                  {transmittingId === n.id 
                                    ? <CircularProgress size={16} /> 
                                    : <PaperAirplaneIcon className="w-4 h-4 text-blue-600" />
                                  }
                                </IconButton>
                              </span>
                            </Tooltip>
                          )}
                          {!isAuthorized && !isCancelled && (
                            <Tooltip title="Editar">
                              <IconButton size="small" onClick={() => handleEdit(n)} sx={{ p: 0.5 }}>
                                <PencilIcon className="w-4 h-4" />
                              </IconButton>
                            </Tooltip>
                          )}
                          {isAuthorized && !isCancelled && (
                            <>
                              <Tooltip title="Visualizar DANFE">
                                <IconButton size="small" onClick={() => handleViewDanfe(n)} sx={{ p: 0.5 }}>
                                  <DocumentTextIcon className="w-4 h-4 text-blue-600" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Baixar DANFE (PDF)">
                                <IconButton size="small" onClick={() => handleDownloadDanfe(n)} sx={{ p: 0.5 }}>
                                  <DocumentArrowDownIcon className="w-4 h-4 text-blue-600" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Cancelar NFCom">
                                <IconButton size="small" onClick={() => handleOpenCancel(n)} sx={{ p: 0.5 }}>
                                  <XMarkIcon className="w-4 h-4 text-red-600" />
                                </IconButton>
                              </Tooltip>
                            </>
                          )}
                          {isCancelled && (
                            <>
                              <Tooltip title="Visualizar DANFE">
                                <IconButton size="small" onClick={() => handleViewDanfe(n)} sx={{ p: 0.5 }}>
                                  <DocumentTextIcon className="w-4 h-4 text-blue-600" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Baixar DANFE (PDF)">
                                <IconButton size="small" onClick={() => handleDownloadDanfe(n)} sx={{ p: 0.5 }}>
                                  <DocumentArrowDownIcon className="w-4 h-4 text-blue-600" />
                                </IconButton>
                              </Tooltip>
                            </>
                          )}
                          
                          <Tooltip title="Baixar XML">
                            <IconButton size="small" onClick={() => handleDownloadXml(n)} disabled={!n.xml_url} sx={{ p: 0.5 }}>
                              <CodeBracketIcon className="w-4 h-4" />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </CardContent>
                    </Card>
                  );
                })}
              </Box>
            </Box>

            {/* Table view for desktop */}
            <TableContainer component={Paper} sx={{ display: { xs: 'none', md: 'block' }, maxHeight: '70vh', overflow: 'auto' }}>
              <Table sx={{ minWidth: 650 }} aria-label="nfcom table" size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell padding="checkbox">
                      <Checkbox
                        size="small"
                        indeterminate={selectedNfcoms.size > 0 && selectedNfcoms.size < nfcoms.filter(n => (n as any).status !== 'cancelada').length}
                        checked={selectedNfcoms.size > 0 && selectedNfcoms.size === nfcoms.filter(n => (n as any).status !== 'cancelada').length}
                        onChange={(e) => handleSelectAllNfcoms(e.target.checked)}
                        disabled={nfcoms.filter(n => (n as any).status !== 'cancelada').length === 0}
                      />
                    </TableCell>
                    <TableCell align="right">Número</TableCell>
                    <TableCell align="center">ID</TableCell>
                    <TableCell>Cliente</TableCell>
                    <TableCell>Cidade/UF</TableCell>
                    <TableCell>Emissão</TableCell>
                    <TableCell align="right">Valor Total</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Email</TableCell>
                    <TableCell align="right">Ações</TableCell>                  
                  </TableRow>
                </TableHead>
                <TableBody>
                  {nfcoms.map((n) => {
                    // Corrigir problema de fuso horário: extrair apenas a data da string ISO
                    const emissao = n.data_emissao ? (() => {
                      const dateStr = n.data_emissao.toString().split('T')[0]; // Pega apenas YYYY-MM-DD
                      const [year, month, day] = dateStr.split('-');
                      return `${day}/${month}/${year}`;
                    })() : 'N/A';
                    const numero = n.numero_nf ? `${n.numero_nf}` : 'N/A';
                    const clienteNome = n.cliente?.nome_razao_social || 'Cliente não identificado';
                    const isAuthorized = !!n.protocolo_autorizacao;
                    const isCancelled = (n as any).status === 'cancelada';
                    const status = isCancelled ? 'Cancelada' : (isAuthorized ? 'Autorizada' : 'Pendente');
                    const statusColor = isCancelled ? 'error' : (isAuthorized ? 'success' : 'warning');

                    return (
                      <TableRow key={n.id} hover>
                        <TableCell padding="checkbox">
                          {!isCancelled && (
                            <Checkbox
                              size="small"
                              checked={selectedNfcoms.has(n.id)}
                              onChange={(e) => handleSelectNfcom(n.id, e.target.checked)}
                            />
                          )}
                        </TableCell>
                        <TableCell align="right">{numero}</TableCell>
                        <TableCell align="center" sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>{n.cliente_id}</TableCell>
                        <TableCell>{clienteNome}</TableCell>
                        <TableCell>{n.dest_municipio ? `${n.dest_municipio}${n.dest_uf ? '/' + n.dest_uf : ''}` : '-'}</TableCell>
                        <TableCell>{emissao}</TableCell>
                        <TableCell align="right">{new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(n.valor_total || 0)}</TableCell>
                        <TableCell><Chip label={status} color={statusColor} size="small" /></TableCell>
                        <TableCell>
                          {n.email_status === 'sent' ? (
                            <Tooltip title={n.email_sent_at ? `Enviado em ${n.email_sent_at}` : 'Enviado'}>
                              <Chip label="Enviado" color="success" size="small" />
                            </Tooltip>
                          ) : n.email_status === 'failed' ? (
                            <Tooltip title={n.email_error_message || n.email_error || 'Falha no envio'}>
                              <Chip label="Falha" color="error" size="small" />
                            </Tooltip>
                          ) : n.email_status === 'pending' ? (
                            <Tooltip title="Pendente de envio">
                              <Chip label="Pendente" color="warning" size="small" />
                            </Tooltip>
                          ) : (
                            <Tooltip title="Não enviado">
                              <Chip label="—" size="small" />
                            </Tooltip>
                          )}
                        </TableCell>
                        <TableCell align="right">
                          <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end' }}>
                            {!isAuthorized && !isCancelled && (
                              <Tooltip title="Transmitir para SEFAZ">
                                <span>
                                  <IconButton size="small" onClick={() => handleTransmit(n)} disabled={transmittingId !== null}>
                                    {transmittingId === n.id 
                                      ? <CircularProgress size={20} /> 
                                      : <PaperAirplaneIcon className="w-5 h-5 text-blue-600" />
                                    }
                                  </IconButton>
                                </span>
                              </Tooltip>
                            )}
                            {!isAuthorized && !isCancelled && (
                              <Tooltip title="Editar">
                                <IconButton size="small" onClick={() => handleEdit(n)}>
                                  <PencilIcon className="w-5 h-5" />
                                </IconButton>
                              </Tooltip>
                            )}
                            {isAuthorized && !isCancelled && (
                              <>
                                <Tooltip title="Visualizar DANFE">
                                  <IconButton size="small" onClick={() => handleViewDanfe(n)}>
                                    <DocumentTextIcon className="w-5 h-5 text-blue-600" />
                                  </IconButton>
                                </Tooltip>
                                <Tooltip title="Baixar DANFE (PDF)">
                                  <IconButton size="small" onClick={() => handleDownloadDanfe(n)}>
                                    <DocumentArrowDownIcon className="w-5 h-5 text-blue-600" />
                                  </IconButton>
                                </Tooltip>
                                <Tooltip title="Cancelar NFCom">
                                  <IconButton size="small" onClick={() => handleOpenCancel(n)}>
                                    <XMarkIcon className="w-5 h-5 text-red-600" />
                                  </IconButton>
                                </Tooltip>
                              </>
                            )}
                            {isCancelled && (
                              <>
                                <Tooltip title="Visualizar DANFE">
                                  <IconButton size="small" onClick={() => handleViewDanfe(n)}>
                                    <DocumentTextIcon className="w-5 h-5 text-blue-600" />
                                  </IconButton>
                                </Tooltip>
                                <Tooltip title="Baixar DANFE (PDF)">
                                  <IconButton size="small" onClick={() => handleDownloadDanfe(n)}>
                                    <DocumentArrowDownIcon className="w-5 h-5 text-blue-600" />
                                  </IconButton>
                                </Tooltip>
                              </>
                            )}
                            
                            <Tooltip title="Baixar XML">
                              <IconButton size="small" onClick={() => handleDownloadXml(n)} disabled={!n.xml_url}>
                                {/* Usando um ícone que remete a código/XML */}
                                <CodeBracketIcon className="w-5 h-5" />
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination
              component="div"
              count={totalRows}
              page={page - 1} // TablePagination uses 0-based indexing
              onPageChange={(event, newPage) => {
                const newPageOneBased = newPage + 1;
                setPage(newPageOneBased);
                loadNfcoms(newPageOneBased);
              }}
              rowsPerPage={rowsPerPage}
              onRowsPerPageChange={handleRowsPerPageChange}
              rowsPerPageOptions={[5, 10, 25, 50, 100]}
              labelRowsPerPage="Itens por página:"

              labelDisplayedRows={({ from, to, count }) => `${from}-${to} de ${count}`}
            />
          </>
        )}
      </Paper>

      {openForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-0 sm:p-4">
          <div className="absolute inset-0 bg-gradient-to-br from-black/60 via-black/50 to-black/70 backdrop-blur-md" onClick={handleCloseForm} />
          <div className="relative bg-gradient-to-br from-white via-gray-50 to-blue-50/30 border border-borderLight rounded-none sm:rounded-2xl lg:rounded-3xl shadow-modern-hover w-full h-full flex flex-col overflow-hidden">
            <div className="flex items-center justify-between p-2 sm:p-3 lg:p-6 border-b border-borderLight bg-gradient-to-r from-white to-blue-50/30 flex-shrink-0">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-lg sm:rounded-xl flex items-center justify-center shadow">
                  <DocumentTextIcon className="w-4 h-4 text-white" />
                </div>
                <div>
                  <h2 className="text-base sm:text-xl font-bold text-text bg-gradient-to-r from-indigo-700 to-indigo-600 bg-clip-text text-transparent">
                    {editingNfcom ? 'Editar NFCom' : 'Nova NFCom'}
                  </h2>
                  {editingNfcom && (
                    <div className="flex flex-col sm:flex-row sm:items-center sm:space-x-4 space-y-1 sm:space-y-0 mt-1">
                      <p className="text-xs sm:text-sm text-indigo-600 font-medium">
                        📄 NF: #{editingNfcom.numero_nf}
                      </p>
                      <p className="text-xs sm:text-sm text-indigo-600 font-medium">
                        👤 Cliente ID: {editingNfcom.cliente_id}
                      </p>
                    </div>
                  )}
                  <p className="text-xs sm:text-sm text-textLight hidden sm:block">Preencha os dados para emitir ou editar a nota fiscal de comunicação.</p>
                </div>
              </div>
              <button
                onClick={handleCloseForm}
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
                  { id: 'general', label: 'Dados Básicos', icon: '📋', color: 'blue' },
                  { id: 'items', label: 'Itens', icon: '🛒', color: 'green' },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center space-x-1 sm:space-x-2 px-3 sm:px-6 py-3 sm:py-5 font-medium tab-transition whitespace-nowrap flex-shrink-0 relative rounded-t-lg ${
                      activeTab === tab.id
                        ? `tab-gradient-${tab.color} text-${tab.color === 'blue' ? 'blue' : 'green'}-700 shadow-modern-hover`
                        : `text-textLight hover:text-text hover:bg-surface/70 tab-hover-scale`
                    }`}
                  >
                    <span className="text-sm sm:text-base">{tab.icon}</span>
                    <span className="text-xs sm:text-sm font-semibold hidden xs:inline">{tab.label}</span>
                    {activeTab === tab.id && (
                      <div className={`absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r ${
                        tab.color === 'blue' ? 'from-blue-500 to-blue-600' :
                        'from-green-500 to-green-600'
                      } rounded-t-sm`} />
                    )}
                  </button>
                ))}
              </div>
              {/* Indicador de scroll para mobile */}
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2 sm:hidden">
                <div className="w-1.5 h-8 bg-gradient-to-b from-border to-borderLight rounded-full opacity-60 shadow-sm"></div>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-2 sm:p-3 lg:p-6 min-h-0 bg-gradient-to-b from-white to-gray-50/30">
              {activeTab === 'general' && (
                <div className="space-y-4 sm:space-y-6">
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-blue-100">
                    <h3 className="text-lg sm:text-xl font-bold text-blue-800 mb-1 sm:mb-2 flex items-center">
                      <span className="mr-2 text-base sm:text-lg">📋</span>
                      <span className="text-sm sm:text-base">Dados Básicos</span>
                    </h3>
                    <p className="text-xs sm:text-sm text-blue-600 hidden sm:block">
                      Informações principais da nota fiscal de comunicação.
                    </p>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                    <div className="sm:col-span-2">
                      <Autocomplete
                        options={clients}
                        getOptionLabel={(option) => `${option.nome_razao_social} (${clientService.formatCpfCnpj(option.cpf_cnpj)})`}
                        value={editingNfcom ? editingNfcom.cliente : (clients?.find(c => c.id === formData.cliente_id) || null)}
                        onChange={(_, value) => {
                          handleInputChange('cliente_id', value?.id || null);
                          if (value && value.enderecos) {
                            setClientAddresses(value.enderecos);
                            handleInputChange('cliente_endereco_id', value.enderecos[0]?.id || null);
                          } else {
                            setClientAddresses([]);
                            handleInputChange('cliente_endereco_id', null);
                          }
                        }}
                        inputValue={clientSearch}
                        onInputChange={(_, value, reason) => {
                          setClientSearch(value);
                          if (reason === 'input') {
                            if (value.length >= 2) {
                              void loadClients(value);
                            } else if (value.length === 0) {
                              // restore default first-10 when input cleared
                              void loadClients('');
                            } else {
                              // single-char: avoid noisy queries, clear temporary list
                              setClients([]);
                            }
                          }
                        }}
                        loading={clientLoading}
                        renderInput={(params) => <TextField {...params} label="Cliente *" error={!!errors.cliente_id} helperText={errors.cliente_id || 'Digite ao menos 2 caracteres para buscar'} size="small" />}
                        disabled={!!editingNfcom}
                      />
                    </div>
                    
                    {editingNfcom ? (
                      // Na edição, mostrar o endereço como texto readonly
                      <div className="sm:col-span-2">
                        <TextField
                          label="Endereço do Cliente"
                          value={`${formData.dest_endereco || ''}, ${formData.dest_numero || ''} - ${formData.dest_bairro || ''}, ${formData.dest_municipio || ''}`}
                          fullWidth
                          size="small"
                          InputProps={{
                            readOnly: true,
                          }}
                          helperText="Endereço usado na emissão da NFCom (não pode ser alterado)"
                        />
                      </div>
                    ) : (
                      // Na criação, mostrar o seletor de endereço
                      clientAddresses.length > 0 && (
                        <div className="sm:col-span-2">
                          <FormControl fullWidth size="small">
                            <InputLabel>Endereço do Cliente *</InputLabel>
                            <Select
                              value={formData.cliente_endereco_id || ''}
                              label="Endereço do Cliente *"
                              onChange={(e: SelectChangeEvent<any>) => handleInputChange('cliente_endereco_id', e.target.value)}
                              error={!!errors.cliente_endereco_id}
                            >
                              {clientAddresses.map((addr) => (
                                <MenuItem key={addr.id} value={addr.id}>
                                  {`${addr.endereco}, ${addr.numero} - ${addr.bairro}, ${addr.municipio}`}
                                </MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                        </div>
                      )
                    )}

                    <div>
                      <TextField
                        label="Data de Emissão *"
                        type="date"
                        value={formData.data_emissao}
                        onChange={(e) => handleInputChange('data_emissao', e.target.value)}
                        fullWidth
                        InputLabelProps={{ shrink: true }}
                        size="small"
                        error={!!errors.data_emissao}
                        helperText={errors.data_emissao}
                      />
                    </div>
                    <div>
                      <FormControl fullWidth size="small">
                        <InputLabel>Finalidade</InputLabel>
                        <Select
                          value={formData.finalidade_emissao}
                          label="Finalidade"
                          onChange={(e) => handleInputChange('finalidade_emissao', e.target.value)}
                        >
                          <MenuItem value={"0"}>Normal</MenuItem>
                          <MenuItem value={"3"}>Substituição</MenuItem>
                          <MenuItem value={"4"}>Ajuste</MenuItem>
                        </Select>
                      </FormControl>
                    </div>
                    <div>
                      <FormControl fullWidth size="small">
                        <InputLabel>Tipo de Faturamento</InputLabel>
                        <Select
                          value={formData.tpFat}
                          label="Tipo de Faturamento"
                          onChange={(e) => handleInputChange('tpFat', e.target.value)}
                        >
                          <MenuItem value={"0"}>Normal</MenuItem>
                          <MenuItem value={"1"}>Centralizado</MenuItem>
                          <MenuItem value={"2"}>Cofaturamento</MenuItem>
                        </Select>
                      </FormControl>
                    </div>
                    <div>
                      <TextField
                        label="Cód. Município Fato Gerador"
                        value={formData.cMunFG}
                        onChange={(e) => handleInputChange('cMunFG', e.target.value)}
                        fullWidth
                        helperText="Preenchido automaticamente com o IBGE da empresa ativa."
                        size="small"
                      />
                    </div>
                    {/* Campos contratuais do cabeçalho da NFCom */}
                    <div className="sm:col-span-2">
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-3">
                        <TextField
                          label="Nº do Contrato"
                          value={formData.numero_contrato || ''}
                          onChange={(e) => handleInputChange('numero_contrato', e.target.value)}
                          size="small"
                          fullWidth
                        />
                        <TextField
                          label="Início do Contrato"
                          type="date"
                          value={formData.d_contrato_ini ? String(formData.d_contrato_ini).split('T')[0] : ''}
                          onChange={(e) => handleInputChange('d_contrato_ini', e.target.value)}
                          InputLabelProps={{ shrink: true }}
                          size="small"
                          fullWidth
                        />
                        <TextField
                          label="Fim do Contrato"
                          type="date"
                          value={formData.d_contrato_fim ? String(formData.d_contrato_fim).split('T')[0] : ''}
                          onChange={(e) => handleInputChange('d_contrato_fim', e.target.value)}
                          InputLabelProps={{ shrink: true }}
                          size="small"
                          fullWidth
                        />
                      </div>
                    </div>
                    {/* Informações Adicionais */}
                    <div className="sm:col-span-2">
                      <TextField
                        label="Informações Adicionais / Observações"
                        value={formData.informacoes_adicionais || ''}
                        onChange={(e) => handleInputChange('informacoes_adicionais', e.target.value)}
                        multiline
                        rows={3}
                        fullWidth
                        size="small"
                        placeholder="Digite aqui observações ou informações complementares que serão exibidas no DANFE..."
                        helperText="Estas informações aparecerão na seção 'Informações Complementares' do DANFE"
                      />
                    </div>
                    {/* Faturas / Cobranças */}
                    <div className="sm:col-span-2">
                      <div className="flex justify-between items-center mb-2">
                        <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>Faturas / Cobranças</Typography>
                        <Button size="small" onClick={handleAddFatura} startIcon={<PlusIcon className="w-4 h-4" />}>Adicionar Fatura</Button>
                      </div>
                      {(formData.faturas || []).map((f: any, idx: number) => (
                        <Paper key={idx} variant="outlined" sx={{ p: 2, mb: 1 }}>
                          <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
                            <TextField label="Nº Fatura" value={f.numero_fatura || ''} size="small" onChange={(e) => handleFaturaChange(idx, 'numero_fatura', e.target.value)} />
                            <TextField label="Vencimento" type="date" value={f.data_vencimento || ''} size="small" InputLabelProps={{ shrink: true }} onChange={(e) => handleFaturaChange(idx, 'data_vencimento', e.target.value)} />
                            <TextField label="Valor" type="number" value={f.valor_fatura || 0} size="small" onChange={(e) => handleFaturaChange(idx, 'valor_fatura', parseFloat(e.target.value) || 0)} />
                            <div className="flex items-center">
                              <TextField label="Cód. Barras" value={f.codigo_barras || ''} size="small" onChange={(e) => handleFaturaChange(idx, 'codigo_barras', e.target.value)} sx={{ flex: 1, mr: 1 }} />
                              <IconButton size="small" color="error" onClick={() => handleRemoveFatura(idx)}><TrashIcon className="w-4 h-4" /></IconButton>
                            </div>
                          </div>
                        </Paper>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'items' && (
                <div className="space-y-4 sm:space-y-6">
                  <div className="bg-gradient-to-r from-green-50 to-emerald-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-green-100">
                    <h3 className="text-lg sm:text-xl font-bold text-green-800 mb-1 sm:mb-2 flex items-center">
                      <span className="mr-2 text-base sm:text-lg">🛒</span>
                      <span className="text-sm sm:text-base">Itens da Nota</span>
                    </h3>
                    <p className="text-xs sm:text-sm text-green-600 hidden sm:block">
                      Adicione os serviços ou produtos que compõem a nota fiscal.
                    </p>
                  </div>
                  <div className="flex justify-end mb-4">
                    <Button 
                      onClick={handleAddItem} 
                      variant="contained" 
                      startIcon={<PlusIcon className="w-4 h-4"/>}
                      size="small"
                      sx={{ 
                        background: 'linear-gradient(135deg, #4caf50 0%, #66bb6a 100%)',
                        '&:hover': { background: 'linear-gradient(135deg, #388e3c 0%, #4caf50 100%)' }
                      }}
                    >
                      <span className="hidden sm:inline">Adicionar Item</span>
                      <span className="sm:hidden">Adicionar</span>
                    </Button>
                  </div>
                  {formData.itens.map((item, index) => (
                    <Paper key={index} elevation={2} sx={{ p: 2, sm: { p: 3 }, position: 'relative', borderRadius: 2, background: 'linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%)', border: '1px solid #e3f2fd' }}>
                      {/* Header do Item */}
                      <div className="flex items-center justify-between mb-3 sm:mb-4">
                        <div className="flex items-center space-x-2">
                          <div className="w-6 h-6 sm:w-8 sm:h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center text-white text-xs sm:text-sm font-bold shadow-sm">
                            {index + 1}
                          </div>
                          <Typography variant="subtitle1" sx={{ fontWeight: 'bold', color: 'primary.main', fontSize: { xs: '0.85rem', sm: '0.9rem' } }}>Item {index + 1}</Typography>
                        </div>
                        <IconButton
                          size="small"
                          onClick={() => handleRemoveItem(index)}
                          sx={{
                            backgroundColor: 'error.light',
                            color: 'white',
                            '&:hover': { backgroundColor: 'error.main' },
                            width: { xs: 28, sm: 32 },
                            height: { xs: 28, sm: 32 }
                          }}
                        >
                          <TrashIcon className="w-3 h-3" />
                        </IconButton>
                      </div>

                      {/* Campo de Serviço - Sempre em linha completa */}
                      <div className="mb-3 sm:mb-4">
                        <Autocomplete
                          options={[...(selectedServicos[index] ? [selectedServicos[index]] : []), ...(servicosOptions[index] || [])].filter((v, i, a) => a.findIndex(o => o?.id === v?.id) === i)}
                          getOptionLabel={(option) => `${option?.codigo || ''} - ${option?.descricao || ''}`}
                          value={selectedServicos[index] || null}
                          onChange={(_, value) => {
                            setSelectedServicos(prev => ({ ...prev, [index]: value }));
                            if (!value) {
                              const cleared = {
                                servico_id: undefined, cClass: '', codigo_servico: '', descricao_servico: '',
                                unidade_medida: 'UN', valor_unitario: 0, cfop: '', ncm: '',
                                base_calculo_icms: 0, aliquota_icms: 0,
                              } as any;
                              applyServiceToItem(index, cleared);
                              return;
                            }
                            const svcFill = {
                              servico_id: value.id, cClass: value.cClass || '', codigo_servico: value.codigo || '',
                              descricao_servico: value.descricao || '', unidade_medida: value.unidade_medida || 'U',
                              valor_unitario: value.valor_unitario != null ? Number(value.valor_unitario) : 0,
                              cfop: value.cfop || '', ncm: value.ncm || '',
                              base_calculo_icms: value.base_calculo_icms_default != null ? Number(value.base_calculo_icms_default) : 0,
                              aliquota_icms: value.aliquota_icms_default != null ? Number(value.aliquota_icms_default) : 0,
                              valor_desconto: (value as any).valor_desconto_default != null ? Number((value as any).valor_desconto_default) : 0,
                              valor_outros: (value as any).valor_outros_default != null ? Number((value as any).valor_outros_default) : 0,
                            };
                            applyServiceToItem(index, svcFill);
                          }}
                          onInputChange={(_, inputValue, reason) => {
                            if (reason === 'input') {
                              if (inputValue && inputValue.length >= 1) {
                                searchServicosForItem(index, inputValue);
                              } else if (inputValue === '') {
                                // restore default options (first-10) for this item
                                if (searchControllers.current[index]) {
                                  try { searchControllers.current[index].abort(); } catch (e) {}
                                  delete searchControllers.current[index];
                                }
                                setServicosOptions(prev => ({ ...prev, [index]: servicos || [] }));
                              } else {
                                // input is a single char (length === 0 handled above), clear options to avoid noisy queries
                                if (searchControllers.current[index]) {
                                  try { searchControllers.current[index].abort(); } catch (e) {}
                                  delete searchControllers.current[index];
                                }
                                setServicosOptions(prev => ({ ...prev, [index]: [] }));
                              }
                            }
                          }}
                          renderInput={(params) => <TextField {...params} label="🔍 Serviço *" size="small" />}
                          isOptionEqualToValue={(option, value) => option?.id === value?.id}
                        />
                      </div>

                      {/* Seção: Identificação */}
                      <div className="mb-3 sm:mb-4 p-2 sm:p-3 bg-blue-50/50 rounded-lg border border-blue-100">
                        <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: 'primary.main', mb: 2, fontSize: '0.8rem' }}>
                          📋 Identificação
                        </Typography>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3">
                          <TextField label="🏷️ Cód. Classificação" value={item.cClass} onChange={(e) => handleItemChange(index, 'cClass', e.target.value)} size="small" />
                          <TextField label="📝 Descrição" value={item.descricao_servico} onChange={(e) => handleItemChange(index, 'descricao_servico', e.target.value)} size="small" />
                        </div>
                        {/* Campos de contrato removidos dos itens — mantidos no cabeçalho da NFCom */}
                      </div>

                      {/* Seção: Tributação */}
                      <div className="mb-3 sm:mb-4 p-2 sm:p-3 bg-green-50/50 rounded-lg border border-green-100">
                        <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: 'success.main', mb: 2, fontSize: '0.8rem' }}>
                          💼 Tributação
                        </Typography>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
                          <TextField label="📋 CFOP" value={item.cfop || ''} onChange={(e) => handleItemChange(index, 'cfop', e.target.value)} size="small" />
                          <TextField label="🏷️ NCM" value={item.ncm || ''} onChange={(e) => handleItemChange(index, 'ncm', e.target.value)} size="small" />
                          <TextField label="💰 Base ICMS" type="number" value={item.base_calculo_icms || 0} onChange={(e) => handleItemChange(index, 'base_calculo_icms', parseFloat(e.target.value) || 0)} size="small" />
                          <TextField label="📊 Alíq. ICMS (%)" type="number" value={item.aliquota_icms || 0} onChange={(e) => handleItemChange(index, 'aliquota_icms', parseFloat(e.target.value) || 0)} size="small" />
                          <TextField label="💰 Base PIS" type="number" value={item.base_calculo_pis || 0} onChange={(e) => handleItemChange(index, 'base_calculo_pis', parseFloat(e.target.value) || 0)} size="small" />
                          <TextField label="📊 Alíq. PIS (%)" type="number" value={item.aliquota_pis || 0} onChange={(e) => handleItemChange(index, 'aliquota_pis', parseFloat(e.target.value) || 0)} size="small" />
                          <TextField label="💰 Base COFINS" type="number" value={item.base_calculo_cofins || 0} onChange={(e) => handleItemChange(index, 'base_calculo_cofins', parseFloat(e.target.value) || 0)} size="small" />
                          <TextField label="📊 Alíq. COFINS (%)" type="number" value={item.aliquota_cofins || 0} onChange={(e) => handleItemChange(index, 'aliquota_cofins', parseFloat(e.target.value) || 0)} size="small" />
                        </div>
                      </div>

                      {/* Seção: Quantidade e Valores */}
                      <div className="p-2 sm:p-3 bg-purple-50/50 rounded-lg border border-purple-100">
                        <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: 'secondary.main', mb: 2, fontSize: '0.8rem' }}>
                          🧮 Valores
                        </Typography>
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 sm:gap-3 mb-3">
                          <TextField label="🔢 Qtd." type="number" value={item.quantidade} onChange={(e) => handleItemChange(index, 'quantidade', parseFloat(e.target.value) || 0)} size="small" />
                          <TextField label="📏 Un." value={item.unidade_medida} onChange={(e) => handleItemChange(index, 'unidade_medida', e.target.value)} size="small" />
                          <TextField label="💵 Vlr. Unitário" type="number" value={item.valor_unitario} onChange={(e) => handleItemChange(index, 'valor_unitario', parseFloat(e.target.value) || 0)} size="small" />
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-3">
                          <TextField label="💸 Vlr. Desconto" type="number" value={item.valor_desconto} onChange={(e) => handleItemChange(index, 'valor_desconto', parseFloat(e.target.value) || 0)} size="small" />
                          <TextField label="➕ Vlr. Outros" type="number" value={item.valor_outros} onChange={(e) => handleItemChange(index, 'valor_outros', parseFloat(e.target.value) || 0)} size="small" />
                          <TextField label="💰 Vlr. Total" type="number" value={item.valor_total} InputProps={{ readOnly: true }} sx={{ backgroundColor: '#f5f5f5' }} size="small" />
                        </div>
                      </div>
                    </Paper>
                  ))}
                </div>
              )}
            </div>

            <div className="flex flex-col gap-2 sm:gap-3 p-2 sm:p-3 lg:p-6 border-t border-borderLight bg-gradient-to-r from-gray-50 to-blue-50/30 flex-shrink-0 shadow-modern">
              <div className="flex items-center justify-between w-full">
                <div className="hidden sm:flex items-center space-x-2 text-xs sm:text-sm text-blue-600 text-center sm:text-left">
                  <span className="text-xs sm:text-lg">💡</span>
                  <p className="leading-tight font-normal text-xs">
                    Navegue pelas abas para preencher informações
                  </p>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-6 h-6 sm:w-8 sm:h-8 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center">
                    <span className="text-white text-xs sm:text-sm">💰</span>
                  </div>
                  <Typography variant="subtitle1" sx={{ fontWeight: 'bold', color: 'primary.main', fontSize: '0.9rem' }}>
                    Total: {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(formData.valor_total)}
                  </Typography>
                </div>
              </div>
              <div className="flex gap-2 sm:gap-3 justify-center sm:justify-end">
                <Button
                  onClick={handleCloseForm}
                  variant="outlined"
                  size="small"
                  sx={{
                    borderColor: 'grey.400',
                    color: 'grey.600',
                    '&:hover': { borderColor: 'grey.500', backgroundColor: 'grey.50' }
                  }}
                  startIcon={<span>❌</span>}
                >
                  Cancelar
                </Button>
                <Button
                  onClick={handleSubmit}
                  variant="contained"
                  disabled={submitting}
                  size="small"
                  sx={{
                    background: 'linear-gradient(135deg, #1976d2 0%, #42a5f5 100%)',
                    '&:hover': { background: 'linear-gradient(135deg, #1565c0 0%, #1976d2 100%)' },
                    '&:disabled': { background: 'grey.400' }
                  }}
                  startIcon={submitting ? <CircularProgress size={16} /> : <span>✅</span>}
                >
                  {submitting ? 'Processando...' : (editingNfcom ? 'Salvar' : 'Emitir')}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      <Snackbar
        open={snackbar.open}
        autoHideDuration={snackbar.persist ? undefined : 6000}
        onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setSnackbar(prev => ({ ...prev, open: false }))} severity={snackbar.severity} sx={{ width: '100%' }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
      {/* Modal detalhado de rejeição da SEFAZ */}
      <Dialog open={rejectionModal.open} onClose={() => setRejectionModal(prev => ({ ...prev, open: false }))} maxWidth="sm" fullWidth>
        <DialogTitle>Rejeição da SEFAZ</DialogTitle>
        <DialogContent dividers>
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2">cStat</Typography>
            <Typography>{rejectionModal.cStat}</Typography>
          </Box>
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2">Motivo (xMotivo)</Typography>
            <Typography sx={{ whiteSpace: 'pre-wrap' }}>{rejectionModal.xMotivo}</Typography>
          </Box>
          {rejectionModal.resultado && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle2">Detalhes (resultado)</Typography>
              <Typography sx={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>{JSON.stringify(rejectionModal.resultado, null, 2)}</Typography>
              {/* Lista de arquivos disponíveis para visualização/baixa */}
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2">Arquivos anexados</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mt: 1 }}>
                  {rejectionModal.resultado.soap_file && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography sx={{ fontSize: '0.9rem', flex: 1 }}>SOAP enviado</Typography>
                      <Button size="small" onClick={() => handleDownloadDebug(rejectionModal.resultado.soap_file, 'soap_enviado.xml')}>Baixar</Button>
                      <Button size="small" onClick={async () => {
                        // Baixa como texto e abre
                        try {
                          const token = localStorage.getItem('token');
                          const baseURL = API_BASE_URL;
                          const resp = await api.post(`/empresas/${rejectionModal.empresaId}/nfcom/${rejectionModal.nfId}/download_debug`, { path: rejectionModal.resultado.soap_file }, { responseType: 'text' });
                          handleViewTextContent('SOAP enviado', resp.data);
                        } catch (e) {
                          // fallback para download binário
                          handleDownloadDebug(rejectionModal.resultado.soap_file, 'soap_enviado.xml');
                        }
                      }}>Visualizar</Button>
                    </Box>
                  )}
                  {rejectionModal.resultado.soap_response_file && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography sx={{ fontSize: '0.9rem', flex: 1 }}>Resposta da SEFAZ</Typography>
                      <Button size="small" onClick={() => handleDownloadDebug(rejectionModal.resultado.soap_response_file, 'sefaz_response.xml')}>Baixar</Button>
                      <Button size="small" onClick={async () => {
                        try {
                          const token = localStorage.getItem('token');
                          const baseURL = API_BASE_URL;
                          const resp = await api.post(`/empresas/${rejectionModal.empresaId}/nfcom/${rejectionModal.nfId}/download_debug`, { path: rejectionModal.resultado.soap_response_file }, { responseType: 'text' });
                          handleViewTextContent('Resposta SEFAZ', resp.data);
                        } catch (e) {
                          handleDownloadDebug(rejectionModal.resultado.soap_response_file, 'sefaz_response.xml');
                        }
                      }}>Visualizar</Button>
                    </Box>
                  )}
                  {rejectionModal.resultado.xml_enviado && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography sx={{ fontSize: '0.9rem', flex: 1 }}>XML enviado</Typography>
                      <Button size="small" onClick={() => {
                        // Forçar download do conteúdo XML
                        try {
                          const blob = new Blob([rejectionModal.resultado.xml_enviado], { type: 'application/xml' });
                          const link = document.createElement('a');
                          link.href = window.URL.createObjectURL(blob);
                          link.download = `xml_enviado_${rejectionModal.nfId || 'nf'}.xml`;
                          document.body.appendChild(link);
                          link.click();
                          document.body.removeChild(link);
                        } catch (e) {
                          setSnackbar({ open: true, message: 'Falha ao baixar XML enviado', severity: 'error', persist: false });
                        }
                      }}>Baixar</Button>
                      <Button size="small" onClick={() => handleViewTextContent('XML enviado', rejectionModal.resultado.xml_enviado)}>Visualizar</Button>
                    </Box>
                  )}
                </Box>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            try { navigator.clipboard.writeText(rejectionModal.xMotivo || ''); setSnackbar({ open: true, message: 'Motivo copiado para a área de transferência', severity: 'success', persist: false }); } catch (e) { setSnackbar({ open: true, message: 'Falha ao copiar', severity: 'error', persist: false }); }
          }}>Copiar motivo</Button>
          <Button onClick={async () => {
            // Reenviar
            if (!rejectionModal.nfId || !rejectionModal.empresaId) return;
            setRejectionModal(prev => ({ ...prev, resending: true }));
            try {
              const token = localStorage.getItem('token');
              const baseURL = API_BASE_URL;
              const resp = await api.post(`/empresas/${rejectionModal.empresaId}/nfcom/${rejectionModal.nfId}/transmitir`, {});
              // Sucesso no reenvio
              setSnackbar({ open: true, message: 'Reenvio bem-sucedido', severity: 'success', persist: false });
              setRejectionModal({ open: false, cStat: '', xMotivo: '', resultado: null, nfId: null, empresaId: null, resending: false });
              // Atualiza lista
              loadNfcoms(page);
            } catch (err: any) {
              const isSefazRejection = !!(err.response && err.response.status === 400 && err.response.data && err.response.data.cStat);
              const detailMsg = stringifyError(err) || err.message || 'Erro no reenvio';
              // Se for rejeição da SEFAZ, não mostramos o snackbar (o modal já está visível)
              if (isSefazRejection) {
                setSnackbar(prev => ({ ...prev, open: false }));
                setRejectionModal(prev => ({ ...prev, cStat: err.response.data.cStat, xMotivo: err.response.data.xMotivo || detailMsg, resultado: err.response.data.resultado || prev.resultado, resending: false }));
              } else {
                setSnackbar({ open: true, message: `Reenvio falhou: ${detailMsg}`, severity: 'error', persist: false });
                setRejectionModal(prev => ({ ...prev, resending: false }));
              }
            }
          }} disabled={rejectionModal.resending} variant="contained">{rejectionModal.resending ? 'Reenviando...' : 'Reenviar'}</Button>
          <Button onClick={() => setRejectionModal(prev => ({ ...prev, open: false }))}>Fechar</Button>
        </DialogActions>
      </Dialog>

      {/* Modal para cancelar NFCom (evento de cancelamento) */}
      <Dialog open={cancelDialog.open} onClose={handleCloseCancel} maxWidth="sm" fullWidth>
        <DialogTitle>Cancelar NFCom</DialogTitle>
        <DialogContent dividers>
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2">Protocolo de autorização (nProt)</Typography>
            <TextField fullWidth value={cancelDialog.nProt} onChange={(e) => setCancelDialog(prev => ({ ...prev, nProt: e.target.value }))} size="small" sx={{ mt: 1 }} />
          </Box>
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2">Justificativa (xJust) *</Typography>
            <TextField 
              fullWidth 
              multiline 
              minRows={3} 
              value={cancelDialog.justificativa} 
              onChange={(e) => setCancelDialog(prev => ({ ...prev, justificativa: e.target.value }))} 
              size="small" 
              sx={{ mt: 1 }}
              helperText={`${cancelDialog.justificativa.trim().length}/255 caracteres (mínimo: 15)`}
              error={cancelDialog.justificativa.trim().length < 15 || cancelDialog.justificativa.trim().length > 255}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseCancel} variant="text">Fechar</Button>
          <Button onClick={handleSubmitCancel} variant="contained" color="error" disabled={cancelSubmitting}>{cancelSubmitting ? <CircularProgress size={16} /> : 'Enviar Cancelamento'}</Button>
        </DialogActions>
      </Dialog>
      
      {/* Modal de confirmação de exclusão */}
      <Dialog
        open={confirmDeleteDialog}
        onClose={() => setConfirmDeleteDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Confirmar Exclusão</DialogTitle>
        <DialogContent>
          <Typography>
            Tem certeza que deseja excluir {selectedNfcoms.size} nota(s) selecionada(s)?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Esta ação não pode ser desfeita. As notas serão removidas permanentemente do sistema.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDeleteDialog(false)} color="inherit">
            Cancelar
          </Button>
          <Button
            onClick={() => {
              setConfirmDeleteDialog(false);
              handleDeleteSelectedNfcoms();
            }}
            color="error"
            variant="contained"
          >
            Excluir
          </Button>
        </DialogActions>
      </Dialog>

      {/* Footer with additional information */}
      <Paper sx={{ mt: 4, p: 3, backgroundColor: '#f8f9fa' }}>
        <Typography variant="h6" gutterBottom sx={{ color: 'primary.main', fontWeight: 600 }}>
          📊 Resumo e Informações
        </Typography>
        
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(4, 1fr)' }, gap: 3, mb: 3 }}>
          {/* Statistics */}
          <Box>
            <Typography variant="subtitle2" sx={{ color: 'text.secondary', mb: 1 }}>
              📈 Estatísticas Gerais
            </Typography>
            <Typography variant="body2" sx={{ mb: 0.5 }}>
              <strong>Valor Total Geral:</strong> {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totalGeralValor || 0)}
            </Typography>
          </Box>

          {/* Status Statistics */}
          <Box>
            <Typography variant="subtitle2" sx={{ color: 'text.secondary', mb: 1 }}>
              📊 Status das NFComs
            </Typography>
            <Typography variant="body2" sx={{ mb: 0.5, color: 'success.main' }}>
              <strong>✅ Autorizadas:</strong> {totalAutorizadas}
            </Typography>
            <Typography variant="body2" sx={{ mb: 0.5, color: 'warning.main' }}>
              <strong>⏳ Pendentes:</strong> {totalPendentes}
            </Typography>
            <Typography variant="body2" sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
              Total filtrado: {totalAutorizadas + totalPendentes}
            </Typography>
          </Box>

          {/* Current Filters */}
          <Box>
            <Typography variant="subtitle2" sx={{ color: 'text.secondary', mb: 1 }}>
              🔍 Filtros Aplicados
            </Typography>
            {hasFiltersApplied() ? (
              <>
                {searchTerm && <Typography variant="body2" sx={{ mb: 0.5 }}>• Busca: "{searchTerm}"</Typography>}
                {(dateFrom || dateTo) && (
                  <Typography variant="body2" sx={{ mb: 0.5 }}>
                    • Período: {dateFrom || 'Início'} até {dateTo || 'Hoje'}
                  </Typography>
                )}
                {statusFilter !== 'all' && <Typography variant="body2" sx={{ mb: 0.5 }}>• Status: {statusFilter === 'authorized' ? 'Autorizadas' : 'Pendentes'}</Typography>}
                {(minValue || maxValue) && (
                  <Typography variant="body2" sx={{ mb: 0.5 }}>
                    • Valor: {minValue ? `R$ ${minValue}` : '0'} até {maxValue ? `R$ ${maxValue}` : '∞'}
                  </Typography>
                )}
                <Button 
                  size="small" 
                  variant="text" 
                  onClick={clearFilters}
                  sx={{ mt: 1, p: 0, fontSize: '0.75rem' }}
                >
                  🗑️ Limpar todos os filtros
                </Button>
              </>
            ) : (
              <Typography variant="body2" sx={{ fontStyle: 'italic', color: 'text.secondary' }}>
                Nenhum filtro aplicado
              </Typography>
            )}
          </Box>

          {/* Quick Actions & Info */}
          <Box>
            <Typography variant="subtitle2" sx={{ color: 'text.secondary', mb: 1 }}>
              ⚡ Ações Rápidas
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Button 
                size="small" 
                variant="outlined" 
                onClick={() => loadNfcoms(page)}
                startIcon={<DocumentArrowDownIcon className="w-4 h-4" />}
              >
                Atualizar Lista
              </Button>
              <Button 
                size="small" 
                variant="outlined" 
                onClick={handleOpenForm}
                startIcon={<PlusIcon className="w-4 h-4" />}
              >
                Nova NFCom
              </Button>
            </Box>
          </Box>
        </Box>

        {/* Tip/Dica em linha separada */}
        <Box sx={{ mt: 2, textAlign: 'left' }}>
          <Typography variant="body2" sx={{ fontSize: '0.8rem', color: 'text.secondary', fontStyle: 'italic' }}>
            💡 Dica: Use os filtros para encontrar NFComs específicas rapidamente
          </Typography>
        </Box>

        {/* Footer note */}
        <Divider sx={{ my: 2 }} />
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap' }}>
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            Sistema Brazcom NFCom - Versão 3.0
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            Última atualização: {new Date().toLocaleString('pt-BR')}
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
};

export default NFCom;