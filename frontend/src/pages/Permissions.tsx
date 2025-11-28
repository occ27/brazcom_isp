import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  IconButton,
  Tooltip
} from '@mui/material';
import { PlusIcon, PencilIcon, TrashIcon } from '@heroicons/react/24/outline';
// No company-scoped permissions; global only
import userService, { Permission } from '../services/userService';
import { useAuth } from '../contexts/AuthContext';

const PermissionsPage: React.FC = () => {
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [openCreate, setOpenCreate] = useState(false);
  const [newPermissionName, setNewPermissionName] = useState('');
  const [newPermissionDesc, setNewPermissionDesc] = useState('');

  const [openEdit, setOpenEdit] = useState(false);
  const [editingPermission, setEditingPermission] = useState<Permission | null>(null);
  const [editPermissionName, setEditPermissionName] = useState('');
  const [editPermissionDesc, setEditPermissionDesc] = useState('');
  const { hasPermission, reloadPermissions } = useAuth();

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    try {
      setLoading(true);
      setError(null);
      const perms = await userService.listPermissions();
      setPermissions(perms || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao carregar permissões');
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePermission = async () => {
    try {
      await userService.createPermission({ name: newPermissionName, description: newPermissionDesc });
      setOpenCreate(false);
      setNewPermissionName('');
      setNewPermissionDesc('');
      await loadAll();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao criar permissão');
    }
  };

  const handleOpenEdit = (p: Permission) => {
    setEditingPermission(p);
    setEditPermissionName(p.name);
    setEditPermissionDesc(p.description || '');
    setOpenEdit(true);
  };

  const handleCloseEdit = () => {
    setEditingPermission(null);
    setEditPermissionName('');
    setEditPermissionDesc('');
    setOpenEdit(false);
  };

  const handleEditPermission = async () => {
    if (!editingPermission) return;
    try {
      await userService.updatePermission(editingPermission.id, { name: editPermissionName, description: editPermissionDesc });
      setOpenEdit(false);
      setEditingPermission(null);
      setEditPermissionName('');
      setEditPermissionDesc('');
      await loadAll();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao editar permissão');
    }
  };

  const handleDeletePermission = async (permissionId: number) => {
    if (!window.confirm('Tem certeza que deseja excluir esta permissão?')) return;
    try {
      await userService.deletePermission(permissionId);
      await loadAll();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao excluir permissão');
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold' }}>
          Permissões
        </Typography>
        {hasPermission('permission_manage') && (
          <Button variant="contained" startIcon={<PlusIcon className="w-5 h-5" />} onClick={() => setOpenCreate(true)}>
            Nova Permissão
          </Button>
        )}
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      <Paper>
        {loading ? (
          <Box sx={{ p: 4 }}>Carregando...</Box>
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Nome</TableCell>
                  <TableCell>Descrição</TableCell>
                  <TableCell>Ações</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {permissions.map((p) => (
                  <TableRow key={p.id} hover>
                    <TableCell>{p.name}</TableCell>
                    <TableCell>{p.description}</TableCell>
                    <TableCell>
                      {hasPermission('permission_manage') && (
                        <Tooltip title="Editar">
                          <IconButton onClick={() => handleOpenEdit(p)} size="small" color="primary">
                            <PencilIcon className="w-4 h-4" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {hasPermission('permission_manage') && (
                        <Tooltip title="Excluir">
                          <IconButton onClick={() => handleDeletePermission(p.id)} size="small" color="error">
                            <TrashIcon className="w-4 h-4" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      {/* Create Permission Dialog */}
      <Dialog open={openCreate} onClose={() => setOpenCreate(false)} fullWidth maxWidth="sm">
        <DialogTitle>Nova Permissão</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <TextField label="Nome" value={newPermissionName} onChange={(e) => setNewPermissionName(e.target.value)} fullWidth />
            <TextField label="Descrição" value={newPermissionDesc} onChange={(e) => setNewPermissionDesc(e.target.value)} fullWidth />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenCreate(false)}>Cancelar</Button>
          <Button variant="contained" onClick={handleCreatePermission} disabled={!newPermissionName}>Criar</Button>
        </DialogActions>
      </Dialog>

      {/* Edit Permission Dialog */}
      <Dialog open={openEdit} onClose={handleCloseEdit} fullWidth maxWidth="sm">
        <DialogTitle>Editar Permissão</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <TextField label="Nome" value={editPermissionName} onChange={(e) => setEditPermissionName(e.target.value)} fullWidth />
            <TextField label="Descrição" value={editPermissionDesc} onChange={(e) => setEditPermissionDesc(e.target.value)} fullWidth />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseEdit}>Cancelar</Button>
          <Button variant="contained" onClick={handleEditPermission} disabled={!editPermissionName}>Salvar</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PermissionsPage;
