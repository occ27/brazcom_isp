import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { Box, Paper, Typography, Button, IconButton, TextField, CircularProgress, Chip, Snackbar, Alert, useMediaQuery, useTheme, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TablePagination, Card, CardContent, Divider, Pagination, InputAdornment, MenuItem } from '@mui/material';
import { PlusIcon, PencilIcon, TrashIcon, MagnifyingGlassIcon, XMarkIcon, PlayIcon } from '@heroicons/react/24/outline';
import { useCompany } from '../contexts/CompanyContext';
import bankAccountService from '../services/bankAccountService';
import receivableService from '../services/receivableService';
import { stringifyError } from '../utils/error';

interface BankAccountCreate {
  bank: string;
  codigo_banco?: string;
  agencia?: string;
  agencia_dv?: string;
  conta?: string;
  conta_dv?: string;
  titular?: string;
  cpf_cnpj_titular?: string;
  carteira?: string;
  convenio?: string;
  remittance_config?: string;
  instructions?: string;
  is_default?: boolean;
  gateway_credentials?: string;
  sicoob_client_id?: string;
  sicoob_access_token?: string;
}

interface BankAccount {
  id: number;
  empresa_id: number;
  bank: string;
  codigo_banco?: string;
  agencia?: string;
  agencia_dv?: string;
  conta?: string;
  conta_dv?: string;
  titular?: string;
  cpf_cnpj_titular?: string;
  carteira?: string;
  convenio?: string;
  nosso_numero_sequence?: number;
  remittance_config?: string;
  instructions?: string;
  is_default?: boolean;
  gateway_credentials?: string;
  sicoob_client_id?: string;
  sicoob_access_token?: string;
  created_at: string;
  updated_at?: string;
}

const BankAccounts: React.FC = () => {
  const { activeCompany } = useCompany();
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editingBankAccount, setEditingBankAccount] = useState<BankAccount | null>(null);

  // Pagination state
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Search state
  const [searchTerm, setSearchTerm] = useState('');

  const [formData, setFormData] = useState<BankAccountCreate>({
    bank: 'SICOB',
    codigo_banco: '',
    agencia: '',
    agencia_dv: '',
    conta: '',
    conta_dv: '',
    titular: '',
    cpf_cnpj_titular: '',
    carteira: '',
    convenio: '',
    remittance_config: '',
    instructions: '',
    is_default: false,
    gateway_credentials: '',
    sicoob_client_id: '',
    sicoob_access_token: ''
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' | 'warning' });

  const loadBankAccounts = useCallback(async () => {
    if (!activeCompany) return;
    setLoading(true);
    try {
      const data = await bankAccountService.listBankAccounts(activeCompany.id);
      setBankAccounts(data || []);
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao carregar contas bancárias', severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [activeCompany]);

  useEffect(() => {
    if (activeCompany) {
      loadBankAccounts();
    }
  }, [activeCompany, loadBankAccounts]);

  // Filter bank accounts based on search term
  const filteredBankAccounts = useMemo(() => {
    if (!searchTerm) return bankAccounts;
    const term = searchTerm.toLowerCase();
    return bankAccounts.filter(ba =>
      ba.bank?.toLowerCase().includes(term) ||
      ba.agencia?.toLowerCase().includes(term) ||
      ba.conta?.toLowerCase().includes(term) ||
      ba.titular?.toLowerCase().includes(term) ||
      ba.convenio?.toLowerCase().includes(term)
    );
  }, [bankAccounts, searchTerm]);

  // Paginate filtered results
  const paginatedBankAccounts = useMemo(() => {
    const start = page * rowsPerPage;
    const end = start + rowsPerPage;
    return filteredBankAccounts.slice(start, end);
  }, [filteredBankAccounts, page, rowsPerPage]);

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.bank?.trim()) newErrors.bank = 'Banco é obrigatório';
    if (!formData.agencia?.trim()) newErrors.agencia = 'Agência é obrigatória';
    if (!formData.conta?.trim()) newErrors.conta = 'Conta é obrigatória';
    if (!formData.titular?.trim()) newErrors.titular = 'Titular é obrigatório';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!activeCompany || !validateForm()) return;

    try {
      if (editingBankAccount) {
        await bankAccountService.updateBankAccount(activeCompany.id, editingBankAccount.id, formData);
        setSnackbar({ open: true, message: 'Conta bancária atualizada com sucesso', severity: 'success' });
      } else {
        await bankAccountService.createBankAccount(activeCompany.id, formData);
        setSnackbar({ open: true, message: 'Conta bancária criada com sucesso', severity: 'success' });
      }
      handleClose();
      loadBankAccounts();
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao salvar conta bancária', severity: 'error' });
    }
  };

  const handleOpen = (bankAccount?: BankAccount) => {
    if (bankAccount) {
      setEditingBankAccount(bankAccount);
      setFormData({
        bank: bankAccount.bank || 'SICOB',
        codigo_banco: bankAccount.codigo_banco || '',
        agencia: bankAccount.agencia || '',
        agencia_dv: bankAccount.agencia_dv || '',
        conta: bankAccount.conta || '',
        conta_dv: bankAccount.conta_dv || '',
        titular: bankAccount.titular || '',
        cpf_cnpj_titular: bankAccount.cpf_cnpj_titular || '',
        carteira: bankAccount.carteira || '',
        convenio: bankAccount.convenio || '',
        remittance_config: bankAccount.remittance_config || '',
        instructions: bankAccount.instructions || '',
        is_default: bankAccount.is_default || false,
        gateway_credentials: '', // Não mostrar credenciais existentes por segurança
        sicoob_client_id: bankAccount.sicoob_client_id || '',
        sicoob_access_token: bankAccount.sicoob_access_token || ''
      });
    } else {
      setEditingBankAccount(null);
      setFormData({
        bank: 'SICOB',
        codigo_banco: '',
        agencia: '',
        agencia_dv: '',
        conta: '',
        conta_dv: '',
        titular: '',
        cpf_cnpj_titular: '',
        carteira: '',
        convenio: '',
        remittance_config: '',
        instructions: '',
        is_default: false,
        gateway_credentials: '',
        sicoob_client_id: '',
        sicoob_access_token: ''
      });
    }
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    setEditingBankAccount(null);
    setFormData({
      bank: 'SICOB',
      codigo_banco: '',
      agencia: '',
      agencia_dv: '',
      conta: '',
      conta_dv: '',
      titular: '',
      cpf_cnpj_titular: '',
      carteira: '',
      convenio: '',
      remittance_config: '',
      instructions: '',
      is_default: false,
      gateway_credentials: ''
    });
    setErrors({});
  };

  const handleDelete = async (bankAccount: BankAccount) => {
    if (!activeCompany || !window.confirm(`Excluir conta bancária "${bankAccount.titular}"?`)) return;
    try {
      await bankAccountService.deleteBankAccount(activeCompany.id, bankAccount.id);
      setSnackbar({ open: true, message: 'Conta bancária excluída com sucesso', severity: 'success' });
      loadBankAccounts();
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao excluir conta bancária', severity: 'error' });
    }
  };

  const handleTestSicoob = async (bankAccount: BankAccount) => {
    if (!activeCompany) return;
    try {
      setLoading(true);
      const result = await receivableService.testSicoobIntegration(activeCompany.id, bankAccount.id);
      setSnackbar({ open: true, message: result.message || 'Teste do Sicoob realizado com sucesso', severity: 'success' });
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao testar integração com Sicoob', severity: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleTestSicoobFromForm = async () => {
    if (!activeCompany) return;
    try {
      setLoading(true);
      const result = await receivableService.testSicoobIntegration(activeCompany.id, editingBankAccount?.id, formData);
      setSnackbar({ open: true, message: result.message || 'Teste do Sicoob realizado com sucesso', severity: result.status === 'success' ? 'success' : result.status === 'warning' ? 'warning' : 'error' });
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao testar integração com Sicoob', severity: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleChangePage = (_: any, newPage: number) => {
    setPage(newPage - 1);
  };

  const handleTableRowsPerPageChange = (event: any) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleMobileRowsPerPageChange = (event: any) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const renderBankAccountTable = () => (
    <TableContainer>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Banco</TableCell>
            <TableCell>Agência/Conta</TableCell>
            <TableCell>Titular</TableCell>
            <TableCell>Convênio</TableCell>
            <TableCell>Padrão</TableCell>
            <TableCell>Ações</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {paginatedBankAccounts.map((ba) => (
            <TableRow key={ba.id}>
              <TableCell>
                <Chip label={ba.bank} color="primary" size="small" />
              </TableCell>
              <TableCell>
                {ba.agencia && ba.conta ? `${ba.agencia}${ba.agencia_dv || ''} / ${ba.conta}${ba.conta_dv || ''}` : '-'}
              </TableCell>
              <TableCell>{ba.titular || '-'}</TableCell>
              <TableCell>{ba.convenio || '-'}</TableCell>
              <TableCell>
                {ba.is_default ? (
                  <Chip label="Sim" color="success" size="small" />
                ) : (
                  <Chip label="Não" color="default" size="small" />
                )}
              </TableCell>
              <TableCell>
                <IconButton size="small" onClick={() => handleOpen(ba)} title="Editar">
                  <PencilIcon className="w-4 h-4" />
                </IconButton>
                <IconButton size="small" onClick={() => handleDelete(ba)} title="Excluir">
                  <TrashIcon className="w-4 h-4 text-red-500" />
                </IconButton>
                {(ba.sicoob_client_id || ba.sicoob_access_token) && (
                  <IconButton size="small" onClick={() => handleTestSicoob(ba)} title="Testar Sicoob" disabled={loading}>
                    <PlayIcon className="w-4 h-4 text-green-500" />
                  </IconButton>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  const renderBankAccountCards = () => (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {paginatedBankAccounts.map((ba) => (
        <Card key={ba.id}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Box>
                <Typography variant="h6" sx={{ mb: 1 }}>
                  {ba.titular || 'Conta sem titular'}
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
                  <Chip label={ba.bank} color="primary" size="small" />
                  {ba.is_default && <Chip label="Padrão" color="success" size="small" />}
                </Box>
              </Box>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <IconButton size="small" onClick={() => handleOpen(ba)}>
                  <PencilIcon className="w-4 h-4" />
                </IconButton>
                <IconButton size="small" onClick={() => handleDelete(ba)}>
                  <TrashIcon className="w-4 h-4 text-red-500" />
                </IconButton>
                {(ba.sicoob_client_id || ba.sicoob_access_token) && (
                  <IconButton size="small" onClick={() => handleTestSicoob(ba)} disabled={loading}>
                    <PlayIcon className="w-4 h-4 text-green-500" />
                  </IconButton>
                )}
              </Box>
            </Box>
            <Divider sx={{ mb: 2 }} />
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
              <Box>
                <Typography variant="body2" color="text.secondary">Agência</Typography>
                <Typography variant="body1">{ba.agencia || '-'}</Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">Conta</Typography>
                <Typography variant="body1">{ba.conta || '-'}</Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">Convênio</Typography>
                <Typography variant="body1">{ba.convenio || '-'}</Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">Carteira</Typography>
                <Typography variant="body1">{ba.carteira || '-'}</Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      ))}
    </Box>
  );

  const renderPagination = () => {
    if (isMobile) {
      return (
        <Box sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mt: 2,
          flexWrap: 'wrap',
          gap: 1,
          borderTop: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper',
          py: 2
        }}>
          <TextField
            select
            size="small"
            value={rowsPerPage}
            onChange={handleMobileRowsPerPageChange}
            sx={{ minWidth: 120 }}
          >
            <MenuItem value={5}>5</MenuItem>
            <MenuItem value={10}>10</MenuItem>
            <MenuItem value={25}>25</MenuItem>
          </TextField>
          <Pagination
            count={Math.max(1, Math.ceil(filteredBankAccounts.length / rowsPerPage))}
            page={page + 1}
            onChange={handleChangePage}
            size="small"
            color="primary"
          />
        </Box>
      );
    }

    return (
      <TablePagination
        rowsPerPageOptions={[5, 10, 25, 50, 100]}
        component="div"
        count={filteredBankAccounts.length}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={(_, newPage) => setPage(newPage)}
        onRowsPerPageChange={handleTableRowsPerPageChange}
        labelRowsPerPage="Itens por página:"
        sx={{
          flexShrink: 0,
          borderTop: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper'
        }}
      />
    );
  };

  if (!activeCompany) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6">Nenhuma empresa ativa</Typography>
        <Typography variant="body2" color="text.secondary">Selecione uma empresa para gerenciar as contas bancárias.</Typography>
      </Paper>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ flexShrink: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 'bold' }}>Contas Bancárias</Typography>
        <Button variant="contained" startIcon={<PlusIcon className="w-5 h-5" />} onClick={() => handleOpen()}>
          Nova Conta
        </Button>
      </Box>

      {/* Search Bar */}
      <Box sx={{ flexShrink: 0, mb: 2 }}>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Buscar por banco, agência, conta, titular ou convênio..."
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
        ) : filteredBankAccounts.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary">
              {searchTerm ? 'Nenhuma conta bancária encontrada' : 'Nenhuma conta bancária cadastrada'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {searchTerm ? 'Tente ajustar os termos da busca' : 'Clique em "Nova Conta" para adicionar a primeira conta bancária'}
            </Typography>
          </Paper>
        ) : isMobile ? (
          renderBankAccountCards()
        ) : (
          renderBankAccountTable()
        )}

        {/* Pagination inside scrollable area */}
        {!loading && filteredBankAccounts.length > 0 && renderPagination()}
      </Box>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={handleClose} />
          <div role="dialog" aria-modal="true" className="relative bg-white rounded-lg shadow-xl w-full max-w-2xl flex flex-col overflow-hidden mx-2 sm:mx-0" style={{ maxHeight: '90vh' }}>
            <div className="p-6 border-b flex-shrink-0">
              <Typography variant="h6">{editingBankAccount ? 'Editar Conta Bancária' : 'Nova Conta Bancária'}</Typography>
            </div>
            <Box sx={{ p: 3, overflowY: 'auto', maxHeight: 'calc(90vh - 140px)' }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <TextField
                  label="Banco"
                  value={formData.bank}
                  onChange={e => handleInputChange('bank', e.target.value)}
                  fullWidth
                  error={!!errors.bank}
                  helperText={errors.bank}
                />
                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
                  <TextField
                    label="Código do Banco"
                    value={formData.codigo_banco}
                    onChange={e => handleInputChange('codigo_banco', e.target.value)}
                    fullWidth
                  />
                  <TextField
                    label="Convênio"
                    value={formData.convenio}
                    onChange={e => handleInputChange('convenio', e.target.value)}
                    fullWidth
                  />
                </Box>
                <Box sx={{ display: 'grid', gridTemplateColumns: '2fr 1fr 2fr 1fr', gap: 2 }}>
                  <TextField
                    label="Agência"
                    value={formData.agencia}
                    onChange={e => handleInputChange('agencia', e.target.value)}
                    fullWidth
                    error={!!errors.agencia}
                    helperText={errors.agencia}
                  />
                  <TextField
                    label="DV"
                    value={formData.agencia_dv}
                    onChange={e => handleInputChange('agencia_dv', e.target.value)}
                    fullWidth
                  />
                  <TextField
                    label="Conta"
                    value={formData.conta}
                    onChange={e => handleInputChange('conta', e.target.value)}
                    fullWidth
                    error={!!errors.conta}
                    helperText={errors.conta}
                  />
                  <TextField
                    label="DV"
                    value={formData.conta_dv}
                    onChange={e => handleInputChange('conta_dv', e.target.value)}
                    fullWidth
                  />
                </Box>
                <TextField
                  label="Titular"
                  value={formData.titular}
                  onChange={e => handleInputChange('titular', e.target.value)}
                  fullWidth
                  error={!!errors.titular}
                  helperText={errors.titular}
                />
                <TextField
                  label="CPF/CNPJ do Titular"
                  value={formData.cpf_cnpj_titular}
                  onChange={e => handleInputChange('cpf_cnpj_titular', e.target.value)}
                  fullWidth
                />
                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
                  <TextField
                    label="Carteira"
                    value={formData.carteira}
                    onChange={e => handleInputChange('carteira', e.target.value)}
                    fullWidth
                  />
                  <TextField
                    label="Instruções"
                    value={formData.instructions}
                    onChange={e => handleInputChange('instructions', e.target.value)}
                    fullWidth
                  />
                </Box>
                <TextField
                  label="Configuração de Remessa"
                  value={formData.remittance_config}
                  onChange={e => handleInputChange('remittance_config', e.target.value)}
                  fullWidth
                  multiline
                  rows={2}
                />
                <TextField
                  label="Credenciais do Gateway (opcional)"
                  value={formData.gateway_credentials}
                  onChange={e => handleInputChange('gateway_credentials', e.target.value)}
                  fullWidth
                  type="password"
                  helperText="Credenciais para integração com gateway de pagamento"
                />
                
                {/* Campos específicos do Sicoob */}
                {formData.bank === 'SICOB' && (
                  <Box sx={{ mt: 2, p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 1, bgcolor: 'background.paper' }}>
                    <Typography variant="h6" sx={{ mb: 2, color: 'primary.main' }}>
                      🔐 Credenciais Sicoob
                    </Typography>
                    <TextField
                      label="Client ID do Sicoob"
                      value={formData.sicoob_client_id}
                      onChange={e => handleInputChange('sicoob_client_id', e.target.value)}
                      fullWidth
                      sx={{ mb: 2 }}
                      helperText="Client ID fornecido pelo Sicoob"
                    />
                    <TextField
                      label="Access Token do Sicoob"
                      value={formData.sicoob_access_token}
                      onChange={e => handleInputChange('sicoob_access_token', e.target.value)}
                      fullWidth
                      type="password"
                      helperText="Access Token fornecido pelo Sicoob"
                    />
                  </Box>
                )}
              </Box>
            </Box>
            <div className="p-6 border-t flex justify-end gap-4 flex-shrink-0">
              <Button onClick={handleClose}>Cancelar</Button>
              {/* Testar Sicoob a partir do formulário (não salva) */}
              {formData.bank === 'SICOB' && (
                <Button onClick={() => handleTestSicoobFromForm()} color="info" variant="outlined" startIcon={<PlayIcon className="w-4 h-4" />}>
                  Testar Sicoob
                </Button>
              )}
              <Button onClick={handleSubmit} variant="contained">Salvar</Button>
            </div>
          </div>
        </div>
      )}

      <Snackbar open={snackbar.open} autoHideDuration={6000} onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}>
        <Alert onClose={() => setSnackbar(prev => ({ ...prev, open: false }))} severity={snackbar.severity} sx={{ width: '100%' }}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default BankAccounts;
