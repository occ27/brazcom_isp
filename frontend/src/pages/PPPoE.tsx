import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  TextField,
  CircularProgress,
  Snackbar,
  Alert,
  useMediaQuery,
  useTheme,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Card,
  CardContent,
  Divider,
  Pagination,
  SelectChangeEvent,
  InputAdornment,
  Autocomplete,
  Tabs,
  Tab,
  FormControlLabel,
  Checkbox,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Router as RouterIcon,
  SettingsEthernet as InterfaceIcon,
  Pool as PoolIcon
} from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import { useAuth } from '../contexts/AuthContext';
import { useCompany } from '../contexts/CompanyContext';
import {
  networkService,
  IPPoolCreate,
  IPPoolUpdate,
  PPPProfileCreate,
  PPPProfileUpdate,
  PPPoEServerCreate,
  PPPoEServerUpdate
} from '../services/networkService';
import { routerService } from '../services/routerService';
import {
  IPPool,
  PPPProfile,
  PPPoEServer,
  Router,
  RouterInterface
} from '../types';

const PPPoE: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { enqueueSnackbar } = useSnackbar();
  const { user } = useAuth();
  const { activeCompany } = useCompany();

  // Estados para dados
  const [ipPools, setIpPools] = useState<IPPool[]>([]);
  const [pppProfiles, setPppProfiles] = useState<PPPProfile[]>([]);
  const [pppoeServers, setPppoeServers] = useState<PPPoEServer[]>([]);
  const [routers, setRouters] = useState<Router[]>([]);
  const [interfaces, setInterfaces] = useState<RouterInterface[]>([]);

  // Estados para UI
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Estados para modais
  const [ipPoolDialog, setIpPoolDialog] = useState(false);
  const [pppProfileDialog, setPppProfileDialog] = useState(false);
  const [pppoeServerDialog, setPppoeServerDialog] = useState(false);
  const [editingIpPool, setEditingIpPool] = useState<IPPool | null>(null);
  const [editingPppProfile, setEditingPppProfile] = useState<PPPProfile | null>(null);
  const [editingPppoeServer, setEditingPppoeServer] = useState<PPPoEServer | null>(null);

  // Estados para formulários
  const [ipPoolForm, setIpPoolForm] = useState<IPPoolCreate>({
    nome: '',
    ranges: '',
    comentario: '',
    is_active: true
  });

  const [pppProfileForm, setPppProfileForm] = useState<PPPProfileCreate>({
    nome: '',
    local_address: '',
    remote_address: '',
    rate_limit: '',
    comentario: '',
    is_active: true
  });

  const [pppoeServerForm, setPppoeServerForm] = useState<PPPoEServerCreate>({
    service_name: '',
    interface_id: 0,
    default_profile_id: 0,
    comentario: '',
    is_active: true
  });

  // Carregar dados
  const loadData = useCallback(async () => {
    if (!activeCompany) return;

    setLoading(true);
    try {
      const [poolsResp, profilesResp, serversResp, routersResp] = await Promise.all([
        networkService.getIPPools(),
        networkService.getPPPProfiles(),
        networkService.getPPPoEServers(),
        routerService.getByCompany(activeCompany.id)
      ]);

      setIpPools(poolsResp || []);
      setPppProfiles(profilesResp || []);
      setPppoeServers(serversResp || []);
      setRouters(routersResp || []);
    } catch (error) {
      console.error('Erro ao carregar dados PPPoE:', error);
      enqueueSnackbar('Erro ao carregar dados PPPoE', { variant: 'error' });
    } finally {
      setLoading(false);
    }
  }, [activeCompany, enqueueSnackbar]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Carregar interfaces quando router muda no modal PPPoE Server
  useEffect(() => {
    const loadInterfaces = async () => {
      if (pppoeServerForm.router_id) {
        try {
          const interfacesResp = await networkService.getRouterInterfaces(pppoeServerForm.router_id);
          setInterfaces(interfacesResp || []);
        } catch (error) {
          console.error('Erro ao carregar interfaces:', error);
          setInterfaces([]);
        }
      } else {
        setInterfaces([]);
      }
    };

    loadInterfaces();
  }, [pppoeServerForm.router_id]);

  // Handlers para IP Pools
  const handleCreateIpPool = async () => {
    try {
      await networkService.createIPPool(ipPoolForm);
      enqueueSnackbar('Pool de IP criado com sucesso!', { variant: 'success' });
      setIpPoolDialog(false);
      resetIpPoolForm();
      loadData();
    } catch (error) {
      console.error('Erro ao criar pool de IP:', error);
      enqueueSnackbar('Erro ao criar pool de IP', { variant: 'error' });
    }
  };

  const handleUpdateIpPool = async () => {
    if (!editingIpPool) return;
    try {
      await networkService.updateIPPool(editingIpPool.id, ipPoolForm);
      enqueueSnackbar('Pool de IP atualizado com sucesso!', { variant: 'success' });
      setIpPoolDialog(false);
      setEditingIpPool(null);
      resetIpPoolForm();
      loadData();
    } catch (error) {
      console.error('Erro ao atualizar pool de IP:', error);
      enqueueSnackbar('Erro ao atualizar pool de IP', { variant: 'error' });
    }
  };

  const handleDeleteIpPool = async (pool: IPPool) => {
    if (!window.confirm(`Deseja realmente excluir o pool "${pool.nome}"?`)) return;
    try {
      await networkService.deleteIPPool(pool.id);
      enqueueSnackbar('Pool de IP excluído com sucesso!', { variant: 'success' });
      loadData();
    } catch (error) {
      console.error('Erro ao excluir pool de IP:', error);
      enqueueSnackbar('Erro ao excluir pool de IP', { variant: 'error' });
    }
  };

  // Handlers para PPP Profiles
  const handleCreatePppProfile = async () => {
    try {
      await networkService.createPPPProfile(pppProfileForm);
      enqueueSnackbar('Perfil PPP criado com sucesso!', { variant: 'success' });
      setPppProfileDialog(false);
      resetPppProfileForm();
      loadData();
    } catch (error) {
      console.error('Erro ao criar perfil PPP:', error);
      enqueueSnackbar('Erro ao criar perfil PPP', { variant: 'error' });
    }
  };

  const handleUpdatePppProfile = async () => {
    if (!editingPppProfile) return;
    try {
      await networkService.updatePPPProfile(editingPppProfile.id, pppProfileForm);
      enqueueSnackbar('Perfil PPP atualizado com sucesso!', { variant: 'success' });
      setPppProfileDialog(false);
      setEditingPppProfile(null);
      resetPppProfileForm();
      loadData();
    } catch (error) {
      console.error('Erro ao atualizar perfil PPP:', error);
      enqueueSnackbar('Erro ao atualizar perfil PPP', { variant: 'error' });
    }
  };

  const handleDeletePppProfile = async (profile: PPPProfile) => {
    if (!window.confirm(`Deseja realmente excluir o perfil "${profile.nome}"?`)) return;
    try {
      await networkService.deletePPPProfile(profile.id);
      enqueueSnackbar('Perfil PPP excluído com sucesso!', { variant: 'success' });
      loadData();
    } catch (error) {
      console.error('Erro ao excluir perfil PPP:', error);
      enqueueSnackbar('Erro ao excluir perfil PPP', { variant: 'error' });
    }
  };

  // Handlers para PPPoE Servers
  const handleCreatePppoeServer = async () => {
    try {
      await networkService.createPPPoEServer(pppoeServerForm);
      enqueueSnackbar('Servidor PPPoE criado com sucesso!', { variant: 'success' });
      setPppoeServerDialog(false);
      resetPppoeServerForm();
      loadData();
    } catch (error) {
      console.error('Erro ao criar servidor PPPoE:', error);
      enqueueSnackbar('Erro ao criar servidor PPPoE', { variant: 'error' });
    }
  };

  const handleUpdatePppoeServer = async () => {
    if (!editingPppoeServer) return;
    try {
      await networkService.updatePPPoEServer(editingPppoeServer.id, pppoeServerForm);
      enqueueSnackbar('Servidor PPPoE atualizado com sucesso!', { variant: 'success' });
      setPppoeServerDialog(false);
      setEditingPppoeServer(null);
      resetPppoeServerForm();
      loadData();
    } catch (error) {
      console.error('Erro ao atualizar servidor PPPoE:', error);
      enqueueSnackbar('Erro ao atualizar servidor PPPoE', { variant: 'error' });
    }
  };

  const handleDeletePppoeServer = async (server: PPPoEServer) => {
    if (!window.confirm(`Deseja realmente excluir o servidor "${server.service_name}"?`)) return;
    try {
      await networkService.deletePPPoEServer(server.id);
      enqueueSnackbar('Servidor PPPoE excluído com sucesso!', { variant: 'success' });
      loadData();
    } catch (error) {
      console.error('Erro ao excluir servidor PPPoE:', error);
      enqueueSnackbar('Erro ao excluir servidor PPPoE', { variant: 'error' });
    }
  };

  // Funções auxiliares
  const resetIpPoolForm = () => {
    setIpPoolForm({
      nome: '',
      ranges: '',
      comentario: '',
      is_active: true
    });
  };

  const resetPppProfileForm = () => {
    setPppProfileForm({
      nome: '',
      local_address: '',
      remote_address: '',
      rate_limit: '',
      comentario: '',
      is_active: true
    });
  };

  const resetPppoeServerForm = () => {
    setPppoeServerForm({
      service_name: '',
      interface_id: 0,
      default_profile_id: 0,
      comentario: '',
      is_active: true
    });
  };

  const openIpPoolDialog = (pool?: IPPool) => {
    if (pool) {
      setEditingIpPool(pool);
      setIpPoolForm({
        router_id: pool.router_id || undefined,
        nome: pool.nome,
        ranges: pool.ranges,
        comentario: pool.comentario || '',
        is_active: pool.is_active
      });
    } else {
      resetIpPoolForm();
      setEditingIpPool(null);
    }
    setIpPoolDialog(true);
  };

  const openPppProfileDialog = (profile?: PPPProfile) => {
    if (profile) {
      setEditingPppProfile(profile);
      setPppProfileForm({
        router_id: profile.router_id || undefined,
        nome: profile.nome,
        local_address: profile.local_address,
        remote_address: profile.remote_address || '',
        rate_limit: profile.rate_limit || '',
        comentario: profile.comentario || '',
        is_active: profile.is_active
      });
    } else {
      resetPppProfileForm();
      setEditingPppProfile(null);
    }
    setPppProfileDialog(true);
  };

  const openPppoeServerDialog = (server?: PPPoEServer) => {
    if (server) {
      setEditingPppoeServer(server);
      setPppoeServerForm({
        router_id: server.router_id || undefined,
        service_name: server.service_name,
        interface_id: server.interface_id,
        default_profile_id: server.default_profile_id,
        comentario: server.comentario || '',
        is_active: server.is_active
      });
    } else {
      resetPppoeServerForm();
      setEditingPppoeServer(null);
    }
    setPppoeServerDialog(true);
  };

  // Filtrar dados baseado na busca
  const filteredIpPools = ipPools.filter(pool =>
    pool.nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
    pool.ranges.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredPppProfiles = pppProfiles.filter(profile =>
    profile.nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
    profile.local_address.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredPppoeServers = pppoeServers.filter(server =>
    server.service_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (!activeCompany) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning">
          Você precisa selecionar uma empresa ativa para gerenciar configurações PPPoE.
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ mb: 3, fontWeight: 'bold' }}>
        Configurações PPPoE
      </Typography>

      {/* Barra de ferramentas */}
      <Box sx={{ mb: 3, display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
        <TextField
          placeholder="Buscar..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: <InputAdornment position="start"><SearchIcon /></InputAdornment>,
          }}
          size="small"
          sx={{ minWidth: 250 }}
        />
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={loadData}
          disabled={loading}
        >
          Atualizar
        </Button>
      </Box>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
          <Tab label="Pools de IP" />
          <Tab label="Perfis PPP" />
          <Tab label="Servidores PPPoE" />
        </Tabs>
      </Box>

      {/* Conteúdo das tabs */}
      {activeTab === 0 && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Pools de IP</Typography>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={() => openIpPoolDialog()}
              >
                Novo Pool
              </Button>
            </Box>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Nome</TableCell>
                    <TableCell>Faixas</TableCell>
                    <TableCell>Router</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Ações</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredIpPools.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage).map((pool) => (
                    <TableRow key={pool.id}>
                      <TableCell>{pool.nome}</TableCell>
                      <TableCell>{pool.ranges}</TableCell>
                      <TableCell>{pool.router?.nome || 'Global'}</TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Box
                            sx={{
                              width: 8,
                              height: 8,
                              borderRadius: '50%',
                              bgcolor: pool.is_active ? 'success.main' : 'error.main',
                              mr: 1
                            }}
                          />
                          {pool.is_active ? 'Ativo' : 'Inativo'}
                        </Box>
                      </TableCell>
                      <TableCell align="right">
                        <IconButton onClick={() => openIpPoolDialog(pool)} size="small">
                          <EditIcon />
                        </IconButton>
                        <IconButton onClick={() => handleDeleteIpPool(pool)} size="small" color="error">
                          <DeleteIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination
              component="div"
              count={filteredIpPools.length}
              page={page}
              onPageChange={(_, newPage) => setPage(newPage)}
              rowsPerPage={rowsPerPage}
              onRowsPerPageChange={(e) => {
                setRowsPerPage(parseInt(e.target.value, 10));
                setPage(0);
              }}
              labelRowsPerPage="Linhas por página"
            />
          </CardContent>
        </Card>
      )}

      {activeTab === 1 && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Perfis PPP</Typography>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={() => openPppProfileDialog()}
              >
                Novo Perfil
              </Button>
            </Box>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Nome</TableCell>
                    <TableCell>Endereço Local</TableCell>
                    <TableCell>Endereço Remoto</TableCell>
                    <TableCell>Limitação</TableCell>
                    <TableCell>Router</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Ações</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredPppProfiles.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage).map((profile) => (
                    <TableRow key={profile.id}>
                      <TableCell>{profile.nome}</TableCell>
                      <TableCell>{profile.local_address}</TableCell>
                      <TableCell>{profile.remote_address || '-'}</TableCell>
                      <TableCell>{profile.rate_limit || '-'}</TableCell>
                      <TableCell>{profile.router?.nome || 'Global'}</TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Box
                            sx={{
                              width: 8,
                              height: 8,
                              borderRadius: '50%',
                              bgcolor: profile.is_active ? 'success.main' : 'error.main',
                              mr: 1
                            }}
                          />
                          {profile.is_active ? 'Ativo' : 'Inativo'}
                        </Box>
                      </TableCell>
                      <TableCell align="right">
                        <IconButton onClick={() => openPppProfileDialog(profile)} size="small">
                          <EditIcon />
                        </IconButton>
                        <IconButton onClick={() => handleDeletePppProfile(profile)} size="small" color="error">
                          <DeleteIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination
              component="div"
              count={filteredPppProfiles.length}
              page={page}
              onPageChange={(_, newPage) => setPage(newPage)}
              rowsPerPage={rowsPerPage}
              onRowsPerPageChange={(e) => {
                setRowsPerPage(parseInt(e.target.value, 10));
                setPage(0);
              }}
              labelRowsPerPage="Linhas por página"
            />
          </CardContent>
        </Card>
      )}

      {activeTab === 2 && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Servidores PPPoE</Typography>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={() => openPppoeServerDialog()}
              >
                Novo Servidor
              </Button>
            </Box>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Nome do Serviço</TableCell>
                    <TableCell>Interface</TableCell>
                    <TableCell>Perfil Padrão</TableCell>
                    <TableCell>Router</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Ações</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredPppoeServers.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage).map((server) => (
                    <TableRow key={server.id}>
                      <TableCell>{server.service_name}</TableCell>
                      <TableCell>{server.interface?.nome || `Interface ${server.interface_id}`}</TableCell>
                      <TableCell>{server.default_profile?.nome || `Perfil ${server.default_profile_id}`}</TableCell>
                      <TableCell>{server.router?.nome || 'Global'}</TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Box
                            sx={{
                              width: 8,
                              height: 8,
                              borderRadius: '50%',
                              bgcolor: server.is_active ? 'success.main' : 'error.main',
                              mr: 1
                            }}
                          />
                          {server.is_active ? 'Ativo' : 'Inativo'}
                        </Box>
                      </TableCell>
                      <TableCell align="right">
                        <IconButton onClick={() => openPppoeServerDialog(server)} size="small">
                          <EditIcon />
                        </IconButton>
                        <IconButton onClick={() => handleDeletePppoeServer(server)} size="small" color="error">
                          <DeleteIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination
              component="div"
              count={filteredPppoeServers.length}
              page={page}
              onPageChange={(_, newPage) => setPage(newPage)}
              rowsPerPage={rowsPerPage}
              onRowsPerPageChange={(e) => {
                setRowsPerPage(parseInt(e.target.value, 10));
                setPage(0);
              }}
              labelRowsPerPage="Linhas por página"
            />
          </CardContent>
        </Card>
      )}

      {/* Dialog IP Pool */}
      <Dialog open={ipPoolDialog} onClose={() => setIpPoolDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>{editingIpPool ? 'Editar Pool de IP' : 'Novo Pool de IP'}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <FormControl fullWidth sx={{ mt: 2 }}>
              <InputLabel>Router (Opcional)</InputLabel>
              <Select
                value={ipPoolForm.router_id || ''}
                onChange={(e) => setIpPoolForm({ ...ipPoolForm, router_id: e.target.value ? Number(e.target.value) : undefined })}
                label="Router (Opcional)"
              >
                <MenuItem value="">Global (Todas as empresas)</MenuItem>
                {routers.map((router) => (
                  <MenuItem key={router.id} value={router.id}>{router.nome}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              fullWidth
              label="Nome"
              value={ipPoolForm.nome}
              onChange={(e) => setIpPoolForm({ ...ipPoolForm, nome: e.target.value })}
              required
            />
            <TextField
              fullWidth
              label="Faixas de IP"
              value={ipPoolForm.ranges}
              onChange={(e) => setIpPoolForm({ ...ipPoolForm, ranges: e.target.value })}
              placeholder="Ex: 192.168.1.2-192.168.1.254"
              required
            />
            <TextField
              fullWidth
              label="Comentário"
              value={ipPoolForm.comentario}
              onChange={(e) => setIpPoolForm({ ...ipPoolForm, comentario: e.target.value })}
              multiline
              rows={2}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={ipPoolForm.is_active}
                  onChange={(e) => setIpPoolForm({ ...ipPoolForm, is_active: e.target.checked })}
                />
              }
              label="Ativo"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIpPoolDialog(false)}>Cancelar</Button>
          <Button
            onClick={editingIpPool ? handleUpdateIpPool : handleCreateIpPool}
            variant="contained"
          >
            {editingIpPool ? 'Atualizar' : 'Criar'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog PPP Profile */}
      <Dialog open={pppProfileDialog} onClose={() => setPppProfileDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>{editingPppProfile ? 'Editar Perfil PPP' : 'Novo Perfil PPP'}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <FormControl fullWidth sx={{ mt: 2 }}>
              <InputLabel>Router (Opcional)</InputLabel>
              <Select
                value={pppProfileForm.router_id || ''}
                onChange={(e) => setPppProfileForm({ ...pppProfileForm, router_id: e.target.value ? Number(e.target.value) : undefined })}
                label="Router (Opcional)"
              >
                <MenuItem value="">Global (Todas as empresas)</MenuItem>
                {routers.map((router) => (
                  <MenuItem key={router.id} value={router.id}>{router.nome}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              fullWidth
              label="Nome"
              value={pppProfileForm.nome}
              onChange={(e) => setPppProfileForm({ ...pppProfileForm, nome: e.target.value })}
              required
            />
            <TextField
              fullWidth
              label="Endereço Local"
              value={pppProfileForm.local_address}
              onChange={(e) => setPppProfileForm({ ...pppProfileForm, local_address: e.target.value })}
              placeholder="Ex: 192.168.1.1"
              required
            />
            <TextField
              fullWidth
              label="Endereço Remoto (Opcional)"
              value={pppProfileForm.remote_address}
              onChange={(e) => setPppProfileForm({ ...pppProfileForm, remote_address: e.target.value })}
              placeholder="Ex: 192.168.1.2"
            />
            <TextField
              fullWidth
              label="Limitação de Velocidade (Opcional)"
              value={pppProfileForm.rate_limit}
              onChange={(e) => setPppProfileForm({ ...pppProfileForm, rate_limit: e.target.value })}
              placeholder="Ex: 10M/10M"
            />
            <TextField
              fullWidth
              label="Comentário"
              value={pppProfileForm.comentario}
              onChange={(e) => setPppProfileForm({ ...pppProfileForm, comentario: e.target.value })}
              multiline
              rows={2}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={pppProfileForm.is_active}
                  onChange={(e) => setPppProfileForm({ ...pppProfileForm, is_active: e.target.checked })}
                />
              }
              label="Ativo"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPppProfileDialog(false)}>Cancelar</Button>
          <Button
            onClick={editingPppProfile ? handleUpdatePppProfile : handleCreatePppProfile}
            variant="contained"
          >
            {editingPppProfile ? 'Atualizar' : 'Criar'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog PPPoE Server */}
      <Dialog open={pppoeServerDialog} onClose={() => setPppoeServerDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>{editingPppoeServer ? 'Editar Servidor PPPoE' : 'Novo Servidor PPPoE'}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <FormControl fullWidth sx={{ mt: 1 }}>
              <InputLabel>Router (Opcional)</InputLabel>
              <Select
                value={pppoeServerForm.router_id || ''}
                onChange={(e) => setPppoeServerForm({ ...pppoeServerForm, router_id: e.target.value ? Number(e.target.value) : undefined })}
                label="Router (Opcional)"
              >
                <MenuItem value="">Global (Todas as empresas)</MenuItem>
                {routers.map((router) => (
                  <MenuItem key={router.id} value={router.id}>{router.nome}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              fullWidth
              label="Nome do Serviço"
              value={pppoeServerForm.service_name}
              onChange={(e) => setPppoeServerForm({ ...pppoeServerForm, service_name: e.target.value })}
              required
            />
            <FormControl fullWidth sx={{ mt: 1 }}>
              <InputLabel>Interface</InputLabel>
              <Select
                value={pppoeServerForm.interface_id}
                onChange={(e) => setPppoeServerForm({ ...pppoeServerForm, interface_id: Number(e.target.value) })}
                label="Interface"
                required
              >
                {interfaces.map((iface) => (
                  <MenuItem key={iface.id} value={iface.id}>{iface.nome}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth sx={{ mt: 1 }}>
              <InputLabel>Perfil Padrão</InputLabel>
              <Select
                value={pppoeServerForm.default_profile_id}
                onChange={(e) => setPppoeServerForm({ ...pppoeServerForm, default_profile_id: Number(e.target.value) })}
                label="Perfil Padrão"
                required
              >
                {pppProfiles.map((profile) => (
                  <MenuItem key={profile.id} value={profile.id}>{profile.nome}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              fullWidth
              label="Comentário"
              value={pppoeServerForm.comentario}
              onChange={(e) => setPppoeServerForm({ ...pppoeServerForm, comentario: e.target.value })}
              multiline
              rows={2}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={pppoeServerForm.is_active}
                  onChange={(e) => setPppoeServerForm({ ...pppoeServerForm, is_active: e.target.checked })}
                />
              }
              label="Ativo"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPppoeServerDialog(false)}>Cancelar</Button>
          <Button
            onClick={editingPppoeServer ? handleUpdatePppoeServer : handleCreatePppoeServer}
            variant="contained"
          >
            {editingPppoeServer ? 'Atualizar' : 'Criar'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PPPoE;