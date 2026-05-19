import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Typography,
  Box,
  Paper,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  TextField,
  Chip,
  Alert,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Menu,
  Divider,
  useMediaQuery,
  useTheme,
  Grid,
  CircularProgress as MuiCircularProgress,
  Tooltip,
  Checkbox,
  FormControlLabel,
  FormHelperText
} from '@mui/material';
import {
  Add as AddIcon,
  FlashOn as ProvisionIcon,
  Info as InfoIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon
} from '@mui/icons-material';
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  ServerIcon,
  EllipsisVerticalIcon
} from '@heroicons/react/24/outline';
import { SettingsEthernet as InterfaceIcon, Block as BlockIcon, Bolt as BoltIcon } from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { useCompany } from '../contexts/CompanyContext';
import { routerService, RouterCreate, RouterUpdate } from '../services/routerService';
import { stringifyError } from '../utils/error';
import { Router } from '../types';

const Routers: React.FC = () => {
  const { user } = useAuth();
  const { activeCompany } = useCompany();
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [routers, setRouters] = useState<Router[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editingRouter, setEditingRouter] = useState<Router | null>(null);
  const [formData, setFormData] = useState<RouterCreate>({
    nome: '',
    ip: '',
    porta: 8728,
    usuario: '',
    senha: '',
    tipo: 'mikrotik',
    metodo_autenticacao_padrao: null,
    radius_server_address: '',
    radius_secret: '',
    api_encoding: 'utf-8',
    metodos_autenticacao: ['IP_MAC', 'PPPOE', 'HOTSPOT', 'RADIUS'],
  });
  const [errors, setErrors] = useState<{ [key: string]: string }>({});
  const [saving, setSaving] = useState(false);
  const [provisioning, setProvisioning] = useState(false);
  const [provisionDialogOpen, setProvisionDialogOpen] = useState(false);
  const [provisionResult, setProvisionResult] = useState<{ success: boolean; steps: string[]; router_nome?: string } | null>(null);
  const [processingDelinquents, setProcessingDelinquents] = useState<{ [key: number]: boolean }>({});
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [activeMenuRouterId, setActiveMenuRouterId] = useState<number | null>(null);
  const [delinquentsDialogOpen, setDelinquentsDialogOpen] = useState(false);
  const [delinquentsResult, setDelinquentsResult] = useState<{
    success: boolean;
    router_nome: string;
    contracts_blocked: number;
    contracts_reactivated: number;
    blocked_details: string[];
    reactivated_details: string[];
    errors: string[];
  } | null>(null);

  const handleOpenMenu = (event: React.MouseEvent<HTMLElement>, routerId: number) => {
    setAnchorEl(event.currentTarget);
    setActiveMenuRouterId(routerId);
  };

  const handleCloseMenu = () => {
    setAnchorEl(null);
    setActiveMenuRouterId(null);
  };

  const snackbarState = useState({
    open: false,
    message: '',
    severity: 'success' as 'success' | 'error' | 'warning'
  });
  const snackbar = snackbarState[0];
  const setSnackbar = snackbarState[1];

  const loadRouters = async () => {
    try {
      setLoading(true);
      const data = await routerService.getAll();
      setRouters(data);
    } catch (error) {
      console.error('Erro ao carregar routers:', error);
      setSnackbar({
        open: true,
        message: 'Erro ao carregar routers: ' + stringifyError(error),
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  

  useEffect(() => {
    if (!activeCompany) {
      // Quando não há empresa selecionada, não tentamos carregar e removemos o loading
      setLoading(false);
      return;
    }
    loadRouters();
  }, [activeCompany]);

  // Verificar se há empresa ativa
  if (!activeCompany) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning">
          <Typography variant="h6">Empresa não selecionada</Typography>
          <Typography>
            Você precisa selecionar uma empresa ativa para gerenciar routers.
            Vá para as configurações ou selecione uma empresa no menu.
          </Typography>
        </Alert>
      </Box>
    );
  }

  const handleOpenDialog = (router?: Router) => {
    if (router) {
      setEditingRouter(router);
      setFormData({
        nome: router.nome,
        ip: router.ip,
        porta: router.porta,
        usuario: router.usuario,
        senha: '', // Senha não vem da API por segurança
        tipo: router.tipo,
        metodo_autenticacao_padrao: router.metodo_autenticacao_padrao ?? null,
        radius_server_address: router.radius_server_address ?? '',
        radius_secret: '',
        api_encoding: router.api_encoding ?? 'utf-8',
        metodos_autenticacao: router.metodos_autenticacao && router.metodos_autenticacao.length > 0
          ? router.metodos_autenticacao
          : ['IP_MAC', 'PPPOE', 'HOTSPOT', 'RADIUS'],
      });
    } else {
      setEditingRouter(null);
      setFormData({
        nome: '',
        ip: '',
        porta: 8728,
        usuario: '',
        senha: '',
        tipo: 'mikrotik',
        metodo_autenticacao_padrao: null,
        radius_server_address: '',
        radius_secret: '',
        api_encoding: 'utf-8',
        metodos_autenticacao: ['IP_MAC', 'PPPOE', 'HOTSPOT', 'RADIUS'],
      });
    }
    setErrors({});
    setOpen(true);
  };

  const handleCloseDialog = () => {
    setOpen(false);
    setEditingRouter(null);
    setFormData({
      nome: '',
      ip: '',
      porta: 8728,
      usuario: '',
      senha: '',
      tipo: 'mikrotik',
      metodo_autenticacao_padrao: null,
      radius_server_address: '',
      radius_secret: '',
      api_encoding: 'utf-8',
      metodos_autenticacao: ['IP_MAC', 'PPPOE', 'HOTSPOT', 'RADIUS'],
    });
    setErrors({});
  };

  const validateForm = () => {
    const newErrors: { [key: string]: string } = {};

    if (!formData.nome.trim()) {
      newErrors.nome = 'Nome é obrigatório';
    }
    if (!formData.ip.trim()) {
      newErrors.ip = 'IP é obrigatório';
    } else if (!/^(\d{1,3}\.){3}\d{1,3}$/.test(formData.ip)) {
      newErrors.ip = 'IP inválido';
    }
    if (!formData.usuario.trim()) {
      newErrors.usuario = 'Usuário é obrigatório';
    }
    // Senha obrigatória apenas na criação, não na edição
    if (!editingRouter && !formData.senha.trim()) {
      newErrors.senha = 'Senha é obrigatória';
    }
    if (!formData.metodos_autenticacao || formData.metodos_autenticacao.length === 0) {
      newErrors.metodos_autenticacao = 'Selecione pelo menos um método de autenticação';
    } else if (formData.metodo_autenticacao_padrao && !formData.metodos_autenticacao.includes(formData.metodo_autenticacao_padrao)) {
      newErrors.metodo_autenticacao_padrao = 'O método padrão deve estar entre os métodos selecionados';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validateForm()) return;

    try {
      setSaving(true);
      if (editingRouter) {
        await routerService.update(editingRouter.id, formData);
        setSnackbar({
          open: true,
          message: 'Router atualizado com sucesso!',
          severity: 'success'
        });
      } else {
        await routerService.create(formData);
        setSnackbar({
          open: true,
          message: 'Router criado com sucesso!',
          severity: 'success'
        });
      }
      handleCloseDialog();
      loadRouters();
    } catch (error) {
      console.error('Erro ao salvar router:', error);
      setSnackbar({
        open: true,
        message: 'Erro ao salvar router: ' + stringifyError(error),
        severity: 'error'
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (router: Router) => {
    if (!window.confirm(`Tem certeza que deseja excluir o router "${router.nome}"?`)) {
      return;
    }

    try {
      await routerService.delete(router.id);
      setSnackbar({
        open: true,
        message: 'Router excluído com sucesso!',
        severity: 'success'
      });
      loadRouters();
    } catch (error) {
      console.error('Erro ao excluir router:', error);
      setSnackbar({
        open: true,
        message: 'Erro ao excluir router: ' + stringifyError(error),
        severity: 'error'
      });
    }
  };

  const handleProvision = async (router: Router) => {
    const isRadius = router.metodo_autenticacao_padrao === 'RADIUS';
    
    if (isRadius) {
      if (!window.confirm(`Deseja provisionar AUTOMATICAMENTE as configurações RADIUS (PPP AAA, Incoming, Server) no roteador "${router.nome}"?`)) {
        return;
      }
    } else {
      if (!window.confirm(`Deseja configurar AUTOMATICAMENTE o sistema de suspensão (Proxy, NAT e Firewall) no roteador "${router.nome}"? Isso irá criar as regras necessárias para o redirecionamento dos clientes bloqueados.`)) {
        return;
      }
    }

    setProvisioning(true);
    setProvisionResult(null);
    setProvisionDialogOpen(true);

    try {
      if (isRadius) {
        const result = await routerService.provisionRadius(router.id);
        setProvisionResult(result);
        if (result.success) {
          setSnackbar({ open: true, message: 'Configuração RADIUS aplicada com sucesso!', severity: 'success' });
          loadRouters();
        } else {
          setSnackbar({ open: true, message: 'RADIUS configurado com alguns alertas.', severity: 'error' });
        }
      } else {
        const response = await routerService.setupSuspension(router.id);
        // Formata o resultado da suspensão para o mesmo padrão do Radius
        setProvisionResult({
          success: true,
          router_nome: router.nome,
          steps: response.details || ['✅ Regras de Firewall criadas', '✅ NAT de redirecionamento configurado', '✅ Web Proxy habilitado']
        });
        setSnackbar({ open: true, message: 'Sistema de suspensão configurado com sucesso!', severity: 'success' });
      }
    } catch (error: any) {
      console.error('Erro no provisionamento:', error);
      const msg = error?.response?.data?.detail || stringifyError(error);
      setProvisionResult({ success: false, steps: [`❌ Erro: ${msg}`] });
      setSnackbar({ open: true, message: 'Falha no provisionamento: ' + msg, severity: 'error' });
    } finally {
      setProvisioning(false);
    }
  };

  const handleProcessDelinquents = async (router: Router) => {
    if (!window.confirm(`Deseja executar o bloqueio/desbloqueio automático de inadimplentes conectados no roteador "${router.nome}" agora?`)) {
      return;
    }

    setProcessingDelinquents(prev => ({ ...prev, [router.id]: true }));

    try {
      const response = await routerService.processDelinquents(router.id);
      if (response.success) {
        setDelinquentsResult({
          success: true,
          router_nome: router.nome,
          contracts_blocked: response.contracts_blocked,
          contracts_reactivated: response.contracts_reactivated,
          blocked_details: response.blocked_details || [],
          reactivated_details: response.reactivated_details || [],
          errors: response.errors || []
        });
        setDelinquentsDialogOpen(true);

        const msg = `Processamento concluído! Suspensos: ${response.contracts_blocked} | Reativados: ${response.contracts_reactivated}`;
        setSnackbar({
          open: true,
          message: msg,
          severity: response.errors && response.errors.length > 0 ? 'warning' : 'success'
        });
      } else {
        setSnackbar({
          open: true,
          message: 'Falha ao processar inadimplentes.',
          severity: 'error'
        });
      }
    } catch (error: any) {
      console.error('Erro ao processar inadimplentes no roteador:', error);
      const msg = error?.response?.data?.detail || stringifyError(error);
      setSnackbar({
        open: true,
        message: 'Erro ao processar inadimplentes: ' + msg,
        severity: 'error'
      });
    } finally {
      setProcessingDelinquents(prev => ({ ...prev, [router.id]: false }));
    }
  };

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: ''
      }));
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <MuiCircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Routers
        </Typography>
        <Button
          variant="contained"
          startIcon={<PlusIcon className="w-5 h-5" />}
          onClick={() => handleOpenDialog()}
        >
          Novo Router
        </Button>
      </Box>

      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Nome</TableCell>
                <TableCell>IP</TableCell>
                <TableCell>Porta</TableCell>
                <TableCell>Tipo</TableCell>
                <TableCell>Autenticação</TableCell>
                <TableCell>Codificação</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Ações</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {routers.map((router) => (
                <TableRow key={router.id}>
                  <TableCell>{router.nome}</TableCell>
                  <TableCell>{router.ip}</TableCell>
                  <TableCell>{router.porta}</TableCell>
                  <TableCell>
                    <Chip
                      label={router.tipo}
                      size="small"
                      color={router.tipo === 'mikrotik' ? 'primary' : 'default'}
                    />
                  </TableCell>
                  <TableCell>
                    {(() => {
                      const metodos = router.metodos_autenticacao && router.metodos_autenticacao.length > 0
                        ? router.metodos_autenticacao
                        : ['IP_MAC', 'PPPOE', 'HOTSPOT', 'RADIUS'];

                      if (metodos.length === 1) {
                        const m = metodos[0];
                        return (
                          <Chip
                            label={m === 'IP_MAC' ? 'IP+MAC' : m}
                            size="small"
                            color={
                              m === 'RADIUS' ? 'success'
                              : m === 'PPPOE' ? 'info'
                              : m === 'HOTSPOT' ? 'warning'
                              : 'default'
                            }
                            variant="filled"
                          />
                        );
                      }

                      return (
                        <Box display="flex" flexDirection="column" gap={0.5}>
                          <Box display="flex" alignItems="center" gap={1}>
                            <Typography variant="caption" color="text.secondary">Padrão:</Typography>
                            <Chip
                              label={router.metodo_autenticacao_padrao ?? 'Não definido'}
                              size="small"
                              color={
                                router.metodo_autenticacao_padrao === 'RADIUS' ? 'success'
                                : router.metodo_autenticacao_padrao === 'PPPOE' ? 'info'
                                : router.metodo_autenticacao_padrao === 'HOTSPOT' ? 'warning'
                                : 'default'
                              }
                              variant={router.metodo_autenticacao_padrao ? 'filled' : 'outlined'}
                            />
                          </Box>
                          <Box display="flex" flexWrap="wrap" gap={0.5}>
                            {metodos.map((m) => (
                              <Chip
                                key={m}
                                label={m === 'IP_MAC' ? 'IP+MAC' : m}
                                size="small"
                                variant="outlined"
                                style={{ fontSize: '10px', height: '18px' }}
                              />
                            ))}
                          </Box>
                        </Box>
                      );
                    })()}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={router.api_encoding === 'latin1' ? 'LATIN1' : 'UTF-8'}
                      size="small"
                      color={router.api_encoding === 'latin1' ? 'secondary' : 'default'}
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={router.is_active ? 'Ativo' : 'Inativo'}
                      size="small"
                      color={router.is_active ? 'success' : 'error'}
                    />
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={(e) => handleOpenMenu(e, router.id)}
                    >
                      <EllipsisVerticalIcon className="w-5 h-5" />
                    </IconButton>
                    <Menu
                      anchorEl={anchorEl}
                      open={activeMenuRouterId === router.id}
                      onClose={handleCloseMenu}
                      transformOrigin={{ horizontal: 'right', vertical: 'top' }}
                      anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
                    >
                      <MenuItem onClick={() => { handleOpenDialog(router); handleCloseMenu(); }}>
                        <PencilIcon className="w-4 h-4 mr-2" />
                        Editar
                      </MenuItem>
                      
                      <MenuItem onClick={() => { navigate(`/routers/${router.id}/interfaces`); handleCloseMenu(); }}>
                        <InterfaceIcon className="w-4 h-4 mr-2" />
                        Gerenciar Interfaces
                      </MenuItem>

                      <MenuItem 
                        onClick={() => { handleProvision(router); handleCloseMenu(); }}
                        sx={{ color: router.metodo_autenticacao_padrao === 'RADIUS' ? 'primary.main' : '#f59e0b' }}
                      >
                        <BoltIcon className="w-4 h-4 mr-2" />
                        {router.metodo_autenticacao_padrao === 'RADIUS' ? "Provisionar RADIUS" : "Configurar Suspensão"}
                      </MenuItem>

                      <MenuItem 
                        onClick={() => { handleProcessDelinquents(router); handleCloseMenu(); }}
                        disabled={!!processingDelinquents[router.id]}
                        sx={{ color: 'error.main' }}
                      >
                        {processingDelinquents[router.id] ? (
                          <MuiCircularProgress size={16} color="error" className="mr-2" />
                        ) : (
                          <BlockIcon className="w-4 h-4 mr-2" />
                        )}
                        Processar Inadimplentes
                      </MenuItem>

                      <Divider />

                      <MenuItem onClick={() => { handleDelete(router); handleCloseMenu(); }} sx={{ color: 'error.main' }}>
                        <TrashIcon className="w-4 h-4 mr-2" />
                        Excluir
                      </MenuItem>
                    </Menu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        {routers.length === 0 && (
          <Box p={3} textAlign="center">
            <Typography color="textSecondary">
              Nenhum router cadastrado
            </Typography>
          </Box>
        )}
      </Paper>

      {/* Dialog para criar/editar router */}
      <Dialog open={open} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingRouter ? 'Editar Router' : 'Novo Router'}
        </DialogTitle>
        <DialogContent>
          <Box component="form" sx={{ mt: 2 }}>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Nome"
                  value={formData.nome}
                  onChange={(e) => handleInputChange('nome', e.target.value)}
                  error={!!errors.nome}
                  helperText={errors.nome}
                  required
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="IP"
                  value={formData.ip}
                  onChange={(e) => handleInputChange('ip', e.target.value)}
                  error={!!errors.ip}
                  helperText={errors.ip}
                  required
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Porta"
                  type="number"
                  value={formData.porta}
                  onChange={(e) => handleInputChange('porta', parseInt(e.target.value))}
                  error={!!errors.porta}
                  helperText={errors.porta}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth error={!!errors.tipo}>
                  <InputLabel>Tipo</InputLabel>
                  <Select
                    value={formData.tipo}
                    onChange={(e) => handleInputChange('tipo', e.target.value)}
                    label="Tipo"
                  >
                    <MenuItem value="mikrotik">MikroTik</MenuItem>
                    <MenuItem value="cisco">Cisco</MenuItem>
                    <MenuItem value="ubiquiti">Ubiquiti</MenuItem>
                    <MenuItem value="outro">Outro</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Usuário"
                  value={formData.usuario}
                  onChange={(e) => handleInputChange('usuario', e.target.value)}
                  error={!!errors.usuario}
                  helperText={errors.usuario}
                  required
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Senha"
                  type="password"
                  value={formData.senha}
                  onChange={(e) => handleInputChange('senha', e.target.value)}
                  error={!!errors.senha}
                  helperText={errors.senha || (editingRouter ? "Deixe vazio para manter a senha atual" : "")}
                  required={!editingRouter}
                />
              </Grid>

              {/* ── Configurações Adicionais ── */}
              <Grid item xs={12}>
                <Box sx={{ mt: 1, mb: 0.5, borderTop: '1px solid', borderColor: 'divider', pt: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Configurações de API e Autenticação
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Codificação da API</InputLabel>
                  <Select
                    value={formData.api_encoding ?? 'utf-8'}
                    onChange={(e) => handleInputChange('api_encoding', e.target.value)}
                    label="Codificação da API"
                  >
                    <MenuItem value="utf-8">UTF-8 (WebFig, Winbox 4, Padrão)</MenuItem>
                    <MenuItem value="latin1">LATIN1 / Windows-1252 (Winbox 3 Legado)</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12}>
                <FormControl component="fieldset" error={!!errors.metodos_autenticacao} fullWidth>
                  <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                    Métodos de Autenticação Habilitados neste Router
                  </Typography>
                  <Box display="flex" flexWrap="wrap" gap={2}>
                    {[
                      { value: 'IP_MAC', label: 'IP + MAC' },
                      { value: 'PPPOE', label: 'PPPoE Local' },
                      { value: 'HOTSPOT', label: 'Hotspot Local' },
                      { value: 'RADIUS', label: 'RADIUS (FreeRadius)' },
                    ].map((item) => {
                      const isChecked = formData.metodos_autenticacao?.includes(item.value) ?? false;
                      return (
                        <FormControlLabel
                          key={item.value}
                          control={
                            <Checkbox
                              checked={isChecked}
                              onChange={(e) => {
                                const checked = e.target.checked;
                                let newMethods = [...(formData.metodos_autenticacao || [])];
                                if (checked) {
                                  if (!newMethods.includes(item.value)) newMethods.push(item.value);
                                } else {
                                  newMethods = newMethods.filter(m => m !== item.value);
                                }
                                handleInputChange('metodos_autenticacao', newMethods);
                                
                                // Se o método desmarcado era o padrão, limpar o padrão
                                if (!checked && formData.metodo_autenticacao_padrao === item.value) {
                                  handleInputChange('metodo_autenticacao_padrao', null);
                                }
                              }}
                              color="primary"
                            />
                          }
                          label={item.label}
                        />
                      );
                    })}
                  </Box>
                  {errors.metodos_autenticacao && (
                    <FormHelperText>{errors.metodos_autenticacao}</FormHelperText>
                  )}
                </FormControl>
              </Grid>

              <Grid item xs={12} sm={6}>
                <FormControl fullWidth error={!!errors.metodo_autenticacao_padrao}>
                  <InputLabel>Método de Autenticação Padrão</InputLabel>
                  <Select
                    value={formData.metodo_autenticacao_padrao ?? ''}
                    onChange={(e) => handleInputChange('metodo_autenticacao_padrao', e.target.value || null)}
                    label="Método de Autenticação Padrão"
                  >
                    <MenuItem value=""><em>Não definido</em></MenuItem>
                    {(formData.metodos_autenticacao || []).includes('RADIUS') && (
                      <MenuItem value="RADIUS">RADIUS (FreeRadius centralizado)</MenuItem>
                    )}
                    {(formData.metodos_autenticacao || []).includes('PPPOE') && (
                      <MenuItem value="PPPOE">PPPoE Local (secrets na RB)</MenuItem>
                    )}
                    {(formData.metodos_autenticacao || []).includes('HOTSPOT') && (
                      <MenuItem value="HOTSPOT">Hotspot Local</MenuItem>
                    )}
                    {(formData.metodos_autenticacao || []).includes('IP_MAC') && (
                      <MenuItem value="IP_MAC">IP/MAC (sem autenticação PPP)</MenuItem>
                    )}
                  </Select>
                  {errors.metodo_autenticacao_padrao && (
                    <FormHelperText>{errors.metodo_autenticacao_padrao}</FormHelperText>
                  )}
                </FormControl>
              </Grid>
              {formData.metodo_autenticacao_padrao === 'RADIUS' && (
                <>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="IP do Servidor RADIUS"
                      value={formData.radius_server_address ?? ''}
                      onChange={(e) => handleInputChange('radius_server_address', e.target.value)}
                      placeholder="ex: 10.20.0.1"
                      helperText="Endereço IP do servidor FreeRadius que este roteador irá consultar"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Segredo RADIUS (opcional)"
                      type="password"
                      value={formData.radius_secret ?? ''}
                      onChange={(e) => handleInputChange('radius_secret', e.target.value)}
                      placeholder="Deixe vazio para usar o segredo do NAS cadastrado"
                      helperText="Usado ao provisionar automaticamente o roteador via API"
                    />
                  </Grid>
                </>
              )}
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancelar</Button>
          <Button
            onClick={handleSave}
            variant="contained"
            disabled={saving}
          >
            {saving ? <MuiCircularProgress size={20} /> : 'Salvar'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog resultado do provisionamento */}
      <Dialog open={provisionDialogOpen} onClose={() => !provisioning && setProvisionDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <ProvisionIcon color={provisionResult?.success ? 'success' : 'warning'} />
          Provisionamento de Roteador
        </DialogTitle>
        <DialogContent dividers>
          {provisioning ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 4, gap: 2 }}>
              <MuiCircularProgress />
              <Typography color="text.secondary">Conectando ao Mikrotik e aplicando configurações...</Typography>
            </Box>
          ) : provisionResult ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Alert severity={provisionResult.success ? 'success' : 'warning'} icon={<InfoIcon />}>
                {provisionResult.success
                  ? 'Configurações aplicadas com sucesso!'
                  : 'Ocorreram alguns erros durante o processo.'}
              </Alert>
              {provisionResult.router_nome && (
                <Typography variant="body2" color="text.secondary">
                  Router: <strong>{provisionResult.router_nome}</strong>
                </Typography>
              )}
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                {provisionResult.steps.map((step, i) => (
                  <Typography key={i} variant="body2" fontFamily="monospace" sx={{ py: 0.5, px: 1, bgcolor: 'grey.50', borderRadius: 1 }}>
                    {step}
                  </Typography>
                ))}
              </Box>
            </Box>
          ) : null}
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={() => setProvisionDialogOpen(false)} disabled={provisioning}>Fechar</Button>
        </DialogActions>
      </Dialog>

      {/* Dialog resultado do processamento de inadimplentes */}
      <Dialog open={delinquentsDialogOpen} onClose={() => setDelinquentsDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, fontWeight: 'bold' }}>
          <BlockIcon color="error" />
          Resumo do Processamento de Inadimplentes
        </DialogTitle>
        <DialogContent dividers>
          {delinquentsResult ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Alert severity={delinquentsResult.errors.length > 0 ? 'warning' : 'success'} icon={<CheckCircleIcon />}>
                {delinquentsResult.errors.length > 0 
                  ? 'Sincronização concluída com alguns alertas.' 
                  : 'Sincronização executada com sucesso absoluto!'}
              </Alert>

              <Typography variant="body2" color="text.secondary">
                Roteador: <strong>{delinquentsResult.router_nome}</strong>
              </Typography>

              {/* Seção Bloqueios */}
              <Box>
                <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 1, fontWeight: 'bold', mb: 1, color: 'error.main' }}>
                  🔴 Contratos Suspensos ({delinquentsResult.contracts_blocked})
                </Typography>
                {delinquentsResult.blocked_details.length > 0 ? (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, pl: 1 }}>
                    {delinquentsResult.blocked_details.map((detail, idx) => (
                      <Typography key={idx} variant="body2" fontFamily="monospace" sx={{ py: 0.3, px: 1, bgcolor: 'grey.50', borderRadius: 1 }}>
                        {detail}
                      </Typography>
                    ))}
                  </Box>
                ) : (
                  <Typography variant="body2" color="text.secondary" sx={{ pl: 1, fontStyle: 'italic' }}>
                    Nenhum novo bloqueio efetuado.
                  </Typography>
                )}
              </Box>

              {/* Seção Desbloqueios */}
              <Box>
                <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 1, fontWeight: 'bold', mb: 1, color: 'success.main' }}>
                  🟢 Contratos Reativados ({delinquentsResult.contracts_reactivated})
                </Typography>
                {delinquentsResult.reactivated_details.length > 0 ? (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, pl: 1 }}>
                    {delinquentsResult.reactivated_details.map((detail, idx) => (
                      <Typography key={idx} variant="body2" fontFamily="monospace" sx={{ py: 0.3, px: 1, bgcolor: 'grey.50', borderRadius: 1 }}>
                        {detail}
                      </Typography>
                    ))}
                  </Box>
                ) : (
                  <Typography variant="body2" color="text.secondary" sx={{ pl: 1, fontStyle: 'italic' }}>
                    Nenhum contrato reativado.
                  </Typography>
                )}
              </Box>

              {/* Seção Erros / Alertas */}
              {delinquentsResult.errors.length > 0 && (
                <Box>
                  <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 1, fontWeight: 'bold', mb: 1, color: 'warning.main' }}>
                    ⚠️ Alertas / Erros ({delinquentsResult.errors.length})
                  </Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, pl: 1 }}>
                    {delinquentsResult.errors.map((error, idx) => (
                      <Typography key={idx} variant="body2" fontFamily="monospace" sx={{ py: 0.5, px: 1, bgcolor: '#fffde7', border: '1px solid #fff59d', color: '#f57f17', borderRadius: 1 }}>
                        {error}
                      </Typography>
                    ))}
                  </Box>
                </Box>
              )}
            </Box>
          ) : null}
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={() => setDelinquentsDialogOpen(false)} variant="contained" color="primary">Fechar</Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
      >
        <Alert
          onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Routers;