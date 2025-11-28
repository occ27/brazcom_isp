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
import { useCompany } from '../contexts/CompanyContext';
import userService, { Role } from '../services/userService';

const RolesPage: React.FC = () => {
  const { activeCompany } = useCompany();
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [openCreate, setOpenCreate] = useState(false);
  const [newRoleName, setNewRoleName] = useState('');
  const [newRoleDesc, setNewRoleDesc] = useState('');

  const [openEdit, setOpenEdit] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [editRoleName, setEditRoleName] = useState('');
  const [editRoleDesc, setEditRoleDesc] = useState('');

  useEffect(() => {
    loadAll();
  }, [activeCompany]);

  const loadAll = async () => {
    if (!activeCompany) return;
    try {
      setLoading(true);
      setError(null);
      const rolesData = await userService.listRoles();
      // Mostrar somente roles da empresa ativa
      const filtered = (rolesData || []).filter((role) => role.empresa_id === activeCompany.id);
      setRoles(filtered);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao carregar roles');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRole = async () => {
    try {
      await userService.createRole({ name: newRoleName, description: newRoleDesc, empresa_id: activeCompany?.id });
      setOpenCreate(false);
      setNewRoleName('');
      setNewRoleDesc('');
      await loadAll();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao criar role');
    }
  };

  const handleOpenEdit = (role: Role) => {
    setEditingRole(role);
    setEditRoleName(role.name);
    setEditRoleDesc(role.description || '');
    setOpenEdit(true);
  };

  const handleCloseEdit = () => {
    setOpenEdit(false);
    setEditingRole(null);
    setEditRoleName('');
    setEditRoleDesc('');
  };

  const handleDeleteRole = async (roleId: number) => {
    if (!window.confirm('Tem certeza que deseja excluir esta role?')) return;
    try {
      await userService.deleteRole(roleId);
      await loadAll();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao excluir role');
    }
  };

  const handleEditRole = async () => {
    if (!editingRole) return;
    try {
      await userService.updateRole(editingRole.id, { name: editRoleName, description: editRoleDesc });
      setOpenEdit(false);
      setEditingRole(null);
      setEditRoleName('');
      setEditRoleDesc('');
      await loadAll();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao editar role');
    }
  };

  if (!activeCompany) {
    return (
      <Box>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold', mb: 4 }}>
          Roles
        </Typography>
        <Alert severity="info">Selecione uma empresa para gerenciar roles.</Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold' }}>
          Roles
        </Typography>
        <Button variant="contained" startIcon={<PlusIcon className="w-5 h-5" />} onClick={() => setOpenCreate(true)}>
          Novo Role
        </Button>
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
                {roles.map((r) => (
                  <TableRow key={r.id} hover>
                    <TableCell>{r.name}</TableCell>
                    <TableCell>{r.description}</TableCell>
                    <TableCell>
                      <Tooltip title="Editar">
                        <IconButton onClick={() => handleOpenEdit(r)} size="small" color="primary">
                          <PencilIcon className="w-4 h-4" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Excluir">
                        <IconButton onClick={() => handleDeleteRole(r.id)} size="small" color="error">
                          <TrashIcon className="w-4 h-4" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      {/* Create Role Dialog */}
      <Dialog open={openCreate} onClose={() => setOpenCreate(false)} fullWidth maxWidth="sm">
        <DialogTitle>Novo Role</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <TextField label="Nome" value={newRoleName} onChange={(e) => setNewRoleName(e.target.value)} fullWidth />
            <TextField label="Descrição" value={newRoleDesc} onChange={(e) => setNewRoleDesc(e.target.value)} fullWidth />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenCreate(false)}>Cancelar</Button>
          <Button variant="contained" onClick={handleCreateRole} disabled={!newRoleName}>Criar</Button>
        </DialogActions>
      </Dialog>

      {/* Edit Role Dialog */}
      <Dialog open={openEdit} onClose={handleCloseEdit} fullWidth maxWidth="sm">
        <DialogTitle>Editar Role</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <TextField label="Nome" value={editRoleName} onChange={(e) => setEditRoleName(e.target.value)} fullWidth />
            <TextField label="Descrição" value={editRoleDesc} onChange={(e) => setEditRoleDesc(e.target.value)} fullWidth />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseEdit}>Cancelar</Button>
          <Button variant="contained" onClick={handleEditRole} disabled={!editRoleName}>Salvar</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default RolesPage;
