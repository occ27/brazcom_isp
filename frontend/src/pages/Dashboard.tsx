import React, { useState, useEffect, useRef } from 'react';
import { Typography, Box, Paper, Grid, CircularProgress } from '@mui/material';
import {
  DocumentTextIcon,
  BuildingOfficeIcon,
  UserIcon,
  ChartBarIcon,
  UsersIcon
} from '@heroicons/react/24/outline';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import api from '../services/api';
import useFitText from '../hooks/useFitText';
import { useNavigate } from 'react-router-dom';

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState<any>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const response = await api.get('/dashboard/stats');
        setDashboardData(response.data);
      } catch (error) {
        console.error('Erro ao carregar dados do dashboard:', error);
        // Fallback para dados estáticos se houver erro
        setDashboardData({
          stats: {
            nfcom_emitidas: 127,
            valor_total: 0,
            autorizadas: 85,
            pendentes: 32,
            canceladas: 10,
          },
          charts: {
            status: [
              { name: 'Autorizadas', value: 85, color: '#4caf50' },
              { name: 'Pendentes', value: 32, color: '#ff9800' },
              { name: 'Canceladas', value: 10, color: '#f44336' },
            ],
            monthly: [
              { month: 'Jan', valor: 45000 },
              { month: 'Fev', valor: 52000 },
              { month: 'Mar', valor: 48000 },
              { month: 'Abr', valor: 61000 },
              { month: 'Mai', valor: 55000 },
              { month: 'Jun', valor: 67000 },
            ]
          }
        });
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const navigate = useNavigate();

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  const colorMap: Record<string, { bg: string; border: string; iconBg: string; text: string }> = {
    blue: { bg: '#e3f2fd', border: '#2196f320', iconBg: '#1976d2', text: '#1565c0' },
    green: { bg: '#e8f5e9', border: '#4caf5020', iconBg: '#2e7d32', text: '#2e7d32' },
    purple: { bg: '#f3e5f5', border: '#9c27b020', iconBg: '#6a1b9a', text: '#6a1b9a' },
    orange: { bg: '#fff3e0', border: '#ff980020', iconBg: '#f57c00', text: '#f57c00' },
  };

  const stats = [
    {
      title: 'Emitidas',
      value: dashboardData?.stats?.nfcom_emitidas?.toString() || '0',
      icon: DocumentTextIcon,
      color: 'blue',
    },
    {
      title: 'Valor Total',
      value: new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(dashboardData?.stats?.valor_total || 0),
      icon: ChartBarIcon,
      color: 'green',
    },
    {
      title: 'Autorizadas',
      value: dashboardData?.stats?.autorizadas?.toString() || '0',
      icon: UserIcon,
      color: 'purple',
    },
    {
      title: 'Pendentes',
      value: dashboardData?.stats?.pendentes?.toString() || '0',
      icon: BuildingOfficeIcon,
      color: 'orange',
    },
  ];

  

  const computeFontSizes = (value: string | number) => {
    const s = String(value);
    const len = s.length;
    if (len <= 3) return { xs: '1.25rem', sm: '1.5rem', md: '1.875rem' };
    if (len <= 6) return { xs: '1rem', sm: '1.25rem', md: '1.5rem' };
    if (len <= 10) return { xs: '0.9rem', sm: '1rem', md: '1.25rem' };
  };

  // Small component to render the number with auto-fit
  const StatNumber: React.FC<{ value: string | number; color?: string }> = ({ value, color }) => {
    const ref = useRef<HTMLElement | null>(null);
    const fitPx = useFitText(ref, { min: 12, max: 36 });
    return (
      <Typography
        ref={ref as any}
        variant="h4"
        component="div"
        sx={{
          fontWeight: 'bold',
          mb: 1,
          color: color || 'text.primary',
          lineHeight: 1.05,
          width: '100%',
          textAlign: 'center',
        }}
        style={{ fontSize: `${Math.round(fitPx)}px` }}
        title={typeof value === 'string' ? value : undefined}
      >
        {value}
      </Typography>
    );
  };

  // Dados para gráfico de pizza - Status das NFComs
  const statusData = dashboardData?.charts?.status || [
    { name: 'Autorizadas', value: 85, color: '#4caf50' },
    { name: 'Pendentes', value: 32, color: '#ff9800' },
    { name: 'Canceladas', value: 10, color: '#f44336' },
  ];

  // Dados para gráfico de barras - Valores mensais
  const monthlyData = dashboardData?.charts?.monthly || [
    { month: 'Jan', valor: 45000 },
    { month: 'Fev', valor: 52000 },
    { month: 'Mar', valor: 48000 },
    { month: 'Abr', valor: 61000 },
    { month: 'Mai', valor: 55000 },
    { month: 'Jun', valor: 67000 },
  ];

  return (
    <Box>
      {/* Header com logo */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <img src="/logo_brazcom_isp.PNG" alt="Brazcom ISP Logo" style={{ height: '100px', marginRight: 0 }} />
        <Box>
          <Box component="header">
            <Typography
              variant="h4"
              component="div"
              sx={{ fontWeight: 900, color: '#0b3d91', lineHeight: 1 }}
            >
              Brazcom
            </Typography>
            <Typography
              variant="subtitle1"
              component="div"
              sx={{ fontWeight: 700, color: '#0b3d91', mt: 0.25, fontSize: { xs: '1rem', sm: '1.25rem' } }}
            >
              ISP Suite
            </Typography>
          </Box>
        </Box>
      </Box>

      {/* Cards de estatísticas */}
      <Grid container spacing={3} columns={10} sx={{ mb: 2 }}>
        {stats.map((stat, index) => (
          <Grid item key={index} xs={10} sm={5} md={stat.title === 'Valor Total' ? 4 : 2}>
            <Paper
              sx={{
                p: 3,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                textAlign: 'center',
                minHeight: 140,
                  background: `linear-gradient(135deg, ${colorMap[stat.color].bg} 0%, #ffffff 100%)`,
                  border: `1px solid ${colorMap[stat.color].border}`,
              }}
            >
              <Box
                sx={{
                  width: 56,
                  height: 56,
                  borderRadius: 3,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  mb: 2,
                  bgcolor: colorMap[stat.color].iconBg,
                  color: '#fff', // ensures icons using currentColor get white stroke/fill
                  boxShadow: 2,
                }}
              >
                  <stat.icon style={{ width: 28, height: 28 }} />
              </Box>
                <StatNumber value={stat.value} color={colorMap[stat.color].text} />
              <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
                {stat.title}
              </Typography>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {/* Gráficos */}
      <Grid container spacing={3} sx={{ mb: 2 }}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: 350 }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: 'primary.main' }}>
              📊 Distribuição por Status das NFComs
            </Typography>
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {statusData.map((entry: { name: string; value: number; color: string }, index: number) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: 350 }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: 'primary.main' }}>
              📈 Valores Mensais (R$)
            </Typography>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={monthlyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip formatter={(value) => [new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value as number), 'Valor']} />
                <Legend />
                <Bar dataKey="valor" fill="#2196f3" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

      <Box sx={{ mt: 2 }}>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: 'primary.main' }}>
          ⚡ Ações Rápidas
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={4}>
              <Paper sx={{ p: 3, cursor: 'pointer', '&:hover': { bgcolor: 'action.hover', transform: 'translateY(-2px)', transition: 'all 0.2s' }, borderRadius: 2, boxShadow: 1 }} onClick={() => navigate('/nfcom?new=true')}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <DocumentTextIcon style={{ width: 24, height: 24, color: '#1976d2', stroke: '#1976d2', marginRight: 12 }} strokeWidth={1.5} />
                <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                  Emitir NFCom
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Criar uma nova NFCom
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={6} md={4}>
              <Paper sx={{ p: 3, cursor: 'pointer', '&:hover': { bgcolor: 'action.hover', transform: 'translateY(-2px)', transition: 'all 0.2s' }, borderRadius: 2, boxShadow: 1 }} onClick={() => navigate('/clients')}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <UsersIcon style={{ width: 24, height: 24, color: '#2e7d32', stroke: '#2e7d32', marginRight: 12 }} strokeWidth={1.5} />
                <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                    Clientes
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Gerenciar clientes e endereços
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={6} md={4}>
              <Paper sx={{ p: 3, cursor: 'pointer', '&:hover': { bgcolor: 'action.hover', transform: 'translateY(-2px)', transition: 'all 0.2s' }, borderRadius: 2, boxShadow: 1 }} onClick={() => navigate('/contracts')}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <DocumentTextIcon style={{ width: 24, height: 24, color: '#f57c00', stroke: '#f57c00', marginRight: 12 }} strokeWidth={1.5} />
                <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                  Contratos
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Gerenciar contratos e cobranças
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default Dashboard;