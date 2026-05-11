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
  useMediaQuery,
  useTheme,
  Grid,
  CircularProgress as MuiCircularProgress,
  Tooltip
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
  ServerIcon
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
  });
  const [errors, setErrors] = useState<{ [key: string]: string }>({});
  const [saving, setSaving] = useState(false);
  const [provisioning, setProvisioning] = useState(false);
  const [provisionDialogOpen, setProvisionDialogOpen] = useState(false);
  const [provisionResult, setProvisionResult] = useState<{ success: boolean; steps: string[]; router_nome?: string } | null>(null);
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success' as 'success' | 'error'
  });

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
                <TableCell>Status</TableCell>
                <TableCell>Ações</TableCell>
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
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={router.is_active ? 'Ativo' : 'Inativo'}
                      size="small"
                      color={router.is_active ? 'success' : 'error'}
                    />
                  </TableCell>
                  <TableCell>
                    <Tooltip title={router.metodo_autenticacao_padrao === 'RADIUS' ? "Provisionar RADIUS" : "Configurar Suspensão"}>
                      <IconButton
                        size="small"
                        onClick={() => handleProvision(router)}
                        sx={{ color: router.metodo_autenticacao_padrao === 'RADIUS' ? 'primary.main' : '#f59e0b' }}
                      >
                        <BoltIcon />
                      </IconButton>
                    </Tooltip>
                    <IconButton
                      size="small"
                      onClick={() => navigate(`/routers/${router.id}/interfaces`)}
                      title="Gerenciar Interfaces"
                      color="primary"
                    >
                      <InterfaceIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleOpenDialog(router)}
                      title="Editar"
                    >
                      <PencilIcon className="w-4 h-4" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleDelete(router)}
                      title="Excluir"
                      color="error"
                    >
                      <TrashIcon className="w-4 h-4" />
                    </IconButton>
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

              {/* ── Seção de Autenticação ── */}
              <Grid item xs={12}>
                <Box sx={{ mt: 1, mb: 0.5, borderTop: '1px solid', borderColor: 'divider', pt: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Método de Autenticação de Clientes
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Método Padrão</InputLabel>
                  <Select
                    value={formData.metodo_autenticacao_padrao ?? ''}
                    onChange={(e) => handleInputChange('metodo_autenticacao_padrao', e.target.value || null)}
                    label="Método Padrão"
                  >
                    <MenuItem value=""><em>Não definido</em></MenuItem>
                    <MenuItem value="RADIUS">RADIUS (FreeRadius centralizado)</MenuItem>
                    <MenuItem value="PPPOE">PPPoE Local (secrets na RB)</MenuItem>
                    <MenuItem value="HOTSPOT">Hotspot Local</MenuItem>
                    <MenuItem value="IP_MAC">IP/MAC (sem autenticação PPP)</MenuItem>
                  </Select>
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