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
  IconButton,
  Tooltip,
  Alert,
  Snackbar,
  Card,
  CardContent,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  NetworkCheck as NetworkIcon,
} from '@mui/icons-material';
import { networkService, IPClassCreate, IPClassUpdate } from '../services/networkService';
import { IPClass } from '../types';

const IPClasses: React.FC = () => {
  const [ipClasses, setIpClasses] = useState<IPClass[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingClass, setEditingClass] = useState<IPClass | null>(null);
  const [formData, setFormData] = useState<IPClassCreate>({
    nome: '',
    rede: '',
    gateway: '',
    dns1: '',
    dns2: '',
  });

  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success' as 'success' | 'error',
  });

  useEffect(() => {
    loadIPClasses();
  }, []);

  const loadIPClasses = async () => {
    try {
      setLoading(true);
      const data = await networkService.getIPClasses();
      setIpClasses(data);
    } catch (error) {
      console.error('Erro ao carregar classes IP:', error);
      showSnackbar('Erro ao carregar classes IP', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (ipClass?: IPClass) => {
    if (ipClass) {
      setEditingClass(ipClass);
      setFormData({
        nome: ipClass.nome,
        rede: ipClass.rede,
        gateway: ipClass.gateway || '',
        dns1: ipClass.dns1 || '',
        dns2: ipClass.dns2 || '',
      });
    } else {
      setEditingClass(null);
      setFormData({
        nome: '',
        rede: '',
        gateway: '',
        dns1: '',
        dns2: '',
      });
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingClass(null);
    setFormData({
      nome: '',
      rede: '',
      gateway: '',
      dns1: '',
      dns2: '',
    });
  };

  const handleSubmit = async () => {
    try {
      if (editingClass) {
        await networkService.updateIPClass(editingClass.id, formData);
        showSnackbar('Classe IP atualizada com sucesso', 'success');
      } else {
        await networkService.createIPClass(formData);
        showSnackbar('Classe IP criada com sucesso', 'success');
      }
      handleCloseDialog();
      loadIPClasses();
    } catch (error) {
      console.error('Erro ao salvar classe IP:', error);
      showSnackbar('Erro ao salvar classe IP', 'error');
    }
  };

  const handleDelete = async (classId: number) => {
    if (window.confirm('Tem certeza que deseja excluir esta classe IP?')) {
      try {
        await networkService.deleteIPClass(classId);
        showSnackbar('Classe IP excluída com sucesso', 'success');
        loadIPClasses();
      } catch (error) {
        console.error('Erro ao excluir classe IP:', error);
        showSnackbar('Erro ao excluir classe IP', 'error');
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

  return (
    <Box p={3}>
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
        <Box display="flex" alignItems="center">
          <NetworkIcon sx={{ mr: 1 }} />
          <Typography variant="h4" component="h1">
            Classes de IP
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog()}
        >
          Nova Classe IP
        </Button>
      </Box>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Gerenciamento de Redes IP
          </Typography>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
            Configure as classes de IP que serão atribuídas às interfaces dos routers.
            Cada classe define uma rede, gateway e servidores DNS.
          </Typography>
        </CardContent>
      </Card>

      <Box mt={3}>
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Nome</TableCell>
                <TableCell>Rede</TableCell>
                <TableCell>Gateway</TableCell>
                <TableCell>DNS Primário</TableCell>
                <TableCell>DNS Secundário</TableCell>
                <TableCell align="right">Ações</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {ipClasses.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    <Typography variant="body2" color="textSecondary">
                      Nenhuma classe IP cadastrada
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                ipClasses.map((ipClass) => (
                  <TableRow key={ipClass.id}>
                    <TableCell>
                      <Box display="flex" alignItems="center">
                        <NetworkIcon sx={{ mr: 1, color: 'primary.main' }} />
                        {ipClass.nome}
                      </Box>
                    </TableCell>
                    <TableCell>{ipClass.rede}</TableCell>
                    <TableCell>{ipClass.gateway || '-'}</TableCell>
                    <TableCell>{ipClass.dns1 || '-'}</TableCell>
                    <TableCell>{ipClass.dns2 || '-'}</TableCell>
                    <TableCell align="right">
                      <Tooltip title="Editar">
                        <IconButton
                          color="primary"
                          onClick={() => handleOpenDialog(ipClass)}
                        >
                          <EditIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Excluir">
                        <IconButton
                          color="error"
                          onClick={() => handleDelete(ipClass.id)}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>

      {/* Dialog para criar/editar classe IP */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingClass ? 'Editar Classe IP' : 'Nova Classe IP'}
        </DialogTitle>
        <DialogContent>
          <Box component="form" sx={{ mt: 1 }}>
            <TextField
              fullWidth
              label="Nome da Classe"
              value={formData.nome}
              onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
              margin="normal"
              required
              helperText="Ex: Rede Interna, DMZ, Clientes"
            />
            <TextField
              fullWidth
              label="Rede"
              value={formData.rede}
              onChange={(e) => setFormData({ ...formData, rede: e.target.value })}
              margin="normal"
              required
              placeholder="192.168.1.0/24"
              helperText="Formato: endereço/máscara (ex: 192.168.1.0/24)"
            />
            <TextField
              fullWidth
              label="Gateway"
              value={formData.gateway}
              onChange={(e) => setFormData({ ...formData, gateway: e.target.value })}
              margin="normal"
              placeholder="192.168.1.1"
            />
            <TextField
              fullWidth
              label="DNS Primário"
              value={formData.dns1}
              onChange={(e) => setFormData({ ...formData, dns1: e.target.value })}
              margin="normal"
              placeholder="8.8.8.8"
            />
            <TextField
              fullWidth
              label="DNS Secundário"
              value={formData.dns2}
              onChange={(e) => setFormData({ ...formData, dns2: e.target.value })}
              margin="normal"
              placeholder="8.8.4.4"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancelar</Button>
          <Button onClick={handleSubmit} variant="contained">
            {editingClass ? 'Atualizar' : 'Criar'}
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

export default IPClasses;