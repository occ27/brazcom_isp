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
  Dns as DnsIcon
} from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import { useAuth } from '../contexts/AuthContext';
import { useCompany } from '../contexts/CompanyContext';
import {
  networkService,
  DHCPServerCreate,
  DHCPServerUpdate,
  DHCPNetworkCreate,
  DHCPNetworkUpdate
} from '../services/networkService';
import { routerService } from '../services/routerService';
import {
  DHCPServer,
  DHCPNetwork,
  Router,
  RouterInterface
} from '../types';

const DHCP: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { enqueueSnackbar } = useSnackbar();
  const { user } = useAuth();
  const { activeCompany } = useCompany();

  // Estados para dados
  const [dhcpServers, setDhcpServers] = useState<DHCPServer[]>([]);
  const [dhcpNetworks, setDhcpNetworks] = useState<DHCPNetwork[]>([]);
  const [routers, setRouters] = useState<Router[]>([]);
  const [interfaces, setInterfaces] = useState<RouterInterface[]>([]);

  // Estados para UI
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Estados para modais
  const [dhcpServerDialog, setDhcpServerDialog] = useState(false);
  const [dhcpNetworkDialog, setDhcpNetworkDialog] = useState(false);
  const [editingDhcpServer, setEditingDhcpServer] = useState<DHCPServer | null>(null);
  const [editingDhcpNetwork, setEditingDhcpNetwork] = useState<DHCPNetwork | null>(null);

  // Estados para formulários
  const [dhcpServerForm, setDhcpServerForm] = useState<DHCPServerCreate>({
    name: '',
    interface_id: 0,
    comentario: '',
    is_active: true
  });

  const [dhcpNetworkForm, setDhcpNetworkForm] = useState<DHCPNetworkCreate>({
    dhcp_server_id: 0,
    network: '',
    gateway: '',
    dns_servers: '',
    lease_time: '',
    comentario: '',
    is_active: true
  });

  // Carregar dados
  const loadData = useCallback(async () => {
    if (!activeCompany) return;

    setLoading(true);
    try {
      const [serversResp, networksResp, routersResp] = await Promise.all([
        networkService.getDHCPServers(),
        networkService.getDHCPNetworks(),
        routerService.getByCompany(activeCompany.id)
      ]);

      setDhcpServers(serversResp || []);
      setDhcpNetworks(networksResp || []);
      setRouters(routersResp || []);
    } catch (error) {
      console.error('Erro ao carregar dados DHCP:', error);
      enqueueSnackbar('Erro ao carregar dados DHCP', { variant: 'error' });
    } finally {
      setLoading(false);
    }
  }, [activeCompany, enqueueSnackbar]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Carregar interfaces quando um router for selecionado
  const loadInterfaces = useCallback(async (routerId: number) => {
    try {
      const interfacesResp = await networkService.getRouterInterfaces(routerId);
      setInterfaces(interfacesResp || []);
    } catch (error) {
      console.error('Erro ao carregar interfaces:', error);
      setInterfaces([]);
    }
  }, []);

  // Handlers para DHCP Servers
  const handleCreateDhcpServer = async () => {
    try {
      await networkService.createDHCPServer(dhcpServerForm);
      enqueueSnackbar('Servidor DHCP criado com sucesso!', { variant: 'success' });
      setDhcpServerDialog(false);
      resetDhcpServerForm();
      loadData();
    } catch (error) {
      console.error('Erro ao criar servidor DHCP:', error);
      enqueueSnackbar('Erro ao criar servidor DHCP', { variant: 'error' });
    }
  };

  const handleUpdateDhcpServer = async () => {
    if (!editingDhcpServer) return;
    try {
      await networkService.updateDHCPServer(editingDhcpServer.id, dhcpServerForm);
      enqueueSnackbar('Servidor DHCP atualizado com sucesso!', { variant: 'success' });
      setDhcpServerDialog(false);
      setEditingDhcpServer(null);
      resetDhcpServerForm();
      loadData();
    } catch (error) {
      console.error('Erro ao atualizar servidor DHCP:', error);
      enqueueSnackbar('Erro ao atualizar servidor DHCP', { variant: 'error' });
    }
  };

  const handleDeleteDhcpServer = async (server: DHCPServer) => {
    if (!window.confirm(`Deseja realmente excluir o servidor DHCP "${server.name}"?`)) return;
    try {
      await networkService.deleteDHCPServer(server.id);
      enqueueSnackbar('Servidor DHCP excluído com sucesso!', { variant: 'success' });
      loadData();
    } catch (error) {
      console.error('Erro ao excluir servidor DHCP:', error);
      enqueueSnackbar('Erro ao excluir servidor DHCP', { variant: 'error' });
    }
  };

  // Handlers para DHCP Networks
  const handleCreateDhcpNetwork = async () => {
    try {
      await networkService.createDHCPNetwork(dhcpNetworkForm);
      enqueueSnackbar('Rede DHCP criada com sucesso!', { variant: 'success' });
      setDhcpNetworkDialog(false);
      resetDhcpNetworkForm();
      loadData();
    } catch (error) {
      console.error('Erro ao criar rede DHCP:', error);
      enqueueSnackbar('Erro ao criar rede DHCP', { variant: 'error' });
    }
  };

  const handleUpdateDhcpNetwork = async () => {
    if (!editingDhcpNetwork) return;
    try {
      await networkService.updateDHCPNetwork(editingDhcpNetwork.id, dhcpNetworkForm);
      enqueueSnackbar('Rede DHCP atualizada com sucesso!', { variant: 'success' });
      setDhcpNetworkDialog(false);
      setEditingDhcpNetwork(null);
      resetDhcpNetworkForm();
      loadData();
    } catch (error) {
      console.error('Erro ao atualizar rede DHCP:', error);
      enqueueSnackbar('Erro ao atualizar rede DHCP', { variant: 'error' });
    }
  };

  const handleDeleteDhcpNetwork = async (network: DHCPNetwork) => {
    if (!window.confirm(`Deseja realmente excluir a rede DHCP "${network.network}"?`)) return;
    try {
      await networkService.deleteDHCPNetwork(network.id);
      enqueueSnackbar('Rede DHCP excluída com sucesso!', { variant: 'success' });
      loadData();
    } catch (error) {
      console.error('Erro ao excluir rede DHCP:', error);
      enqueueSnackbar('Erro ao excluir rede DHCP', { variant: 'error' });
    }
  };

  // Funções auxiliares
  const resetDhcpServerForm = () => {
    setDhcpServerForm({
      name: '',
      interface_id: 0,
      comentario: '',
      is_active: true
    });
  };

  const resetDhcpNetworkForm = () => {
    setDhcpNetworkForm({
      dhcp_server_id: 0,
      network: '',
      gateway: '',
      dns_servers: '',
      lease_time: '',
      comentario: '',
      is_active: true
    });
  };

  const openDhcpServerDialog = (server?: DHCPServer) => {
    if (server) {
      setEditingDhcpServer(server);
      setDhcpServerForm({
        router_id: server.router_id || undefined,
        name: server.name,
        interface_id: server.interface_id,
        comentario: server.comentario || '',
        is_active: server.is_active
      });
      // Carregar interfaces do router se houver
      if (server.router_id) {
        loadInterfaces(server.router_id);
      }
    } else {
      resetDhcpServerForm();
      setEditingDhcpServer(null);
    }
    setDhcpServerDialog(true);
  };

  const openDhcpNetworkDialog = (network?: DHCPNetwork) => {
    if (network) {
      setEditingDhcpNetwork(network);
      setDhcpNetworkForm({
        router_id: network.router_id || undefined,
        dhcp_server_id: network.dhcp_server_id,
        network: network.network,
        gateway: network.gateway || '',
        dns_servers: network.dns_servers || '',
        lease_time: network.lease_time || '',
        comentario: network.comentario || '',
        is_active: network.is_active
      });
    } else {
      resetDhcpNetworkForm();
      setEditingDhcpNetwork(null);
    }
    setDhcpNetworkDialog(true);
  };

  // Filtrar dados baseado na busca
  const filteredDhcpServers = dhcpServers.filter(server =>
    server.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredDhcpNetworks = dhcpNetworks.filter(network =>
    network.network.toLowerCase().includes(searchTerm.toLowerCase()) ||
    network.dhcp_server?.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (!activeCompany) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning">
          Você precisa selecionar uma empresa ativa para gerenciar configurações DHCP.
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ mb: 3, fontWeight: 'bold' }}>
        Configurações DHCP
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
          <Tab label="Servidores DHCP" />
          <Tab label="Redes DHCP" />
        </Tabs>
      </Box>

      {/* Conteúdo das tabs */}
      {activeTab === 0 && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Servidores DHCP</Typography>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={() => openDhcpServerDialog()}
              >
                Novo Servidor
              </Button>
            </Box>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Nome</TableCell>
                    <TableCell>Interface</TableCell>
                    <TableCell>Router</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Ações</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredDhcpServers.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage).map((server) => (
                    <TableRow key={server.id}>
                      <TableCell>{server.name}</TableCell>
                      <TableCell>{server.interface?.nome || `Interface ${server.interface_id}`}</TableCell>
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
                        <IconButton onClick={() => openDhcpServerDialog(server)} size="small">
                          <EditIcon />
                        </IconButton>
                        <IconButton onClick={() => handleDeleteDhcpServer(server)} size="small" color="error">
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
              count={filteredDhcpServers.length}
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
              <Typography variant="h6">Redes DHCP</Typography>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={() => openDhcpNetworkDialog()}
              >
                Nova Rede
              </Button>
            </Box>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Rede</TableCell>
                    <TableCell>Gateway</TableCell>
                    <TableCell>Servidores DNS</TableCell>
                    <TableCell>Servidor DHCP</TableCell>
                    <TableCell>Router</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Ações</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredDhcpNetworks.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage).map((network) => (
                    <TableRow key={network.id}>
                      <TableCell>{network.network}</TableCell>
                      <TableCell>{network.gateway || '-'}</TableCell>
                      <TableCell>{network.dns_servers || '-'}</TableCell>
                      <TableCell>{network.dhcp_server?.name || `Servidor ${network.dhcp_server_id}`}</TableCell>
                      <TableCell>{network.router?.nome || 'Global'}</TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Box
                            sx={{
                              width: 8,
                              height: 8,
                              borderRadius: '50%',
                              bgcolor: network.is_active ? 'success.main' : 'error.main',
                              mr: 1
                            }}
                          />
                          {network.is_active ? 'Ativo' : 'Inativo'}
                        </Box>
                      </TableCell>
                      <TableCell align="right">
                        <IconButton onClick={() => openDhcpNetworkDialog(network)} size="small">
                          <EditIcon />
                        </IconButton>
                        <IconButton onClick={() => handleDeleteDhcpNetwork(network)} size="small" color="error">
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
              count={filteredDhcpNetworks.length}
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

      {/* Dialog DHCP Server */}
      <Dialog open={dhcpServerDialog} onClose={() => setDhcpServerDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>{editingDhcpServer ? 'Editar Servidor DHCP' : 'Novo Servidor DHCP'}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Router (Opcional)</InputLabel>
              <Select
                value={dhcpServerForm.router_id || ''}
                onChange={(e) => {
                  const routerId = e.target.value ? Number(e.target.value) : undefined;
                  setDhcpServerForm({ ...dhcpServerForm, router_id: routerId });
                  if (routerId) {
                    loadInterfaces(routerId);
                  } else {
                    setInterfaces([]);
                  }
                }}
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
              value={dhcpServerForm.name}
              onChange={(e) => setDhcpServerForm({ ...dhcpServerForm, name: e.target.value })}
              required
            />
            <FormControl fullWidth>
              <InputLabel>Interface</InputLabel>
              <Select
                value={dhcpServerForm.interface_id}
                onChange={(e) => setDhcpServerForm({ ...dhcpServerForm, interface_id: Number(e.target.value) })}
                required
                disabled={interfaces.length === 0}
              >
                {interfaces.length === 0 ? (
                  <MenuItem value="" disabled>Selecione um router primeiro</MenuItem>
                ) : (
                  interfaces.map((iface) => (
                    <MenuItem key={iface.id} value={iface.id}>{iface.nome}</MenuItem>
                  ))
                )}
              </Select>
            </FormControl>
            <TextField
              fullWidth
              label="Comentário"
              value={dhcpServerForm.comentario}
              onChange={(e) => setDhcpServerForm({ ...dhcpServerForm, comentario: e.target.value })}
              multiline
              rows={2}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={dhcpServerForm.is_active}
                  onChange={(e) => setDhcpServerForm({ ...dhcpServerForm, is_active: e.target.checked })}
                />
              }
              label="Ativo"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDhcpServerDialog(false)}>Cancelar</Button>
          <Button
            onClick={editingDhcpServer ? handleUpdateDhcpServer : handleCreateDhcpServer}
            variant="contained"
          >
            {editingDhcpServer ? 'Atualizar' : 'Criar'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog DHCP Network */}
      <Dialog open={dhcpNetworkDialog} onClose={() => setDhcpNetworkDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>{editingDhcpNetwork ? 'Editar Rede DHCP' : 'Nova Rede DHCP'}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Servidor DHCP</InputLabel>
              <Select
                value={dhcpNetworkForm.dhcp_server_id}
                onChange={(e) => setDhcpNetworkForm({ ...dhcpNetworkForm, dhcp_server_id: Number(e.target.value) })}
                required
              >
                {dhcpServers.map((server) => (
                  <MenuItem key={server.id} value={server.id}>{server.name}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              fullWidth
              label="Rede"
              value={dhcpNetworkForm.network}
              onChange={(e) => setDhcpNetworkForm({ ...dhcpNetworkForm, network: e.target.value })}
              placeholder="Ex: 192.168.1.0/24"
              required
            />
            <TextField
              fullWidth
              label="Gateway (Opcional)"
              value={dhcpNetworkForm.gateway}
              onChange={(e) => setDhcpNetworkForm({ ...dhcpNetworkForm, gateway: e.target.value })}
              placeholder="Ex: 192.168.1.1"
            />
            <TextField
              fullWidth
              label="Servidores DNS (Opcional)"
              value={dhcpNetworkForm.dns_servers}
              onChange={(e) => setDhcpNetworkForm({ ...dhcpNetworkForm, dns_servers: e.target.value })}
              placeholder="Ex: 8.8.8.8,8.8.4.4"
            />
            <TextField
              fullWidth
              label="Tempo de Concessão (Opcional)"
              value={dhcpNetworkForm.lease_time}
              onChange={(e) => setDhcpNetworkForm({ ...dhcpNetworkForm, lease_time: e.target.value })}
              placeholder="Ex: 1d 00:00:00"
            />
            <TextField
              fullWidth
              label="Comentário"
              value={dhcpNetworkForm.comentario}
              onChange={(e) => setDhcpNetworkForm({ ...dhcpNetworkForm, comentario: e.target.value })}
              multiline
              rows={2}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={dhcpNetworkForm.is_active}
                  onChange={(e) => setDhcpNetworkForm({ ...dhcpNetworkForm, is_active: e.target.checked })}
                />
              }
              label="Ativo"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDhcpNetworkDialog(false)}>Cancelar</Button>
          <Button
            onClick={editingDhcpNetwork ? handleUpdateDhcpNetwork : handleCreateDhcpNetwork}
            variant="contained"
          >
            {editingDhcpNetwork ? 'Atualizar' : 'Criar'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DHCP;