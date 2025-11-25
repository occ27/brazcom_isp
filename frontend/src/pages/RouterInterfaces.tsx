import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  IconButton,
  Tooltip,
  Alert,
  Snackbar,
  Card,
  CardContent,
  Grid,
  Divider,
  Autocomplete,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Router as RouterIcon,
  SettingsEthernet as InterfaceIcon,
  NetworkCheck as NetworkIcon,
  PlayArrow as ApplyIcon,
} from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import { networkService, RouterInterfaceCreate, RouterInterfaceUpdate } from '../services/networkService';
import { routerService } from '../services/routerService';
import { RouterInterface, Router, IPClass } from '../types';

const RouterInterfaces: React.FC = () => {
  const { routerId } = useParams<{ routerId: string }>();
  const navigate = useNavigate();

  const [router, setRouter] = useState<Router | null>(null);
  const [interfaces, setInterfaces] = useState<RouterInterface[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingInterface, setEditingInterface] = useState<RouterInterface | null>(null);
  const [formData, setFormData] = useState<RouterInterfaceCreate>({
    nome: '',
    tipo: 'ethernet',
    mac_address: '',
    comentario: '',
    is_active: true,
  });

  const [ipClasses, setIpClasses] = useState<IPClass[]>([]);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [selectedInterface, setSelectedInterface] = useState<RouterInterface | null>(null);
  const [selectedIpClass, setSelectedIpClass] = useState<IPClass | null>(null);

  const [deleteConfirmDialog, setDeleteConfirmDialog] = useState({
    open: false,
    interfaceId: 0,
    impact: null as any,
  });

  const [removeIPClassConfirmDialog, setRemoveIPClassConfirmDialog] = useState({
    open: false,
    interfaceId: 0,
    ipClassId: 0,
    impact: null as any,
  });

  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success' as 'success' | 'error',
  });

  useEffect(() => {
    if (routerId) {
      loadRouterAndInterfaces();
      loadIPClasses();
    }
  }, [routerId]);

  const loadRouterAndInterfaces = async () => {
    try {
      setLoading(true);
      const [routerData, interfacesData] = await Promise.all([
        routerService.getById(parseInt(routerId!)),
        networkService.getRouterInterfaces(parseInt(routerId!)),
      ]);
      setRouter(routerData);
      setInterfaces(interfacesData);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      showSnackbar('Erro ao carregar dados do router', 'error');
    } finally {
      setLoading(false);
    }
  };

  const loadIPClasses = async () => {
    try {
      const classes = await networkService.getIPClasses();
      setIpClasses(classes);
    } catch (error) {
      console.error('Erro ao carregar classes IP:', error);
      showSnackbar('Erro ao carregar classes IP', 'error');
    }
  };

  const handleOpenDialog = (interfaceItem?: RouterInterface) => {
    if (interfaceItem) {
      setEditingInterface(interfaceItem);
      setFormData({
        nome: interfaceItem.nome,
        tipo: interfaceItem.tipo,
        mac_address: interfaceItem.mac_address || '',
        comentario: interfaceItem.comentario || '',
        is_active: interfaceItem.is_active,
      });
    } else {
      setEditingInterface(null);
      setFormData({
        nome: '',
        tipo: 'ethernet',
        mac_address: '',
        comentario: '',
        is_active: true,
      });
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingInterface(null);
    setFormData({
      nome: '',
      tipo: 'ethernet',
      mac_address: '',
      comentario: '',
      is_active: true,
    });
  };

  const handleSubmit = async () => {
    try {
      if (editingInterface) {
        await networkService.updateRouterInterface(editingInterface.id, formData);
        showSnackbar('Interface atualizada com sucesso', 'success');
      } else {
        await networkService.createRouterInterface(parseInt(routerId!), formData);
        showSnackbar('Interface criada com sucesso', 'success');
      }
      handleCloseDialog();
      loadRouterAndInterfaces();
    } catch (error) {
      console.error('Erro ao salvar interface:', error);
      showSnackbar('Erro ao salvar interface', 'error');
    }
  };

  const handleDelete = async (interfaceId: number) => {
    try {
      await networkService.deleteRouterInterface(interfaceId);
      showSnackbar('Interface excluída com sucesso', 'success');
      loadRouterAndInterfaces();
    } catch (error: any) {
      console.error('Erro ao excluir interface:', error);
      
      // Verificar se é erro de confirmação necessária
      const errorData = error?.response?.data;
      const isConfirmationRequired = 
        error?.response?.status === 400 && (
          errorData?.confirmation_required || 
          errorData?.detail?.confirmation_required
        );
      
      if (isConfirmationRequired) {
        const impact = errorData?.impact || errorData?.detail?.impact;
        setDeleteConfirmDialog({
          open: true,
          interfaceId,
          impact: impact,
        });
      } else {
        showSnackbar('Erro ao excluir interface', 'error');
      }
    }
  };

  const handleConfirmDelete = async () => {
    try {
      await networkService.deleteRouterInterface(deleteConfirmDialog.interfaceId, true);
      showSnackbar('Interface excluída com sucesso', 'success');
      setDeleteConfirmDialog({ open: false, interfaceId: 0, impact: null });
      loadRouterAndInterfaces();
    } catch (error) {
      console.error('Erro ao confirmar exclusão:', error);
      showSnackbar('Erro ao excluir interface', 'error');
      setDeleteConfirmDialog({ open: false, interfaceId: 0, impact: null });
    }
  };

  const handleConfirmRemoveIPClass = async () => {
    try {
      await networkService.removeIPClassFromInterface(
        removeIPClassConfirmDialog.interfaceId, 
        removeIPClassConfirmDialog.ipClassId, 
        true
      );
      showSnackbar('Classe IP removida com sucesso', 'success');
      setRemoveIPClassConfirmDialog({ open: false, interfaceId: 0, ipClassId: 0, impact: null });
      loadRouterAndInterfaces();
    } catch (error) {
      console.error('Erro ao confirmar remoção de classe IP:', error);
      showSnackbar('Erro ao remover classe IP', 'error');
      setRemoveIPClassConfirmDialog({ open: false, interfaceId: 0, ipClassId: 0, impact: null });
    }
  };

  const handleSyncInterfaces = async () => {
    try {
      await networkService.syncRouterInterfaces(parseInt(routerId!));
      showSnackbar('Interfaces sincronizadas com sucesso', 'success');
      loadRouterAndInterfaces();
    } catch (error) {
      console.error('Erro ao sincronizar interfaces:', error);
      showSnackbar('Erro ao sincronizar interfaces', 'error');
    }
  };

  const handleApplyIPConfig = async (interfaceId: number) => {
    try {
      await networkService.applyIPConfigToInterface(interfaceId);
      showSnackbar('Configuração IP aplicada com sucesso', 'success');
    } catch (error) {
      console.error('Erro ao aplicar configuração IP:', error);
      showSnackbar('Erro ao aplicar configuração IP', 'error');
    }
  };

  const handleAssignIPClass = async () => {
    if (!selectedInterface || !selectedIpClass) return;

    try {
      const result = await networkService.assignIPClassToInterface({
        interface_id: selectedInterface.id,
        ip_class_id: selectedIpClass.id,
      });

      // Verifica se houve aplicação automática no router
      if (result.application_status === 'success' && result.applied_configs) {
        const configsMessage = result.applied_configs.join(', ');
        showSnackbar(`Classe IP atribuída e aplicada no router: ${configsMessage}`, 'success');
      } else if (result.application_status && result.application_status.startsWith('error:')) {
        const errorMessage = result.application_status.replace('error: ', '');
        showSnackbar(`Classe IP atribuída, mas erro na aplicação: ${errorMessage}`, 'error');
      } else {
        showSnackbar('Classe IP atribuída com sucesso', 'success');
      }

      setAssignDialogOpen(false);
      setSelectedInterface(null);
      setSelectedIpClass(null);
      loadRouterAndInterfaces();
    } catch (error) {
      console.error('Erro ao atribuir classe IP:', error);
      showSnackbar('Erro ao atribuir classe IP', 'error');
    }
  };

  const handleRemoveIPClass = async (interfaceId: number, ipClassId: number) => {
    try {
      await networkService.removeIPClassFromInterface(interfaceId, ipClassId);
      showSnackbar('Classe IP removida com sucesso', 'success');
      loadRouterAndInterfaces();
    } catch (error: any) {
      console.error('=== ERRO REMOÇÃO CLASSE IP ===');
      console.error('Error:', error);
      console.error('Error.response:', error?.response);
      console.error('Error.response.data:', error?.response?.data);
      console.error('================================');
      
      // Verificar se é erro de confirmação necessária
      const errorData = error?.response?.data;
      const isConfirmationRequired = 
        error?.response?.status === 400 && (
          errorData?.confirmation_required || 
          errorData?.detail?.confirmation_required
        );
      
      if (isConfirmationRequired) {
        console.log('✅ Detectado erro de confirmação necessária para remoção de classe IP');
        const impact = errorData?.impact || errorData?.detail?.impact;
        setRemoveIPClassConfirmDialog({
          open: true,
          interfaceId,
          ipClassId,
          impact: impact,
        });
      } else {
        console.log('❌ Erro não é de confirmação, mostrando snackbar');
        showSnackbar('Erro ao remover classe IP', 'error');
      }
    }
  };

  const showSnackbar = (message: string, severity: 'success' | 'error') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>Carregando...</Typography>
      </Box>
    );
  }

  if (!router) {
    return (
      <Box p={3}>
        <Alert severity="error">Router não encontrado</Alert>
      </Box>
    );
  }

  return (
    <Box p={3}>
      <Box display="flex" alignItems="center" mb={3}>
        <RouterIcon sx={{ mr: 1 }} />
        <Typography variant="h4" component="h1">
          Interfaces do Router: {router.nome}
        </Typography>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Informações do Router
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Typography><strong>Nome:</strong> {router.nome}</Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography><strong>IP:</strong> {router.ip}</Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography><strong>Tipo:</strong> {router.tipo}</Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography><strong>Status:</strong>
                <Chip
                  label={router.is_active ? 'Ativo' : 'Inativo'}
                  color={router.is_active ? 'success' : 'error'}
                  size="small"
                  sx={{ ml: 1 }}
                />
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">
          Interfaces ({interfaces.length})
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleSyncInterfaces}
            sx={{ mr: 1 }}
          >
            Sincronizar
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
          >
            Nova Interface
          </Button>
        </Box>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Nome</TableCell>
              <TableCell>Tipo</TableCell>
              <TableCell>MAC Address</TableCell>
              <TableCell>Classes IP</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Comentário</TableCell>
              <TableCell>Ações</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {interfaces.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography variant="body2" color="textSecondary">
                    Nenhuma interface cadastrada
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              interfaces.map((interfaceItem) => (
                <TableRow key={interfaceItem.id}>
                  <TableCell>
                    <Box display="flex" alignItems="center">
                      <InterfaceIcon sx={{ mr: 1, color: 'primary.main' }} />
                      {interfaceItem.nome}
                    </Box>
                  </TableCell>
                  <TableCell>{interfaceItem.tipo}</TableCell>
                  <TableCell>{interfaceItem.mac_address || '-'}</TableCell>
                  <TableCell>
                    <Box display="flex" flexWrap="wrap" gap={0.5}>
                      {interfaceItem.ip_classes && interfaceItem.ip_classes.length > 0 ? (
                        interfaceItem.ip_classes.map((ipClass) => (
                          <Chip
                            key={ipClass.id}
                            label={ipClass.nome}
                            size="small"
                            onDelete={() => handleRemoveIPClass(interfaceItem.id, ipClass.id)}
                            color="primary"
                            variant="outlined"
                          />
                        ))
                      ) : (
                        <Typography variant="body2" color="textSecondary">
                          Nenhuma
                        </Typography>
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={interfaceItem.is_active ? 'Ativa' : 'Inativa'}
                      color={interfaceItem.is_active ? 'success' : 'error'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{interfaceItem.comentario || '-'}</TableCell>
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      <Tooltip title="Editar">
                        <IconButton
                          color="primary"
                          onClick={() => handleOpenDialog(interfaceItem)}
                        >
                          <EditIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Atribuir Classe IP">
                        <IconButton
                          color="secondary"
                          onClick={() => {
                            setSelectedInterface(interfaceItem);
                            setAssignDialogOpen(true);
                          }}
                        >
                          <NetworkIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Aplicar Configuração IP">
                        <IconButton
                          color="success"
                          onClick={() => handleApplyIPConfig(interfaceItem.id)}
                        >
                          <ApplyIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Excluir">
                        <IconButton
                          color="error"
                          onClick={() => handleDelete(interfaceItem.id)}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Dialog para criar/editar interface */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingInterface ? 'Editar Interface' : 'Nova Interface'}
        </DialogTitle>
        <DialogContent>
          <Box component="form" sx={{ mt: 1 }}>
            <TextField
              fullWidth
              label="Nome da Interface"
              value={formData.nome}
              onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
              margin="normal"
              required
            />
            <FormControl fullWidth margin="normal" required>
              <InputLabel>Tipo</InputLabel>
              <Select
                value={formData.tipo}
                onChange={(e) => setFormData({ ...formData, tipo: e.target.value })}
                label="Tipo"
              >
                <MenuItem value="ethernet">Ethernet</MenuItem>
                <MenuItem value="wireless">Wireless</MenuItem>
                <MenuItem value="vlan">VLAN</MenuItem>
                <MenuItem value="bridge">Bridge</MenuItem>
                <MenuItem value="ppp">PPP</MenuItem>
                <MenuItem value="other">Outro</MenuItem>
              </Select>
            </FormControl>
            <TextField
              fullWidth
              label="MAC Address"
              value={formData.mac_address}
              onChange={(e) => setFormData({ ...formData, mac_address: e.target.value })}
              margin="normal"
              placeholder="XX:XX:XX:XX:XX:XX"
            />
            <TextField
              fullWidth
              label="Comentário"
              value={formData.comentario}
              onChange={(e) => setFormData({ ...formData, comentario: e.target.value })}
              margin="normal"
              multiline
              rows={2}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancelar</Button>
          <Button onClick={handleSubmit} variant="contained">
            {editingInterface ? 'Atualizar' : 'Criar'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog para atribuir classe IP */}
      <Dialog open={assignDialogOpen} onClose={() => setAssignDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          Atribuir Classe IP à Interface
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 1 }}>
            {selectedInterface && (
              <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
                Interface: <strong>{selectedInterface.nome}</strong>
              </Typography>
            )}
            <Autocomplete
              options={ipClasses}
              getOptionLabel={(option) => `${option.nome} (${option.rede})`}
              value={selectedIpClass}
              onChange={(event, newValue) => setSelectedIpClass(newValue)}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Classe IP"
                  placeholder="Selecione uma classe IP"
                  fullWidth
                  margin="normal"
                />
              )}
              renderOption={(props, option) => (
                <ListItem {...props}>
                  <ListItemText
                    primary={option.nome}
                    secondary={`${option.rede}${option.gateway ? ` - Gateway: ${option.gateway}` : ''}`}
                  />
                </ListItem>
              )}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAssignDialogOpen(false)}>Cancelar</Button>
          <Button
            onClick={handleAssignIPClass}
            variant="contained"
            disabled={!selectedIpClass}
          >
            Atribuir
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog de confirmação de exclusão */}
      <Dialog
        open={deleteConfirmDialog.open}
        onClose={() => setDeleteConfirmDialog({ open: false, interfaceId: 0, impact: null })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Confirmar Exclusão da Interface</DialogTitle>
        <DialogContent>
          {deleteConfirmDialog.impact && (
            <Box>
              <Typography variant="body1" sx={{ mb: 2 }}>
                Tem certeza que deseja excluir a interface <strong>{deleteConfirmDialog.impact.interface_name}</strong> do router <strong>{deleteConfirmDialog.impact.router_name}</strong>?
              </Typography>
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                <strong>Impacto da exclusão:</strong>
              </Typography>
              
              <Box sx={{ pl: 2, mb: 2 }}>
                <Typography variant="body2" sx={{ mb: 0.5 }}>
                  • Classes IP atribuídas: {deleteConfirmDialog.impact.ip_classes_assigned}
                </Typography>
                <Typography variant="body2" sx={{ mb: 0.5 }}>
                  • Endereços IP configurados: {deleteConfirmDialog.impact.ip_addresses_configured}
                </Typography>
              </Box>
              
              <Typography variant="body2" color="error" sx={{ fontWeight: 'bold' }}>
                ⚠️ {deleteConfirmDialog.impact.warning}
              </Typography>
              
              <Typography variant="body2" sx={{ mt: 2 }}>
                Esta ação não pode ser desfeita.
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => setDeleteConfirmDialog({ open: false, interfaceId: 0, impact: null })} 
            color="inherit"
          >
            Cancelar
          </Button>
          <Button
            onClick={handleConfirmDelete}
            color="error"
            variant="contained"
          >
            Excluir Interface
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog de confirmação de remoção de classe IP */}
      <Dialog
        open={removeIPClassConfirmDialog.open}
        onClose={() => setRemoveIPClassConfirmDialog({ open: false, interfaceId: 0, ipClassId: 0, impact: null })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Confirmar Remoção da Classe IP</DialogTitle>
        <DialogContent>
          {removeIPClassConfirmDialog.impact && (
            <Box>
              <Typography variant="body1" sx={{ mb: 2 }}>
                Tem certeza que deseja remover a classe IP <strong>{removeIPClassConfirmDialog.impact.ip_class_name}</strong> da interface <strong>{removeIPClassConfirmDialog.impact.interface_name}</strong> do router <strong>{removeIPClassConfirmDialog.impact.router_name}</strong>?
              </Typography>
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                <strong>Impacto da remoção:</strong>
              </Typography>
              
              <Box sx={{ pl: 2, mb: 2 }}>
                <Typography variant="body2" sx={{ mb: 0.5 }}>
                  • Rede: {removeIPClassConfirmDialog.impact.network}
                </Typography>
                <Typography variant="body2" sx={{ mb: 0.5 }}>
                  • Gateway configurado: {removeIPClassConfirmDialog.impact.gateway_configured ? 'Sim' : 'Não'}
                </Typography>
                <Typography variant="body2" sx={{ mb: 0.5 }}>
                  • DNS configurado: {removeIPClassConfirmDialog.impact.dns_configured ? 'Sim' : 'Não'}
                </Typography>
              </Box>
              
              <Typography variant="body2" color="error" sx={{ fontWeight: 'bold' }}>
                ⚠️ {removeIPClassConfirmDialog.impact.warning}
              </Typography>
              
              <Typography variant="body2" sx={{ mt: 2 }}>
                Esta ação não pode ser desfeita.
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => setRemoveIPClassConfirmDialog({ open: false, interfaceId: 0, ipClassId: 0, impact: null })} 
            color="inherit"
          >
            Cancelar
          </Button>
          <Button
            onClick={handleConfirmRemoveIPClass}
            color="error"
            variant="contained"
          >
            Remover Classe IP
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
      >
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default RouterInterfaces;