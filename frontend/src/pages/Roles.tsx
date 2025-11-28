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
  ,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  ListItemText,
  OutlinedInput
} from '@mui/material';
import { PlusIcon, PencilIcon, TrashIcon } from '@heroicons/react/24/outline';
import { useCompany } from '../contexts/CompanyContext';
import userService, { Role, Permission } from '../services/userService';
import { useAuth } from '../contexts/AuthContext';

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
  const [allPermissions, setAllPermissions] = useState<Permission[]>([]);
  const [rolePermBefore, setRolePermBefore] = useState<number[]>([]);
  const [selectedPermissionIds, setSelectedPermissionIds] = useState<number[]>([]);
  const { hasPermission, reloadPermissions } = useAuth();

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
    // carregar permissões e marcar as já atribuídas
    (async () => {
      try {
        const [perms, rolePerms] = await Promise.all([
          userService.listPermissions(),
          userService.listRolePermissions(role.id)
        ]);
        setAllPermissions(perms || []);
        const ids = (rolePerms || []).map((p) => p.id);
        setRolePermBefore(ids);
        setSelectedPermissionIds(ids);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Erro ao carregar permissões');
      } finally {
        setOpenEdit(true);
      }
    })();
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
      // Atualizar permissões: calcular diferenças
      const before = new Set(rolePermBefore || []);
      const after = new Set(selectedPermissionIds || []);
      const toAdd = Array.from(after).filter((id) => !before.has(id));
      const toRemove = Array.from(before).filter((id) => !after.has(id));
      await Promise.all([
        ...toAdd.map((pid) => userService.addPermissionToRole(editingRole.id, pid)),
        ...toRemove.map((pid) => userService.removePermissionFromRole(editingRole.id, pid)),
      ]);
      // reload permissions in auth context (in case current user's perms changed)
      try { await reloadPermissions(); } catch (e) { /* ignore */ }
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
        {hasPermission('role_manage') && (
          <Button variant="contained" startIcon={<PlusIcon className="w-5 h-5" />} onClick={() => setOpenCreate(true)}>
            Novo Role
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
                {roles.map((r) => (
                  <TableRow key={r.id} hover>
                    <TableCell>{r.name}</TableCell>
                    <TableCell>{r.description}</TableCell>
                    <TableCell>
                      {hasPermission('role_manage') && (
                        <Tooltip title="Editar">
                          <IconButton onClick={() => handleOpenEdit(r)} size="small" color="primary">
                            <PencilIcon className="w-4 h-4" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {hasPermission('role_manage') && (
                        <Tooltip title="Excluir">
                          <IconButton onClick={() => handleDeleteRole(r.id)} size="small" color="error">
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
            <FormControl fullWidth>
              <InputLabel id="role-perms-label">Permissões</InputLabel>
              <Select
                labelId="role-perms-label"
                multiple
                value={selectedPermissionIds}
                onChange={(e) => setSelectedPermissionIds(typeof e.target.value === 'string' ? e.target.value.split(',').map(Number) : e.target.value as number[])}
                input={<OutlinedInput label="Permissões" />}
                renderValue={(selected) => {
                  const ids = selected as number[];
                  return allPermissions.filter(p => ids.includes(p.id)).map(p => p.name).join(', ');
                }}
              >
                {allPermissions.map((p) => (
                  <MenuItem key={p.id} value={p.id}>
                    <Checkbox checked={selectedPermissionIds.indexOf(p.id) > -1} />
                    <ListItemText primary={p.name} secondary={p.description} />
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
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
