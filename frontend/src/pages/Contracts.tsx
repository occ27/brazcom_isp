import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { stringifyError } from '../utils/error';
import {
  Box, Paper, Typography, Button, IconButton, TextField, CircularProgress, Snackbar, Alert,
  Dialog, DialogTitle, DialogContent, DialogActions, Autocomplete, FormControl, InputLabel, Select, MenuItem,
  Card, CardContent, Divider, Chip, Tooltip, SelectChangeEvent, useMediaQuery, useTheme,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TablePagination, Pagination,
  Checkbox
} from '@mui/material';
import { PlusIcon, PencilIcon, TrashIcon, DocumentTextIcon, EyeIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import { useCompany } from '../contexts/CompanyContext';
import contratoService, { Contrato, ContratoListResponse } from '../services/contratoService';
import clientService from '../services/clientService';
import servicoService, { Servico } from '../services/servicoService';
import { Cliente } from '../types';

const Contracts: React.FC = () => {
  const { activeCompany } = useCompany();
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
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [loading, setLoading] = useState<boolean>(true);
  const [openForm, setOpenForm] = useState(false);
  const [editing, setEditing] = useState<Contrato | null>(null);
  const [form, setForm] = useState<Partial<Contrato>>({
    quantidade: 1,
    periodicidade: 'MENSAL',
    valor_unitario: 0,
    auto_emit: true,
    is_active: true,
    status: 'ATIVO',
    periodo_carencia: 0,
    multa_atraso_percentual: 0.0,
    taxa_instalacao: 0.0,
    taxa_instalacao_paga: false
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' | 'warning' });
  
  // Pagination state
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [totalRows, setTotalRows] = useState(0);

  // Search state
  const [searchTerm, setSearchTerm] = useState('');
  
  // Due date filter state
  const [diaVencimentoMin, setDiaVencimentoMin] = useState<number | ''>('');
  const [diaVencimentoMax, setDiaVencimentoMax] = useState<number | ''>('');
  
  // Bulk selection state
  const [selectedContracts, setSelectedContracts] = useState<number[]>([]);
  const [bulkEmitLoading, setBulkEmitLoading] = useState(false);
  const [bulkDialogOpen, setBulkDialogOpen] = useState(false);
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
    const eligibleContracts = contratos.filter(c => isContractEligibleForEmission(c));
    setSelectedContracts(checked ? eligibleContracts.map(c => c.id) : []);
  }, [contratos, isContractEligibleForEmission]);

  // Check if all eligible contracts are selected
  const isAllSelected = useMemo(() => {
    const eligibleContracts = contratos.filter(c => isContractEligibleForEmission(c));
    return eligibleContracts.length > 0 && selectedContracts.length === eligibleContracts.length;
  }, [contratos, selectedContracts, isContractEligibleForEmission]);

  // Check if some (but not all) eligible contracts are selected
  const isIndeterminate = useMemo(() => {
    const eligibleContracts = contratos.filter(c => isContractEligibleForEmission(c));
    return selectedContracts.length > 0 && selectedContracts.length < eligibleContracts.length;
  }, [contratos, selectedContracts, isContractEligibleForEmission]);

  // Calculate total value of selected contracts
  const selectedContractsTotalValue = useMemo(() => {
    return contratos
      .filter(c => selectedContracts.includes(c.id))
      .reduce((total, contrato) => total + (contrato.valor_total || 0), 0);
  }, [contratos, selectedContracts]);

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
        diaVencimentoMax || undefined
      );
      setContratos(data.contratos);
      setTotalRows(data.total);
    } catch (e) {
      setSnackbar({ open: true, message: 'Erro ao carregar contratos', severity: 'error' });
    } finally { setLoading(false); }
  }, [activeCompany, page, rowsPerPage, searchTerm, diaVencimentoMin, diaVencimentoMax]);

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
  }, [searchTerm, diaVencimentoMin, diaVencimentoMax, activeCompany]);

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

  const loadClients = useCallback(async (search: string = '') => {
    if (!activeCompany) return;
    setClientLoading(true);
    try {
      // When search is empty, this will return the first page (limit 10).
      const response = await clientService.getClientsByCompany(activeCompany.id, 1, 10, search || undefined);
      setClients(response.clientes || []);
    } catch (error) {
      console.error("Erro ao carregar clientes:", error);
      setClients([]);
    } finally {
      setClientLoading(false);
    }
  }, [activeCompany]);

  const loadServicos = useCallback(async (search: string = '') => {
    if (!activeCompany) return;
    setServicoLoading(true);
    try {
      // Use paginated endpoint to get the first `limit` services when search is empty
      const resp = await servicoService.getServicosByEmpresaPaginated(activeCompany.id, 1, 10, search || undefined);
      setServicos(resp.servicos || []);
    } catch (error) {
      console.error("Erro ao carregar serviços:", error);
      setServicos([]);
    } finally {
      setServicoLoading(false);
    }
  }, [activeCompany]);

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
                      {isContractEligibleForEmission(c) && (
                        <Checkbox
                          checked={selectedContracts.includes(c.id)}
                          onChange={(e) => handleContractSelect(c.id, e.target.checked)}
                          size="small"
                        />
                      )}
                      {isExpired ? (
                        <Chip label="VENCIDO" color="error" size="small" variant="filled" />
                      ) : (
                        <>
                          {isActive && <Chip label="Ativo" color="success" size="small" />}
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
                <Tooltip title="Editar">
                  <IconButton size="small" onClick={() => handleOpenForm(c)}>
                    <PencilIcon className="w-5 h-5" />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Excluir">
                  <IconButton size="small" onClick={() => remove(c)}>
                    <TrashIcon className="w-5 h-5 text-red-500" />
                  </IconButton>
                </Tooltip>
              </Box>
            </CardContent>
          </Card>
        );
      })}
    </Box>
  );

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
            <TableCell sx={{ fontWeight: 600 }}>Nº Contrato</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Cliente</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Cidade/UF</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>CPF/CNPJ</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Serviço</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Periodicidade</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Dia Emissão</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Dia Venc.</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Valor Unitário</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Status ISP</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
            <TableCell sx={{ fontWeight: 600, width: 120 }}>Ações</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
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
                  disabled={!isContractEligibleForEmission(c)}
                  size="small"
                />
              </TableCell>
              <TableCell>{c.numero_contrato || `Contrato #${c.id}`}</TableCell>
              <TableCell>{c.cliente_razao_social || c.cliente_nome || `Cliente #${c.cliente_id}`}</TableCell>
              <TableCell>{c.cliente_municipio ? `${c.cliente_municipio}${c.cliente_uf ? '/' + c.cliente_uf : ''}` : '-'}</TableCell>
              <TableCell>{c.cliente_cpf_cnpj ? clientService.formatCpfCnpj(c.cliente_cpf_cnpj) : '-'}</TableCell>
              <TableCell>{c.servico_descricao || `Serviço #${c.servico_id}`}</TableCell>
              <TableCell>{c.periodicidade || 'MENSAL'}</TableCell>
              <TableCell>{c.dia_emissao || '-'}</TableCell>
              <TableCell>{c.dia_vencimento ?? (c.vencimento ? (() => { const m = (String(c.vencimento)).match(/^(\d{4})-(\d{2})-(\d{2})/); return m ? m[3] : '-'; })() : '-')}</TableCell>
              <TableCell>
                {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(c.valor_unitario || 0)}
              </TableCell>
              <TableCell>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', alignItems: 'center' }}>
                  {isExpired ? (
                    <Chip label="VENCIDO" color="error" size="small" variant="filled" />
                  ) : (
                    <>
                      {c.is_active && <Chip label="Ativo" color="success" size="small" />}
                      {!c.is_active && <Chip label="Inativo" color="default" size="small" />}
                    </>
                  )}
                  {c.auto_emit && <Chip label="Auto" color="info" size="small" />}
                </Box>
              </TableCell>
              <TableCell>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', alignItems: 'center' }}>
                  {c.status && (
                    <Chip 
                      label={c.status === 'ATIVO' ? 'Ativo' : 
                             c.status === 'SUSPENSO' ? 'Suspenso' : 
                             c.status === 'CANCELADO' ? 'Cancelado' : 
                             c.status === 'PENDENTE_INSTALACAO' ? 'Pendente Instalação' : c.status} 
                      color={c.status === 'ATIVO' ? 'success' : 
                             c.status === 'SUSPENSO' ? 'warning' : 
                             c.status === 'CANCELADO' ? 'error' : 
                             c.status === 'PENDENTE_INSTALACAO' ? 'info' : 'default'} 
                      size="small" 
                      variant="outlined" 
                    />
                  )}
                  {c.taxa_instalacao && c.taxa_instalacao > 0 && (
                    <Chip 
                      label={c.taxa_instalacao_paga ? 'Instalação Paga' : 'Taxa Pendente'} 
                      color={c.taxa_instalacao_paga ? 'success' : 'warning'} 
                      size="small" 
                      variant="outlined" 
                    />
                  )}
                </Box>
              </TableCell>
              <TableCell>
                <Tooltip title="Editar">
                  <IconButton size="small" onClick={() => handleOpenForm(c)}>
                    <PencilIcon className="w-4 h-4" />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Excluir">
                  <IconButton size="small" onClick={() => remove(c)}>
                    <TrashIcon className="w-4 h-4 text-red-500" />
                  </IconButton>
                </Tooltip>
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

  const handleOpenForm = async (c?: Contrato) => {
    if (c) {
      setEditing(c);
  // Normalize date fields to YYYY-MM-DD for date inputs to avoid timezone shifts
  const normalized: any = { ...c };
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
  // Debugging: log raw + normalized to help diagnose TZ/format issues
  // eslint-disable-next-line no-console
  console.log('handleOpenForm - vencimento raw:', c.vencimento, 'normalized:', normalized.vencimento);
  setForm(normalized);

      // Carregar dados do cliente selecionado
      if (c.cliente_id && activeCompany) {
        try {
          const clientResponse = await clientService.getClientById(c.cliente_id, activeCompany.id);
          setClients([clientResponse]);
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
    } else {
      setEditing(null);
      setForm({ quantidade: 1, periodicidade: 'MENSAL', valor_unitario: 0, auto_emit: true, is_active: true, dia_emissao: 1, status: 'ATIVO', periodo_carencia: 0, multa_atraso_percentual: 0.0, taxa_instalacao: 0.0, taxa_instalacao_paga: false, sla_garantido: undefined, velocidade_garantida: '', subscription_id: undefined });
      // Reset input values and prefetch the first 10 clients and services
      setClientSearch('');
      setServicoSearch('');
      // Prefetch defaults (do not await)
      if (activeCompany) {
        loadClients('');
        loadServicos('');
      }
    }
    // If editing we may still want the default lists for the other autocomplete fields
    // e.g. if editing has client set, but servico list is empty, prefetch services (and vice-versa)
    if (c) {
      if (!clientSearch && activeCompany) loadClients('');
      if (!servicoSearch && activeCompany) loadServicos('');
    }
    setOpenForm(true);
  };

  const handleCloseForm = () => {
    setOpenForm(false);
    setEditing(null);
    setErrors({});
  };

  const handleInputChange = (field: string, value: any) => {
    setForm(prev => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: '' }));
  };

  const validateForm = (): boolean => {
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
      newErrors.servico_id = 'Serviço é obrigatório';
    }

    // Valor unitário obrigatório e positivo
    if (form.valor_unitario === undefined || form.valor_unitario === null || form.valor_unitario <= 0) {
      newErrors.valor_unitario = 'Valor unitário é obrigatório e deve ser maior que zero';
    }

    // Quantidade obrigatória e positiva
    if (form.quantidade === undefined || form.quantidade === null || form.quantidade <= 0) {
      newErrors.quantidade = 'Quantidade é obrigatória e deve ser maior que zero';
    }

    // Dia de emissão obrigatório e deve estar entre 1 e 31
    if (form.dia_emissao === undefined || form.dia_emissao === null) {
      newErrors.dia_emissao = 'Dia de emissão é obrigatório';
    } else {
      const dia = Number(form.dia_emissao);
      if (dia < 1 || dia > 31) {
        newErrors.dia_emissao = 'Dia de emissão deve estar entre 1 e 31';
      }
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
    return Object.keys(newErrors).length === 0;
  };

  const submit = async () => {
    if (!validateForm()) {
      setSnackbar({ open: true, message: 'Por favor, corrija os erros do formulário.', severity: 'warning' });
      return;
    }
    if (!activeCompany) return;
    try {
      if (editing) {
        await contratoService.updateContrato(activeCompany.id, editing.id, form as any);
        setSnackbar({ open: true, message: 'Contrato atualizado com sucesso!', severity: 'success' });
      } else {
        await contratoService.createContrato(activeCompany.id, form as any);
        setSnackbar({ open: true, message: 'Contrato criado com sucesso!', severity: 'success' });
      }
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
      setSnackbar({ open: true, message: 'Erro ao excluir contrato', severity: 'error' });
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
          Contratos de Serviço
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            startIcon={<PlusIcon className="w-5 h-5" />}
            sx={{ py: 1.5, width: { xs: '100%', sm: 'auto' } }}
            onClick={() => handleOpenForm()}
          >
            Novo Contrato
          </Button>
          {selectedContracts.length > 0 && (
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
        </Box>
      </Box>

      <Paper sx={{ p: { xs: 1, sm: 2 }, backgroundColor: 'grey.50', minHeight: 'calc(100vh - 250px)' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
          <Typography variant="h6">Contratos Cadastrados</Typography>
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
                sx={{ minWidth: { xs: 90, sm: 120 } }}
              />
              <TextField
                size="small"
                type="number"
                placeholder="Dia venc. max"
                value={diaVencimentoMax}
                onChange={(e) => setDiaVencimentoMax(e.target.value === '' ? '' : Number(e.target.value))}
                inputProps={{ min: 1, max: 31 }}
                sx={{ minWidth: { xs: 90, sm: 120 } }}
              />
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
              {searchTerm ? 'Tente ajustar os termos da busca' : 'Comece cadastrando seu primeiro contrato de serviço.'}
            </Typography>
            {!searchTerm && (
              <Button variant="outlined" startIcon={<PlusIcon className="w-5 h-5" />} onClick={() => handleOpenForm()}>
                Cadastrar Primeiro Contrato
              </Button>
            )}
          </Box>
        ) : isMobile ? (
          renderContractCards()
        ) : (
          renderContractTable()
        )}
        
        {!loading && contratos.length > 0 && renderPagination()}
      </Paper>

      {openForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-0 sm:p-4">
          <div
            className="absolute inset-0 bg-gradient-to-br from-black/60 via-black/50 to-black/70 backdrop-blur-md"
            onClick={handleCloseForm}
          />
          <div className="relative bg-gradient-to-br from-white via-gray-50 to-blue-50 border border-borderLight rounded-2xl sm:rounded-3xl shadow-modern-hover w-full max-w-sm sm:max-w-md lg:max-w-4xl h-full sm:h-auto max-h-screen sm:max-h-[90vh] flex flex-col overflow-hidden">
            <div className="flex items-center justify-between p-3 sm:p-6 border-b border-borderLight bg-gradient-to-r from-white to-blue-50/30 flex-shrink-0">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-lg sm:rounded-xl flex items-center justify-center shadow">
                  <DocumentTextIcon className="w-4 h-4 text-white" />
                </div>
                <div>
                  <h2 className="text-base sm:text-xl font-bold text-text bg-gradient-to-r from-indigo-700 to-indigo-600 bg-clip-text text-transparent">
                    {editing ? 'Editar Contrato' : 'Novo Contrato de Serviço'}
                  </h2>
                  <p className="text-xs sm:text-sm text-textLight hidden sm:block">Preencha os dados do contrato corretamente.</p>
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

            <div className="flex-1 overflow-y-auto p-3 sm:p-6 min-h-0 bg-gradient-to-b from-white to-gray-50/30">
              <div className="space-y-4 sm:space-y-6">
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-blue-100">
                  <h3 className="text-lg sm:text-xl font-bold text-blue-800 mb-1 sm:mb-2 flex items-center">
                    <span className="mr-2 text-base sm:text-lg">📋</span>
                    <span className="text-sm sm:text-base">Identificação</span>
                  </h3>
                  <p className="text-xs sm:text-sm text-blue-600 hidden sm:block">
                    Informações básicas do contrato de serviço.
                  </p>
                  <div className="mt-3 sm:mt-4">
                    <TextField
                      label="Número do Contrato"
                      value={form.numero_contrato || ''}
                      onChange={e => handleInputChange('numero_contrato', e.target.value)}
                      fullWidth
                      size="small"
                      error={!!errors.numero_contrato}
                      helperText={errors.numero_contrato}
                    />
                    {/* Mostrar CPF/CNPJ e telefone do cliente selecionado para facilitar identificação */}
                    {(() => {
                      const sel = clients.find(cl => cl.id === form.cliente_id);
                      if (sel) {
                        return (
                          <Box sx={{ mt: 1 }}>
                            {sel.cpf_cnpj && <Typography variant="caption" color="text.secondary">CPF/CNPJ: {clientService.formatCpfCnpj(sel.cpf_cnpj)}</Typography>}
                            {sel.telefone && <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>Telefone: {sel.telefone}</Typography>}
                          </Box>
                        );
                      }
                      return null;
                    })()}
                  </div>
                </div>

                <div className="bg-gradient-to-r from-cyan-50 to-blue-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-cyan-100">
                  <h3 className="text-lg sm:text-xl font-bold text-cyan-800 mb-1 sm:mb-2 flex items-center">
                    <span className="mr-2 text-base sm:text-lg">👤</span>
                    <span className="text-sm sm:text-base">Cliente e Serviço</span>
                  </h3>
                  <p className="text-xs sm:text-sm text-cyan-600 hidden sm:block">
                    Selecione o cliente e o serviço contratado.
                  </p>
                  <div className="mt-3 sm:mt-4 space-y-3 sm:space-y-4">
                    <Autocomplete
                      options={clients}
                      getOptionLabel={(option) => `${option.nome_razao_social} (${clientService.formatCpfCnpj(option.cpf_cnpj)})`}
                      value={clients.find(cl => cl.id === form.cliente_id) || null}
                      onChange={async (_, value) => {
                        handleInputChange('cliente_id', value?.id || undefined);
                        
                        // Preencher automaticamente o endereço de instalação com o primeiro endereço do cliente
                        // apenas se o campo estiver vazio
                        if (value && activeCompany && !form.endereco_instalacao) {
                          try {
                            const clientDetails = await clientService.getClientById(value.id, activeCompany.id);
                            if (clientDetails.enderecos && clientDetails.enderecos.length > 0) {
                              // Pegar o primeiro endereço (ou o principal se existir)
                              const enderecoPrincipal = clientDetails.enderecos.find(e => e.is_principal) || clientDetails.enderecos[0];
                              
                              // Formatar o endereço completo
                              const enderecoCompleto = `${enderecoPrincipal.endereco}, ${enderecoPrincipal.numero}${enderecoPrincipal.complemento ? ', ' + enderecoPrincipal.complemento : ''} - ${enderecoPrincipal.bairro}, ${enderecoPrincipal.municipio}/${enderecoPrincipal.uf}, CEP: ${enderecoPrincipal.cep}`;
                              
                              handleInputChange('endereco_instalacao', enderecoCompleto);
                            }
                          } catch (error) {
                            console.error('Erro ao buscar endereços do cliente:', error);
                          }
                        } else if (!value) {
                          // Limpar o endereço se nenhum cliente foi selecionado
                          handleInputChange('endereco_instalacao', '');
                        }
                      }}
                      inputValue={clientSearch}
                      onInputChange={(_, value, reason) => {
                        setClientSearch(value);
                        if (reason === 'input') {
                          if (value.length >= 2) {
                            loadClients(value);
                          } else if (value.length === 0) {
                            // restore default first-10 when input cleared
                            loadClients('');
                          } else {
                            // single-char typed: do not query remote, clear results to avoid noisy responses
                            setClients([]);
                          }
                        }
                      }}
                      loading={clientLoading}
                      renderInput={(params) => <TextField {...params} label="Cliente *" error={!!errors.cliente_id} helperText={errors.cliente_id || 'Digite ao menos 2 caracteres para buscar'} size="small" />}
                    />
                    <Autocomplete
                      options={servicos}
                      getOptionLabel={(option) => `${option.codigo || ''} - ${option.descricao || ''}`}
                      value={servicos.find(s => s.id === form.servico_id) || null}
                      onChange={(_, value) => {
                        handleInputChange('servico_id', value?.id || undefined);
                        if (value) {
                          handleInputChange('valor_unitario', value.valor_unitario || 0);
                        }
                      }}
                      inputValue={servicoSearch}
                      onInputChange={(_, value, reason) => {
                        setServicoSearch(value);
                        if (reason === 'input') {
                          if (value.length >= 1) {
                            loadServicos(value);
                          } else if (value.length === 0) {
                            // restore default first-10 when input cleared
                            loadServicos('');
                          }
                        }
                      }}
                      loading={servicoLoading}
                      renderInput={(params) => <TextField {...params} label="Serviço *" error={!!errors.servico_id} helperText={errors.servico_id || 'Digite para buscar um serviço'} size="small" />}
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
                          label="Dia de Vencimento (1-31)"
                          type="number"
                          value={form.dia_vencimento ?? ''}
                          onChange={e => handleInputChange('dia_vencimento', e.target.value === '' ? undefined : Number(e.target.value))}
                          fullWidth
                          size="small"
                          helperText="Dia do mês para vencimento da fatura (opcional). Usado na geração automática de faturas."
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
                    Informe a quantidade e valor unitário do serviço.
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
                      label="Valor Unitário (R$)"
                      type="number"
                      value={form.valor_unitario || 0}
                      onChange={e => handleInputChange('valor_unitario', parseFloat(e.target.value || '0'))}
                      fullWidth
                      size="small"
                      error={!!errors.valor_unitario}
                      helperText={errors.valor_unitario}
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
                  <div className="mt-3 sm:mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                    <FormControl fullWidth size="small">
                      <InputLabel>Emissão Automática</InputLabel>
                      <Select
                        value={form.auto_emit ? 'true' : 'false'}
                        label="Emissão Automática"
                        onChange={(e: SelectChangeEvent) => handleInputChange('auto_emit', e.target.value === 'true')}
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
                      </Select>
                    </FormControl>
                  </div>
                </div>

                <div className="bg-gradient-to-r from-emerald-50 to-green-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-emerald-100">
                  <h3 className="text-lg sm:text-xl font-bold text-emerald-800 mb-1 sm:mb-2 flex items-center">
                    <span className="mr-2 text-base sm:text-lg">📍</span>
                    <span className="text-sm sm:text-base">Informações de Instalação</span>
                  </h3>
                  <p className="text-xs sm:text-sm text-emerald-600 hidden sm:block">
                    Dados específicos da instalação do serviço de internet.
                  </p>
                  <div className="mt-3 sm:mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                    <TextField
                      label="Endereço de Instalação"
                      value={form.endereco_instalacao || ''}
                      onChange={e => handleInputChange('endereco_instalacao', e.target.value)}
                      fullWidth
                      size="small"
                      multiline
                      rows={2}
                      helperText="Endereço onde o serviço será instalado"
                    />
                    <FormControl fullWidth size="small">
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
                    </FormControl>
                    <TextField
                      label="Coordenadas GPS"
                      value={form.coordenadas_gps || ''}
                      onChange={e => handleInputChange('coordenadas_gps', e.target.value)}
                      fullWidth
                      size="small"
                      placeholder="latitude,longitude"
                      helperText="Ex: -23.550520,-46.633308"
                    />
                    <TextField
                      label="Data de Instalação"
                      type="date"
                      value={form.data_instalacao || ''}
                      onChange={e => handleInputChange('data_instalacao', e.target.value)}
                      fullWidth
                      size="small"
                      InputLabelProps={{ shrink: true }}
                    />
                    <TextField
                      label="Responsável Técnico"
                      value={form.responsavel_tecnico || ''}
                      onChange={e => handleInputChange('responsavel_tecnico', e.target.value)}
                      fullWidth
                      size="small"
                      helperText="Nome do técnico responsável pela instalação"
                    />
                    <TextField
                      label="Velocidade Garantida"
                      value={form.velocidade_garantida || ''}
                      onChange={e => handleInputChange('velocidade_garantida', e.target.value)}
                      fullWidth
                      size="small"
                      placeholder="Ex: 10M/10M"
                      helperText="Velocidade de download/upload garantida"
                    />
                  </div>
                </div>

                <div className="bg-gradient-to-r from-rose-50 to-pink-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-rose-100">
                  <h3 className="text-lg sm:text-xl font-bold text-rose-800 mb-1 sm:mb-2 flex items-center">
                    <span className="mr-2 text-base sm:text-lg">💰</span>
                    <span className="text-sm sm:text-base">Cobrança e SLA</span>
                  </h3>
                  <p className="text-xs sm:text-sm text-rose-600 hidden sm:block">
                    Configurações de cobrança e qualidade do serviço.
                  </p>
                  <div className="mt-3 sm:mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
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
                      helperText="ID da subscription relacionada (opcional)"
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-2 sm:gap-3 p-3 sm:p-6 border-t border-borderLight bg-gradient-to-r from-gray-50 to-blue-50/30 flex-shrink-0 shadow-modern">
              <div className="hidden sm:flex items-center space-x-2 text-xs sm:text-sm text-indigo-600 text-center sm:text-left">
                <span className="text-xs sm:text-lg">💡</span>
                <p className="leading-tight font-normal text-xs">Preencha os dados do contrato corretamente.</p>
              </div>
              <div className="flex gap-2 sm:gap-3 justify-center sm:justify-end">
                <button onClick={handleCloseForm} className="px-4 sm:px-5 py-2 sm:py-2.5 btn-secondary rounded-lg sm:rounded-xl shadow-sm hover:shadow-md transition-all duration-200 font-semibold flex-shrink-0 text-sm sm:text-sm">Cancelar</button>
                <button onClick={submit} className="px-4 sm:px-5 py-2 sm:py-2.5 btn-primary rounded-lg sm:rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 font-semibold flex-shrink-0 text-sm sm:text-sm bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700">{editing ? 'Atualizar' : 'Criar'}</button>
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
          <DialogActions>
          </DialogActions>
        </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={6000} onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}>
        <Alert onClose={() => setSnackbar(prev => ({ ...prev, open: false }))} severity={snackbar.severity} sx={{ width: '100%' }}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default Contracts;
