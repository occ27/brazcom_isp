import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Paper, Typography, Button, IconButton, TextField,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Dialog, DialogTitle, DialogContent, DialogActions,
  Chip, Alert, CircularProgress, Tooltip, InputAdornment
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Router as RouterIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Lock as LockIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon
} from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';

// ─── Tipos ──────────────────────────────────────────────────────────────────

interface NASClient {
  id: number;
  nasname: string;
  shortname: string;
  type: string;
  ports: number | null;
  secret: string;
  server: string | null;
  community: string | null;
  description: string;
}

interface NASFormData {
  nasname: string;
  secret: string;
  shortname: string;
  nas_type: string;
  description: string;
  ports: string;
}

const EMPTY_FORM: NASFormData = {
  nasname: '',
  secret: '',
  shortname: '',
  nas_type: 'other',
  description: '',
  ports: '',
};

// ─── Serviço ─────────────────────────────────────────────────────────────────

const nasService = {
  list: () => api.get('/radius/nas/').then(r => r.data as NASClient[]),
  create: (data: NASFormData) =>
    api.post('/radius/nas/', null, {
      params: {
        nasname: data.nasname,
        secret: data.secret,
        shortname: data.shortname || data.nasname,
        nas_type: data.nas_type,
        description: data.description,
        ...(data.ports ? { ports: parseInt(data.ports) } : {}),
      },
    }).then(r => r.data),
  update: (id: number, data: Partial<NASFormData>) =>
    api.put(`/radius/nas/${id}`, null, {
      params: {
        ...(data.nasname ? { nasname: data.nasname } : {}),
        ...(data.secret ? { secret: data.secret } : {}),
        ...(data.shortname ? { shortname: data.shortname } : {}),
        ...(data.nas_type ? { nas_type: data.nas_type } : {}),
        ...(data.description !== undefined ? { description: data.description } : {}),
        ...(data.ports ? { ports: parseInt(data.ports) } : {}),
      },
    }).then(r => r.data as NASClient),
  delete: (id: number) => api.delete(`/radius/nas/${id}`).then(r => r.data),
};

// ─── Componente ──────────────────────────────────────────────────────────────

const RadiusNASPage: React.FC = () => {
  const { user } = useAuth();
  const { enqueueSnackbar } = useSnackbar();

  const [clients, setClients] = useState<NASClient[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingClient, setEditingClient] = useState<NASClient | null>(null);
  const [deletingClient, setDeletingClient] = useState<NASClient | null>(null);
  const [form, setForm] = useState<NASFormData>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [showSecrets, setShowSecrets] = useState<Record<number, boolean>>({});

  // Apenas super_admin pode acessar
  if (!user?.is_superuser) {
    return (
      <Box sx={{ p: 4 }}>
        <Alert severity="error" icon={<LockIcon />}>
          Acesso restrito. Apenas o super administrador pode gerenciar clientes NAS.
        </Alert>
      </Box>
    );
  }

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await nasService.list();
      setClients(data);
    } catch {
      enqueueSnackbar('Erro ao carregar clientes NAS', { variant: 'error' });
    } finally {
      setLoading(false);
    }
  }, [enqueueSnackbar]);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => {
    setEditingClient(null);
    setForm(EMPTY_FORM);
    setDialogOpen(true);
  };

  const openEdit = (client: NASClient) => {
    setEditingClient(client);
    setForm({
      nasname: client.nasname,
      secret: client.secret,
      shortname: client.shortname || '',
      nas_type: client.type || 'other',
      description: client.description || '',
      ports: client.ports ? String(client.ports) : '',
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.nasname.trim()) {
      enqueueSnackbar('IP/hostname do roteador é obrigatório', { variant: 'warning' });
      return;
    }
    if (!form.secret.trim()) {
      enqueueSnackbar('Segredo RADIUS é obrigatório', { variant: 'warning' });
      return;
    }
    setSaving(true);
    try {
      if (editingClient) {
        await nasService.update(editingClient.id, form);
        enqueueSnackbar(`NAS "${form.nasname}" atualizado com sucesso`, { variant: 'success' });
      } else {
        await nasService.create(form);
        enqueueSnackbar(`NAS "${form.nasname}" registrado no FreeRadius`, { variant: 'success' });
      }
      setDialogOpen(false);
      load();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Erro ao salvar cliente NAS';
      enqueueSnackbar(msg, { variant: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const openDelete = (client: NASClient) => {
    setDeletingClient(client);
    setDeleteDialogOpen(true);
  };

  const handleDelete = async () => {
    if (!deletingClient) return;
    try {
      await nasService.delete(deletingClient.id);
      enqueueSnackbar(`NAS "${deletingClient.nasname}" removido`, { variant: 'success' });
      setDeleteDialogOpen(false);
      load();
    } catch {
      enqueueSnackbar('Erro ao remover cliente NAS', { variant: 'error' });
    }
  };

  const toggleSecret = (id: number) =>
    setShowSecrets(prev => ({ ...prev, [id]: !prev[id] }));

  return (
    <Box>
      {/* Cabeçalho */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <RouterIcon sx={{ fontSize: 32, color: 'primary.main' }} />
          <Box>
            <Typography variant="h5" fontWeight={700}>
              Clientes RADIUS NAS
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Roteadores/Mikrotik autorizados a usar o FreeRadius · Substitui o <code>clients.conf</code>
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Recarregar">
            <IconButton onClick={load} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={openCreate}
            id="btn-add-nas"
          >
            Adicionar NAS
          </Button>
        </Box>
      </Box>

      {/* Aviso informativo */}
      <Alert
        severity="info"
        icon={<CheckCircleIcon />}
        sx={{ mb: 3, borderRadius: 2 }}
      >
        <Typography variant="body2">
          <strong>Sem acesso root.</strong> Alterações aqui são gravadas diretamente na tabela{' '}
          <code>nas</code> do MySQL e lidas pelo FreeRadius em tempo real (
          <code>read_clients = yes</code> já configurado).
        </Typography>
      </Alert>

      {/* Tabela */}
      <Paper elevation={2} sx={{ borderRadius: 2, overflow: 'hidden' }}>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: 'grey.50' }}>
                <TableCell sx={{ fontWeight: 700 }}>ID</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>IP / Hostname (NAS)</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Nome Curto</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Segredo RADIUS</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Tipo</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Descrição</TableCell>
                <TableCell align="center" sx={{ fontWeight: 700 }}>Ações</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 6 }}>
                    <CircularProgress size={32} />
                  </TableCell>
                </TableRow>
              ) : clients.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 6 }}>
                    <RouterIcon sx={{ fontSize: 48, color: 'grey.300', mb: 1 }} />
                    <Typography color="text.secondary">
                      Nenhum NAS registrado. Adicione o primeiro roteador.
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                clients.map(client => (
                  <TableRow key={client.id} hover>
                    <TableCell>
                      <Chip label={client.id} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight={600} fontFamily="monospace">
                        {client.nasname}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {client.shortname || '—'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Typography variant="body2" fontFamily="monospace" sx={{ minWidth: 100 }}>
                          {showSecrets[client.id] ? client.secret : '••••••••••'}
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={() => toggleSecret(client.id)}
                          title={showSecrets[client.id] ? 'Ocultar segredo' : 'Mostrar segredo'}
                        >
                          {showSecrets[client.id]
                            ? <VisibilityOffIcon fontSize="small" />
                            : <VisibilityIcon fontSize="small" />}
                        </IconButton>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={client.type || 'other'}
                        size="small"
                        color={client.type === 'other' ? 'default' : 'primary'}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 200 }}>
                        {client.description || '—'}
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      <Tooltip title="Editar">
                        <IconButton size="small" onClick={() => openEdit(client)} id={`btn-edit-nas-${client.id}`}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Remover">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => openDelete(client)}
                          id={`btn-delete-nas-${client.id}`}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Dialog criar/editar */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <RouterIcon color="primary" />
          {editingClient ? 'Editar Cliente NAS' : 'Adicionar Cliente NAS'}
        </DialogTitle>
        <DialogContent dividers>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, pt: 1 }}>

            <TextField
              id="nas-nasname"
              label="IP / Hostname do Roteador *"
              value={form.nasname}
              onChange={e => setForm(f => ({ ...f, nasname: e.target.value }))}
              placeholder="ex: 192.168.100.1"
              helperText="IP ou hostname do Mikrotik que enviará autenticações ao FreeRadius"
              fullWidth
              InputProps={{
                startAdornment: <InputAdornment position="start"><RouterIcon fontSize="small" /></InputAdornment>
              }}
            />

            <TextField
              id="nas-secret"
              label="Segredo RADIUS *"
              value={form.secret}
              onChange={e => setForm(f => ({ ...f, secret: e.target.value }))}
              placeholder="ex: testing123"
              helperText="Deve coincidir com o segredo configurado na Mikrotik (/radius add secret=...)"
              fullWidth
              InputProps={{
                startAdornment: <InputAdornment position="start"><LockIcon fontSize="small" /></InputAdornment>
              }}
            />

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                id="nas-shortname"
                label="Nome Curto"
                value={form.shortname}
                onChange={e => setForm(f => ({ ...f, shortname: e.target.value }))}
                placeholder="ex: rb-sede"
                helperText="Identificação interna"
                fullWidth
              />
              <TextField
                id="nas-type"
                label="Tipo NAS"
                value={form.nas_type}
                onChange={e => setForm(f => ({ ...f, nas_type: e.target.value }))}
                helperText='Use "other" para Mikrotik'
                fullWidth
              />
            </Box>

            <TextField
              id="nas-description"
              label="Descrição"
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="ex: Mikrotik Torre Sede — PPPoE principal"
              fullWidth
              multiline
              rows={2}
            />

          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={() => setDialogOpen(false)} disabled={saving}>Cancelar</Button>
          <Button
            id="btn-save-nas"
            variant="contained"
            onClick={handleSave}
            disabled={saving}
            startIcon={saving ? <CircularProgress size={16} /> : undefined}
          >
            {saving ? 'Salvando...' : editingClient ? 'Salvar Alterações' : 'Registrar NAS'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog confirmar exclusão */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'error.main' }}>
          <WarningIcon color="error" /> Confirmar Remoção
        </DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            <Typography variant="body2">
              O roteador <strong>{deletingClient?.nasname}</strong> ({deletingClient?.shortname}) será
              removido do FreeRadius. Ele <strong>não poderá mais autenticar usuários</strong> PPPoE.
            </Typography>
          </Alert>
          <Typography variant="body2" color="text.secondary">
            Esta ação é imediata. Para reverter, cadastre o NAS novamente.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancelar</Button>
          <Button
            id="btn-confirm-delete-nas"
            variant="contained"
            color="error"
            onClick={handleDelete}
          >
            Remover NAS
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default RadiusNASPage;
