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
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Sistema de Suporte - Tickets
        </Typography>
        {hasPermission('tickets_manage') && (
          <Button
            variant="contained"
            startIcon={<PlusIcon className="w-5 h-5" />}
            onClick={() => setCreateDialogOpen(true)}
          >
            Novo Ticket
          </Button>
        )}
      </Box>

      {/* Filtros */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box display="flex" gap={2} flexWrap="wrap" alignItems="center">
          <TextField
            label="Buscar"
            variant="outlined"
            size="small"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: <MagnifyingGlassIcon className="w-4 h-4 mr-2" />,
            }}
            sx={{ minWidth: 200 }}
          />

          <FormControl size="small" sx={{ minWidth: 120 }}>
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

          <FormControl size="small" sx={{ minWidth: 120 }}>
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

          <FormControl size="small" sx={{ minWidth: 120 }}>
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

          <Button
            variant="outlined"
            onClick={() => {
              setSearchTerm('');
              setStatusFilter('');
              setPrioridadeFilter('');
              setCategoriaFilter('');
            }}
            startIcon={<XMarkIcon className="w-4 h-4" />}
          >
            Limpar
          </Button>
        </Box>
      </Paper>

      {/* Tabela de Tickets */}
      <Paper>
        {loading ? (
          <Box display="flex" justifyContent="center" p={4}>
            <CircularProgress />
          </Box>
        ) : (
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
              labelRowsPerPage="Linhas por página"
            />
          </>
        )}
      </Paper>

      {/* Dialog para criar ticket */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Criar Novo Ticket</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Título"
              fullWidth
              value={newTicket.titulo}
              onChange={(e) => setNewTicket({ ...newTicket, titulo: e.target.value })}
              required
              error={formErrors.titulo}
              helperText={formErrors.titulo ? "O título é obrigatório" : ""}
            />
            <TextField
              label="Descrição"
              fullWidth
              multiline
              rows={4}
              value={newTicket.descricao}
              onChange={(e) => setNewTicket({ ...newTicket, descricao: e.target.value })}
              required
              error={formErrors.descricao}
              helperText={formErrors.descricao ? "A descrição é obrigatória" : ""}
            />
            <Box display="flex" gap={2}>
              <FormControl fullWidth>
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
              <FormControl fullWidth>
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
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancelar</Button>
          <Button onClick={handleCreateTicket} variant="contained">
            Criar Ticket
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog para ver detalhes do ticket */}
      <Dialog open={detailDialogOpen} onClose={() => setDetailDialogOpen(false)} maxWidth="lg" fullWidth>
        <DialogTitle>
          Ticket #{selectedTicket?.id} - {selectedTicket?.titulo}
        </DialogTitle>
        <DialogContent>
          {selectedTicket && (
            <Box sx={{ pt: 2 }}>
              <Box display="flex" gap={2} mb={2}>
                <Chip
                  icon={getStatusIcon(selectedTicket.status)}
                  label={selectedTicket.status.replace('_', ' ')}
                  color={getStatusColor(selectedTicket.status)}
                />
                <Chip
                  label={selectedTicket.prioridade}
                  color={getPrioridadeColor(selectedTicket.prioridade)}
                />
                <Chip label={selectedTicket.categoria} />
              </Box>

              <Typography variant="body1" mb={2}>
                <strong>Descrição:</strong> {selectedTicket.descricao}
              </Typography>

              <Box display="flex" gap={4} mb={2}>
                <Typography variant="body2">
                  <strong>Cliente:</strong> {selectedTicket.cliente_nome || 'N/A'}
                </Typography>
                <Typography variant="body2">
                  <strong>Criado por:</strong> {selectedTicket.criado_por_nome}
                </Typography>
                <Typography variant="body2">
                  <strong>Criado em:</strong> {new Date(selectedTicket.created_at).toLocaleString('pt-BR')}
                </Typography>
              </Box>

              <Divider sx={{ my: 2 }} />

              <Typography variant="h6" mb={2}>Comentários</Typography>

              <List>
                {comments.map((comment) => (
                  <ListItem key={comment.id} alignItems="flex-start">
                    <ListItemAvatar>
                      <Avatar>
                        <UserIcon className="w-4 h-4" />
                      </Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="subtitle2">
                            Comentário #{comment.id}
                          </Typography>
                          {comment.is_internal && (
                            <Chip label="Interno" size="small" color="warning" />
                          )}
                        </Box>
                      }
                      secondary={
                        <>
                          <Typography variant="body2" color="text.secondary">
                            {new Date(comment.created_at).toLocaleString('pt-BR')}
                          </Typography>
                          {comment.comentario}
                        </>
                      }
                    />
                  </ListItem>
                ))}
              </List>

              <Divider sx={{ my: 2 }} />

              <Typography variant="h6" mb={2}>Adicionar Comentário</Typography>
              <Box display="flex" flexDirection="column" gap={2}>
                <TextField
                  label="Comentário"
                  multiline
                  rows={3}
                  fullWidth
                  value={newComment.comentario}
                  onChange={(e) => setNewComment({ ...newComment, comentario: e.target.value })}
                />
                <Box display="flex" alignItems="center" gap={2}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={newComment.is_internal}
                        onChange={(e) => setNewComment({ ...newComment, is_internal: e.target.checked })}
                      />
                    }
                    label="Comentário interno"
                  />
                  <Button
                    variant="contained"
                    onClick={handleAddComment}
                    disabled={!newComment.comentario.trim()}
                    startIcon={<ChatBubbleLeftIcon className="w-4 h-4" />}
                  >
                    Adicionar Comentário
                  </Button>
                </Box>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          {hasPermission('tickets_manage') && selectedTicket && (
            <Button 
              onClick={() => handleDeleteTicket(selectedTicket)} 
              color="error" 
              startIcon={<TrashIcon className="w-4 h-4" />}
            >
              Excluir Ticket
            </Button>
          )}
          <Button onClick={() => setDetailDialogOpen(false)}>Fechar</Button>
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