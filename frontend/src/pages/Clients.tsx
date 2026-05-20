import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Paper, Typography, Button, IconButton, TextField, CircularProgress, Chip, Snackbar, Alert, useMediaQuery, useTheme, MenuItem, FormControl, InputLabel, Select, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TablePagination, Card, CardContent, Divider, Pagination, SelectChangeEvent, InputAdornment, Dialog, DialogTitle, DialogContent, DialogActions, Menu, ListItemIcon, ListItemText } from '@mui/material';
import { PlusIcon, PencilIcon, TrashIcon, MagnifyingGlassIcon, XMarkIcon, DocumentTextIcon, EllipsisVerticalIcon } from '@heroicons/react/24/outline';
import api from '../services/authService';
import { formatCurrency } from '../utils/currencyUtils';
import { useAuth } from '../contexts/AuthContext';
import { useCompany } from '../contexts/CompanyContext';
import clientService, { ClientCreate } from '../services/clientService';
import { companyService } from '../services/companyService';
import { stringifyError } from '../utils/error';
import { DocumentArrowDownIcon } from '@heroicons/react/24/outline';
import reportService from '../services/reportService';

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
    try {
      // Load Receivables
      const recRes = await api.get(`/receivables/cliente/${client.id}?empresa_id=${activeCompany.id}`);
      setClientReceivables(recRes.data || []);
      
      // Load Contracts
      const conRes = await api.get(`/servicos-contratados/cliente/${client.id}?empresa_id=${activeCompany.id}`);
      setClientContracts(conRes.data || []);
    } catch (e) {
      console.error('Erro ao carregar dados do extrato', e);
      setSnackbar({ open: true, message: 'Erro ao carregar extrato financeiro', severity: 'error' });
    } finally {
      setStatementLoading(false);
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
          <ListItemIcon><DocumentTextIcon className="w-4 h-4 text-indigo-500" /></ListItemIcon>
          <ListItemText primary="Extrato Financeiro" />
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

      {/* Modal Extrato Financeiro */}
      <Dialog open={statementOpen} onClose={() => setStatementOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontWeight: 'bold' }}>
          Extrato Financeiro: {selectedClientForStatement?.nome_razao_social}
          <IconButton onClick={() => setStatementOpen(false)}><XMarkIcon className="w-6 h-6" /></IconButton>
        </DialogTitle>
        <DialogContent dividers>
          <Box sx={{ mb: 3, display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
            <FormControl size="small" sx={{ minWidth: 250 }}>
              <InputLabel>Filtrar por Contrato</InputLabel>
              <Select
                value={statementFilterContract}
                label="Filtrar por Contrato"
                onChange={(e) => setStatementFilterContract(e.target.value)}
              >
                <MenuItem value="all">Todos os Contratos / Lançamentos</MenuItem>
                {clientContracts.map(c => (
                  <MenuItem key={c.id} value={c.id.toString()}>
                    Contrato #{c.id} - {c.servico_descricao || 'Serviço'}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl size="small" sx={{ minWidth: 150 }}>
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
            
            <Paper variant="outlined" sx={{ p: 1, px: 2, display: 'flex', gap: 3, bgcolor: 'grey.50' }}>
              <Box>
                <Typography variant="caption" color="text.secondary" display="block">Total Recebido</Typography>
                <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'success.main' }}>{formatCurrency(statementTotals.paid)}</Typography>
              </Box>
              <Divider orientation="vertical" flexItem />
              <Box>
                <Typography variant="caption" color="text.secondary" display="block">Total Pendente</Typography>
                <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'warning.main' }}>{formatCurrency(statementTotals.pending)}</Typography>
              </Box>
            </Paper>
          </Box>

          {statementLoading ? (
            <Box sx={{ py: 10, textAlign: 'center' }}><CircularProgress /></Box>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Vencimento</TableCell>
                    <TableCell>Contrato</TableCell>
                    <TableCell>Método</TableCell>
                    <TableCell align="right">Valor</TableCell>
                    <TableCell align="right">Vlr Pago</TableCell>
                    <TableCell>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredReceivables.length === 0 ? (
                    <TableRow><TableCell colSpan={5} align="center" sx={{ py: 3 }}>Nenhuma cobrança encontrada.</TableCell></TableRow>
                  ) : filteredReceivables.map(r => (
                    <TableRow key={r.id} hover>
                      <TableCell>{new Date(r.due_date).toLocaleDateString('pt-BR')}</TableCell>
                      <TableCell>{r.servico_contratado_id ? `#${r.servico_contratado_id}` : 'Avulso'}</TableCell>
                      <TableCell>{r.tipo === 'MERCADO_PAGO' ? 'Mercado Pago' : r.bank}</TableCell>
                      <TableCell align="right">{formatCurrency(r.amount)}</TableCell>
                      <TableCell align="right">
                        {r.paid_amount !== null && r.paid_amount !== undefined ? formatCurrency(r.paid_amount) : '-'}
                      </TableCell>
                      <TableCell>
                        <Chip 
                          label={r.status} 
                          size="small" 
                          color={r.status === 'PAID' ? 'success' : r.status === 'CANCELLED' ? 'default' : 'warning'} 
                          variant="outlined"
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                  {filteredReceivables.length > 0 && (
                    <TableRow sx={{ bgcolor: 'grey.100', '& td': { fontWeight: 'bold' } }}>
                      <TableCell colSpan={3} align="right">TOTAIS:</TableCell>
                      <TableCell align="right">
                        {formatCurrency(filteredReceivables.reduce((acc, r) => acc + r.amount, 0))}
                      </TableCell>
                      <TableCell align="right">
                        {formatCurrency(filteredReceivables.reduce((acc, r) => acc + (r.paid_amount || 0), 0))}
                      </TableCell>
                      <TableCell />
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          {!statementLoading && filteredReceivables.length > 0 && (
            <Box sx={{ mt: 3, p: 2, bgcolor: 'primary.50', borderRadius: 2, border: '1px solid', borderColor: 'primary.100' }}>
              <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold', color: 'primary.700' }}>
                Resumo do Filtro Atual
              </Typography>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">Quantidade</Typography>
                  <Typography variant="body1" sx={{ fontWeight: 'bold' }}>{filteredReceivables.length} registro(s)</Typography>
                </Box>
                <Box alignSelf="flex-end" sx={{ textAlign: 'right' }}>
                  <Typography variant="caption" color="text.secondary">Soma dos Valores</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 'bold', color: 'primary.800' }}>
                    {formatCurrency(filteredReceivables.reduce((acc, r) => acc + r.amount, 0))}
                  </Typography>
                </Box>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setStatementOpen(false)}>Fechar</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={5000} onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}>
        <Alert severity={snackbar.severity} onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default Clients;