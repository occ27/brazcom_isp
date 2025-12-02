import React, { useEffect, useState, useCallback } from 'react';
import {
  Box, Paper, Typography, Button, IconButton, TextField, CircularProgress,
  Chip, Snackbar, Alert, useMediaQuery, useTheme, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, TablePagination,
  Card, CardContent, Divider, Dialog, DialogTitle, DialogContent,
  DialogActions, FormControl, InputLabel, Select, MenuItem,
  Fab, Tooltip, Avatar, List, ListItem, ListItemText, ListItemAvatar,
  FormControlLabel, Checkbox
} from '@mui/material';
import {
  PlusIcon, MagnifyingGlassIcon, XMarkIcon, ChatBubbleLeftIcon,
  ClockIcon, UserIcon, ExclamationTriangleIcon, CheckCircleIcon,
  XCircleIcon, PauseIcon, PlayIcon, TrashIcon
} from '@heroicons/react/24/outline';
import { useCompany } from '../contexts/CompanyContext';
import ticketService from '../services/ticketService';
import clientService, { ClientAutocomplete as ClientAutocompleteType } from '../services/clientService';
import { stringifyError } from '../utils/error';
import { Ticket, TicketComment, StatusTicket, PrioridadeTicket, CategoriaTicket } from '../types';
import ClientAutocomplete from '../components/ClientAutocomplete';
import { useAuth } from '../contexts/AuthContext';

const Tickets: React.FC = () => {
  const { activeCompany } = useCompany();
  const { hasPermission } = useAuth();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusTicket | ''>('');
  const [prioridadeFilter, setPrioridadeFilter] = useState<PrioridadeTicket | ''>('');
  const [categoriaFilter, setCategoriaFilter] = useState<CategoriaTicket | ''>('');

  // Paginação
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Dialogs
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [comments, setComments] = useState<TicketComment[]>([]);

  // Form validation errors
  const [formErrors, setFormErrors] = useState({
    titulo: false,
    descricao: false,
    cliente: false
  });

  // Form states
  const [newTicket, setNewTicket] = useState({
    titulo: '',
    descricao: '',
    prioridade: 'NORMAL' as PrioridadeTicket,
    categoria: 'SUPORTE' as CategoriaTicket,
    cliente: null as ClientAutocompleteType | null,
    atribuido_para_id: ''
  });

  const [newComment, setNewComment] = useState({
    comentario: '',
    is_internal: false
  });

  // Status update states
  const [statusUpdating, setStatusUpdating] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState<StatusTicket | ''>('');

  const loadTickets = useCallback(async () => {
    if (!activeCompany) return;

    try {
      setLoading(true);
      const data = await ticketService.listTickets(
        page * rowsPerPage,
        rowsPerPage,
        statusFilter || undefined,
        prioridadeFilter || undefined,
        categoriaFilter || undefined,
        undefined, // cliente_id
        undefined, // atribuido_para_id
        searchTerm || undefined
      );
      setTickets(data);
    } catch (err) {
      setError(stringifyError(err));
    } finally {
      setLoading(false);
    }
  }, [activeCompany, page, rowsPerPage, statusFilter, prioridadeFilter, categoriaFilter, searchTerm]);

  useEffect(() => {
    loadTickets();
  }, [loadTickets]);

  const handleCreateTicket = async () => {
    // Reset previous errors
    setFormErrors({ titulo: false, descricao: false, cliente: false });

    // Validação
    const errors = { titulo: false, descricao: false, cliente: false };
    let hasError = false;

    if (!newTicket.titulo.trim()) {
      errors.titulo = true;
      hasError = true;
    }
    if (!newTicket.descricao.trim()) {
      errors.descricao = true;
      hasError = true;
    }
    if (!newTicket.cliente) {
      errors.cliente = true;
      hasError = true;
    }

    if (hasError) {
      setFormErrors(errors);
      setError('Por favor, preencha todos os campos obrigatórios');
      return;
    }

    try {
      const ticketData = {
        ...newTicket,
        cliente_id: newTicket.cliente!.id,
        atribuido_para_id: newTicket.atribuido_para_id ? parseInt(newTicket.atribuido_para_id) : undefined
      };
      await ticketService.createTicket(ticketData);
      setSuccess('Ticket criado com sucesso!');
      setCreateDialogOpen(false);
      setNewTicket({
        titulo: '',
        descricao: '',
        prioridade: 'NORMAL',
        categoria: 'SUPORTE',
        cliente: null,
        atribuido_para_id: ''
      });
      setFormErrors({ titulo: false, descricao: false, cliente: false });
      loadTickets();
    } catch (err) {
      setError(stringifyError(err));
    }
  };

  const handleViewTicket = async (ticket: Ticket) => {
    setSelectedTicket(ticket);
    setSelectedStatus(ticket.status); // Inicializar com o status atual
    try {
      const commentsData = await ticketService.getComments(ticket.id);
      setComments(commentsData);
      setDetailDialogOpen(true);
    } catch (err) {
      setError(stringifyError(err));
    }
  };

  const handleAddComment = async () => {
    if (!selectedTicket) return;

    try {
      await ticketService.addComment(selectedTicket.id, newComment);
      setSuccess('Comentário adicionado!');
      setNewComment({ comentario: '', is_internal: false });
      // Recarregar comentários
      const commentsData = await ticketService.getComments(selectedTicket.id);
      setComments(commentsData);
      // Recarregar ticket para atualizar contadores
      loadTickets();
    } catch (err) {
      setError(stringifyError(err));
    }
  };

  const handleDeleteTicket = async (ticket: Ticket) => {
    if (!window.confirm(`Tem certeza que deseja excluir o ticket "${ticket.titulo}"?`)) {
      return;
    }

    try {
      await ticketService.deleteTicket(ticket.id);
      setSuccess('Ticket excluído com sucesso!');
      setDetailDialogOpen(false);
      loadTickets();
    } catch (err) {
      setError(stringifyError(err));
    }
  };

  const handleStatusChange = (newStatus: StatusTicket) => {
    setSelectedStatus(newStatus);
  };

  const handleUpdateStatus = async () => {
    if (!selectedTicket || !selectedStatus || selectedStatus === selectedTicket.status) {
      return;
    }

    setStatusUpdating(true);
    try {
      await ticketService.updateTicket(selectedTicket.id, { status: selectedStatus });
      setSuccess('Status do ticket atualizado com sucesso!');
      
      // Atualizar o ticket selecionado com o novo status
      setSelectedTicket({ ...selectedTicket, status: selectedStatus });
      
      // Recarregar a lista de tickets
      loadTickets();
      
      // Reset do status selecionado
      setSelectedStatus('');
    } catch (err) {
      setError(stringifyError(err));
    } finally {
      setStatusUpdating(false);
    }
  };

  const getStatusColor = (status: StatusTicket) => {
    switch (status) {
      case 'ABERTO': return 'error';
      case 'EM_ANDAMENTO': return 'warning';
      case 'AGUARDANDO_CLIENTE': return 'info';
      case 'RESOLVIDO': return 'success';
      case 'FECHADO': return 'default';
      case 'CANCELADO': return 'default';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: StatusTicket) => {
    switch (status) {
      case 'ABERTO': return <ExclamationTriangleIcon className="w-4 h-4" />;
      case 'EM_ANDAMENTO': return <PlayIcon className="w-4 h-4" />;
      case 'AGUARDANDO_CLIENTE': return <PauseIcon className="w-4 h-4" />;
      case 'RESOLVIDO': return <CheckCircleIcon className="w-4 h-4" />;
      case 'FECHADO': return <CheckCircleIcon className="w-4 h-4" />;
      case 'CANCELADO': return <XCircleIcon className="w-4 h-4" />;
      default: return <ExclamationTriangleIcon className="w-4 h-4" />;
    }
  };

  const getPrioridadeColor = (prioridade: PrioridadeTicket) => {
    switch (prioridade) {
      case 'BAIXA': return 'success';
      case 'NORMAL': return 'info';
      case 'ALTA': return 'warning';
      case 'URGENTE': return 'error';
      default: return 'default';
    }
  };

  if (!activeCompany) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography variant="h6" color="textSecondary">
          Selecione uma empresa para visualizar os tickets
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ 
      p: isMobile ? 1 : 3,
      minHeight: '100vh',
      width: '100%'
    }}>
      <Box 
        display="flex" 
        justifyContent="space-between" 
        alignItems="center" 
        mb={isMobile ? 2 : 3}
        sx={{ 
          flexDirection: isMobile ? 'column' : 'row',
          alignItems: isMobile ? 'flex-start' : 'center',
          gap: isMobile ? 2 : 0
        }}
      >
        <Typography 
          variant={isMobile ? "h5" : "h4"} 
          component="h1"
          sx={{ width: isMobile ? '100%' : 'auto' }}
        >
          Sistema de Suporte - Tickets
        </Typography>
        {hasPermission('tickets_manage') && (
          <Button
            variant="contained"
            startIcon={<PlusIcon className="w-5 h-5" />}
            onClick={() => setCreateDialogOpen(true)}
            sx={{ 
              width: isMobile ? '100%' : 'auto',
              height: isMobile ? 48 : 'auto'
            }}
          >
            Novo Ticket
          </Button>
        )}
      </Box>

      {/* Filtros */}
      <Paper sx={{ 
        p: isMobile ? 1.5 : 2, 
        mb: isMobile ? 1.5 : 2,
        mx: isMobile ? -1 : 0
      }}>
        <Box 
          display="flex" 
          gap={isMobile ? 1.5 : 2} 
          flexWrap="wrap" 
          alignItems="center"
          sx={{ 
            flexDirection: isMobile ? 'column' : 'row',
            alignItems: isMobile ? 'stretch' : 'center'
          }}
        >
          <TextField
            label="Buscar"
            variant="outlined"
            size="small"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: <MagnifyingGlassIcon className="w-4 h-4 mr-2" />,
            }}
            sx={{ 
              minWidth: isMobile ? '100%' : 200,
              width: isMobile ? '100%' : 'auto',
              '& .MuiInputBase-root': {
                height: isMobile ? 48 : 'auto'
              }
            }}
          />

          <Box 
            display="flex" 
            gap={isMobile ? 1.5 : 2} 
            sx={{ 
              flexDirection: isMobile ? 'column' : 'row',
              width: isMobile ? '100%' : 'auto'
            }}
          >
            <FormControl 
              size="small" 
              sx={{ 
                minWidth: isMobile ? '100%' : 120,
                '& .MuiInputBase-root': {
                  height: isMobile ? 48 : 'auto'
                }
              }}
            >
              <InputLabel>Status</InputLabel>
              <Select
                value={statusFilter}
                label="Status"
                onChange={(e) => setStatusFilter(e.target.value as StatusTicket)}
              >
                <MenuItem value="">Todos</MenuItem>
                <MenuItem value="ABERTO">Aberto</MenuItem>
                <MenuItem value="EM_ANDAMENTO">Em Andamento</MenuItem>
                <MenuItem value="AGUARDANDO_CLIENTE">Aguardando Cliente</MenuItem>
                <MenuItem value="RESOLVIDO">Resolvido</MenuItem>
                <MenuItem value="FECHADO">Fechado</MenuItem>
                <MenuItem value="CANCELADO">Cancelado</MenuItem>
              </Select>
            </FormControl>

            <FormControl 
              size="small" 
              sx={{ 
                minWidth: isMobile ? '100%' : 120,
                '& .MuiInputBase-root': {
                  height: isMobile ? 48 : 'auto'
                }
              }}
            >
              <InputLabel>Prioridade</InputLabel>
              <Select
                value={prioridadeFilter}
                label="Prioridade"
                onChange={(e) => setPrioridadeFilter(e.target.value as PrioridadeTicket)}
              >
                <MenuItem value="">Todas</MenuItem>
                <MenuItem value="BAIXA">Baixa</MenuItem>
                <MenuItem value="NORMAL">Normal</MenuItem>
                <MenuItem value="ALTA">Alta</MenuItem>
                <MenuItem value="URGENTE">Urgente</MenuItem>
              </Select>
            </FormControl>

            <FormControl 
              size="small" 
              sx={{ 
                minWidth: isMobile ? '100%' : 120,
                '& .MuiInputBase-root': {
                  height: isMobile ? 48 : 'auto'
                }
              }}
            >
              <InputLabel>Categoria</InputLabel>
              <Select
                value={categoriaFilter}
                label="Categoria"
                onChange={(e) => setCategoriaFilter(e.target.value as CategoriaTicket)}
              >
                <MenuItem value="">Todas</MenuItem>
                <MenuItem value="TECNICO">Técnico</MenuItem>
                <MenuItem value="COBRANCA">Cobrança</MenuItem>
                <MenuItem value="INSTALACAO">Instalação</MenuItem>
                <MenuItem value="SUPORTE">Suporte</MenuItem>
                <MenuItem value="CANCELAMENTO">Cancelamento</MenuItem>
                <MenuItem value="OUTRO">Outro</MenuItem>
              </Select>
            </FormControl>
          </Box>

          <Button
            variant="outlined"
            onClick={() => {
              setSearchTerm('');
              setStatusFilter('');
              setPrioridadeFilter('');
              setCategoriaFilter('');
            }}
            startIcon={<XMarkIcon className="w-4 h-4" />}
            sx={{ 
              width: isMobile ? '100%' : 'auto',
              mt: isMobile ? 1 : 0,
              height: isMobile ? 48 : 'auto'
            }}
          >
            Limpar
          </Button>
        </Box>
      </Paper>

      {/* Tabela de Tickets */}
      <Paper sx={{ 
        mx: isMobile ? -1 : 0,
        borderRadius: isMobile ? 0 : 1
      }}>
        {loading ? (
          <Box display="flex" justifyContent="center" p={4}>
            <CircularProgress />
          </Box>
        ) : isMobile ? (
          // Layout mobile com cards
          <Box sx={{ p: isMobile ? 1.5 : 2 }}>
            {tickets.map((ticket) => (
              <Card key={ticket.id} sx={{ 
                mb: 1.5,
                borderRadius: 2,
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                '&:hover': {
                  boxShadow: '0 4px 16px rgba(0,0,0,0.15)'
                },
                display: 'flex',
                flexDirection: 'column',
                minHeight: 180
              }}>
                <CardContent sx={{ 
                  p: 2,
                  display: 'flex',
                  flexDirection: 'column',
                  height: '100%'
                }}>
                  <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1.5}>
                    <Typography 
                      variant="h6" 
                      sx={{ 
                        fontSize: '1.1rem',
                        fontWeight: 600,
                        lineHeight: 1.3,
                        pr: 1
                      }}
                    >
                      #{ticket.id} - {ticket.titulo}
                    </Typography>
                  </Box>
                  
                  <Box display="flex" gap={1} mb={1.5} flexWrap="wrap">
                    <Chip
                      icon={getStatusIcon(ticket.status)}
                      label={ticket.status.replace('_', ' ')}
                      color={getStatusColor(ticket.status)}
                      size="small"
                      sx={{ fontSize: '0.75rem' }}
                    />
                    <Chip
                      label={ticket.prioridade}
                      color={getPrioridadeColor(ticket.prioridade)}
                      size="small"
                      sx={{ fontSize: '0.75rem' }}
                    />
                    <Chip 
                      label={ticket.categoria} 
                      size="small" 
                      sx={{ fontSize: '0.75rem' }}
                    />
                  </Box>

                  <Typography 
                    variant="body2" 
                    color="text.secondary" 
                    mb={1}
                    sx={{ fontSize: '0.875rem' }}
                  >
                    <strong>Cliente:</strong> {ticket.cliente_nome || 'N/A'}
                  </Typography>

                  <Box 
                    display="flex" 
                    justifyContent="space-between" 
                    alignItems="center"
                    sx={{ mt: 'auto' }}
                  >
                    <Typography 
                      variant="body2" 
                      color="text.secondary"
                      sx={{ fontSize: '0.75rem' }}
                    >
                      <strong>Criado em:</strong> {new Date(ticket.created_at).toLocaleDateString('pt-BR')}
                    </Typography>
                    <IconButton 
                      onClick={() => handleViewTicket(ticket)} 
                      size="small"
                      sx={{ 
                        p: 0.5,
                        color: 'primary.main',
                        '&:hover': {
                          backgroundColor: 'primary.light',
                          color: 'primary.contrastText'
                        }
                      }}
                    >
                      <ChatBubbleLeftIcon className="w-4 h-4" />
                    </IconButton>
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>
        ) : (
          // Layout desktop com tabela
          <>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>Título</TableCell>
                    <TableCell>Cliente</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Prioridade</TableCell>
                    <TableCell>Categoria</TableCell>
                    <TableCell>Criado em</TableCell>
                    <TableCell>Ações</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {tickets.map((ticket) => (
                    <TableRow key={ticket.id} hover>
                      <TableCell>{ticket.id}</TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {ticket.titulo}
                        </Typography>
                      </TableCell>
                      <TableCell>{ticket.cliente_nome || 'N/A'}</TableCell>
                      <TableCell>
                        <Chip
                          icon={getStatusIcon(ticket.status)}
                          label={ticket.status.replace('_', ' ')}
                          color={getStatusColor(ticket.status)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={ticket.prioridade}
                          color={getPrioridadeColor(ticket.prioridade)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{ticket.categoria}</TableCell>
                      <TableCell>
                        {new Date(ticket.created_at).toLocaleDateString('pt-BR')}
                      </TableCell>
                      <TableCell>
                        <Tooltip title="Ver detalhes">
                          <IconButton onClick={() => handleViewTicket(ticket)}>
                            <ChatBubbleLeftIcon className="w-4 h-4" />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination
              component="div"
              count={tickets.length}
              page={page}
              onPageChange={(event, newPage) => setPage(newPage)}
              rowsPerPage={rowsPerPage}
              onRowsPerPageChange={(event) => {
                setRowsPerPage(parseInt(event.target.value, 10));
                setPage(0);
              }}
              labelRowsPerPage={isMobile ? "Linhas" : "Linhas por página"}
              sx={{
                '.MuiTablePagination-toolbar': {
                  flexWrap: isMobile ? 'wrap' : 'nowrap',
                  gap: isMobile ? 1 : 0,
                  minHeight: isMobile ? 48 : 'auto'
                },
                '.MuiTablePagination-selectLabel, .MuiTablePagination-displayedRows': {
                  fontSize: isMobile ? '0.75rem' : '0.875rem'
                }
              }}
            />
          </>
        )}
      </Paper>

      {/* Dialog para criar ticket */}
      <Dialog 
        open={createDialogOpen} 
        onClose={() => setCreateDialogOpen(false)} 
        maxWidth="md" 
        fullWidth
        fullScreen={isMobile}
        sx={{
          '& .MuiDialog-paper': {
            margin: isMobile ? 0 : 32,
            width: isMobile ? '100%' : 'auto',
            maxWidth: isMobile ? 'none' : 'md',
            height: isMobile ? '100%' : 'auto'
          }
        }}
      >
        <DialogTitle sx={{ 
          pb: isMobile ? 1 : 2,
          fontSize: isMobile ? '1.25rem' : '1.5rem'
        }}>
          Criar Novo Ticket
        </DialogTitle>
        <DialogContent sx={{ 
          p: isMobile ? 2 : 3,
          flex: 1,
          overflow: 'auto'
        }}>
          <Box sx={{ 
            pt: isMobile ? 1 : 2, 
            display: 'flex', 
            flexDirection: 'column', 
            gap: isMobile ? 2 : 2 
          }}>
            <TextField
              label="Título"
              fullWidth
              value={newTicket.titulo}
              onChange={(e) => setNewTicket({ ...newTicket, titulo: e.target.value })}
              required
              error={formErrors.titulo}
              helperText={formErrors.titulo ? "O título é obrigatório" : ""}
              sx={{
                '& .MuiInputBase-root': {
                  height: isMobile ? 56 : 'auto'
                }
              }}
            />
            <TextField
              label="Descrição"
              fullWidth
              multiline
              rows={isMobile ? 4 : 4}
              value={newTicket.descricao}
              onChange={(e) => setNewTicket({ ...newTicket, descricao: e.target.value })}
              required
              error={formErrors.descricao}
              helperText={formErrors.descricao ? "A descrição é obrigatória" : ""}
            />
            <Box 
              display="flex" 
              gap={isMobile ? 2 : 2}
              sx={{ flexDirection: isMobile ? 'column' : 'row' }}
            >
              <FormControl 
                fullWidth
                sx={{
                  '& .MuiInputBase-root': {
                    height: isMobile ? 56 : 'auto'
                  }
                }}
              >
                <InputLabel>Prioridade</InputLabel>
                <Select
                  value={newTicket.prioridade}
                  label="Prioridade"
                  onChange={(e) => setNewTicket({ ...newTicket, prioridade: e.target.value as PrioridadeTicket })}
                >
                  <MenuItem value="BAIXA">Baixa</MenuItem>
                  <MenuItem value="NORMAL">Normal</MenuItem>
                  <MenuItem value="ALTA">Alta</MenuItem>
                  <MenuItem value="URGENTE">Urgente</MenuItem>
                </Select>
              </FormControl>
              <FormControl 
                fullWidth
                sx={{
                  '& .MuiInputBase-root': {
                    height: isMobile ? 56 : 'auto'
                  }
                }}
              >
                <InputLabel>Categoria</InputLabel>
                <Select
                  value={newTicket.categoria}
                  label="Categoria"
                  onChange={(e) => setNewTicket({ ...newTicket, categoria: e.target.value as CategoriaTicket })}
                >
                  <MenuItem value="TECNICO">Técnico</MenuItem>
                  <MenuItem value="COBRANCA">Cobrança</MenuItem>
                  <MenuItem value="INSTALACAO">Instalação</MenuItem>
                  <MenuItem value="SUPORTE">Suporte</MenuItem>
                  <MenuItem value="CANCELAMENTO">Cancelamento</MenuItem>
                  <MenuItem value="OUTRO">Outro</MenuItem>
                </Select>
              </FormControl>
            </Box>
            <Box sx={{
              '& .MuiInputBase-root': {
                height: isMobile ? 56 : 'auto'
              }
            }}>
              <ClientAutocomplete
                value={newTicket.cliente}
                onChange={(cliente) => setNewTicket({ ...newTicket, cliente })}
                label="Cliente"
                placeholder="Digite nome, CPF/CNPJ, email ou telefone..."
                required={true}
                error={formErrors.cliente}
                helperText={formErrors.cliente ? "A seleção de um cliente é obrigatória" : ""}
              />
            </Box>
          </Box>
        </DialogContent>
        <DialogActions sx={{ 
          flexDirection: 'row', 
          gap: 1,
          p: isMobile ? 2 : 3,
          pt: isMobile ? 1 : 3,
          justifyContent: 'space-between'
        }}>
          <Button 
            onClick={() => setCreateDialogOpen(false)}
            sx={{ minWidth: 'auto', px: 2 }}
          >
            <XMarkIcon className="w-4 h-4" />
          </Button>
          <Button 
            onClick={handleCreateTicket} 
            variant="contained"
            sx={{ minWidth: 'auto', px: 2 }}
          >
            <PlusIcon className="w-4 h-4" />
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog para ver detalhes do ticket */}
      <Dialog 
        open={detailDialogOpen} 
        onClose={() => setDetailDialogOpen(false)} 
        maxWidth="lg" 
        fullWidth
        fullScreen={isMobile}
        sx={{
          '& .MuiDialog-paper': {
            margin: isMobile ? 0 : 32,
            width: isMobile ? '100%' : 'auto',
            maxWidth: isMobile ? 'none' : 'lg',
            height: isMobile ? '100%' : 'auto'
          }
        }}
      >
        <DialogTitle sx={{ 
          pb: isMobile ? 1 : 2,
          fontSize: isMobile ? '1.25rem' : '1.5rem'
        }}>
          Ticket #{selectedTicket?.id} - {selectedTicket?.titulo}
        </DialogTitle>
        <DialogContent sx={{ 
          p: isMobile ? 2 : 3,
          flex: 1,
          overflow: 'auto'
        }}>
          {selectedTicket && (
            <Box sx={{ pt: isMobile ? 1 : 2 }}>
              <Box 
                display="flex" 
                gap={1} 
                mb={isMobile ? 2 : 2}
                sx={{ 
                  flexDirection: 'row',
                  alignItems: 'center',
                  flexWrap: 'wrap'
                }}
              >
                <Chip
                  icon={getStatusIcon(selectedTicket.status)}
                  label={selectedTicket.status.replace('_', ' ')}
                  color={getStatusColor(selectedTicket.status)}
                  size="small"
                  sx={{ 
                    fontSize: isMobile ? '0.7rem' : '0.75rem',
                    height: isMobile ? 24 : 28,
                    '& .MuiChip-icon': {
                      fontSize: isMobile ? '0.875rem' : '1rem'
                    }
                  }}
                />
                <Chip
                  label={selectedTicket.prioridade}
                  color={getPrioridadeColor(selectedTicket.prioridade)}
                  size="small"
                  sx={{ 
                    fontSize: isMobile ? '0.7rem' : '0.75rem',
                    height: isMobile ? 24 : 28
                  }}
                />
                <Chip 
                  label={selectedTicket.categoria} 
                  size="small" 
                  sx={{ 
                    fontSize: isMobile ? '0.7rem' : '0.75rem',
                    height: isMobile ? 24 : 28
                  }}
                />
              </Box>

              <Typography 
                variant="body1" 
                mb={isMobile ? 2 : 2}
                sx={{ fontSize: isMobile ? '1rem' : '1rem' }}
              >
                <strong>Descrição:</strong> {selectedTicket.descricao}
              </Typography>

              <Box 
                display="flex" 
                gap={isMobile ? 1 : 4} 
                mb={isMobile ? 2 : 2}
                sx={{ 
                  flexDirection: 'row',
                  alignItems: 'center',
                  flexWrap: 'wrap'
                }}
              >
                <Typography 
                  variant="body2"
                  sx={{ 
                    fontSize: isMobile ? '0.75rem' : '0.875rem',
                    flex: isMobile ? '1 1 100%' : 'none'
                  }}
                >
                  <strong>Cliente:</strong> {selectedTicket.cliente_nome || 'N/A'}
                </Typography>
                <Typography 
                  variant="body2"
                  sx={{ 
                    fontSize: isMobile ? '0.75rem' : '0.875rem',
                    flex: isMobile ? '1 1 45%' : 'none'
                  }}
                >
                  <strong>Criado por:</strong> {selectedTicket.criado_por_nome}
                </Typography>
                <Typography 
                  variant="body2"
                  sx={{ 
                    fontSize: isMobile ? '0.75rem' : '0.875rem',
                    flex: isMobile ? '1 1 45%' : 'none'
                  }}
                >
                  <strong>Criado em:</strong> {new Date(selectedTicket.created_at).toLocaleString('pt-BR')}
                </Typography>
              </Box>

              {/* Seção de alteração de status */}
              {hasPermission('tickets_manage') && (
                <Box sx={{ 
                  mb: isMobile ? 2 : 3, 
                  p: isMobile ? 1.5 : 2, 
                  border: '1px solid #e0e0e0', 
                  borderRadius: 1 
                }}>
                  <Typography 
                    variant="h6" 
                    mb={isMobile ? 1.5 : 2}
                    sx={{ fontSize: isMobile ? '1.1rem' : '1.25rem' }}
                  >
                    Alterar Status
                  </Typography>
                  <Box 
                    display="flex" 
                    gap={isMobile ? 1.5 : 2} 
                    alignItems="center"
                    sx={{ 
                      flexDirection: isMobile ? 'column' : 'row',
                      alignItems: isMobile ? 'stretch' : 'center'
                    }}
                  >
                    <FormControl 
                      size="small" 
                      sx={{ 
                        minWidth: isMobile ? '100%' : 200,
                        width: isMobile ? '100%' : 'auto',
                        '& .MuiInputBase-root': {
                          height: isMobile ? 48 : 'auto'
                        }
                      }}
                    >
                      <InputLabel>Status</InputLabel>
                      <Select
                        value={selectedStatus}
                        label="Status"
                        onChange={(e) => handleStatusChange(e.target.value as StatusTicket)}
                      >
                        <MenuItem value="ABERTO">Aberto</MenuItem>
                        <MenuItem value="EM_ANDAMENTO">Em Andamento</MenuItem>
                        <MenuItem value="AGUARDANDO_CLIENTE">Aguardando Cliente</MenuItem>
                        <MenuItem value="RESOLVIDO">Resolvido</MenuItem>
                        <MenuItem value="FECHADO">Fechado</MenuItem>
                        <MenuItem value="CANCELADO">Cancelado</MenuItem>
                      </Select>
                    </FormControl>
                    <Button 
                      variant="outlined" 
                      size="small"
                      onClick={handleUpdateStatus}
                      disabled={statusUpdating}
                      sx={{ 
                        width: isMobile ? '100%' : 'auto',
                        height: isMobile ? 48 : 'auto',
                        mt: isMobile ? 1 : 0
                      }}
                    >
                      {statusUpdating ? <CircularProgress size={16} /> : 'Atualizar'}
                    </Button>
                  </Box>
                </Box>
              )}

              <Divider sx={{ my: isMobile ? 1.5 : 2 }} />

              <Typography 
                variant="h6" 
                mb={isMobile ? 1.5 : 2}
                sx={{ fontSize: isMobile ? '1.1rem' : '1.25rem' }}
              >
                Comentários
              </Typography>

              <List sx={{ 
                width: '100%',
                bgcolor: 'background.paper',
                borderRadius: 1,
                p: isMobile ? 1 : 0
              }}>
                {comments.map((comment) => (
                  <ListItem
                    key={comment.id}
                    alignItems="flex-start"
                    sx={{
                      px: isMobile ? 1.5 : 2,
                      py: isMobile ? 1.5 : 2,
                      borderBottom: '1px solid #f0f0f0',
                      '&:last-child': { borderBottom: 'none' }
                    }}
                  >
                    <Box sx={{ width: '100%' }}>
                      {/* Primeira linha: Avatar + Data/Hora + Chip Interno */}
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        <Avatar sx={{
                          width: isMobile ? 28 : 32,
                          height: isMobile ? 28 : 32,
                          flexShrink: 0
                        }}>
                          <UserIcon className="w-3 h-3" />
                        </Avatar>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem' }}
                        >
                          {new Date(comment.created_at).toLocaleString('pt-BR')}
                        </Typography>
                        {comment.is_internal && (
                          <Chip
                            label="Interno"
                            size="small"
                            color="warning"
                            sx={{ fontSize: '0.65rem', height: 18, ml: 'auto' }}
                          />
                        )}
                      </Box>

                      {/* Conteúdo do comentário - usando todo o espaço */}
                      <Typography
                        variant="body2"
                        sx={{
                          fontSize: isMobile ? '0.8rem' : '0.875rem',
                          color: 'text.primary',
                          lineHeight: 1.4
                        }}
                      >
                        {comment.comentario}
                      </Typography>
                    </Box>
                  </ListItem>
                ))}
              </List>

              <Divider sx={{ my: isMobile ? 1.5 : 2 }} />

              <Typography 
                variant="h6" 
                mb={isMobile ? 1.5 : 2}
                sx={{ fontSize: isMobile ? '1.1rem' : '1.25rem' }}
              >
                Adicionar Comentário
              </Typography>
              <Box display="flex" flexDirection="column" gap={isMobile ? 1.5 : 2}>
                <TextField
                  label="Comentário"
                  multiline
                  rows={isMobile ? 3 : 3}
                  fullWidth
                  value={newComment.comentario}
                  onChange={(e) => setNewComment({ ...newComment, comentario: e.target.value })}
                  sx={{
                    '& .MuiInputBase-root': {
                      fontSize: isMobile ? '0.875rem' : '1rem'
                    }
                  }}
                />
                <Box 
                  display="flex" 
                  alignItems="center" 
                  gap={isMobile ? 1.5 : 2}
                  sx={{ 
                    flexDirection: isMobile ? 'column' : 'row',
                    alignItems: isMobile ? 'flex-start' : 'center'
                  }}
                >
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={newComment.is_internal}
                        onChange={(e) => setNewComment({ ...newComment, is_internal: e.target.checked })}
                        sx={{ 
                          '& .MuiSvgIcon-root': {
                            fontSize: isMobile ? 20 : 24
                          }
                        }}
                      />
                    }
                    label="Comentário interno"
                    sx={{
                      '& .MuiFormControlLabel-label': {
                        fontSize: isMobile ? '0.875rem' : '1rem'
                      }
                    }}
                  />
                  <Button
                    variant="contained"
                    onClick={handleAddComment}
                    disabled={!newComment.comentario.trim()}
                    startIcon={<ChatBubbleLeftIcon className="w-4 h-4" />}
                    sx={{ 
                      width: isMobile ? '100%' : 'auto',
                      height: isMobile ? 48 : 'auto',
                      mt: isMobile ? 1 : 0,
                      fontSize: isMobile ? '0.875rem' : '0.875rem'
                    }}
                  >
                    Adicionar Comentário
                  </Button>
                </Box>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ 
          flexDirection: 'row', 
          gap: 1,
          p: isMobile ? 2 : 3,
          pt: isMobile ? 1 : 3,
          justifyContent: 'space-between'
        }}>
          {hasPermission('tickets_manage') && selectedTicket && (
            <Button 
              onClick={() => handleDeleteTicket(selectedTicket)} 
              color="error" 
              startIcon={<TrashIcon className="w-4 h-4" />}
              sx={{ minWidth: 'auto', px: 2 }}
            >
            </Button>
          )}
          <Button 
            onClick={() => setDetailDialogOpen(false)}
            sx={{ minWidth: 'auto', px: 2 }}
          >
            <XMarkIcon className="w-4 h-4" />
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar para mensagens */}
      <Snackbar open={!!error} autoHideDuration={6000} onClose={() => setError(null)}>
        <Alert onClose={() => setError(null)} severity="error">
          {error}
        </Alert>
      </Snackbar>

      <Snackbar open={!!success} autoHideDuration={6000} onClose={() => setSuccess(null)}>
        <Alert onClose={() => setSuccess(null)} severity="success">
          {success}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Tickets;