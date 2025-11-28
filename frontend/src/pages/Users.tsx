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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControlLabel,
  Switch,
  Alert,
  Chip,
  Tooltip,
  Stack,
  Select,
  MenuItem,
  FormControl,
  InputLabel
} from '@mui/material';
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  UserIcon,
  ShieldCheckIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/AuthContext';
import { useCompany } from '../contexts/CompanyContext';
import userService, { Usuario, UsuarioCreate, UsuarioUpdate, Role } from '../services/userService';

const Users: React.FC = () => {
  const { user: currentUser } = useAuth();
  const { activeCompany } = useCompany();
  const [users, setUsers] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingUser, setEditingUser] = useState<Usuario | null>(null);
  const [formData, setFormData] = useState<UsuarioCreate>({
    nome: '',
    email: '',
    password: '',
    is_superuser: false
  });

  const [rolesList, setRolesList] = useState<Role[]>([]);
  const [assignedRoles, setAssignedRoles] = useState<Role[]>([]);
  const [roleToAssign, setRoleToAssign] = useState<number | string>('');

  // Verificar permissões
  const canManageUsers = currentUser?.is_superuser ||
    (activeCompany && currentUser &&
     // Verificar se é admin da empresa selecionada (isso seria checado no backend)
     true); // Por enquanto, assumimos que se tem empresa selecionada, pode gerenciar

  useEffect(() => {
    if (activeCompany && canManageUsers) {
      loadUsers();
    } else {
      setLoading(false);
    }
  }, [activeCompany, canManageUsers]);

  const loadUsers = async () => {
    if (!activeCompany) return;

    try {
      setLoading(true);
      setError(null);
      const usersData = await userService.getUsersByEmpresa(activeCompany.id);
      setUsers(usersData);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao carregar usuários');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (user?: Usuario) => {
    if (user) {
      setEditingUser(user);
      setFormData({
        nome: user.full_name,
        email: user.email,
        password: '', // Não preencher senha na edição
        is_superuser: user.is_superuser
      });
      // carregar roles e roles atribuídas para este usuário
      loadRoles();
      loadAssignedRoles(user.id);
    } else {
      setEditingUser(null);
      setFormData({
        nome: '',
        email: '',
        password: '',
        is_superuser: false
      });
      // carregar roles disponíveis para atribuição
      loadRoles();
      setAssignedRoles([]);
    }
    setOpenDialog(true);
  };

  const loadRoles = async () => {
    try {
      const r = await userService.listRoles();
      // mostrar somente roles da company ativa (excluir roles globais)
      const filtered = (r || []).filter((role) => role.empresa_id === activeCompany?.id);
      setRolesList(filtered);
    } catch (err: any) {
      // ignorar erro leve
    }
  };

  const loadAssignedRoles = async (userId: number) => {
    try {
      const r = await userService.getUserRoles(userId);
      setAssignedRoles(r || []);
    } catch (err: any) {
      // ignorar erro leve
    }
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingUser(null);
    setFormData({
      nome: '',
      email: '',
      password: '',
      is_superuser: false
    });
  };

  const handleSubmit = async () => {
    if (!activeCompany) return;

    try {
      if (editingUser) {
        // Atualizar usuário existente
        const updateData: UsuarioUpdate = {
          nome: formData.nome,
          email: formData.email,
          is_superuser: formData.is_superuser
        };
        if (formData.password) {
          updateData.password = formData.password;
        }
        await userService.updateUser(editingUser.id, updateData);
        // atualizar roles caso tenha seleção
        if (roleToAssign && roleToAssign !== '') {
          await userService.assignRole(Number(roleToAssign), editingUser.id, activeCompany?.id);
          await loadAssignedRoles(editingUser.id);
          setRoleToAssign('');
        }
      } else {
        // Criar novo usuário
        const created = await userService.createUserForEmpresa(activeCompany.id, formData);
        if (roleToAssign && roleToAssign !== '') {
          await userService.assignRole(Number(roleToAssign), created.id, activeCompany?.id);
          setRoleToAssign('');
        }
      }
      await loadUsers();
      handleCloseDialog();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao salvar usuário');
    }
  };

  const handleDeleteUser = async (userId: number) => {
    if (!window.confirm('Tem certeza que deseja excluir este usuário?')) return;

    try {
      await userService.deleteUser(userId);
      await loadUsers();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao excluir usuário');
    }
  };

  if (!activeCompany) {
    return (
      <Box>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold', mb: 4 }}>
          Usuários
        </Typography>
        <Alert severity="info">
          Selecione uma empresa para gerenciar usuários.
        </Alert>
      </Box>
    );
  }

  if (!canManageUsers) {
    return (
      <Box>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold', mb: 4 }}>
          Usuários
        </Typography>
        <Alert severity="warning">
          Você não tem permissão para gerenciar usuários desta empresa.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold' }}>
          Usuários
        </Typography>
        <Button
          variant="contained"
          startIcon={<PlusIcon className="w-5 h-5" />}
          onClick={() => handleOpenDialog()}
          sx={{ py: 1.5 }}
        >
          Novo Usuário
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ width: '100%', overflow: 'hidden' }}>
        {loading ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <Typography>Carregando usuários...</Typography>
          </Box>
        ) : users.length === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <UserIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <Typography variant="h6" gutterBottom>
              Nenhum usuário encontrado
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Comece adicionando o primeiro usuário à empresa.
            </Typography>
            <Button
              variant="outlined"
              startIcon={<PlusIcon className="w-5 h-5" />}
              onClick={() => handleOpenDialog()}
            >
              Adicionar Usuário
            </Button>
          </Box>
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Nome</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Nível de Acesso</TableCell>
                  <TableCell align="right">Ações</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id} hover>
                    <TableCell>{user.full_name}</TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>
                      <Chip
                        label={user.is_active ? 'Ativo' : 'Inativo'}
                        color={user.is_active ? 'success' : 'error'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {user.is_superuser ? (
                        <Chip
                          icon={<ShieldCheckIcon className="w-4 h-4" />}
                          label="Superusuário"
                          color="primary"
                          size="small"
                        />
                      ) : (
                        <Chip
                          label="Usuário"
                          variant="outlined"
                          size="small"
                        />
                      )}
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="Editar">
                        <IconButton
                          onClick={() => handleOpenDialog(user)}
                          size="small"
                          color="primary"
                        >
                          <PencilIcon className="w-4 h-4" />
                        </IconButton>
                      </Tooltip>
                      {user.id !== currentUser?.id && (
                        <Tooltip title="Excluir">
                          <IconButton
                            onClick={() => handleDeleteUser(user.id)}
                            size="small"
                            color="error"
                          >
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

      {/* Dialog para criar/editar usuário */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingUser ? 'Editar Usuário' : 'Novo Usuário'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Nome Completo"
              value={formData.nome}
              onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Email"
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Senha"
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              fullWidth
              required={!editingUser}
              helperText={editingUser ? "Deixe em branco para manter a senha atual" : ""}
            />
            {currentUser?.is_superuser && (
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.is_superuser}
                    onChange={(e) => setFormData({ ...formData, is_superuser: e.target.checked })}
                  />
                }
                label="Superusuário"
              />
            )}
            {/* Roles */}
            <Box>
              <InputLabel sx={{ mb: 1 }}>Roles</InputLabel>
              <Stack direction="row" spacing={1} sx={{ mb: 1, flexWrap: 'wrap' }}>
                {assignedRoles.map((r) => (
                  <Chip
                    key={r.id}
                    label={r.name}
                    onDelete={async () => {
                      try {
                        await userService.unassignRole(r.id, editingUser?.id || 0);
                        if (editingUser) await loadAssignedRoles(editingUser.id);
                      } catch (err: any) {
                        setError(err.response?.data?.detail || 'Erro ao desatribuir role');
                      }
                    }}
                    color="primary"
                    size="small"
                  />
                ))}
              </Stack>
              <FormControl fullWidth>
                <InputLabel id="select-role-label">Atribuir role</InputLabel>
                <Select
                  labelId="select-role-label"
                  value={roleToAssign}
                  label="Atribuir role"
                  onChange={(e) => setRoleToAssign(e.target.value as number | '')}
                >
                  <MenuItem value="">(nenhum)</MenuItem>
                  {rolesList.map((r) => (
                    <MenuItem key={r.id} value={r.id}>{r.name}{r.description ? ` — ${r.description}` : ''}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog} startIcon={<XMarkIcon className="w-4 h-4" />}>
            Cancelar
          </Button>
          <Button
            onClick={handleSubmit}
            variant="contained"
            disabled={!formData.nome || !formData.email || (!editingUser && !formData.password)}
          >
            {editingUser ? 'Atualizar' : 'Criar'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Users;