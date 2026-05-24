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
import contratoService, { Contrato } from '../services/contratoService';
import { stringifyError } from '../utils/error';
import { Ticket, TicketComment, StatusTicket, PrioridadeTicket, CategoriaTicket } from '../types';
import ContractAutocomplete from '../components/ContractAutocomplete';
import { useAuth } from '../contexts/AuthContext';
import userService, { Usuario as UserInterface } from '../services/userService';
import FileUploader from '../components/FileUploader';
import { API_BASE_URL } from '../services/api';

const Tickets: React.FC = () => {
  const { activeCompany } = useCompany();
  const { user, hasPermission } = useAuth();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const isTecnico = !user?.is_superuser && !hasPermission('clients_manage');

  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>(isTecnico ? 'ATIVOS' : '');
  const [prioridadeFilter, setPrioridadeFilter] = useState<PrioridadeTicket | ''>('');
  const [categoriaFilter, setCategoriaFilter] = useState<CategoriaTicket | ''>('');

  // Paginação
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [totalTickets, setTotalTickets] = useState(0);

  // Dialogs
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [comments, setComments] = useState<TicketComment[]>([]);

  // Form validation errors
  const [formErrors, setFormErrors] = useState({
    titulo: false,
    descricao: false,
    contrato: false
  });

  const [tecnicos, setTecnicos] = useState<UserInterface[]>([]);

  // Form states
  const [newTicket, setNewTicket] = useState({
    titulo: '',
    descricao: '',
    prioridade: 'NORMAL' as PrioridadeTicket,
    categoria: 'SUPORTE' as CategoriaTicket,
    contrato: null as Contrato | null,
    atribuido_para_id: ''
  });

  const [newComment, setNewComment] = useState({
    comentario: '',
    is_internal: false
  });

  // Status update states
  const [statusUpdating, setStatusUpdating] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState<StatusTicket | ''>('');

  // Ticket closure states
  const [closureDialogOpen, setClosureDialogOpen] = useState(false);
  const [closureForm, setClosureForm] = useState({
    foto_onu_serial: '',
    foto_equipamentos: '',
    foto_velocidade: '',
    foto_cto: '',
    splitter_cto: '',
    material_utilizado: '',
    problema_encontrado: '',
    resolucao: ''
  });

  const loadTickets = useCallback(async () => {
    if (!activeCompany) return;

    try {
      setLoading(true);
      const data = await ticketService.listTickets(
        page * rowsPerPage,
        rowsPerPage,
        statusFilter === 'ATIVOS' ? 'ABERTO,EM_ANDAMENTO,AGUARDANDO_CLIENTE' : (statusFilter || undefined),
        prioridadeFilter || undefined,
        categoriaFilter || undefined,
        undefined, // cliente_id
        undefined, // atribuido_para_id
        searchTerm || undefined
      );
      setTickets(data.data);
      setTotalTickets(data.total);
    } catch (err) {
      setError(stringifyError(err));
    } finally {
      setLoading(false);
    }
  }, [activeCompany, page, rowsPerPage, statusFilter, prioridadeFilter, categoriaFilter, searchTerm]);

  useEffect(() => {
    if (isTecnico) {
      setStatusFilter('ATIVOS');
    }
  }, [isTecnico]);

  const loadTecnicos = useCallback(async () => {
    if (!activeCompany) return;
    try {
      const data = await userService.getUsersByEmpresa(activeCompany.id, 'technical');
      setTecnicos(data);
    } catch (err) {
      console.error('Erro ao buscar técnicos:', err);
    }
  }, [activeCompany]);

  useEffect(() => {
    if (activeCompany) {
      loadTecnicos();
    }
  }, [activeCompany, loadTecnicos]);

  useEffect(() => {
    loadTickets();
  }, [loadTickets]);

  const handleCreateTicket = async () => {
    // Reset previous errors
    setFormErrors({ titulo: false, descricao: false, contrato: false });

    // Validação
    const errors = { titulo: false, descricao: false, contrato: false };
    let hasError = false;

    if (!newTicket.titulo.trim()) {
      errors.titulo = true;
      hasError = true;
    }
    if (!newTicket.descricao.trim()) {
      errors.descricao = true;
      hasError = true;
    }
    if (!newTicket.contrato) {
      errors.contrato = true;
      hasError = true;
    }

    if (hasError) {
      setFormErrors(errors);
      setError('Por favor, preencha todos os campos obrigatórios');
      return;
    }

    try {
      const ticketData = {
        titulo: newTicket.titulo,
        descricao: newTicket.descricao,
        prioridade: newTicket.prioridade,
        categoria: newTicket.categoria,
        cliente_id: newTicket.contrato!.cliente_id,
        contrato_id: newTicket.contrato!.id,
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
        contrato: null,
        atribuido_para_id: ''
      });
      setFormErrors({ titulo: false, descricao: false, contrato: false });
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

  const handlePhotoUpload = async (field: 'foto_onu_serial' | 'foto_equipamentos' | 'foto_velocidade' | 'foto_cto', file: File | null) => {
    if (!selectedTicket) return;
    if (!file) {
      setClosureForm(prev => ({ ...prev, [field]: '' }));
      return;
    }

    try {
      const response = await ticketService.uploadPhoto(selectedTicket.id, file);
      setClosureForm(prev => ({ ...prev, [field]: response.file_path }));
    } catch (err: any) {
      setError('Erro ao enviar imagem: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleSaveClosure = async () => {
    if (!selectedTicket || !selectedStatus) return;

    const {
      foto_onu_serial,
      foto_equipamentos,
      foto_velocidade,
      foto_cto,
      splitter_cto,
      material_utilizado,
      problema_encontrado,
      resolucao
    } = closureForm;

    if (
      !foto_onu_serial.trim() ||
      !foto_equipamentos.trim() ||
      !foto_velocidade.trim() ||
      !foto_cto.trim() ||
      !splitter_cto.trim() ||
      !material_utilizado.trim() ||
      !problema_encontrado.trim() ||
      !resolucao.trim()
    ) {
      setError('Todos os campos de encerramento são obrigatórios para fechar o chamado.');
      return;
    }

    setStatusUpdating(true);
    try {
      const updated = await ticketService.updateTicket(selectedTicket.id, {
        status: selectedStatus,
        foto_onu_serial,
        foto_equipamentos,
        foto_velocidade,
        foto_cto,
        splitter_cto,
        material_utilizado,
        problema_encontrado,
        resolucao
      });
      setSuccess('Chamado finalizado com sucesso!');
      setSelectedTicket(updated);
      setClosureDialogOpen(false);
      loadTickets();
      setSelectedStatus('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao fechar o chamado');
    } finally {
      setStatusUpdating(false);
    }
  };

  const handleUpdateStatus = async () => {
    if (!selectedTicket || !selectedStatus || selectedStatus === selectedTicket.status) {
      return;
    }

    if (selectedStatus === 'RESOLVIDO' || selectedStatus === 'FECHADO') {
      setClosureForm({
        foto_onu_serial: selectedTicket.foto_onu_serial || '',
        foto_equipamentos: selectedTicket.foto_equipamentos || '',
        foto_velocidade: selectedTicket.foto_velocidade || '',
        foto_cto: selectedTicket.foto_cto || '',
        splitter_cto: selectedTicket.splitter_cto || '',
        material_utilizado: selectedTicket.material_utilizado || '',
        problema_encontrado: selectedTicket.problema_encontrado || '',
        resolucao: selectedTicket.resolucao || ''
      });
      setClosureDialogOpen(true);
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
      {!isTecnico && (
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
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <MenuItem value="">Todos</MenuItem>
                  <MenuItem value="ATIVOS">Ativos (Aberto, Em Andamento, Aguardando)</MenuItem>
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
      )}

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
                    {ticket.contrato_numero && ` (Contrato: #${ticket.contrato_numero})`}
                    {ticket.contrato_endereco && (
                      <span style={{ display: 'block', fontSize: '0.75rem', marginTop: '2px', color: '#666' }}>
                        <strong>Endereço:</strong> {ticket.contrato_endereco}
                      </span>
                    )}
                    <span style={{ display: 'block', fontSize: '0.75rem', marginTop: '4px', color: '#666' }}>
                      <strong>Atribuído a:</strong> {ticket.atribuido_para_nome || 'Não atribuído'}
                    </span>
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
                    <TableCell>Atribuído a</TableCell>
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
                      <TableCell>
                        <Box>
                          <Typography variant="body2" fontWeight="medium">
                            {ticket.cliente_nome || 'N/A'}
                          </Typography>
                          {ticket.contrato_numero && (
                            <Typography variant="caption" color="text.secondary" display="block">
                              Contrato: #{ticket.contrato_numero}
                            </Typography>
                          )}
                          {ticket.contrato_endereco && (
                            <Typography 
                              variant="caption" 
                              color="text.secondary" 
                              display="block" 
                              sx={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                              title={ticket.contrato_endereco}
                            >
                              {ticket.contrato_endereco}
                            </Typography>
                          )}
                        </Box>
                      </TableCell>
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
                      <TableCell>{ticket.atribuido_para_nome || 'Não atribuído'}</TableCell>
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
          </>
        )}
        <TablePagination
          component="div"
          count={totalTickets}
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
            width: isMobile ? '100%' : '100%',
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
              <ContractAutocomplete
                value={newTicket.contrato}
                onChange={(contrato) => setNewTicket({ ...newTicket, contrato })}
                label="Contrato do Cliente"
                placeholder="Busque por cliente, CPF/CNPJ, contrato..."
                required={true}
                error={formErrors.contrato}
                helperText={formErrors.contrato ? "A seleção de um contrato é obrigatória" : ""}
              />
            </Box>
            <FormControl 
              fullWidth
              sx={{
                '& .MuiInputBase-root': {
                  height: isMobile ? 56 : 'auto'
                }
              }}
            >
              <InputLabel>Atribuir Técnico</InputLabel>
              <Select
                value={newTicket.atribuido_para_id}
                label="Atribuir Técnico"
                onChange={(e) => setNewTicket({ ...newTicket, atribuido_para_id: e.target.value })}
              >
                <MenuItem value=""><em>Nenhum (Sem atribuição)</em></MenuItem>
                {tecnicos.map((tech) => (
                  <MenuItem key={tech.id} value={tech.id.toString()}>
                    {tech.nome || tech.full_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
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
        maxWidth={false} 
        fullWidth
        fullScreen={isMobile}
        sx={{
          '& .MuiDialog-paper': {
            margin: isMobile ? 0 : 2, // Margem reduzida (16px) em desktops para aproveitar mais espaço lateral
            width: isMobile ? '100%' : 'calc(100% - 32px)',
            maxWidth: '1400px',
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

              {/* Informações de Encerramento (se resolvido ou fechado) */}
              {['RESOLVIDO', 'FECHADO'].includes(selectedTicket.status) && (
                <Box sx={{ mt: 2, mb: 3, p: 2, border: '1px solid #e0e0e0', borderRadius: 2, bgcolor: '#f9f9f9' }}>
                  <Typography variant="subtitle1" mb={2} color="primary.main" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CheckCircleIcon className="w-5 h-5 text-green-600" />
                    Detalhes do Encerramento do Chamado
                  </Typography>
                  
                  <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2, mb: 3 }}>
                    <Box>
                      <Typography variant="caption" color="text.secondary">Splitter Utilizado</Typography>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>{selectedTicket.splitter_cto || 'N/A'}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">Problema Encontrado</Typography>
                      <Typography variant="body2" style={{ whiteSpace: 'pre-line' }}>{selectedTicket.problema_encontrado || 'N/A'}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">Material Utilizado</Typography>
                      <Typography variant="body2" style={{ whiteSpace: 'pre-line' }}>{selectedTicket.material_utilizado || 'N/A'}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">Solução / Resolução</Typography>
                      <Typography variant="body2" style={{ whiteSpace: 'pre-line' }}>{selectedTicket.resolucao || 'N/A'}</Typography>
                    </Box>
                  </Box>

                  <Typography variant="subtitle2" color="text.secondary" mb={1}>Fotos do Encerramento</Typography>
                  <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', md: '1fr 1fr 1fr 1fr' }, gap: 2 }}>
                    {[
                      { label: 'Serial ONU/Roteador', path: selectedTicket.foto_onu_serial },
                      { label: 'Equipamentos Instalados', path: selectedTicket.foto_equipamentos },
                      { label: 'Teste de Velocidade', path: selectedTicket.foto_velocidade },
                      { label: 'CTO Utilizada', path: selectedTicket.foto_cto },
                    ].map((photo, i) => (
                      <Box key={i} sx={{ border: '1px solid #e0e0e0', borderRadius: 1, p: 1, textAlign: 'center', bgcolor: '#fff' }}>
                        <Typography variant="caption" color="text.secondary" display="block" noWrap mb={1} sx={{ fontSize: '0.7rem' }}>
                          {photo.label}
                        </Typography>
                        {photo.path ? (
                          <a href={`${API_BASE_URL}${photo.path}`} target="_blank" rel="noopener noreferrer">
                            <img
                              src={`${API_BASE_URL}${photo.path}`}
                              alt={photo.label}
                              style={{ width: '100%', height: 100, objectFit: 'contain', cursor: 'pointer' }}
                            />
                          </a>
                        ) : (
                          <Typography variant="caption" color="error" display="block">Sem foto</Typography>
                        )}
                      </Box>
                    ))}
                  </Box>
                </Box>
              )}

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
                    flex: '1 1 100%'
                  }}
                >
                  <strong>Cliente:</strong> {selectedTicket.cliente_nome || 'N/A'}
                  {selectedTicket.contrato_numero && ` (Contrato: #${selectedTicket.contrato_numero})`}
                </Typography>
                {selectedTicket.contrato_endereco && (
                  <Typography 
                    variant="body2"
                    sx={{ 
                      fontSize: isMobile ? '0.75rem' : '0.875rem',
                      flex: '1 1 100%',
                      mt: -0.5,
                      color: 'text.secondary'
                    }}
                  >
                    <strong>Endereço de Instalação:</strong> {selectedTicket.contrato_endereco}
                  </Typography>
                )}
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
                <Typography 
                  variant="body2"
                  sx={{ 
                    fontSize: isMobile ? '0.75rem' : '0.875rem',
                    flex: isMobile ? '1 1 45%' : 'none'
                  }}
                >
                  <strong>Atribuído a:</strong> {selectedTicket.atribuido_para_nome || 'Nenhum'}
                </Typography>
              </Box>

              {/* Seção de alteração de status e atribuição */}
              {hasPermission('tickets_manage') && (selectedTicket && (!['RESOLVIDO', 'FECHADO', 'CANCELADO'].includes(selectedTicket.status) || user?.is_superuser || user?.is_company_admin)) && (
                <Box sx={{ 
                  mb: isMobile ? 2 : 3, 
                  p: isMobile ? 1.5 : 2, 
                  border: '1px solid #e0e0e0', 
                  borderRadius: 1 
                }}>
                  <Box display="flex" gap={2} sx={{ flexDirection: isMobile ? 'column' : 'row' }}>
                    <Box sx={{ flex: 1 }}>
                      <Typography 
                        variant="subtitle2" 
                        mb={1}
                        color="text.secondary"
                      >
                        Alterar Status
                      </Typography>
                      <Box 
                        display="flex" 
                        gap={1} 
                        alignItems="center"
                      >
                        <FormControl 
                          size="small" 
                          fullWidth
                          sx={{
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
                          sx={{ height: isMobile ? 48 : 40 }}
                        >
                          {statusUpdating ? <CircularProgress size={16} /> : 'Atualizar'}
                        </Button>
                      </Box>
                    </Box>

                    <Box sx={{ flex: 1 }}>
                      <Typography 
                        variant="subtitle2" 
                        mb={1}
                        color="text.secondary"
                      >
                        Atribuir Técnico
                      </Typography>
                      <FormControl 
                        size="small" 
                        fullWidth
                        sx={{
                          '& .MuiInputBase-root': {
                            height: isMobile ? 48 : 'auto'
                          }
                        }}
                      >
                        <InputLabel>Técnico</InputLabel>
                        <Select
                          value={selectedTicket.atribuido_para_id || ''}
                          label="Técnico"
                          onChange={async (e) => {
                            const val = e.target.value;
                            const techId = val ? parseInt(val as string) : null;
                            try {
                              const updated = await ticketService.updateTicket(selectedTicket.id, {
                                atribuido_para_id: techId
                              });
                              setSelectedTicket(updated);
                              setSuccess('Técnico atribuído com sucesso!');
                              loadTickets();
                            } catch (err) {
                              setError('Erro ao atribuir técnico');
                            }
                          }}
                        >
                          <MenuItem value=""><em>Nenhum (Sem atribuição)</em></MenuItem>
                          {tecnicos.map((tech) => (
                            <MenuItem key={tech.id} value={tech.id}>
                              {tech.nome || tech.full_name}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    </Box>
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
          {(user?.is_superuser || user?.is_company_admin) && selectedTicket && (
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

      <Dialog 
        open={closureDialogOpen} 
        onClose={() => setClosureDialogOpen(false)} 
        maxWidth={false} 
        fullWidth
        fullScreen={isMobile}
        sx={{
          '& .MuiDialog-paper': {
            margin: isMobile ? 0 : 2, // Margem reduzida (16px) em desktops para aproveitar mais espaço lateral
            width: isMobile ? '100%' : 'calc(100% - 32px)',
            maxWidth: '1400px',
            height: isMobile ? '100%' : 'auto'
          }
        }}
      >
        <DialogTitle sx={{ pb: 1, fontSize: '1.25rem', fontWeight: 600 }}>
          Encerramento do Chamado #{selectedTicket?.id}
        </DialogTitle>
        <DialogContent sx={{ p: isMobile ? 2 : 3, overflowY: 'auto' }}>
          <Typography variant="body2" color="text.secondary" mb={3}>
            Para resolver ou fechar este chamado, é obrigatório anexar as fotos solicitadas e preencher todos os detalhes técnicos abaixo.
          </Typography>

          {selectedTicket && (
            <Paper variant="outlined" sx={{ p: 2, mb: 3, bgcolor: '#f8fafc', borderColor: '#e2e8f0' }}>
              <Typography variant="subtitle2" color="text.secondary" sx={{ fontWeight: 600, mb: 1 }}>
                Informações do Cliente & Contrato
              </Typography>
              <Box display="flex" flexDirection="column" gap={0.5}>
                <Typography variant="body2">
                  <strong>Cliente:</strong> {selectedTicket.cliente_nome || 'N/A'}
                </Typography>
                {selectedTicket.contrato_numero && (
                  <Typography variant="body2">
                    <strong>Contrato:</strong> #{selectedTicket.contrato_numero}
                  </Typography>
                )}
                {selectedTicket.contrato_endereco && (
                  <Typography variant="body2">
                    <strong>Endereço de Instalação:</strong> {selectedTicket.contrato_endereco}
                  </Typography>
                )}
              </Box>
            </Paper>
          )}

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {/* Seção de Fotos */}
            <Typography variant="subtitle2" sx={{ fontWeight: 600, borderBottom: '1px solid #eee', pb: 1 }}>
              Fotos Obrigatórias
            </Typography>
            
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <FileUploader
                  label="1. Foto do Serial Number ONU/Roteador *"
                  accept="image/*"
                  maxSize={10}
                  currentFile={closureForm.foto_onu_serial}
                  onFileSelect={(file) => handlePhotoUpload('foto_onu_serial', file)}
                  placeholder="Selecione a foto do serial number"
                />
              </Paper>
              
              <Paper variant="outlined" sx={{ p: 2 }}>
                <FileUploader
                  label="2. Foto dos Equipamentos Instalados *"
                  accept="image/*"
                  maxSize={10}
                  currentFile={closureForm.foto_equipamentos}
                  onFileSelect={(file) => handlePhotoUpload('foto_equipamentos', file)}
                  placeholder="Selecione a foto dos equipamentos"
                />
              </Paper>

              <Paper variant="outlined" sx={{ p: 2 }}>
                <FileUploader
                  label="3. Foto do Teste de Velocidade *"
                  accept="image/*"
                  maxSize={10}
                  currentFile={closureForm.foto_velocidade}
                  onFileSelect={(file) => handlePhotoUpload('foto_velocidade', file)}
                  placeholder="Selecione a foto do teste de velocidade"
                />
              </Paper>

              <Paper variant="outlined" sx={{ p: 2 }}>
                <FileUploader
                  label="4. Foto da CTO Utilizada *"
                  accept="image/*"
                  maxSize={10}
                  currentFile={closureForm.foto_cto}
                  onFileSelect={(file) => handlePhotoUpload('foto_cto', file)}
                  placeholder="Selecione a foto da CTO"
                />
              </Paper>
            </Box>

            {/* Seção de Informações Técnicas */}
            <Typography variant="subtitle2" sx={{ fontWeight: 600, borderBottom: '1px solid #eee', pb: 1, mt: 1 }}>
              Informações Técnicas & Detalhes
            </Typography>

            <FormControl fullWidth size="small">
              <InputLabel>Splitter Utilizado na CTO *</InputLabel>
              <Select
                value={closureForm.splitter_cto}
                label="Splitter Utilizado na CTO *"
                onChange={(e) => setClosureForm(prev => ({ ...prev, splitter_cto: e.target.value }))}
              >
                <MenuItem value="1/2">Splitter 1/2</MenuItem>
                <MenuItem value="1/4">Splitter 1/4</MenuItem>
                <MenuItem value="1/8">Splitter 1/8</MenuItem>
                <MenuItem value="1/16">Splitter 1/16</MenuItem>
                <MenuItem value="Outro">Outro</MenuItem>
              </Select>
            </FormControl>

            <TextField
              label="Material Utilizado *"
              fullWidth
              multiline
              rows={2}
              placeholder="Ex: 20 metros de cabo drop, 2 conectores Fast, 1 ONU"
              value={closureForm.material_utilizado}
              onChange={(e) => setClosureForm(prev => ({ ...prev, material_utilizado: e.target.value }))}
            />

            <TextField
              label="Problema Encontrado *"
              fullWidth
              multiline
              rows={2}
              placeholder="Descreva o problema identificado pelo técnico no local..."
              value={closureForm.problema_encontrado}
              onChange={(e) => setClosureForm(prev => ({ ...prev, problema_encontrado: e.target.value }))}
            />

            <TextField
              label="Como foi Solucionado (Resolução) *"
              fullWidth
              multiline
              rows={2}
              placeholder="Descreva os procedimentos realizados para resolver o chamado..."
              value={closureForm.resolucao}
              onChange={(e) => setClosureForm(prev => ({ ...prev, resolucao: e.target.value }))}
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: isMobile ? 2 : 3, justifyContent: 'space-between' }}>
          <Button 
            onClick={() => setClosureDialogOpen(false)}
            variant="outlined"
            disabled={statusUpdating}
          >
            Cancelar
          </Button>
          <Button 
            onClick={handleSaveClosure} 
            variant="contained"
            disabled={statusUpdating}
            startIcon={statusUpdating ? <CircularProgress size={16} /> : <CheckCircleIcon className="w-4 h-4" />}
          >
            {statusUpdating ? 'Salvando...' : 'Finalizar Chamado'}
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