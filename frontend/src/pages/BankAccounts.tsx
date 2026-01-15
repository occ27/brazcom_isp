import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { Box, Paper, Typography, Button, IconButton, TextField, CircularProgress, Chip, Snackbar, Alert, useMediaQuery, useTheme, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TablePagination, Card, CardContent, Divider, Pagination, InputAdornment, MenuItem, Tooltip } from '@mui/material';
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
  sicredi_codigo_beneficiario?: string;
  sicredi_posto?: string;
  sicredi_byte_id?: string;
  multa_atraso_percentual?: number;
  juros_atraso_percentual?: number;
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
  sicredi_codigo_beneficiario?: string;
  sicredi_posto?: string;
  sicredi_byte_id?: string;
  multa_atraso_percentual?: number;
  juros_atraso_percentual?: number;
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
    codigo_banco: '756',
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
    sicoob_access_token: '',
    sicredi_codigo_beneficiario: '',
    sicredi_posto: '',
    sicredi_byte_id: '',
    multa_atraso_percentual: 2.0,
    juros_atraso_percentual: 1.0
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
    setFormData(prev => {
      const newData = { ...prev, [field]: value };
      // Auto-fill codigo_banco based on bank selection
      if (field === 'bank') {
        if (value === 'SICOB') {
          newData.codigo_banco = '756';
        } else if (value === 'SICREDI') {
          newData.codigo_banco = '748';
        } else {
          newData.codigo_banco = '';
        }
      }
      return newData;
    });
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

    // Validações específicas por banco
    if (formData.bank === 'SICREDI') {
      if (!formData.carteira?.trim()) newErrors.carteira = 'Carteira é obrigatória para SICREDI';
      if (!formData.convenio?.trim()) newErrors.convenio = 'Convênio é obrigatório para SICREDI';
      if (!formData.sicredi_codigo_beneficiario?.trim()) newErrors.sicredi_codigo_beneficiario = 'Código do beneficiário é obrigatório para SICREDI';
      if (!formData.sicredi_posto?.trim()) newErrors.sicredi_posto = 'Posto é obrigatório para SICREDI';
      if (!formData.sicredi_byte_id?.trim()) newErrors.sicredi_byte_id = 'Byte ID é obrigatório para SICREDI';
    } else if (formData.bank === 'SICOB') {
      if (!formData.sicoob_client_id?.trim()) newErrors.sicoob_client_id = 'Client ID é obrigatório para SICOOB';
      if (!formData.sicoob_access_token?.trim()) newErrors.sicoob_access_token = 'Access Token é obrigatório para SICOOB';
    }

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
      const bank = bankAccount.bank || 'SICOB';
      let codigo_banco = bankAccount.codigo_banco || '';
      if (!codigo_banco) {
        if (bank === 'SICOB') {
          codigo_banco = '756';
        } else if (bank === 'SICREDI') {
          codigo_banco = '748';
        }
      }
      setFormData({
        bank: bank,
        codigo_banco: codigo_banco,
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
        sicoob_access_token: bankAccount.sicoob_access_token || '',
        sicredi_codigo_beneficiario: bankAccount.sicredi_codigo_beneficiario || '',
        sicredi_posto: bankAccount.sicredi_posto || '',
        sicredi_byte_id: bankAccount.sicredi_byte_id || '',
        multa_atraso_percentual: bankAccount.multa_atraso_percentual || 2.0,
        juros_atraso_percentual: bankAccount.juros_atraso_percentual || 1.0
      });
    } else {
      setEditingBankAccount(null);
      setFormData({
        bank: 'SICOB',
        codigo_banco: '756',
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
      codigo_banco: '756',
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
      sicoob_access_token: '',
      sicredi_codigo_beneficiario: '',
      sicredi_posto: '',
      sicredi_byte_id: '',
      multa_atraso_percentual: 2.0,
      juros_atraso_percentual: 1.0
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
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell sx={{ fontWeight: 'bold', fontSize: '0.875rem' }}>Banco</TableCell>
            <TableCell sx={{ fontWeight: 'bold', fontSize: '0.875rem' }}>Agência/Conta</TableCell>
            <TableCell sx={{ fontWeight: 'bold', fontSize: '0.875rem' }}>Titular</TableCell>
            <TableCell sx={{ fontWeight: 'bold', fontSize: '0.875rem' }}>Convênio</TableCell>
            <TableCell sx={{ fontWeight: 'bold', fontSize: '0.875rem' }}>Status</TableCell>
            <TableCell sx={{ fontWeight: 'bold', fontSize: '0.875rem' }}>Ações</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {paginatedBankAccounts.map((ba) => (
            <TableRow key={ba.id} hover>
              <TableCell>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Chip label={ba.bank} color="primary" size="small" />
                  {ba.bank === 'SICREDI' && (ba.sicredi_codigo_beneficiario || ba.sicredi_posto) && (
                    <Chip label="CNAB" color="info" size="small" variant="outlined" sx={{ fontSize: '0.7rem', height: 20 }} />
                  )}
                  {ba.bank === 'SICOB' && (ba.sicoob_client_id) && (
                    <Chip label="API" color="secondary" size="small" variant="outlined" sx={{ fontSize: '0.7rem', height: 20 }} />
                  )}
                </Box>
              </TableCell>
              <TableCell sx={{ fontSize: '0.875rem' }}>
                {ba.agencia && ba.conta ? `${ba.agencia}${ba.agencia_dv || ''} / ${ba.conta}${ba.conta_dv || ''}` : '-'}
              </TableCell>
              <TableCell sx={{ fontSize: '0.875rem', maxWidth: 200 }}>
                <Typography sx={{ fontSize: '0.875rem' }} noWrap>
                  {ba.titular || '-'}
                </Typography>
              </TableCell>
              <TableCell sx={{ fontSize: '0.875rem' }}>{ba.convenio || '-'}</TableCell>
              <TableCell>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  {ba.is_default ? (
                    <Chip label="Padrão" color="success" size="small" sx={{ fontSize: '0.7rem', height: 20 }} />
                  ) : (
                    <Chip label="Normal" color="default" size="small" variant="outlined" sx={{ fontSize: '0.7rem', height: 20 }} />
                  )}
                </Box>
              </TableCell>
              <TableCell>
                <Box sx={{ display: 'flex', gap: 0.5 }}>
                  <IconButton size="small" onClick={() => handleOpen(ba)} title="Editar" sx={{ p: 0.5 }}>
                    <PencilIcon className="w-4 h-4" />
                  </IconButton>
                  <IconButton size="small" onClick={() => handleDelete(ba)} title="Excluir" sx={{ p: 0.5 }}>
                    <TrashIcon className="w-4 h-4 text-red-500" />
                  </IconButton>
                  {(ba.sicoob_client_id || ba.sicoob_access_token) && (
                    <IconButton size="small" onClick={() => handleTestSicoob(ba)} title="Testar Sicoob" disabled={loading} sx={{ p: 0.5 }}>
                      <PlayIcon className="w-4 h-4 text-green-500" />
                    </IconButton>
                  )}
                </Box>
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
        <Card key={ba.id} sx={{ borderRadius: 2 }}>
          <CardContent sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="h6" sx={{ mb: 1, fontSize: '1rem', wordBreak: 'break-word' }}>
                  {ba.titular || 'Conta sem titular'}
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, mb: 1, flexWrap: 'wrap' }}>
                  <Chip label={ba.bank} color="primary" size="small" />
                  {ba.is_default && <Chip label="Padrão" color="success" size="small" />}
                  {ba.bank === 'SICREDI' && (ba.sicredi_codigo_beneficiario || ba.sicredi_posto) && (
                    <Chip label="CNAB 240" color="info" size="small" variant="outlined" />
                  )}
                  {ba.bank === 'SICOB' && (ba.sicoob_client_id) && (
                    <Chip label="API" color="secondary" size="small" variant="outlined" />
                  )}
                </Box>
              </Box>
              <Box sx={{ display: 'flex', gap: 0.5, ml: 1 }}>
                <IconButton size="small" onClick={() => handleOpen(ba)} sx={{ p: 1 }}>
                  <PencilIcon className="w-4 h-4" />
                </IconButton>
                <IconButton size="small" onClick={() => handleDelete(ba)} sx={{ p: 1 }}>
                  <TrashIcon className="w-4 h-4 text-red-500" />
                </IconButton>
                {(ba.sicoob_client_id || ba.sicoob_access_token) && (
                  <IconButton size="small" onClick={() => handleTestSicoob(ba)} disabled={loading} sx={{ p: 1 }}>
                    <PlayIcon className="w-4 h-4 text-green-500" />
                  </IconButton>
                )}
              </Box>
            </Box>
            <Divider sx={{ mb: 2 }} />
            <Box sx={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 1 }}>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.75rem' }}>Agência</Typography>
                  <Typography variant="body1" sx={{ fontSize: '0.875rem', fontWeight: 500 }}>
                    {ba.agencia ? `${ba.agencia}${ba.agencia_dv || ''}` : '-'}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.75rem' }}>Conta</Typography>
                  <Typography variant="body1" sx={{ fontSize: '0.875rem', fontWeight: 500 }}>
                    {ba.conta ? `${ba.conta}${ba.conta_dv || ''}` : '-'}
                  </Typography>
                </Box>
              </Box>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.75rem' }}>Convênio</Typography>
                  <Typography variant="body1" sx={{ fontSize: '0.875rem' }}>{ba.convenio || '-'}</Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.75rem' }}>Carteira</Typography>
                  <Typography variant="body1" sx={{ fontSize: '0.875rem' }}>{ba.carteira || '-'}</Typography>
                </Box>
              </Box>
            </Box>
            {/* Mostrar informações específicas do banco em mobile */}
            {isMobile && (
              <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                {ba.bank === 'SICREDI' && (ba.sicredi_codigo_beneficiario || ba.sicredi_posto || ba.sicredi_byte_id) && (
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                      Beneficiário: {ba.sicredi_codigo_beneficiario || '-'} | Posto: {ba.sicredi_posto || '-'} | Byte: {ba.sicredi_byte_id || '-'}
                    </Typography>
                  </Box>
                )}
                {ba.bank === 'SICOB' && ba.sicoob_client_id && (
                  <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                    API Sicoob configurada
                  </Typography>
                )}
              </Box>
            )}
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
      <Paper sx={{ p: isMobile ? 3 : 4, textAlign: 'center', m: isMobile ? 1 : 0 }}>
        <Typography variant="h6">Nenhuma empresa ativa</Typography>
        <Typography variant="body2" color="text.secondary">Selecione uma empresa para gerenciar as contas bancárias.</Typography>
      </Paper>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ flexShrink: 0, display: 'flex', flexDirection: isMobile ? 'column' : 'row', justifyContent: 'space-between', alignItems: isMobile ? 'stretch' : 'center', gap: isMobile ? 2 : 0, mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 'bold', fontSize: isMobile ? '1.25rem' : '1.5rem' }}>Contas Bancárias</Typography>
        <Button variant="contained" startIcon={<PlusIcon className="w-5 h-5" />} onClick={() => handleOpen()} fullWidth={isMobile}>
          Nova Conta
        </Button>
      </Box>

      {/* Search Bar */}
      <Box sx={{ flexShrink: 0, mb: 2 }}>
        <TextField
          fullWidth
          size={isMobile ? "small" : "medium"}
          variant="outlined"
          placeholder={isMobile ? "Buscar contas..." : "Buscar por banco, agência, conta, titular ou convênio..."}
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

      <Box sx={{ flexGrow: 1, overflow: 'auto', p: isMobile ? 0.5 : 0 }}>
        {loading && !open ? (
          <Box sx={{ display: 'flex', flexGrow: 1, justifyContent: 'center', alignItems: 'center', p: isMobile ? 2 : 0 }}>
            <CircularProgress />
          </Box>
        ) : filteredBankAccounts.length === 0 ? (
          <Paper sx={{ p: isMobile ? 3 : 4, textAlign: 'center', m: isMobile ? 1 : 0 }}>
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={handleClose} />
          <div role="dialog" aria-modal="true" className="relative bg-white rounded-lg shadow-xl w-full max-w-2xl flex flex-col overflow-hidden mx-1 sm:mx-2" style={{ maxHeight: isMobile ? '95vh' : '90vh' }}>
            <div className="p-4 sm:p-6 border-b flex-shrink-0">
              <Typography variant="h6" className="text-sm sm:text-base">{editingBankAccount ? 'Editar Conta Bancária' : 'Nova Conta Bancária'}</Typography>
            </div>
            <Box sx={{ p: isMobile ? 2 : 3, overflowY: 'auto', maxHeight: isMobile ? 'calc(95vh - 120px)' : 'calc(90vh - 140px)' }}>
              <Alert severity="info" sx={{ mb: 2, fontSize: isMobile ? '0.875rem' : '1rem' }}>
                <Typography variant="body2" sx={{ fontSize: isMobile ? '0.75rem' : '0.875rem' }}>
                  <strong>Campos obrigatórios:</strong> Agência, Conta e Titular são sempre obrigatórios. 
                  {formData.bank === 'SICREDI' && ' Para SICREDI: Carteira, Convênio e configurações específicas são obrigatórios.'}
                  {formData.bank === 'SICOB' && ' Para SICOOB: Client ID e Access Token são obrigatórios.'}
                </Typography>
              </Alert>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <TextField
                  select
                  label="Banco"
                  value={formData.bank}
                  onChange={e => handleInputChange('bank', e.target.value)}
                  fullWidth
                  error={!!errors.bank}
                  helperText={errors.bank}
                >
                  <MenuItem value="SICOB">SICOOB</MenuItem>
                  <MenuItem value="SICREDI">SICREDI</MenuItem>
                </TextField>
                <Box sx={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 2 }}>
                  <TextField
                    label="Código do Banco"
                    value={formData.codigo_banco}
                    onChange={e => handleInputChange('codigo_banco', e.target.value)}
                    fullWidth
                    InputProps={{
                      readOnly: true,
                    }}
                    helperText="Preenchido automaticamente com base no banco selecionado"
                  />
                </Box>
                <Box sx={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '2fr 1fr 2fr 1fr', gap: 2 }}>
                  <TextField
                    label="Agência *"
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
                    label="Conta *"
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
                  label="Titular *"
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
                <Box sx={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 2 }}>
                  <TextField
                    label={formData.bank === 'SICREDI' ? "Carteira *" : "Carteira"}
                    value={formData.carteira}
                    onChange={e => handleInputChange('carteira', e.target.value)}
                    fullWidth
                    error={!!errors.carteira}
                    helperText={errors.carteira}
                  />
                  <TextField
                    label={formData.bank === 'SICREDI' ? "Convênio *" : "Convênio"}
                    value={formData.convenio}
                    onChange={e => handleInputChange('convenio', e.target.value)}
                    fullWidth
                    error={!!errors.convenio}
                    helperText={errors.convenio}
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
                
                {/* Configurações de cobrança comuns */}
                <Box sx={{ mt: 2, p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 1, bgcolor: 'background.paper' }}>
                  <Typography variant="h6" sx={{ mb: 2, color: 'primary.main' }}>
                    ⚙️ Configurações de Cobrança
                  </Typography>
                  <Box sx={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 2 }}>
                    <TextField
                      label="Multa por Atraso (%)"
                      type="number"
                      value={formData.multa_atraso_percentual}
                      onChange={e => handleInputChange('multa_atraso_percentual', parseFloat(e.target.value) || 0)}
                      fullWidth
                      inputProps={{ min: 0, max: 100, step: 0.1 }}
                      helperText="Percentual de multa por atraso"
                    />
                    <TextField
                      label="Juros por Dia (%)"
                      type="number"
                      value={formData.juros_atraso_percentual}
                      onChange={e => handleInputChange('juros_atraso_percentual', parseFloat(e.target.value) || 0)}
                      fullWidth
                      inputProps={{ min: 0, max: 100, step: 0.01 }}
                      helperText="Percentual de juros por dia de atraso"
                    />
                  </Box>
                </Box>
                
                {/* Campos específicos do Sicoob */}
                {formData.bank === 'SICOB' && (
                  <Box sx={{ mt: 2, p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 1, bgcolor: 'background.paper' }}>
                    <Typography variant="h6" sx={{ mb: 2, color: 'primary.main' }}>
                      🔐 Credenciais Sicoob
                    </Typography>
                    <TextField
                      label="Client ID do Sicoob *"
                      value={formData.sicoob_client_id}
                      onChange={e => handleInputChange('sicoob_client_id', e.target.value)}
                      fullWidth
                      sx={{ mb: 2 }}
                      error={!!errors.sicoob_client_id}
                      helperText={errors.sicoob_client_id || "Client ID fornecido pelo Sicoob"}
                    />
                    <TextField
                      label="Access Token do Sicoob *"
                      value={formData.sicoob_access_token}
                      onChange={e => handleInputChange('sicoob_access_token', e.target.value)}
                      fullWidth
                      type="password"
                      error={!!errors.sicoob_access_token}
                      helperText={errors.sicoob_access_token || "Access Token fornecido pelo Sicoob"}
                    />
                  </Box>
                )}

                {/* Campos específicos do Sicredi */}
                {formData.bank === 'SICREDI' && (
                  <Box sx={{ mt: 2, p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 1, bgcolor: 'background.paper' }}>
                    <Typography variant="h6" sx={{ mb: 2, color: 'primary.main' }}>
                      🔐 Configurações Sicredi
                    </Typography>
                    <TextField
                      label="Código do Beneficiário *"
                      value={formData.sicredi_codigo_beneficiario}
                      onChange={e => handleInputChange('sicredi_codigo_beneficiario', e.target.value)}
                      fullWidth
                      sx={{ mb: 2 }}
                      error={!!errors.sicredi_codigo_beneficiario}
                      helperText={errors.sicredi_codigo_beneficiario || "Código do beneficiário fornecido pelo Sicredi"}
                    />
                    <Box sx={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 2 }}>
                      <TextField
                        label="Posto de Atendimento *"
                        value={formData.sicredi_posto}
                        onChange={e => handleInputChange('sicredi_posto', e.target.value)}
                        fullWidth
                        error={!!errors.sicredi_posto}
                        helperText={errors.sicredi_posto || "Posto de atendimento (AA)"}
                      />
                      <TextField
                        label="Byte de Identificação *"
                        value={formData.sicredi_byte_id}
                        onChange={e => handleInputChange('sicredi_byte_id', e.target.value)}
                        fullWidth
                        error={!!errors.sicredi_byte_id}
                        helperText={errors.sicredi_byte_id || "Byte de identificação"}
                      />
                    </Box>
                  </Box>
                )}
              </Box>
            </Box>
            <div className={`p-4 sm:p-6 border-t flex ${isMobile ? 'justify-center' : 'justify-end'} flex-shrink-0`}>
              <div className={`flex ${isMobile ? 'gap-2' : 'gap-2'}`}>
                <Tooltip title="Cancelar">
                  <IconButton onClick={handleClose} color="default" size="large">
                    <XMarkIcon className="w-5 h-5" />
                  </IconButton>
                </Tooltip>
                {/* Testar Sicoob a partir do formulário (não salva) */}
                {formData.bank === 'SICOB' && (
                  <Tooltip title="Testar Sicoob">
                    <IconButton onClick={() => handleTestSicoobFromForm()} color="info" size="large" disabled={loading}>
                      <PlayIcon className="w-5 h-5" />
                    </IconButton>
                  </Tooltip>
                )}
                <Tooltip title="Salvar">
                  <IconButton onClick={handleSubmit} color="primary" size="large" sx={{ bgcolor: 'primary.main', color: 'white', '&:hover': { bgcolor: 'primary.dark' } }}>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </IconButton>
                </Tooltip>
              </div>
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
