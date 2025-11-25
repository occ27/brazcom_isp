import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { Box, Paper, Typography, Button, IconButton, TextField, CircularProgress, Chip, Snackbar, Alert, useMediaQuery, useTheme, MenuItem, FormControl, InputLabel, Select, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TablePagination, Card, CardContent, Divider, Pagination, SelectChangeEvent, InputAdornment, Autocomplete, Tabs, Tab, FormControlLabel, Checkbox } from '@mui/material';
import { PlusIcon, PencilIcon, TrashIcon, MagnifyingGlassIcon, XMarkIcon } from '@heroicons/react/24/outline';
import cclassList from '../data/cclass.json';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import cfopList from '../data/cfop.json';
import { useCompany } from '../contexts/CompanyContext';
import servicoService, { Servico, ServicoListResponse } from '../services/servicoService';
import { stringifyError } from '../utils/error';

interface ServicoCreate {
  tipo: string;
  codigo: string;
  descricao: string;
  cClass?: string;
  unidade_medida: string;
  valor_unitario: number;
  cfop?: string;
  ncm?: string;
  base_calculo_icms_default?: number;
  aliquota_icms_default?: number;
  valor_desconto_default?: number;
  valor_outros_default?: number;
  upload_speed?: number;
  download_speed?: number;
  max_limit?: string;
  fidelity_months?: number;
  billing_cycle?: string;
  notes?: string;
  promotional_price?: number;
  promotional_months?: number;
  promotional_active?: boolean;
}

const Servicos: React.FC = () => {
  const { activeCompany } = useCompany();
  const [servicos, setServicos] = useState<Servico[]>([]);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editingServico, setEditingServico] = useState<Servico | null>(null);

  // Pagination state
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [totalRows, setTotalRows] = useState(0);

  // Search state
  const [searchTerm, setSearchTerm] = useState('');

  const [formData, setFormData] = useState<ServicoCreate>({ tipo: 'SERVICO', codigo: '', descricao: '', cClass: '', unidade_medida: 'UN', valor_unitario: 0, cfop: '', ncm: '', base_calculo_icms_default: 0, aliquota_icms_default: 0, valor_desconto_default: 0, valor_outros_default: 0, upload_speed: 0, download_speed: 0, max_limit: '', fidelity_months: 0, billing_cycle: 'MENSAL', notes: '', promotional_price: 0, promotional_months: 0, promotional_active: false });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' | 'warning' });
  const [tabValue, setTabValue] = useState(0);

  const loadServicos = useCallback(async () => {
    if (!activeCompany) return;
    setLoading(true);
    try {
      const data: ServicoListResponse = await servicoService.getServicosByEmpresaPaginated(
        activeCompany.id,
        page + 1,
        rowsPerPage,
        searchTerm || undefined
      );
      setServicos(data.servicos);
      setTotalRows(data.total);
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao carregar serviços', severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [activeCompany, page, rowsPerPage, searchTerm]);

  useEffect(() => {
    if (activeCompany) {
      loadServicos();
    }
  }, [activeCompany, loadServicos]);
  // Keep a ref to the latest `loadServicos` so the debounce effect can call it without
  // having `loadServicos` as a dependency (which would change when `page` changes and
  // cause the debounce effect to re-run and reset the page to 0).
  const loadServicosRef = useRef(loadServicos);
  useEffect(() => { loadServicosRef.current = loadServicos; }, [loadServicos]);

  // Debounce search (only depends on the search term and activeCompany)
  useEffect(() => {
    if (activeCompany) {
      const timeoutId = setTimeout(() => {
        setPage(0);
        loadServicosRef.current();
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

  // Filter services based on search term
  const filteredServicos = useMemo(() => {
    return servicos;
  }, [servicos]);

  // Paginate filtered services
  const paginatedServicos = useMemo(() => {
    return filteredServicos;
  }, [filteredServicos]);

  const renderServiceCards = () => (
    <Box sx={{ display: 'grid', gap: 2 }}>
      {paginatedServicos.map((s) => (
        <Card key={s.id} variant="outlined">
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="h6" sx={{ fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {s.descricao}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  Código: {s.codigo || '-'}
                </Typography>
              </Box>
              <Chip label={s.ativo !== false ? 'Ativo' : 'Inativo'} color={s.ativo !== false ? 'success' : 'default'} size="small" />
            </Box>
            <Divider sx={{ my: 1.5 }} />
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="body2">
                {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(s.valor_unitario ?? 0)}
              </Typography>
              <Box>
                <IconButton size="small" onClick={() => handleOpen(s)} title="Editar">
                  <PencilIcon className="w-5 h-5" />
                </IconButton>
                <IconButton size="small" onClick={() => handleDelete(s)} title="Excluir">
                  <TrashIcon className="w-5 h-5 text-red-500" />
                </IconButton>
              </Box>
            </Box>
          </CardContent>
        </Card>
      ))}
    </Box>
  );

  const renderServiceTable = () => (
    <TableContainer component={Paper} sx={{ maxHeight: '70vh', overflow: 'auto' }}>
      <Table stickyHeader>
        <TableHead>
          <TableRow>
            <TableCell sx={{ fontWeight: 600 }}>Tipo</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Código</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Descrição</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Valor Unitário</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Unidade</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>CFOP</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>NCM</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
            <TableCell sx={{ fontWeight: 600, width: 120 }}>Ações</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {paginatedServicos.map((s) => (
            <TableRow key={s.id} hover>
              <TableCell>{s.tipo === 'PLANO_INTERNET' ? 'Plano Internet' : 'Serviço'}</TableCell>
              <TableCell>{s.codigo || '-'}</TableCell>
              <TableCell sx={{ maxWidth: 300 }}>
                <Typography sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {s.descricao}
                </Typography>
              </TableCell>
              <TableCell>
                {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(s.valor_unitario ?? 0)}
              </TableCell>
              <TableCell>{s.unidade_medida || '-'}</TableCell>
              <TableCell>{s.cfop || '-'}</TableCell>
              <TableCell>{s.ncm || '-'}</TableCell>
              <TableCell>
                <Chip label={s.ativo !== false ? 'Ativo' : 'Inativo'} color={s.ativo !== false ? 'success' : 'default'} size="small" />
              </TableCell>
              <TableCell>
                <IconButton size="small" onClick={() => handleOpen(s)} title="Editar">
                  <PencilIcon className="w-4 h-4" />
                </IconButton>
                <IconButton size="small" onClick={() => handleDelete(s)} title="Excluir">
                  <TrashIcon className="w-4 h-4 text-red-500" />
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
            count={Math.max(1, Math.ceil((totalRows || 0) / rowsPerPage))}
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
        count={totalRows}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={handleChangePage}
        onRowsPerPageChange={handleTableRowsPerPageChange}
        labelRowsPerPage="Itens por página:"
        sx={{ flexShrink: 0, borderTop: '1px solid', borderColor: 'divider' }}
      />
    );
  };

  const handleOpen = (servico?: Servico) => {
    if (servico) {
      setEditingServico(servico);
      setFormData({
        tipo: servico.tipo || 'SERVICO',
        codigo: servico.codigo || '',
        descricao: servico.descricao || '',
        cClass: (servico as any).cClass || '',
        unidade_medida: servico.unidade_medida || 'UN',
        valor_unitario: servico.valor_unitario ?? 0,
        cfop: servico.cfop || '',
        ncm: servico.ncm || '',
        base_calculo_icms_default: servico.base_calculo_icms_default ?? 0,
        aliquota_icms_default: servico.aliquota_icms_default ?? 0,
        valor_desconto_default: (servico as any).valor_desconto_default ?? 0,
        valor_outros_default: (servico as any).valor_outros_default ?? 0,
        upload_speed: (servico as any).upload_speed ?? 0,
        download_speed: (servico as any).download_speed ?? 0,
        max_limit: (servico as any).max_limit || '',
        fidelity_months: (servico as any).fidelity_months ?? 0,
        billing_cycle: (servico as any).billing_cycle || 'MENSAL',
        notes: (servico as any).notes || '',
        promotional_price: (servico as any).promotional_price ?? 0,
        promotional_months: (servico as any).promotional_months ?? 0,
        promotional_active: (servico as any).promotional_active ?? false,
      });
    } else {
      setEditingServico(null);
      setFormData({ tipo: 'SERVICO', codigo: '', descricao: '', cClass: '', unidade_medida: 'UN', valor_unitario: 0, cfop: '', ncm: '', base_calculo_icms_default: 0, aliquota_icms_default: 0, valor_desconto_default: 0, valor_outros_default: 0, upload_speed: 0, download_speed: 0, max_limit: '', fidelity_months: 0, billing_cycle: 'MENSAL', notes: '', promotional_price: 0, promotional_months: 0, promotional_active: false });
    }
    setErrors({});
    setOpen(true);
    setTabValue(0);
  };

  const handleClose = () => setOpen(false);

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: '' }));
  };

  const handleSubmit = async () => {
    if (!activeCompany) return;
    // Validation logic here...
    const newErrors: Record<string, string> = {};
    
    // Campos obrigatórios
    if (!formData.codigo.trim()) {
      newErrors.codigo = 'Código é obrigatório.';
    }
    if (!formData.descricao.trim()) {
      newErrors.descricao = 'Descrição é obrigatória.';
    }
    if (!formData.unidade_medida.trim()) {
      newErrors.unidade_medida = 'Unidade de medida é obrigatória.';
    }
    if (!formData.cClass) {
      newErrors.cClass = 'Código de classificação é obrigatório.';
    }
    if (!formData.cfop) {
      newErrors.cfop = 'CFOP é obrigatório.';
    }
    
    // Validação de promoção
    if (formData.promotional_active) {
      if (!formData.promotional_price || formData.promotional_price <= 0) {
        newErrors.promotional_price = 'Preço promocional deve ser maior que zero.';
      }
      if (!formData.promotional_months || formData.promotional_months <= 0) {
        newErrors.promotional_months = 'Meses promocionais deve ser maior que zero.';
      }
    }
    
    // NCM: if provided, must be 8 numeric digits (standard NCM format)
    if (formData.ncm && !/^\d{8}$/.test(formData.ncm)) {
      newErrors.ncm = 'NCM inválido. Deve conter 8 dígitos numéricos.';
    }
    // CFOP: if provided, should be 4 numeric digits (basic check). The full allowed list is defined in the MOC (item 7.7) —
    // if needed we can enforce a whitelist once the table is available.
    if (formData.cfop && !/^\d{4}$/.test(formData.cfop)) {
      newErrors.cfop = 'CFOP inválido. Deve conter 4 dígitos.';
    }
    if (Object.keys(newErrors).length) {
      setErrors(newErrors);
      
      // Navegar para a aba com erro
      const errorFields = Object.keys(newErrors);
      const geralFields = ['tipo', 'codigo', 'descricao', 'unidade_medida', 'valor_unitario'];
      const fiscalFields = ['cClass', 'cfop', 'ncm', 'base_calculo_icms_default', 'aliquota_icms_default', 'valor_desconto_default', 'valor_outros_default'];
      const planoFields = ['upload_speed', 'download_speed', 'max_limit', 'fidelity_months', 'billing_cycle', 'notes', 'promotional_price', 'promotional_months', 'promotional_active'];
      
      if (errorFields.some(field => geralFields.includes(field))) {
        setTabValue(0);
      } else if (errorFields.some(field => fiscalFields.includes(field))) {
        setTabValue(1);
      } else if (errorFields.some(field => planoFields.includes(field))) {
        setTabValue(2);
      }
      
      return;
    }
    try {
      if (editingServico) {
        await servicoService.updateServico(activeCompany.id, editingServico.id, formData as any);
        setSnackbar({ open: true, message: 'Serviço atualizado com sucesso', severity: 'success' });
      } else {
        await servicoService.createServico(activeCompany.id, formData as any);
        setSnackbar({ open: true, message: 'Serviço criado com sucesso', severity: 'success' });
      }
      handleClose();
      loadServicos();
    } catch (error) {
      setSnackbar({ open: true, message: stringifyError(error) || 'Erro ao salvar serviço', severity: 'error' });
    }
  };

  const handleDelete = async (servico: Servico) => {
    if (!activeCompany || !window.confirm(`Excluir serviço "${servico.descricao}"?`)) return;
    try {
      await servicoService.deleteServico(activeCompany.id, servico.id);
      setSnackbar({ open: true, message: 'Serviço excluído', severity: 'success' });
      loadServicos();
    } catch (e) {
      setSnackbar({ open: true, message: 'Erro ao excluir serviço', severity: 'error' });
    }
  };

  if (!activeCompany) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6">Nenhuma empresa ativa</Typography>
        <Typography variant="body2" color="text.secondary">Selecione uma empresa para gerenciar os serviços.</Typography>
      </Paper>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ flexShrink: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 'bold' }}>Serviços</Typography>
        <Button variant="contained" startIcon={<PlusIcon className="w-5 h-5" />} onClick={() => handleOpen()}>
          Novo Serviço
        </Button>
      </Box>

      {/* Search Bar */}
      <Box sx={{ flexShrink: 0, mb: 2 }}>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Buscar por descrição, código, NCM ou CFOP..."
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
        ) : filteredServicos.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary">
              {searchTerm ? 'Nenhum serviço encontrado' : 'Nenhum serviço cadastrado'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {searchTerm ? 'Tente ajustar os termos da busca' : 'Clique em "Novo Serviço" para adicionar o primeiro'}
            </Typography>
          </Paper>
        ) : isMobile ? (
          renderServiceCards()
        ) : (
          renderServiceTable()
        )}
      </Box>
      
      {!loading && filteredServicos.length > 0 && renderPagination()}

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={handleClose} />
          {/* dialog container: limit height and make content scrollable */}
          <div role="dialog" aria-modal="true" className="relative bg-white rounded-lg shadow-xl w-full max-w-2xl flex flex-col overflow-hidden mx-2 sm:mx-0" style={{ maxHeight: '90vh' }}>
            <div className="p-6 border-b flex-shrink-0">
              <Typography variant="h6">{editingServico ? 'Editar Serviço' : 'Novo Serviço'}</Typography>
            </div>
            {/* content: tabs for better organization */}
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)} aria-label="servico tabs">
                <Tab label="Geral" />
                <Tab label="Fiscal" />
                {formData.tipo === 'PLANO_INTERNET' && <Tab label="Plano" />}
              </Tabs>
            </Box>
            <Box sx={{ p: 3, overflowY: 'auto', maxHeight: 'calc(90vh - 220px)' }}>
              {tabValue === 0 && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <FormControl fullWidth>
                    <InputLabel sx={{ backgroundColor: 'white', padding: '0 4px' }}>Tipo</InputLabel>
                    <Select value={formData.tipo} onChange={e => handleInputChange('tipo', e.target.value)}>
                      <MenuItem value="SERVICO">Serviço</MenuItem>
                      <MenuItem value="PLANO_INTERNET">Plano de Internet</MenuItem>
                    </Select>
                  </FormControl>
                  <TextField label="Código" value={formData.codigo} onChange={e => handleInputChange('codigo', e.target.value)} fullWidth error={!!errors.codigo} helperText={errors.codigo} />
                  <TextField label="Descrição" value={formData.descricao} onChange={e => handleInputChange('descricao', e.target.value)} fullWidth error={!!errors.descricao} helperText={errors.descricao} />
                  <TextField label="Unidade de Medida" value={formData.unidade_medida} onChange={e => handleInputChange('unidade_medida', e.target.value)} fullWidth error={!!errors.unidade_medida} helperText={errors.unidade_medida} />
                  <TextField label="Valor Unitário" type="number" value={formData.valor_unitario} onChange={e => handleInputChange('valor_unitario', parseFloat(e.target.value) || 0)} fullWidth />
                </Box>
              )}
              {tabValue === 1 && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <GroupedCClassAutocomplete
                    cclassList={cclassList as any}
                    value={formData.cClass}
                    onChange={(code: string) => handleInputChange('cClass', code)}
                    error={!!errors.cClass}
                    helperText={errors.cClass}
                  />
                  <Autocomplete
                    options={cfopList as any}
                    getOptionLabel={(opt: any) => `${opt.code} — ${opt.description}`}
                    value={(cfopList as any).find((c: any) => c.code === (formData.cfop || '').replace('.', '')) || null}
                    onChange={(_, value) => handleInputChange('cfop', value ? value.code : '')}
                    renderInput={(params) => (
                      <TextField {...params} label="CFOP" fullWidth error={!!errors.cfop} helperText={errors.cfop} />
                    )}
                  />
                  <TextField label="NCM" value={formData.ncm} onChange={e => handleInputChange('ncm', e.target.value)} fullWidth />
                  <TextField label="Base Cálculo ICMS (padrão)" type="number" value={formData.base_calculo_icms_default} onChange={e => handleInputChange('base_calculo_icms_default', parseFloat(e.target.value) || 0)} fullWidth />
                  <TextField label="Alíquota ICMS (%)" type="number" value={formData.aliquota_icms_default} onChange={e => handleInputChange('aliquota_icms_default', parseFloat(e.target.value) || 0)} fullWidth />
                  <TextField label="Valor Desconto (padrão)" type="number" value={formData.valor_desconto_default} onChange={e => handleInputChange('valor_desconto_default', parseFloat(e.target.value) || 0)} fullWidth />
                  <TextField label="Valor Outros (padrão)" type="number" value={formData.valor_outros_default} onChange={e => handleInputChange('valor_outros_default', parseFloat(e.target.value) || 0)} fullWidth />
                </Box>
              )}
              {tabValue === 2 && formData.tipo === 'PLANO_INTERNET' && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <TextField label="Velocidade de Upload (Mbps)" type="number" value={formData.upload_speed} onChange={e => handleInputChange('upload_speed', parseFloat(e.target.value) || 0)} fullWidth />
                  <TextField label="Velocidade de Download (Mbps)" type="number" value={formData.download_speed} onChange={e => handleInputChange('download_speed', parseFloat(e.target.value) || 0)} fullWidth />
                  <TextField label="Limite Máximo (opcional, ex: 10M/10M - gerado automaticamente se vazio)" value={formData.max_limit} onChange={e => handleInputChange('max_limit', e.target.value)} fullWidth />
                  <TextField label="Fidelidade (meses)" type="number" value={formData.fidelity_months} onChange={e => handleInputChange('fidelity_months', parseInt(e.target.value) || 0)} fullWidth />
                  <FormControl fullWidth sx={{ minWidth: 200 }}>
                    <InputLabel sx={{ backgroundColor: 'white', padding: '0 4px' }}>Ciclo de Cobrança</InputLabel>
                    <Select value={formData.billing_cycle} onChange={e => handleInputChange('billing_cycle', e.target.value)}>
                      <MenuItem value="MENSAL">Mensal</MenuItem>
                      <MenuItem value="TRIMESTRAL">Trimestral</MenuItem>
                      <MenuItem value="SEMESTRAL">Semestral</MenuItem>
                      <MenuItem value="ANUAL">Anual</MenuItem>
                    </Select>
                  </FormControl>
                  <TextField label="Observações" multiline rows={3} value={formData.notes} onChange={e => handleInputChange('notes', e.target.value)} fullWidth />
                  <FormControlLabel
                    control={<Checkbox checked={formData.promotional_active} onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleInputChange('promotional_active', e.target.checked)} />}
                    label="Ativar promoção"
                  />
                  {formData.promotional_active && (
                    <>
                      <TextField label="Preço promocional" type="number" value={formData.promotional_price} onChange={e => handleInputChange('promotional_price', parseFloat(e.target.value) || 0)} fullWidth />
                      <TextField label="Meses promocionais" type="number" value={formData.promotional_months} onChange={e => handleInputChange('promotional_months', parseInt(e.target.value) || 0)} fullWidth />
                    </>
                  )}
                </Box>
              )}
            </Box>
            <div className="p-6 border-t flex justify-end gap-4 flex-shrink-0">
              <Button onClick={handleClose}>Cancelar</Button>
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

export default Servicos;

// --- GroupedCClassAutocomplete component (kept in same file for simplicity) ---
type CClassItem = { code: string; title: string; example?: string };

function GroupedCClassAutocomplete({ cclassList, value, onChange, error, helperText }: { cclassList: CClassItem[]; value?: string; onChange: (code: string) => void; error?: boolean; helperText?: string }) {
  const itemOptions = useMemo(() => (cclassList || []).filter((i: any) => i.code && String(i.code).length === 7), [cclassList]);
  const groupTitles = useMemo(() => {
    const map: Record<string, string> = {};
    (cclassList || []).forEach((i: any) => {
      if (i.code && String(i.code).length === 3) map[String(i.code)] = i.title;
    });
    return map;
  }, [cclassList]);

  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  // Initialize groups collapsed by default when itemOptions become available.
  useEffect(() => {
    if (Object.keys(collapsed).length === 0 && itemOptions.length > 0) {
      const codes = Array.from(new Set(itemOptions.map((o: any) => String(o.code).slice(0, 3))));
      const init: Record<string, boolean> = {};
      codes.forEach(c => { init[c] = true; });
      setCollapsed(init);
    }
  }, [itemOptions]);

  const selectedOption = useMemo(() => itemOptions.find((i: any) => i.code === value) || null, [itemOptions, value]);

  return (
    <Autocomplete
      options={itemOptions}
      groupBy={(opt: any) => String(opt.code).slice(0, 3)}
      getOptionLabel={(opt: any) => `${opt.code} — ${opt.title}`}
      value={selectedOption}
      onChange={(_, val) => onChange(val ? val.code : '')}
      renderGroup={(params) => {
        const groupCode = params.group;
        const title = groupTitles[groupCode] || '';
        const isCollapsed = !!collapsed[groupCode];
        return (
          <li key={params.key}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 12px' }}>
              <div style={{ fontWeight: 600 }}>{groupCode} — {title}</div>
              <div>
                <button type="button" onClick={() => setCollapsed(prev => ({ ...prev, [groupCode]: !prev[groupCode] }))} style={{ background: 'none', border: 'none', cursor: 'pointer' }} aria-label={isCollapsed ? 'Expandir grupo' : 'Recolher grupo'}>
                  {isCollapsed ? <ExpandMoreIcon fontSize="small" /> : <ExpandLessIcon fontSize="small" />}
                </button>
              </div>
            </div>
            {!isCollapsed && <ul style={{ margin: 0 }}>{params.children}</ul>}
          </li>
        );
      }}
      renderInput={(params) => (
        <TextField {...params} label="Cód. Classificação (NFCom) — escolha o item (7 dígitos)" fullWidth error={error} helperText={helperText} />
      )}
      isOptionEqualToValue={(opt, val) => opt.code === val.code}
      sx={{ width: '100%' }}
    />
  );
}
