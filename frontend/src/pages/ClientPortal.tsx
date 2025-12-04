import React, { useEffect, useState } from 'react';
import {
  Box, Paper, Typography, Card, CardContent, Grid, Chip,
  List, ListItem, ListItemText, ListItemIcon, Divider,
  Button, Avatar, useTheme, useMediaQuery, CircularProgress
} from '@mui/material';
import {
  DocumentTextIcon, WifiIcon, ChatBubbleLeftIcon, CreditCardIcon,
  UserIcon, BellIcon, DocumentTextIcon as ReceiptIcon, CogIcon
} from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/AuthContext';
import clientService from '../services/clientService';
import { companyService } from '../services/companyService';

interface ClienteInfo {
  id: number;
  nome_razao_social: string;
  cpf_cnpj: string;
  email: string;
  telefone: string;
  enderecos: any[];
  empresa_id: number;
}

interface EmpresaInfo {
  id: number;
  razao_social: string;
  nome_fantasia?: string;
  cnpj: string;
  email: string;
  telefone?: string;
  logo_url?: string;
}

interface ServicoContratado {
  id: number;
  servico_nome: string;
  status: string;
  valor_mensal: number;
  data_contratacao: string;
}

interface Fatura {
  id: number;
  numero: string;
  valor_total: number;
  data_emissao: string;
  data_vencimento: string;
  status: string;
}

interface Ticket {
  id: number;
  titulo: string;
  status: string;
  prioridade: string;
  created_at: string;
}

const ClientPortal: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { user, logout } = useAuth();

  const [clienteInfo, setClienteInfo] = useState<ClienteInfo | null>(null);
  const [empresaInfo, setEmpresaInfo] = useState<EmpresaInfo | null>(null);
  const [servicos, setServicos] = useState<ServicoContratado[]>([]);
  const [faturas, setFaturas] = useState<Fatura[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadClientData();
  }, []);

  useEffect(() => {
    if (clienteInfo?.empresa_id) {
      loadEmpresaInfo();
    }
  }, [clienteInfo]);

  const loadClientData = async () => {
    try {
      setLoading(true);
      if (user?.cliente_id) {
        await Promise.all([
          loadClienteInfo(),
          loadServicos(),
          loadFaturas(),
          loadTickets()
        ]);
      }
    } catch (error) {
      console.error('Erro ao carregar dados do cliente:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadClienteInfo = async () => {
    try {
      const clientData = await clientService.getCurrentClient();
      setClienteInfo({
        id: clientData.id,
        nome_razao_social: clientData.nome_razao_social,
        cpf_cnpj: clientData.cpf_cnpj,
        email: clientData.email || '',
        telefone: clientData.telefone || '',
        enderecos: clientData.enderecos || [],
        empresa_id: clientData.empresa_id
      });
    } catch (error) {
      console.error('Erro ao carregar informações do cliente:', error);
    }
  };

  const loadEmpresaInfo = async () => {
    try {
      // Usar endpoint do portal do cliente para obter dados da empresa (token de cliente)
      const empresaData = await clientService.getCurrentCompany();
      console.log('Dados da empresa carregados (cliente):', empresaData);
      setEmpresaInfo({
        id: empresaData.id,
        razao_social: empresaData.razao_social,
        nome_fantasia: empresaData.nome_fantasia,
        cnpj: empresaData.cnpj,
        email: empresaData.email,
        telefone: empresaData.telefone,
        logo_url: empresaData.logo_url
      });
    } catch (error) {
      console.error('Erro ao carregar informações da empresa (cliente):', error);
    }
  };

  const loadServicos = async () => {
    try {
      // TODO: Implementar quando houver endpoint de serviços contratados
      // Por enquanto, deixar vazio ou mock
      setServicos([]);
    } catch (error) {
      console.error('Erro ao carregar serviços:', error);
    }
  };

  const loadFaturas = async () => {
    try {
      // TODO: Implementar quando houver endpoint de faturas
      // Por enquanto, deixar vazio ou mock
      setFaturas([]);
    } catch (error) {
      console.error('Erro ao carregar faturas:', error);
    }
  };

  const loadTickets = async () => {
    try {
      // TODO: Implementar quando houver endpoint de tickets
      // Por enquanto, deixar vazio ou mock
      setTickets([]);
    } catch (error) {
      console.error('Erro ao carregar tickets:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'ativo': return 'success';
      case 'inativo': return 'error';
      case 'suspenso': return 'warning';
      case 'aberto': return 'info';
      case 'em_andamento': return 'warning';
      case 'resolvido': return 'success';
      case 'fechado': return 'default';
      case 'pago': return 'success';
      case 'pendente': return 'warning';
      case 'atrasado': return 'error';
      default: return 'default';
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
    <Box sx={{ p: isMobile ? 1 : 3, minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
      {/* Header */}
      <Paper sx={{ p: isMobile ? 2 : 3, mb: 3, backgroundColor: 'primary.main', color: 'white' }}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box display="flex" alignItems="center" gap={2}>
            {empresaInfo?.logo_url ? (
              <Box
                component="img"
                src={`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}${empresaInfo.logo_url}`}
                alt={`${empresaInfo.nome_fantasia || empresaInfo.razao_social} Logo`}
                sx={{
                  height: 60,
                  width: 60,
                  borderRadius: 1,
                  objectFit: 'contain',
                  backgroundColor: 'rgba(255,255,255,0.1)',
                  p: 1
                }}
                onError={(e: React.SyntheticEvent<HTMLImageElement, Event>) => {
                  console.error('Erro ao carregar logo da empresa:', empresaInfo.logo_url);
                  // Esconde a imagem com erro
                  e.currentTarget.style.display = 'none';
                }}
              />
            ) : (
              <Avatar sx={{ width: 60, height: 60, bgcolor: 'rgba(255,255,255,0.2)' }}>
                <UserIcon className="w-8 h-8" />
              </Avatar>
            )}
            <Box>
              <Typography variant="h4" component="h1" sx={{ fontSize: isMobile ? '1.5rem' : '2rem' }}>
                Portal do Cliente
              </Typography>
              <Typography variant="subtitle1" sx={{ opacity: 0.9 }}>
                {empresaInfo?.nome_fantasia || empresaInfo?.razao_social || 'Bem-vindo ao seu painel de controle'}
              </Typography>
            </Box>
          </Box>
          <Box display="flex" alignItems="center" gap={2}>
            <Typography variant="body1" sx={{ opacity: 0.9 }}>
              Olá, {(clienteInfo?.nome_razao_social || user?.full_name || 'Cliente').split(' ')[0]}
            </Typography>
            <Button
              variant="outlined"
              color="inherit"
              onClick={() => {
                logout();
                window.location.href = '/';
              }}
              sx={{
                borderColor: 'rgba(255,255,255,0.3)',
                color: 'white',
                '&:hover': {
                  borderColor: 'white',
                  backgroundColor: 'rgba(255,255,255,0.1)',
                }
              }}
            >
              Sair
            </Button>
          </Box>
        </Box>
      </Paper>

      <Grid container spacing={isMobile ? 2 : 3}>
        {/* Informações do Cliente */}
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2} mb={2}>
                <UserIcon className="w-6 h-6" />
                <Typography variant="h6">Meus Dados</Typography>
              </Box>
              <Divider sx={{ mb: 2 }} />
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">Nome</Typography>
                <Typography variant="body1" sx={{ fontWeight: 500 }}>
                  {clienteInfo?.nome_razao_social || 'Carregando...'}
                </Typography>
              </Box>
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">CPF/CNPJ</Typography>
                <Typography variant="body1">
                  {clienteInfo?.cpf_cnpj || 'Não informado'}
                </Typography>
              </Box>
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">Email</Typography>
                <Typography variant="body1">
                  {clienteInfo?.email || 'Não informado'}
                </Typography>
              </Box>
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">Telefone</Typography>
                <Typography variant="body1">
                  {clienteInfo?.telefone || 'Não informado'}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Serviços Contratados */}
        <Grid item xs={12} md={8}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2} mb={2}>
                <WifiIcon className="w-6 h-6" />
                <Typography variant="h6">Serviços Contratados</Typography>
              </Box>
              <Divider sx={{ mb: 2 }} />
              {servicos.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  Nenhum serviço contratado encontrado.
                </Typography>
              ) : (
                <List>
                  {servicos.map((servico) => (
                    <ListItem key={servico.id} sx={{ px: 0 }}>
                      <ListItemText
                        primary={
                          <Box display="flex" justifyContent="space-between" alignItems="center">
                            <Typography variant="subtitle1">{servico.servico_nome}</Typography>
                            <Chip
                              label={servico.status}
                              color={getStatusColor(servico.status)}
                              size="small"
                            />
                          </Box>
                        }
                        secondary={
                          <Box>
                            <Typography variant="body2" color="text.secondary">
                              Contratado em: {new Date(servico.data_contratacao).toLocaleDateString('pt-BR')}
                            </Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              R$ {servico.valor_mensal.toFixed(2)}/mês
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Faturas */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                <Box display="flex" alignItems="center" gap={2}>
                  <ReceiptIcon className="w-6 h-6" />
                  <Typography variant="h6">Últimas Faturas</Typography>
                </Box>
                <Button size="small" variant="outlined">
                  Ver Todas
                </Button>
              </Box>
              <Divider sx={{ mb: 2 }} />
              {faturas.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  Nenhuma fatura encontrada.
                </Typography>
              ) : (
                <List>
                  {faturas.slice(0, 3).map((fatura) => (
                    <ListItem key={fatura.id} sx={{ px: 0 }}>
                      <ListItemText
                        primary={
                          <Box display="flex" justifyContent="space-between" alignItems="center">
                            <Typography variant="subtitle1">#{fatura.numero}</Typography>
                            <Chip
                              label={fatura.status}
                              color={getStatusColor(fatura.status)}
                              size="small"
                            />
                          </Box>
                        }
                        secondary={
                          <Box>
                            <Typography variant="body2" color="text.secondary">
                              Vencimento: {new Date(fatura.data_vencimento).toLocaleDateString('pt-BR')}
                            </Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              R$ {fatura.valor_total.toFixed(2)}
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Tickets de Suporte */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                <Box display="flex" alignItems="center" gap={2}>
                  <ChatBubbleLeftIcon className="w-6 h-6" />
                  <Typography variant="h6">Tickets de Suporte</Typography>
                </Box>
                <Button size="small" variant="outlined">
                  Novo Ticket
                </Button>
              </Box>
              <Divider sx={{ mb: 2 }} />
              {tickets.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  Nenhum ticket encontrado.
                </Typography>
              ) : (
                <List>
                  {tickets.slice(0, 3).map((ticket) => (
                    <ListItem key={ticket.id} sx={{ px: 0 }}>
                      <ListItemText
                        primary={
                          <Box display="flex" justifyContent="space-between" alignItems="center">
                            <Typography variant="subtitle1" sx={{ fontSize: '0.9rem' }}>
                              {ticket.titulo}
                            </Typography>
                            <Chip
                              label={ticket.status.replace('_', ' ')}
                              color={getStatusColor(ticket.status)}
                              size="small"
                            />
                          </Box>
                        }
                        secondary={
                          <Typography variant="body2" color="text.secondary">
                            Criado em: {new Date(ticket.created_at).toLocaleDateString('pt-BR')}
                          </Typography>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Ações Rápidas */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" mb={2}>Ações Rápidas</Typography>
              <Divider sx={{ mb: 2 }} />
              <Grid container spacing={2}>
                <Grid item xs={6} sm={3}>
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<ReceiptIcon className="w-5 h-5" />}
                    sx={{ height: 80, flexDirection: 'column', gap: 1 }}
                  >
                    <Typography variant="body2">Faturas</Typography>
                  </Button>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<ChatBubbleLeftIcon className="w-5 h-5" />}
                    sx={{ height: 80, flexDirection: 'column', gap: 1 }}
                  >
                    <Typography variant="body2">Suporte</Typography>
                  </Button>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<DocumentTextIcon className="w-5 h-5" />}
                    sx={{ height: 80, flexDirection: 'column', gap: 1 }}
                  >
                    <Typography variant="body2">Contratos</Typography>
                  </Button>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<CogIcon className="w-5 h-5" />}
                    sx={{ height: 80, flexDirection: 'column', gap: 1 }}
                  >
                    <Typography variant="body2">Configurações</Typography>
                  </Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Sobre a Empresa */}
        {empresaInfo && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" gap={2} mb={2}>
                  <UserIcon className="w-6 h-6" />
                  <Typography variant="h6">Sobre a Empresa</Typography>
                </Box>
                <Divider sx={{ mb: 2 }} />
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2" color="text.secondary">Razão Social</Typography>
                      <Typography variant="body1" sx={{ fontWeight: 500 }}>
                        {empresaInfo.razao_social}
                      </Typography>
                    </Box>
                    {empresaInfo.nome_fantasia && (
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" color="text.secondary">Nome Fantasia</Typography>
                        <Typography variant="body1">
                          {empresaInfo.nome_fantasia}
                        </Typography>
                      </Box>
                    )}
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2" color="text.secondary">CNPJ</Typography>
                      <Typography variant="body1">
                        {empresaInfo.cnpj}
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2" color="text.secondary">Email</Typography>
                      <Typography variant="body1">
                        {empresaInfo.email}
                      </Typography>
                    </Box>
                    {empresaInfo.telefone && (
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" color="text.secondary">Telefone</Typography>
                        <Typography variant="body1">
                          {empresaInfo.telefone}
                        </Typography>
                      </Box>
                    )}
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default ClientPortal;