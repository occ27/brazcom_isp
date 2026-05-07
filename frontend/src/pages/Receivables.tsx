import React, { useEffect, useState, useCallback, useMemo } from 'react';
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
import receivableService, { Receivable } from '../services/receivableService';
import bankAccountService, { BankAccount } from '../services/bankAccountService';
import { stringifyError } from '../utils/error';
import api from '../services/authService';

const Receivables: React.FC = () => {
  const { activeCompany } = useCompany();
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
  
  // Modals
  const [openCreate, setOpenCreate] = useState(false);
  const [openDetails, setOpenDetails] = useState(false);
  const [openPdfModal, setOpenPdfModal] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  
  // Data for Form
  const [clients, setClients] = useState<any[]>([]);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [formData, setFormData] = useState({
    cliente_id: '',
    amount: '',
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
    try {
      await receivableService.createReceivable({
        ...formData,
        empresa_id: activeCompany.id,
        amount: parseFloat(formData.amount),
        cliente_id: parseInt(formData.cliente_id),
        bank_account_id: parseInt(formData.bank_account_id),
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

  const handleSettle = async (id: number) => {
    if (!window.confirm('Confirmar o recebimento manual desta cobrança? O sistema marcará como PAGO e solicitará baixa no banco se houver boleto registrado.')) return;
    try {
      await receivableService.settleReceivable(id);
      setSnackbar({ open: true, message: 'Cobrança baixada manualmente', severity: 'success' });
      loadReceivables();
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e), severity: 'error' });
    }
    setAnchorEl(null);
  };

  const handleCancel = async (id: number) => {
    if (!window.confirm('Confirmar cancelamento desta cobrança? (Será solicitada baixa no banco se registrada)')) return;
    try {
      await receivableService.cancelReceivable(id);
      setSnackbar({ open: true, message: 'Solicitação de cancelamento enviada', severity: 'success' });
      loadReceivables();
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e), severity: 'error' });
    }
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
            <Button variant="contained" color="secondary" startIcon={<CloudIcon className="w-5 h-5" />} onClick={handleBatchRegisterBB}>
              Registrar Selecionados ({selectedIds.length})
            </Button>
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
                <TableCell>Status</TableCell>
                <TableCell>Banco</TableCell>
                <TableCell align="right">Ações</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading && receivables.length === 0 ? (
                <TableRow><TableCell colSpan={8} align="center" sx={{ py: 5 }}><CircularProgress /></TableCell></TableRow>
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
                  <TableCell>
                    {r.status === 'REGISTRATION_FAILED' ? (
                      <Chip label="Falha" size="small" color="error" variant="outlined" onClick={() => setErrorDialog({ open: true, msg: r.registro_result || '' })} sx={{ cursor: 'pointer' }} />
                    ) : getStatusChip(r.status)}
                  </TableCell>
                  <TableCell><Typography variant="caption" sx={{ fontWeight: 600 }}>{r.bank}</Typography></TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                      {(r.status === 'REGISTERED' || r.status === 'PAID') && (
                        <IconButton 
                          size="small" 
                          onClick={() => handlePrint(r.id)} 
                          title="Imprimir Boleto"
                        >
                          <PrinterIcon className="w-4 h-4" />
                        </IconButton>
                      )}
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
        
        {selectedReceivable?.status !== 'PAID' && selectedReceivable?.status !== 'CANCELLED' && (
          <MenuItem onClick={() => { handleSettle(selectedReceivable!.id); setAnchorEl(null); }}>
            <CheckCircleIcon className="w-4 h-4 mr-2 text-green-500" /> Baixar
          </MenuItem>
        )}
        
        {selectedReceivable?.status !== 'PAID' && selectedReceivable?.status !== 'CANCELLED' && (
          <MenuItem onClick={() => { handleCancel(selectedReceivable!.id); setAnchorEl(null); }}>
            <TrashIcon className="w-4 h-4 mr-2 text-red-500" /> Cancelar
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
            <Grid item xs={6}>
              <TextField label="Valor (R$)" fullWidth size="small" value={formData.amount} onChange={(e) => setFormData({ ...formData, amount: e.target.value })} />
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

      <Snackbar open={snackbar.open} autoHideDuration={6000} onClose={() => setSnackbar({ ...snackbar, open: false })}>
        <Alert severity={snackbar.severity}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default Receivables;
