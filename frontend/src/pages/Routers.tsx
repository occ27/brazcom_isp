import React, { useState, useEffect } from 'react';
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
  CircularProgress,
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
  Grid
} from '@mui/material';
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  ServerIcon
} from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/AuthContext';
import { useCompany } from '../contexts/CompanyContext';
import { routerService, RouterCreate, RouterUpdate } from '../services/routerService';
import { stringifyError } from '../utils/error';
import { Router } from '../types';

const Routers: React.FC = () => {
  const { user } = useAuth();
  const { activeCompany } = useCompany();
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
    tipo: 'mikrotik'
  });
  const [errors, setErrors] = useState<{ [key: string]: string }>({});
  const [saving, setSaving] = useState(false);
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
        tipo: router.tipo
      });
    } else {
      setEditingRouter(null);
      setFormData({
        nome: '',
        ip: '',
        porta: 8728,
        usuario: '',
        senha: '',
        tipo: 'mikrotik'
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
      tipo: 'mikrotik'
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
        <CircularProgress />
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
                      label={router.is_active ? 'Ativo' : 'Inativo'}
                      size="small"
                      color={router.is_active ? 'success' : 'error'}
                    />
                  </TableCell>
                  <TableCell>
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
            {saving ? <CircularProgress size={20} /> : 'Salvar'}
          </Button>
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