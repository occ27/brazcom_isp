import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { 
  Box, Paper, Typography, Button, IconButton, TextField, 
  CircularProgress, Chip, Snackbar, Alert, useMediaQuery, 
  useTheme, Table, TableBody, TableCell, TableContainer, 
  TableHead, TableRow, TablePagination, Card, CardContent, 
  Divider, InputAdornment, MenuItem, Tabs, Tab, Checkbox,
  Tooltip, Menu, Dialog, DialogTitle, DialogContent, DialogActions
} from '@mui/material';
import { 
  PlusIcon, MagnifyingGlassIcon, XMarkIcon, 
  DocumentArrowDownIcon, CheckCircleIcon, 
  EllipsisVerticalIcon, TrashIcon, 
  ArrowPathIcon, CloudIcon, QrCodeIcon,
  ArrowTopRightOnSquareIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline';
import { useCompany } from '../contexts/CompanyContext';
import receivableService, { Receivable } from '../services/receivableService';
import bankAccountService from '../services/bankAccountService';
import { stringifyError } from '../utils/error';

const Receivables: React.FC = () => {
  const { activeCompany } = useCompany();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  // State
  const [receivables, setReceivables] = useState<Receivable[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [tabValue, setTabValue] = useState(0); // 0: Todos, 1: Pendentes, 2: Registrados, 3: Pagos, 4: Falhas
  
  // Selection
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  
  // Pagination
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  
  // Search & Filter
  const [searchTerm, setSearchTerm] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  
  // UI State
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' | 'warning' });
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedReceivable, setSelectedReceivable] = useState<Receivable | null>(null);
  const [errorDialog, setErrorDialog] = useState<{open: boolean, msg: string}>({ open: false, msg: '' });

  const loadReceivables = useCallback(async () => {
    if (!activeCompany) return;
    setLoading(true);
    try {
      const data = await receivableService.listReceivables(activeCompany.id, 0, 500, startDate, endDate);
      setReceivables(data || []);
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao carregar cobranças', severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [activeCompany, startDate, endDate]);

  useEffect(() => {
    if (activeCompany) {
      loadReceivables();
    }
  }, [activeCompany, loadReceivables]);

  // Filter Logic
  const filteredReceivables = useMemo(() => {
    let result = receivables;
    
    // Tab Filter
    if (tabValue === 1) result = result.filter(r => r.status === 'PENDING');
    else if (tabValue === 2) result = result.filter(r => r.status === 'REGISTERED');
    else if (tabValue === 3) result = result.filter(r => r.status === 'PAID');
    else if (tabValue === 4) result = result.filter(r => r.status === 'REGISTRATION_FAILED');
    
    // Search Filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter(r =>
        r.id.toString().includes(term) ||
        (r.cliente_nome || '').toLowerCase().includes(term) ||
        (r.nosso_numero || '').toLowerCase().includes(term) ||
        (r.bank || '').toLowerCase().includes(term)
      );
    }
    
    return result;
  }, [receivables, tabValue, searchTerm]);

  // Pagination Logic
  const paginatedReceivables = useMemo(() => {
    const start = page * rowsPerPage;
    return filteredReceivables.slice(start, start + rowsPerPage);
  }, [filteredReceivables, page, rowsPerPage]);

  const handleGenerate = useCallback(async () => {
    if (!activeCompany) return;
    setGenerating(true);
    try {
      const created = await receivableService.generateForCompany(activeCompany.id);
      setSnackbar({ open: true, message: `${created?.length || 0} cobranças geradas com sucesso`, severity: 'success' });
      loadReceivables();
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao gerar cobranças', severity: 'error' });
    } finally {
      setGenerating(false);
    }
  }, [activeCompany, loadReceivables]);

  const handleSettle = async (id: number) => {
    try {
      await receivableService.settleReceivable(id);
      setSnackbar({ open: true, message: 'Cobrança marcada como paga', severity: 'success' });
      loadReceivables();
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e), severity: 'error' });
    }
    setAnchorEl(null);
  };

  const handleCancel = async (id: number) => {
    if (!window.confirm('Deseja realmente cancelar esta cobrança?')) return;
    try {
      await receivableService.cancelReceivable(id);
      setSnackbar({ open: true, message: 'Cobrança cancelada', severity: 'success' });
      loadReceivables();
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e), severity: 'error' });
    }
    setAnchorEl(null);
  };

  const handleBatchRegisterBB = async () => {
    if (!activeCompany || selectedIds.length === 0) return;
    
    // Precisamos de uma conta bancária BB para registrar. 
    // Vamos assumir que o backend sabe qual usar ou pegamos a primeira disponível do BB.
    setLoading(true);
    try {
      // Buscar contas para achar uma do BB
      const accounts = await bankAccountService.listBankAccounts(activeCompany.id);
      const bbAccount = accounts.find(a => a.bank === 'BANCO DO BRASIL' || a.bank === 'BANCO_DO_BRASIL');
      
      if (!bbAccount) {
        setSnackbar({ open: true, message: 'Nenhuma conta do Banco do Brasil configurada para registro API', severity: 'error' });
        setLoading(false);
        return;
      }

      const res = await bankAccountService.registerBoletosApi(activeCompany.id, bbAccount.id, selectedIds);
      const successCount = res.results.filter((r: any) => r.ok).length;
      const errorCount = res.results.filter((r: any) => !r.ok).length;
      
      if (errorCount === 0) {
        setSnackbar({ open: true, message: `${successCount} boletos registrados com sucesso`, severity: 'success' });
      } else {
        setSnackbar({ open: true, message: `${successCount} sucesso, ${errorCount} erro(s).`, severity: 'warning' });
      }
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
    if (s === 'REGISTRATION_FAILED') return (
      <Tooltip title="Clique para ver o erro">
        <Chip 
          label="Falha no Registro" 
          size="small" 
          color="error" 
          onClick={(e) => {
            e.stopPropagation();
            const r = receivables.find(x => x.status === status); // This is wrong, should pass the receivable
          }}
        />
      </Tooltip>
    );
    return <Chip label={status} size="small" />;
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', p: 2 }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h5" sx={{ fontWeight: 700, color: 'primary.main' }}>
          Gestão de Cobranças
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {selectedIds.length > 0 && (
            <Button 
              variant="contained" 
              color="secondary"
              startIcon={<CloudIcon className="w-5 h-5" />}
              onClick={handleBatchRegisterBB}
            >
              Registrar Selecionados ({selectedIds.length})
            </Button>
          )}
          <Button 
            variant="contained" 
            startIcon={generating ? <CircularProgress size={20} color="inherit" /> : <PlusIcon className="w-5 h-5" />}
            onClick={handleGenerate}
            disabled={generating}
            sx={{ borderRadius: 2 }}
          >
            Gerar Cobranças do Mês
          </Button>
        </Box>
      </Box>

      <Paper sx={{ borderRadius: 3, overflow: 'hidden', flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Tabs */}
        <Tabs 
          value={tabValue} 
          onChange={(_, v) => { setTabValue(v); setPage(0); }} 
          sx={{ borderBottom: 1, borderColor: 'divider', px: 2, pt: 1 }}
        >
          <Tab label="Todos" />
          <Tab label="Pendentes" />
          <Tab label="Registrados" />
          <Tab label="Pagos" />
          <Tab label="Falhas" />
        </Tabs>

        {/* Search & Actions */}
        <Box sx={{ p: 2, display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <TextField
            sx={{ flexGrow: 1, minWidth: 200 }}
            size="small"
            placeholder="Buscar por cliente, nosso número ou ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <MagnifyingGlassIcon className="w-5 h-5 text-gray-400" />
                </InputAdornment>
              ),
              endAdornment: searchTerm && (
                <IconButton size="small" onClick={() => setSearchTerm('')}>
                  <XMarkIcon className="w-4 h-4" />
                </IconButton>
              )
            }}
          />
          
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <TextField
              type="date"
              label="Início"
              size="small"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              InputLabelProps={{ shrink: true }}
              sx={{ width: 150 }}
            />
            <TextField
              type="date"
              label="Fim"
              size="small"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              InputLabelProps={{ shrink: true }}
              sx={{ width: 150 }}
            />
            {(startDate || endDate) && (
              <IconButton size="small" onClick={() => { setStartDate(''); setEndDate(''); }}>
                <XMarkIcon className="w-4 h-4" />
              </IconButton>
            )}
          </Box>

          <IconButton onClick={loadReceivables} disabled={loading}>
            <ArrowPathIcon className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </IconButton>
        </Box>

        {/* Table */}
        <TableContainer sx={{ flexGrow: 1 }}>
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox">
                  <Checkbox 
                    checked={selectedIds.length === paginatedReceivables.length && paginatedReceivables.length > 0}
                    indeterminate={selectedIds.length > 0 && selectedIds.length < paginatedReceivables.length}
                    onChange={(e) => {
                      if (e.target.checked) setSelectedIds(paginatedReceivables.map(r => r.id));
                      else setSelectedIds([]);
                    }}
                  />
                </TableCell>
                <TableCell sx={{ fontWeight: 600 }}>ID</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Cliente</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Vencimento</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">Valor</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Banco</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">Ações</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading && filteredReceivables.length === 0 ? (
                <TableRow><TableCell colSpan={8} align="center" sx={{ py: 5 }}><CircularProgress /></TableCell></TableRow>
              ) : paginatedReceivables.length === 0 ? (
                <TableRow><TableCell colSpan={8} align="center" sx={{ py: 5 }}>Nenhuma cobrança encontrada</TableCell></TableRow>
              ) : paginatedReceivables.map(r => (
                <TableRow key={r.id} hover>
                  <TableCell padding="checkbox">
                    <Checkbox 
                      checked={selectedIds.includes(r.id)}
                      onChange={() => setSelectedIds(prev => prev.includes(r.id) ? prev.filter(id => id !== r.id) : [...prev, r.id])}
                    />
                  </TableCell>
                  <TableCell>{r.id}</TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>{r.cliente_nome || '-'}</Typography>
                    <Typography variant="caption" color="text.secondary">{r.cliente_cpf_cnpj}</Typography>
                  </TableCell>
                  <TableCell>{new Date(r.due_date).toLocaleDateString('pt-BR')}</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 600 }}>
                    {r.amount.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </TableCell>
                  <TableCell>
                    {r.status === 'REGISTRATION_FAILED' ? (
                      <Tooltip title="Ver erro de registro">
                        <Chip 
                          label="Falha" 
                          size="small" 
                          color="error" 
                          variant="outlined"
                          onClick={() => setErrorDialog({ open: true, msg: r.registro_result || 'Erro desconhecido' })}
                          sx={{ cursor: 'pointer' }}
                        />
                      </Tooltip>
                    ) : getStatusChip(r.status)}
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <Typography variant="caption" sx={{ fontWeight: 600 }}>{r.bank}</Typography>
                      {r.nosso_numero && <Typography variant="caption" color="text.secondary">({r.nosso_numero})</Typography>}
                    </Box>
                  </TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                      {r.bb_boleto_url && (
                        <Tooltip title="Ver PDF">
                          <IconButton size="small" onClick={() => window.open(r.bb_boleto_url, '_blank')}>
                            <ArrowTopRightOnSquareIcon className="w-4 h-4 text-blue-500" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {r.bb_pix_qrcode && (
                        <Tooltip title="Copiar PIX">
                          <IconButton size="small" onClick={() => {
                            navigator.clipboard.writeText(r.bb_pix_qrcode!);
                            setSnackbar({ open: true, message: 'PIX copiado!', severity: 'success' });
                          }}>
                            <QrCodeIcon className="w-4 h-4 text-green-500" />
                          </IconButton>
                        </Tooltip>
                      )}
                      <IconButton size="small" onClick={(e) => {
                        setAnchorEl(e.currentTarget);
                        setSelectedReceivable(r);
                      }}>
                        <EllipsisVerticalIcon className="w-5 h-5" />
                      </IconButton>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          rowsPerPageOptions={[10, 25, 50, 100]}
          component="div"
          count={filteredReceivables.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={(_, p) => setPage(p)}
          onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
          labelRowsPerPage="Itens por página:"
        />
      </Paper>

      {/* Row Actions Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={() => setAnchorEl(null)}
      >
        <MenuItem onClick={() => handleSettle(selectedReceivable!.id)} disabled={selectedReceivable?.status === 'PAID'}>
          <CheckCircleIcon className="w-4 h-4 mr-2 text-green-500" /> Baixar Manualmente
        </MenuItem>
        <MenuItem onClick={() => handleCancel(selectedReceivable!.id)} disabled={selectedReceivable?.status === 'PAID'}>
          <TrashIcon className="w-4 h-4 mr-2 text-red-500" /> Cancelar Cobrança
        </MenuItem>
        <Divider />
        <MenuItem onClick={() => setAnchorEl(null)}>
          <InformationCircleIcon className="w-4 h-4 mr-2" /> Ver Detalhes
        </MenuItem>
      </Menu>

      {/* Error Dialog */}
      <Dialog open={errorDialog.open} onClose={() => setErrorDialog({ ...errorDialog, open: false })}>
        <DialogTitle sx={{ color: 'error.main', display: 'flex', alignItems: 'center', gap: 1 }}>
          <InformationCircleIcon className="w-6 h-6" /> Detalhes do Erro de Registro
        </DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', bgcolor: '#f5f5f5', p: 2, borderRadius: 1 }}>
            {errorDialog.msg}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setErrorDialog({ ...errorDialog, open: false })}>Fechar</Button>
        </DialogActions>
      </Dialog>

      <Snackbar 
        open={snackbar.open} 
        autoHideDuration={6000} 
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert severity={snackbar.severity} sx={{ borderRadius: 2 }}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default Receivables;
