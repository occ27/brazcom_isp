import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { 
  Box, Paper, Typography, Button, IconButton, TextField, 
  CircularProgress, Chip, Snackbar, Alert, useMediaQuery, 
  useTheme, Table, TableBody, TableCell, TableContainer, 
  TableHead, TableRow, Card, CardContent, Divider, 
  InputAdornment, MenuItem, Tooltip, Tabs, Tab,
  Dialog, DialogTitle, DialogContent, DialogActions,
  FormControlLabel, Checkbox, Grid, Select, FormControl, InputLabel,
  TablePagination
} from '@mui/material';
import { 
  PlusIcon, PencilIcon, TrashIcon, MagnifyingGlassIcon, 
  XMarkIcon, PlayIcon, ArrowDownTrayIcon, ArrowUpTrayIcon,
  DocumentDuplicateIcon, CheckCircleIcon, InformationCircleIcon,
  ArrowPathIcon, CloudIcon, ArrowTopRightOnSquareIcon, QrCodeIcon
} from '@heroicons/react/24/outline';
import { useCompany } from '../contexts/CompanyContext';
import bankAccountService, { BankAccount } from '../services/bankAccountService';
import { stringifyError } from '../utils/error';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`bank-tabpanel-${index}`}
      aria-labelledby={`bank-tab-${index}`}
      {...other}
      style={{ height: '100%' }}
    >
      {value === index && (
        <Box sx={{ py: 3, height: '100%' }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const BankAccounts: React.FC = () => {
  const { activeCompany } = useCompany();
  const theme = useTheme();
  
  // State
  const [tabValue, setTabValue] = useState(1);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingAccount, setEditingAccount] = useState<BankAccount | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' | 'warning' });
  
  // Boletos Tab State
  const [selectedAccount, setSelectedAccount] = useState<number | ''>('');
  const [boletos, setBoletos] = useState<any[]>([]);
  const [boletoLoading, setBoletoLoading] = useState(false);
  const [selectedBoletoIds, setSelectedBoletoIds] = useState<number[]>([]);
  const [boletoStatus, setBoletoStatus] = useState<string>('');
  const [boletoStartDate, setBoletoStartDate] = useState('');
  const [boletoEndDate, setBoletoEndDate] = useState('');
  const [boletoDateType, setBoletoDateType] = useState('due_date');
  const [boletoPage, setBoletoPage] = useState(0);
  const [boletoRowsPerPage, setBoletoRowsPerPage] = useState(50);
  const [boletoTotal, setBoletoTotal] = useState(0);
  
  // Retorno Tab State
  const [retornoFile, setRetornoFile] = useState<File | null>(null);
  const [retornoLoading, setRetornoLoading] = useState(false);
  const [retornoResult, setRetornoResult] = useState<any>(null);

  // Form State
  const [formData, setFormData] = useState<Partial<BankAccount>>({
    bank: 'SICOB',
    name: '',
    codigo_banco: '756',
    agencia: '',
    agencia_dv: '',
    conta: '',
    conta_dv: '',
    titular: '',
    cpf_cnpj_titular: '',
    carteira: '',
    carteira_variacao: '',
    convenio: '',
    cnab_version: '240',
    instrucao1: '',
    instrucao2: '',
    dias_protesto: 0,
    dias_baixa: 0,
    is_default: false,
    is_active: true,
    multa_atraso_percentual: 2.0,
    juros_atraso_percentual: 1.0,
    desconto_pontualidade_tipo: 'VALOR' as 'VALOR' | 'PERCENTUAL',
    desconto_pontualidade_valor: 0.0,
    desconto_pontualidade_dias: 0,
    sicoob_client_id: '',
    sicoob_access_token: '',
    sicredi_codigo_beneficiario: '',
    sicredi_posto: '',
    sicredi_byte_id: '',
    bb_client_id: '',
    bb_client_secret: '',
    bb_app_key: '',
    bb_sandbox: true
  });
  
  const [errors, setErrors] = useState<Record<string, string>>({});

  const loadBankAccounts = useCallback(async () => {
    if (!activeCompany) return;
    setLoading(true);
    try {
      const data = await bankAccountService.listBankAccounts(activeCompany.id);
      setBankAccounts(data || []);
      if (data && data.length > 0 && !selectedAccount) {
        setSelectedAccount(data[0].id);
      }
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao carregar contas bancárias', severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [activeCompany, selectedAccount]);

  useEffect(() => {
    if (activeCompany) {
      loadBankAccounts();
    }
  }, [activeCompany, loadBankAccounts]);

  const loadBoletos = useCallback(async () => {
    if (!activeCompany || !selectedAccount) return;
    setBoletoLoading(true);
    try {
      const data = await bankAccountService.listBoletos(activeCompany.id, selectedAccount as number, { 
        status: boletoStatus || undefined,
        start_date: boletoStartDate || undefined,
        end_date: boletoEndDate || undefined,
        date_type: boletoDateType,
        page: boletoPage + 1,
        per_page: boletoRowsPerPage
      });
      setBoletos(data.data || []);
      setBoletoTotal(data.total || 0);
      setSelectedBoletoIds([]);
    } catch (e) {
      setSnackbar({ open: true, message: 'Erro ao carregar boletos', severity: 'error' });
    } finally {
      setBoletoLoading(false);
    }
  }, [activeCompany, selectedAccount, boletoStatus, boletoStartDate, boletoEndDate, boletoDateType, boletoPage, boletoRowsPerPage]);

  useEffect(() => {
    setBoletoPage(0);
  }, [selectedAccount, boletoStatus, boletoStartDate, boletoEndDate, boletoDateType]);

  useEffect(() => {
    if (tabValue === 1 && selectedAccount) {
      loadBoletos();
    }
  }, [tabValue, selectedAccount, loadBoletos]);

  const handleTabChange = (_: any, newValue: number) => {
    setTabValue(newValue);
  };

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => {
      const newData = { ...prev, [field]: value };
      if (field === 'bank') {
        if (value === 'SICOB') newData.codigo_banco = '756';
        else if (value === 'SICREDI') newData.codigo_banco = '748';
        else if (value === 'BANCO DO BRASIL' || value === 'BANCO_DO_BRASIL') newData.codigo_banco = '001';
      }
      return newData;
    });
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: '' }));
  };

  const handleSave = async () => {
    if (!activeCompany) return;
    try {
      if (editingAccount) {
        await bankAccountService.updateBankAccount(activeCompany.id, editingAccount.id, formData);
        setSnackbar({ open: true, message: 'Conta atualizada com sucesso', severity: 'success' });
      } else {
        await bankAccountService.createBankAccount(activeCompany.id, formData);
        setSnackbar({ open: true, message: 'Conta criada com sucesso', severity: 'success' });
      }
      setOpenDialog(false);
      loadBankAccounts();
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao salvar conta', severity: 'error' });
    }
  };

  const handleRegisterBB = async () => {
    if (!activeCompany || !selectedAccount || selectedBoletoIds.length === 0) return;
    setBoletoLoading(true);
    try {
      const res = await bankAccountService.registerBoletosApi(activeCompany.id, selectedAccount as number, selectedBoletoIds);
      const successCount = res.results.filter((r: any) => r.ok).length;
      const errors = res.results.filter((r: any) => !r.ok);
      const errorCount = errors.length;
      
      if (errorCount === 0) {
        setSnackbar({ open: true, message: `${successCount} boleto(s) registrado(s) com sucesso no BB`, severity: 'success' });
      } else {
        const firstError = errors[0]?.error || 'Erro desconhecido';
        setSnackbar({ 
          open: true, 
          message: errorCount === 1 ? `Erro: ${firstError}` : `${successCount} sucesso, ${errorCount} erro(s). Primeiro erro: ${firstError}`, 
          severity: 'error' 
        });
      }
      loadBoletos();
      setSelectedBoletoIds([]);
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao registrar boletos no BB', severity: 'error' });
    } finally {
      setBoletoLoading(false);
    }
  };

  const handleCancelBoletoBB = async (receivableId: number) => {
    if (!activeCompany || !selectedAccount || !window.confirm('Deseja solicitar a baixa deste boleto na API do BB?')) return;
    try {
      await bankAccountService.cancelBoletoApi(activeCompany.id, selectedAccount as number, receivableId);
      setSnackbar({ open: true, message: 'Baixa solicitada com sucesso', severity: 'success' });
      loadBoletos();
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao cancelar boleto', severity: 'error' });
    }
  };

  const handleUploadRetorno = async () => {
    if (!activeCompany || !selectedAccount || !retornoFile) return;
    setRetornoLoading(true);
    setRetornoResult(null);
    try {
      const res = await bankAccountService.uploadRetorno(activeCompany.id, selectedAccount as number, retornoFile);
      setRetornoResult(res);
      setSnackbar({ open: true, message: 'Arquivo de retorno processado', severity: 'success' });
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao processar retorno', severity: 'error' });
    } finally {
      setRetornoLoading(false);
    }
  };

  const currentAccount = useMemo(() => 
    bankAccounts.find(a => a.id === selectedAccount), 
    [bankAccounts, selectedAccount]
  );

  const isBB = currentAccount?.bank === 'BANCO DO BRASIL' || currentAccount?.bank === 'BANCO_DO_BRASIL';

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', p: 2 }}>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h5" sx={{ fontWeight: 700, color: 'primary.main' }}>
          Gestão Bancária e Cobranças
        </Typography>
        <Button 
          variant="contained" 
          startIcon={<PlusIcon className="w-5 h-5" />}
          onClick={() => {
            setEditingAccount(null);
            setFormData({ bank: 'SICOB', is_active: true, bb_sandbox: true });
            setOpenDialog(true);
          }}
          sx={{ borderRadius: 2 }}
        >
          Nova Conta
        </Button>
      </Box>

      <Paper sx={{ borderRadius: 3, display: 'flex', flexDirection: 'column' }}>
        <Tabs 
          value={tabValue} 
          onChange={handleTabChange} 
          variant="scrollable"
          scrollButtons="auto"
          sx={{ borderBottom: 1, borderColor: 'divider', px: 2, pt: 1 }}
        >
          <Tab label="Contas Bancárias" icon={<CheckCircleIcon className="w-5 h-5" />} iconPosition="start" />
          <Tab label="Boletos / API" icon={<DocumentDuplicateIcon className="w-5 h-5" />} iconPosition="start" />
          <Tab label="Remessa" icon={<ArrowDownTrayIcon className="w-5 h-5" />} iconPosition="start" />
          <Tab label="Retorno" icon={<ArrowUpTrayIcon className="w-5 h-5" />} iconPosition="start" />
        </Tabs>

        {/* Tab 0: Contas */}
        <TabPanel value={tabValue} index={0}>
          <Box sx={{ px: 2 }}>
            {loading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 5 }}><CircularProgress /></Box>
            ) : (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600 }}>Banco</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Agência/Conta</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Nome/Titular</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>API BB</TableCell>
                      <TableCell sx={{ fontWeight: 600 }} align="right">Ações</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {bankAccounts.map(acc => (
                      <TableRow key={acc.id} hover>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Chip label={acc.bank} size="small" color="primary" variant="outlined" />
                            {acc.is_default && <Chip label="Padrão" size="small" color="success" />}
                          </Box>
                        </TableCell>
                        <TableCell>
                          {acc.agencia}-{acc.agencia_dv} / {acc.conta}-{acc.conta_dv}
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>{acc.name || '-'}</Typography>
                          <Typography variant="caption" color="text.secondary">{acc.titular}</Typography>
                        </TableCell>
                        <TableCell>
                          {(acc.bank === 'BANCO DO BRASIL' || acc.bank === 'BANCO_DO_BRASIL') ? (
                            <Chip 
                              label={acc.bb_sandbox ? 'Sandbox' : 'Produção'} 
                              size="small" 
                              color={acc.bb_sandbox ? 'warning' : 'success'} 
                              icon={<CloudIcon className="w-3 h-3" />}
                            />
                          ) : '-'}
                        </TableCell>
                        <TableCell align="right">
                          <IconButton onClick={() => {
                            setEditingAccount(acc);
                            setFormData({ ...acc, bb_client_secret: '' });
                            setOpenDialog(true);
                          }}><PencilIcon className="w-4 h-4" /></IconButton>
                          <IconButton color="error" onClick={() => {
                            if (window.confirm('Excluir esta conta?')) {
                              bankAccountService.deleteBankAccount(activeCompany!.id, acc.id).then(() => loadBankAccounts());
                            }
                          }}><TrashIcon className="w-4 h-4" /></IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Box>
        </TabPanel>

        {/* Tab 1: Boletos / API */}
        <TabPanel value={tabValue} index={1}>
          <Box sx={{ px: 2 }}>
            <Box sx={{ mb: 2, display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
              <FormControl size="small" sx={{ minWidth: 200 }}>
                <InputLabel>Conta Bancária</InputLabel>
                <Select
                  value={selectedAccount}
                  label="Conta Bancária"
                  onChange={(e) => setSelectedAccount(e.target.value as number)}
                >
                  {bankAccounts.map(a => (
                    <MenuItem key={a.id} value={a.id}>{a.name || a.bank}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              <FormControl size="small" sx={{ minWidth: 150 }}>
                <InputLabel>Status</InputLabel>
                <Select
                  value={boletoStatus}
                  label="Status"
                  onChange={(e) => setBoletoStatus(e.target.value)}
                >
                  <MenuItem value="">Todos</MenuItem>
                  <MenuItem value="PENDING">Pendente</MenuItem>
                  <MenuItem value="REGISTERED">Registrado</MenuItem>
                  <MenuItem value="PAID">Pago</MenuItem>
                </Select>
              </FormControl>

              <FormControl size="small" sx={{ minWidth: 150 }}>
                <InputLabel>Filtrar por</InputLabel>
                <Select
                  value={boletoDateType}
                  label="Filtrar por"
                  onChange={(e) => setBoletoDateType(e.target.value)}
                >
                  <MenuItem value="due_date">Vencimento</MenuItem>
                  <MenuItem value="issue_date">Emissão</MenuItem>
                </Select>
              </FormControl>

              <TextField type="date" label="Início" size="small" value={boletoStartDate} onChange={(e) => setBoletoStartDate(e.target.value)} InputLabelProps={{ shrink: true }} />
              <TextField type="date" label="Fim" size="small" value={boletoEndDate} onChange={(e) => setBoletoEndDate(e.target.value)} InputLabelProps={{ shrink: true }} />

              <Button 
                variant="outlined" 
                startIcon={<ArrowPathIcon className="w-4 h-4" />}
                onClick={loadBoletos}
                disabled={!selectedAccount || boletoLoading}
              >
                Atualizar
              </Button>

              <Box sx={{ flexGrow: 1 }} />

              {isBB && (
                <Button 
                  variant="contained" 
                  color="secondary"
                  startIcon={<CloudIcon className="w-4 h-4" />}
                  onClick={handleRegisterBB}
                  disabled={selectedBoletoIds.length === 0 || boletoLoading}
                >
                  {boletoLoading ? <CircularProgress size={20} color="inherit" /> : `Registrar via API BB (${selectedBoletoIds.length})`}
                </Button>
              )}
            </Box>

            <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: '70vh', overflow: 'auto' }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell padding="checkbox">
                      <Checkbox 
                        checked={selectedBoletoIds.length === boletos.length && boletos.length > 0}
                        indeterminate={selectedBoletoIds.length > 0 && selectedBoletoIds.length < boletos.length}
                        onChange={(e) => {
                          if (e.target.checked) setSelectedBoletoIds(boletos.map(b => b.id));
                          else setSelectedBoletoIds([]);
                        }}
                      />
                    </TableCell>
                    <TableCell>Cliente</TableCell>
                    <TableCell>Emissão</TableCell>
                    <TableCell>Vencimento</TableCell>
                    <TableCell align="right">Valor</TableCell>
                    <TableCell>Nosso Número</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">BB API</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {boletoLoading ? (
                    <TableRow><TableCell colSpan={7} align="center" sx={{ py: 3 }}><CircularProgress size={24} /></TableCell></TableRow>
                  ) : boletos.length === 0 ? (
                    <TableRow><TableCell colSpan={7} align="center" sx={{ py: 3 }}>Nenhum boleto encontrado</TableCell></TableRow>
                  ) : boletos.map(b => (
                    <TableRow key={b.id} hover>
                      <TableCell padding="checkbox">
                        <Checkbox 
                          checked={selectedBoletoIds.includes(b.id)}
                          onChange={() => {
                            setSelectedBoletoIds(prev => prev.includes(b.id) ? prev.filter(id => id !== b.id) : [...prev, b.id]);
                          }}
                        />
                      </TableCell>
                      <TableCell>{b.cliente_nome}</TableCell>
                      <TableCell>{new Date(b.issue_date).toLocaleDateString('pt-BR')}</TableCell>
                      <TableCell>{new Date(b.due_date).toLocaleDateString('pt-BR')}</TableCell>
                      <TableCell align="right">{b.amount.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</TableCell>
                      <TableCell sx={{ fontFamily: 'monospace' }}>{b.nosso_numero || '-'}</TableCell>
                      <TableCell>
                        <Chip label={b.status} size="small" color={b.status === 'PAID' ? 'success' : b.status === 'REGISTERED' ? 'primary' : 'default'} />
                      </TableCell>
                      <TableCell align="right">
                        {b.bb_boleto_url && (
                          <Tooltip title="Abrir Boleto PDF">
                            <IconButton size="small" onClick={() => window.open(b.bb_boleto_url, '_blank')}>
                              <ArrowTopRightOnSquareIcon className="w-4 h-4 text-blue-500" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {b.bb_pix_qrcode && (
                          <Tooltip title="PIX QR Code">
                            <IconButton size="small" onClick={() => {
                              navigator.clipboard.writeText(b.bb_pix_qrcode);
                              setSnackbar({ open: true, message: 'PIX Copia e Cola copiado!', severity: 'success' });
                            }}>
                              <QrCodeIcon className="w-4 h-4 text-green-500" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {b.bb_boleto_numero && b.status !== 'PAID' && (
                          <Tooltip title="Cancelar/Baixar API BB">
                            <IconButton size="small" color="error" onClick={() => handleCancelBoletoBB(b.id)}>
                              <TrashIcon className="w-4 h-4" />
                            </IconButton>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination 
              component="div" 
              count={boletoTotal} 
              rowsPerPage={boletoRowsPerPage} 
              page={boletoPage} 
              onPageChange={(_, p) => setBoletoPage(p)} 
              onRowsPerPageChange={(e) => { setBoletoRowsPerPage(parseInt(e.target.value, 10)); setBoletoPage(0); }} 
              labelRowsPerPage="Itens por página:"
              labelDisplayedRows={({ from, to, count }) => `${from}-${to} de ${count !== -1 ? count : `mais de ${to}`}`}
              sx={{ 
                '.MuiTablePagination-toolbar': { justifyContent: 'flex-start' },
                '.MuiTablePagination-spacer': { display: 'none' }
              }}
            />
          </Box>
        </TabPanel>

        {/* Tab 2: Remessa */}
        <TabPanel value={tabValue} index={2}>
          <Box sx={{ px: 2, textAlign: 'center', py: 5 }}>
            <Typography variant="h6">Arquivos de Remessa (CNAB)</Typography>
            <Typography color="text.secondary" sx={{ mb: 3 }}>Gere arquivos de remessa para registro manual em bancos sem integração por API.</Typography>
            <Button variant="outlined" startIcon={<ArrowDownTrayIcon className="w-5 h-5" />}>
              Gerar Remessa CNAB
            </Button>
          </Box>
        </TabPanel>

        {/* Tab 3: Retorno */}
        <TabPanel value={tabValue} index={3}>
          <Box sx={{ px: 2, maxWidth: 600, mx: 'auto', py: 3 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>Importar Arquivo de Retorno</Typography>
            <Paper variant="outlined" sx={{ p: 3, textAlign: 'center', backgroundColor: '#f9fafb' }}>
              <input
                accept=".ret,.TXT"
                style={{ display: 'none' }}
                id="retorno-file-upload"
                type="file"
                onChange={(e) => setRetornoFile(e.target.files?.[0] || null)}
              />
              <label htmlFor="retorno-file-upload">
                <Button variant="outlined" component="span" startIcon={<ArrowUpTrayIcon className="w-5 h-5" />} sx={{ mb: 2 }}>
                  {retornoFile ? retornoFile.name : 'Selecionar Arquivo .RET'}
                </Button>
              </label>
              
              {retornoFile && (
                <Box sx={{ mt: 2 }}>
                  <Button 
                    variant="contained" 
                    fullWidth 
                    onClick={handleUploadRetorno}
                    disabled={retornoLoading || !selectedAccount}
                  >
                    {retornoLoading ? <CircularProgress size={20} /> : 'Processar Agora'}
                  </Button>
                </Box>
              )}
            </Paper>

            {retornoResult && (
              <Box sx={{ mt: 3 }}>
                <Alert severity="success">
                  {retornoResult.message || 'Processamento concluído'}
                </Alert>
              </Box>
            )}
          </Box>
        </TabPanel>
      </Paper>

      {/* Dialog for Create/Edit */}
      <Dialog 
        open={openDialog} 
        onClose={() => setOpenDialog(false)} 
        maxWidth="md" 
        fullWidth
        PaperProps={{ sx: { borderRadius: 3 } }}
      >
        <DialogTitle sx={{ fontWeight: 700 }}>
          {editingAccount ? 'Editar Conta Bancária' : 'Nova Conta Bancária'}
        </DialogTitle>
        <DialogContent dividers>
          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={12} md={6}>
              <TextField
                select
                fullWidth
                label="Banco"
                value={formData.bank}
                onChange={e => handleInputChange('bank', e.target.value)}
                error={!!errors.bank}
              >
                <MenuItem value="SICOB">SICOOB (API)</MenuItem>
                <MenuItem value="SICREDI">SICREDI (CNAB/API)</MenuItem>
                <MenuItem value="BANCO DO BRASIL">BANCO DO BRASIL (API)</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Nome da Configuração"
                value={formData.name}
                onChange={e => handleInputChange('name', e.target.value)}
              />
            </Grid>

            <Grid item xs={6} md={4}>
              <TextField fullWidth label="Agência" value={formData.agencia} onChange={e => handleInputChange('agencia', e.target.value)} />
            </Grid>
            <Grid item xs={6} md={2}>
              <TextField fullWidth label="DV" value={formData.agencia_dv} onChange={e => handleInputChange('agencia_dv', e.target.value)} />
            </Grid>
            <Grid item xs={6} md={4}>
              <TextField fullWidth label="Conta" value={formData.conta} onChange={e => handleInputChange('conta', e.target.value)} />
            </Grid>
            <Grid item xs={6} md={2}>
              <TextField fullWidth label="DV" value={formData.conta_dv} onChange={e => handleInputChange('conta_dv', e.target.value)} />
            </Grid>

            <Grid item xs={12} md={8}>
              <TextField fullWidth label="Titular" value={formData.titular} onChange={e => handleInputChange('titular', e.target.value)} />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField fullWidth label="CPF/CNPJ Titular" value={formData.cpf_cnpj_titular} onChange={e => handleInputChange('cpf_cnpj_titular', e.target.value)} />
            </Grid>

            <Grid item xs={12}><Divider><Chip label="Configurações de Boleto" size="small" /></Divider></Grid>

            <Grid item xs={4}>
              <TextField fullWidth label="Carteira" value={formData.carteira} onChange={e => handleInputChange('carteira', e.target.value)} />
            </Grid>
            <Grid item xs={4}>
              <TextField fullWidth label="Variação" value={formData.carteira_variacao} onChange={e => handleInputChange('carteira_variacao', e.target.value)} />
            </Grid>
            <Grid item xs={4}>
              <TextField fullWidth label="Convênio" value={formData.convenio} onChange={e => handleInputChange('convenio', e.target.value)} />
            </Grid>

            <Grid item xs={6}>
              <TextField fullWidth label="Instrução 1" value={formData.instrucao1} onChange={e => handleInputChange('instrucao1', e.target.value)} />
            </Grid>
            <Grid item xs={6}>
              <TextField fullWidth label="Instrução 2" value={formData.instrucao2} onChange={e => handleInputChange('instrucao2', e.target.value)} />
            </Grid>

            {(formData.bank === 'BANCO DO BRASIL' || formData.bank === 'BANCO_DO_BRASIL') && (
              <>
                <Grid item xs={12}><Divider><Chip label="Credenciais API BB" size="small" /></Divider></Grid>
                <Grid item xs={12}>
                  <TextField fullWidth label="Client ID" value={formData.bb_client_id} onChange={e => handleInputChange('bb_client_id', e.target.value)} />
                </Grid>
                <Grid item xs={12}>
                  <TextField fullWidth type="password" label="Client Secret" value={formData.bb_client_secret} onChange={e => handleInputChange('bb_client_secret', e.target.value)} placeholder="Deixe em branco para manter o atual" />
                </Grid>
                <Grid item xs={12}>
                  <TextField fullWidth label="App Key (Developer Key)" value={formData.bb_app_key} onChange={e => handleInputChange('bb_app_key', e.target.value)} />
                </Grid>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={<Checkbox checked={formData.bb_sandbox} onChange={e => handleInputChange('bb_sandbox', e.target.checked)} />}
                    label="Ambiente Sandbox (Homologação)"
                  />
                </Grid>
              </>
            )}

            <Grid item xs={12}><Divider><Chip label="Regras de Atraso" size="small" /></Divider></Grid>
            <Grid item xs={6}>
              <TextField 
                fullWidth 
                label="Multa por Atraso (%)" 
                type="number"
                value={formData.multa_atraso_percentual} 
                onChange={e => handleInputChange('multa_atraso_percentual', parseFloat(e.target.value))} 
              />
            </Grid>
            <Grid item xs={6}>
              <TextField 
                fullWidth 
                label="Juros Mensal (%)" 
                type="number"
                value={formData.juros_atraso_percentual} 
                onChange={e => handleInputChange('juros_atraso_percentual', parseFloat(e.target.value))} 
              />
            </Grid>

            <Grid item xs={12}><Divider><Chip label="Desconto de Pontualidade" size="small" color="success" /></Divider></Grid>
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth>
                <InputLabel>Tipo de Desconto</InputLabel>
                <Select
                  label="Tipo de Desconto"
                  value={formData.desconto_pontualidade_tipo || 'VALOR'}
                  onChange={e => handleInputChange('desconto_pontualidade_tipo', e.target.value)}
                >
                  <MenuItem value="VALOR">Valor Fixo (R$)</MenuItem>
                  <MenuItem value="PERCENTUAL">Percentual (%)</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label={formData.desconto_pontualidade_tipo === 'PERCENTUAL' ? 'Desconto (%)' : 'Desconto (R$)'}
                type="number"
                inputProps={{ min: 0, step: 0.01 }}
                value={formData.desconto_pontualidade_valor ?? 0}
                onChange={e => handleInputChange('desconto_pontualidade_valor', parseFloat(e.target.value) || 0)}
                helperText="0 = sem desconto"
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Validade (dias antes do vencimento)"
                type="number"
                inputProps={{ min: 0, step: 1 }}
                value={formData.desconto_pontualidade_dias ?? 0}
                onChange={e => handleInputChange('desconto_pontualidade_dias', parseInt(e.target.value) || 0)}
                helperText="0 = válido até o dia do vencimento"
              />
            </Grid>

            <Grid item xs={12}>
              <FormControlLabel
                control={<Checkbox checked={formData.is_default} onChange={e => handleInputChange('is_default', e.target.checked)} />}
                label="Conta Padrão da Empresa"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={() => setOpenDialog(false)}>Cancelar</Button>
          <Button onClick={handleSave} variant="contained" sx={{ borderRadius: 2 }}>Salvar Alterações</Button>
        </DialogActions>
      </Dialog>

      <Snackbar 
        open={snackbar.open} 
        autoHideDuration={6000} 
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert severity={snackbar.severity}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default BankAccounts;
