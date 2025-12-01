import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { Box, Paper, Typography, Button, IconButton, TextField, CircularProgress, Chip, Snackbar, Alert, useMediaQuery, useTheme, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TablePagination, Card, CardContent, Divider, Pagination, InputAdornment, MenuItem } from '@mui/material';
import { PlusIcon, MagnifyingGlassIcon, XMarkIcon, DocumentArrowDownIcon } from '@heroicons/react/24/outline';
import { useCompany } from '../contexts/CompanyContext';
import receivableService from '../services/receivableService';
import { stringifyError } from '../utils/error';

interface Receivable {
  id: number;
  empresa_id: number;
  cliente_id: number;
  servico_contratado_id?: number;
  nfcom_fatura_id?: number;
  tipo: string;
  issue_date: string;
  due_date: string;
  amount: number;
  discount: number;
  interest_percent: number;
  fine_percent: number;
  bank: string;
  carteira?: string;
  agencia?: string;
  conta?: string;
  nosso_numero?: string;
  bank_registration_id?: string;
  codigo_barras?: string;
  linha_digitavel?: string;
  status: string;
  registered_at?: string;
  printed_at?: string;
  sent_at?: string;
  paid_at?: string;
  registro_result?: string;
  pdf_url?: string;
  bank_account_id?: number;
  bank_account_snapshot?: string;
  bank_payload?: string;
  created_at: string;
  updated_at?: string;
}

const Receivables: React.FC = () => {
  const { activeCompany } = useCompany();
  const [receivables, setReceivables] = useState<Receivable[]>([]);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  // Pagination state
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Search state
  const [searchTerm, setSearchTerm] = useState('');

  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' | 'warning' });

  const loadReceivables = useCallback(async () => {
    if (!activeCompany) return;
    setLoading(true);
    try {
      const data = await receivableService.listReceivables(activeCompany.id, page + 1, rowsPerPage);
      setReceivables(data || []);
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao carregar cobranças', severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [activeCompany, page, rowsPerPage]);

  useEffect(() => {
    if (activeCompany) {
      loadReceivables();
    }
  }, [activeCompany, loadReceivables]);

  // Filter receivables based on search term
  const filteredReceivables = useMemo(() => {
    if (!searchTerm) return receivables;
    const term = searchTerm.toLowerCase();
    return receivables.filter(r =>
      r.id.toString().includes(term) ||
      r.status?.toLowerCase().includes(term) ||
      r.bank?.toLowerCase().includes(term) ||
      r.nosso_numero?.toLowerCase().includes(term) ||
      r.due_date?.includes(term)
    );
  }, [receivables, searchTerm]);

  // Paginate filtered results
  const paginatedReceivables = useMemo(() => {
    const start = page * rowsPerPage;
    const end = start + rowsPerPage;
    return filteredReceivables.slice(start, end);
  }, [filteredReceivables, page, rowsPerPage]);

  const handleGenerate = async () => {
    if (!activeCompany) return;
    setGenerating(true);
    try {
      const created = await receivableService.generateForCompany(activeCompany.id);
      setSnackbar({
        open: true,
        message: `${created?.length || 0} cobranças geradas com sucesso`,
        severity: 'success'
      });
      loadReceivables();
    } catch (e) {
      setSnackbar({ open: true, message: stringifyError(e) || 'Erro ao gerar cobranças', severity: 'error' });
    } finally {
      setGenerating(false);
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

  const getStatusColor = (status: string) => {
    switch (status?.toUpperCase()) {
      case 'PAID':
        return 'success';
      case 'PENDING':
        return 'warning';
      case 'OVERDUE':
        return 'error';
      case 'CANCELLED':
        return 'default';
      case 'REGISTERED':
        return 'info';
      default:
        return 'default';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status?.toUpperCase()) {
      case 'PAID':
        return 'Pago';
      case 'PENDING':
        return 'Pendente';
      case 'OVERDUE':
        return 'Vencido';
      case 'CANCELLED':
        return 'Cancelado';
      case 'REGISTERED':
        return 'Registrado';
      default:
        return status || 'Desconhecido';
    }
  };

  const renderReceivableTable = () => (
    <TableContainer>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell>
            <TableCell>Vencimento</TableCell>
            <TableCell>Valor</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Banco</TableCell>
            <TableCell>Nosso Número</TableCell>
            <TableCell>Ações</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {paginatedReceivables.map((r) => (
            <TableRow key={r.id}>
              <TableCell>{r.id}</TableCell>
              <TableCell>
                {new Date(r.due_date).toLocaleDateString('pt-BR')}
              </TableCell>
              <TableCell>
                {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(r.amount || 0)}
              </TableCell>
              <TableCell>
                <Chip
                  label={getStatusLabel(r.status)}
                  color={getStatusColor(r.status) as any}
                  size="small"
                />
              </TableCell>
              <TableCell>
                <Chip label={r.bank || 'N/A'} color="primary" size="small" />
              </TableCell>
              <TableCell>{r.nosso_numero || '-'}</TableCell>
              <TableCell>
                {r.pdf_url && (
                  <IconButton size="small" title="Download PDF" onClick={() => window.open(r.pdf_url, '_blank')}>
                    <DocumentArrowDownIcon className="w-4 h-4" />
                  </IconButton>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  const renderReceivableCards = () => (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {paginatedReceivables.map((r) => (
        <Card key={r.id}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Box>
                <Typography variant="h6" sx={{ mb: 1 }}>
                  Cobrança #{r.id}
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
                  <Chip
                    label={getStatusLabel(r.status)}
                    color={getStatusColor(r.status) as any}
                    size="small"
                  />
                  {r.bank && <Chip label={r.bank} color="primary" size="small" />}
                </Box>
              </Box>
              <Box sx={{ display: 'flex', gap: 1 }}>
                {r.pdf_url && (
                  <IconButton size="small" title="Download PDF" onClick={() => window.open(r.pdf_url, '_blank')}>
                    <DocumentArrowDownIcon className="w-4 h-4" />
                  </IconButton>
                )}
              </Box>
            </Box>
            <Divider sx={{ mb: 2 }} />
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
              <Box>
                <Typography variant="body2" color="text.secondary">Vencimento</Typography>
                <Typography variant="body1">
                  {new Date(r.due_date).toLocaleDateString('pt-BR')}
                </Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">Valor</Typography>
                <Typography variant="body1">
                  {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(r.amount || 0)}
                </Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">Nosso Número</Typography>
                <Typography variant="body1">{r.nosso_numero || '-'}</Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">Emissão</Typography>
                <Typography variant="body1">
                  {new Date(r.issue_date).toLocaleDateString('pt-BR')}
                </Typography>
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
            count={Math.ceil(filteredReceivables.length / rowsPerPage)}
            page={page + 1}
            onChange={handleChangePage}
            size="small"
            showFirstButton
            showLastButton
          />
        </Box>
      );
    }

    return (
      <TablePagination
        rowsPerPageOptions={[5, 10, 25, 50, 100]}
        component="div"
        count={filteredReceivables.length}
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
        <Typography variant="body2" color="text.secondary">Selecione uma empresa para gerenciar as cobranças.</Typography>
      </Paper>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ flexShrink: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 'bold' }}>Cobranças / Recebíveis</Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="contained"
            startIcon={generating ? <CircularProgress size={16} /> : <PlusIcon className="w-5 h-5" />}
            onClick={handleGenerate}
            disabled={generating}
          >
            {generating ? 'Gerando...' : 'Gerar Cobranças'}
          </Button>
        </Box>
      </Box>

      {/* Search Bar */}
      <Box sx={{ flexShrink: 0, mb: 2 }}>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Buscar por ID, status, banco, nosso número ou data..."
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
        {loading && !generating ? (
          <Box sx={{ display: 'flex', flexGrow: 1, justifyContent: 'center', alignItems: 'center' }}><CircularProgress /></Box>
        ) : filteredReceivables.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary">
              {searchTerm ? 'Nenhuma cobrança encontrada' : 'Nenhuma cobrança cadastrada'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {searchTerm ? 'Tente ajustar os termos da busca' : 'Clique em "Gerar Cobranças" para criar as primeiras cobranças'}
            </Typography>
          </Paper>
        ) : isMobile ? (
          renderReceivableCards()
        ) : (
          renderReceivableTable()
        )}

        {/* Pagination inside scrollable area */}
        {!loading && filteredReceivables.length > 0 && renderPagination()}
      </Box>

      <Snackbar open={snackbar.open} autoHideDuration={6000} onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}>
        <Alert onClose={() => setSnackbar(prev => ({ ...prev, open: false }))} severity={snackbar.severity} sx={{ width: '100%' }}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default Receivables;
