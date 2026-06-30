import React, { useState, useEffect, useRef } from 'react';
import { Typography, Box, Grid, CircularProgress, Fade, Grow } from '@mui/material';
import {
  UsersIcon,
  DocumentCheckIcon,
  CurrencyDollarIcon,
  ExclamationTriangleIcon,
  DocumentTextIcon,
  ChartPieIcon,
  BuildingOfficeIcon,
  WifiIcon
} from '@heroicons/react/24/outline';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';
import api from '../services/api';
import useFitText from '../hooks/useFitText';
import { useNavigate } from 'react-router-dom';
import { useCompany } from '../contexts/CompanyContext';
import { useAuth } from '../contexts/AuthContext';

// Custom Card Component with Glassmorphism and Hover Effects
const PremiumCard = React.forwardRef<HTMLDivElement, { children: React.ReactNode; sx?: any; onClick?: () => void }>(
  ({ children, sx, onClick }, ref) => (
    <Box
      ref={ref}
      onClick={onClick}
      sx={{
        background: 'rgba(255, 255, 255, 0.85)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        borderRadius: '24px',
        border: '1px solid rgba(255, 255, 255, 0.4)',
        boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.05)',
        padding: 3,
        transition: 'all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1)',
        cursor: onClick ? 'pointer' : 'default',
        position: 'relative',
        overflow: 'hidden',
        '&:hover': onClick ? {
          transform: 'translateY(-6px)',
          boxShadow: '0 12px 40px 0 rgba(31, 38, 135, 0.1)',
          border: '1px solid rgba(255, 255, 255, 0.6)',
        } : {},
        ...sx
      }}
    >
      {children}
    </Box>
  )
);

PremiumCard.displayName = 'PremiumCard';

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState<any>(null);
  const navigate = useNavigate();
  const { activeCompany } = useCompany();
  const { hasPermission } = useAuth();
  const canViewFinancials = hasPermission('company_manage');

  useEffect(() => {
    if (!activeCompany) return;
    
    setLoading(true);
    const fetchDashboardData = async () => {
      try {
        const response = await api.get('/dashboard/stats');
        setDashboardData(response.data);
      } catch (error) {
        console.error('Erro ao carregar dados do dashboard:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, [activeCompany]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
        <CircularProgress size={60} thickness={4} sx={{ color: '#4f46e5' }} />
      </Box>
    );
  }

  const stats = dashboardData?.stats || {};
  const formatCurrency = (val: number) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val || 0);

  // Main Metrics
  const mainMetrics = [
    {
      title: 'Total de Clientes',
      value: stats.clientes_total || 0,
      icon: UsersIcon,
      color: '#4f46e5', // Indigo
      bgLight: '#e0e7ff',
      trend: '+12% vs mês ant.',
    },
    {
      title: 'Contratos Ativos',
      value: stats.contratos_ativos || 0,
      icon: DocumentCheckIcon,
      color: '#10b981', // Emerald
      bgLight: '#d1fae5',
      trend: '+5 novos hoje',
    },
    {
      title: 'Recebido (Mês)',
      value: formatCurrency(stats.recebido_mes),
      icon: CurrencyDollarIcon,
      color: '#06b6d4', // Cyan
      bgLight: '#cffafe',
      trend: 'Dentro da meta',
    },
    {
      title: 'Inadimplência',
      value: formatCurrency(stats.vencido_total),
      icon: ExclamationTriangleIcon,
      color: '#f43f5e', // Rose
      bgLight: '#ffe4e6',
      trend: 'Atenção necessária',
    },
  ];

  const visibleMetrics = canViewFinancials 
    ? mainMetrics 
    : mainMetrics.slice(0, 2); // Somente Clientes e Contratos

  const StatNumber: React.FC<{ value: string | number; color?: string }> = ({ value, color }) => {
    const ref = useRef<HTMLElement | null>(null);
    const fitPx = useFitText(ref, { min: 20, max: 42 });
    return (
      <Typography
        ref={ref as any}
        component="div"
        sx={{
          fontWeight: 800,
          color: color || '#1e293b',
          lineHeight: 1.2,
          mb: 0.5,
          fontFamily: '"Plus Jakarta Sans", "Inter", sans-serif',
          letterSpacing: '-1px'
        }}
        style={{ fontSize: `${Math.round(fitPx)}px` }}
      >
        {value}
      </Typography>
    );
  };

  const monthlyData = dashboardData?.charts?.monthly || [];
  const statusData = dashboardData?.charts?.status || [
    { name: 'Ativos', value: 1, color: '#10b981' },
    { name: 'Bloqueados', value: 0, color: '#f43f5e' },
  ];

  // Custom Tooltip for Area Chart
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <Box sx={{ background: 'rgba(255,255,255,0.95)', p: 2, borderRadius: 3, boxShadow: '0 4px 20px rgba(0,0,0,0.1)', border: '1px solid #e2e8f0' }}>
          <Typography variant="subtitle2" color="text.secondary">{label}</Typography>
          <Typography variant="h6" color="primary.main" fontWeight="bold">
            {formatCurrency(payload[0].value)}
          </Typography>
        </Box>
      );
    }
    return null;
  };

  return (
    <Box sx={{ pb: 6, px: { xs: 1, md: 2 } }}>
      
      {/* Header / Welcome Area with subtle gradient background */}
      <Box sx={{ 
        mb: 5, 
        p: 4, 
        borderRadius: '28px', 
        background: 'linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%)',
        color: 'white',
        position: 'relative',
        overflow: 'hidden',
        boxShadow: '0 10px 30px rgba(79, 70, 229, 0.3)'
      }}>
        {/* Abstract shapes in background */}
        <Box sx={{ position: 'absolute', top: -50, right: -20, width: 200, height: 200, borderRadius: '50%', background: 'rgba(255,255,255,0.1)', filter: 'blur(20px)' }} />
        <Box sx={{ position: 'absolute', bottom: -80, left: '20%', width: 150, height: 150, borderRadius: '50%', background: 'rgba(255,255,255,0.1)', filter: 'blur(15px)' }} />
        
        <Grid container spacing={2} alignItems="center" sx={{ position: 'relative', zIndex: 1 }}>
          <Grid item xs={12} md={8}>
            <Typography variant="h3" sx={{ fontWeight: 800, mb: 1, letterSpacing: '-1px', fontFamily: '"Plus Jakarta Sans", "Inter", sans-serif' }}>
              Visão Geral
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 400, opacity: 0.9 }}>
              Bem-vindo ao centro de comando do seu provedor.
            </Typography>
          </Grid>
          {canViewFinancials && (
            <Grid item xs={12} md={4} sx={{ display: 'flex', justifyContent: { xs: 'flex-start', md: 'flex-end' } }}>
               <Box sx={{ background: 'rgba(255,255,255,0.2)', p: 2, borderRadius: '20px', backdropFilter: 'blur(10px)', display: 'flex', alignItems: 'center', gap: 2 }}>
                  <ChartPieIcon className="w-8 h-8 text-white" />
                  <Box>
                    <Typography variant="caption" sx={{ opacity: 0.8, textTransform: 'uppercase', letterSpacing: '1px' }}>Meta do Mês</Typography>
                    <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1 }}>{formatCurrency(stats.pendente_mes + stats.recebido_mes)}</Typography>
                  </Box>
               </Box>
            </Grid>
          )}
        </Grid>
      </Box>

      {/* Top Metrics Row */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {visibleMetrics.map((metric, idx) => (
          <Grow in={true} timeout={500 + (idx * 200)} key={idx}>
            <Grid item xs={12} sm={6} lg={3}>
              <PremiumCard>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                  <Box sx={{ 
                    p: 1.5, 
                    borderRadius: '16px', 
                    background: metric.bgLight,
                    color: metric.color,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <metric.icon style={{ width: 26, height: 26 }} strokeWidth={2} />
                  </Box>
                  <Typography variant="caption" sx={{ px: 1.5, py: 0.5, borderRadius: '12px', background: '#f1f5f9', color: '#64748b', fontWeight: 600 }}>
                    {metric.trend}
                  </Typography>
                </Box>
                
                <StatNumber value={metric.value} />
                <Typography variant="body2" sx={{ color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', fontSize: '0.75rem' }}>
                  {metric.title}
                </Typography>
              </PremiumCard>
            </Grid>
          </Grow>
        ))}
      </Grid>

      {/* Charts Row */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
         {/* Area Chart - Revenue */}
        {canViewFinancials && (
          <Grid item xs={12} lg={8}>
            <Fade in={true} timeout={1000}>
              <PremiumCard sx={{ height: 420, display: 'flex', flexDirection: 'column' }}>
                <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 800, color: '#1e293b', fontFamily: '"Plus Jakarta Sans", sans-serif' }}>
                      Evolução do Faturamento
                    </Typography>
                    <Typography variant="body2" color="text.secondary">Receitas consolidadas dos últimos 6 meses</Typography>
                  </Box>
                </Box>
                <Box sx={{ flexGrow: 1, minHeight: 0 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={monthlyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#4f46e5" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                      <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} dy={10} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} tickFormatter={(value) => `R$ ${value / 1000}k`} />
                      <RechartsTooltip 
                        contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.08)' }}
                        formatter={(value: any) => [formatCurrency(value), 'Faturamento']}
                      />
                      <Area type="monotone" dataKey="value" stroke="#4f46e5" strokeWidth={3} fillOpacity={1} fill="url(#colorValue)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </Box>
              </PremiumCard>
            </Fade>
          </Grid>
        )}

        {/* Doughnut Chart - Status */}
        <Grid item xs={12} lg={canViewFinancials ? 4 : 12}>
          <Fade in={true} timeout={1200}>
            <PremiumCard sx={{ height: 420, display: 'flex', flexDirection: 'column' }}>
              <Typography variant="h6" sx={{ fontWeight: 800, color: '#1e293b', fontFamily: '"Plus Jakarta Sans", sans-serif', mb: 1 }}>
                Status dos Contratos
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Distribuição atual da base</Typography>
              
              <Box sx={{ flexGrow: 1, width: '100%', position: 'relative' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={statusData}
                      cx="50%"
                      cy="50%"
                      innerRadius={80}
                      outerRadius={110}
                      paddingAngle={5}
                      dataKey="value"
                      stroke="none"
                    >
                      {statusData.map((entry: any, index: number) => (
                        <Cell key={`cell-${index}`} fill={entry.color} style={{ filter: `drop-shadow(0px 4px 8px ${entry.color}40)` }} />
                      ))}
                    </Pie>
                    <RechartsTooltip 
                      contentStyle={{ borderRadius: '16px', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }}
                      itemStyle={{ fontWeight: 'bold' }}
                    />
                    <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontWeight: 600, fontSize: '14px', color: '#475569' }} />
                  </PieChart>
                </ResponsiveContainer>
                
                {/* Center text in Doughnut */}
                <Box sx={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -70%)', textAlign: 'center', pointerEvents: 'none' }}>
                  <Typography variant="h4" sx={{ fontWeight: 800, color: '#1e293b', lineHeight: 1 }}>{stats.contratos_ativos + stats.contratos_bloqueados}</Typography>
                  <Typography variant="caption" sx={{ color: '#64748b', fontWeight: 600 }}>TOTAL</Typography>
                </Box>
              </Box>
            </PremiumCard>
          </Fade>
        </Grid>

      </Grid>

      {/* Quick Actions & Extra Stats */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={7}>
          <Typography variant="h6" sx={{ fontWeight: 800, mb: 3, color: '#1e293b', fontFamily: '"Plus Jakarta Sans", sans-serif' }}>
            Ações Rápidas
          </Typography>
          <Grid container spacing={2}>
            {[
              { label: 'Novo Cliente', icon: UsersIcon, color: '#3b82f6', path: '/clients' },
              { label: 'Gerar Faturas', icon: CurrencyDollarIcon, color: '#10b981', path: '/receivables' },
              { label: 'Emitir NFCom', icon: DocumentTextIcon, color: '#8b5cf6', path: '/nfcom?new=true' },
              { label: 'Provisionar', icon: WifiIcon, color: '#f59e0b', path: '/routers' },
            ].map((action, idx) => (
              <Grid item xs={6} sm={3} key={idx}>
                <PremiumCard onClick={() => navigate(action.path)} sx={{ p: 2, textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
                  <Box sx={{ p: 1.5, borderRadius: '14px', background: `${action.color}15`, color: action.color }}>
                    <action.icon className="w-8 h-8" strokeWidth={2} />
                  </Box>
                  <Typography variant="body2" sx={{ fontWeight: 700, color: '#334155' }}>
                    {action.label}
                  </Typography>
                </PremiumCard>
              </Grid>
            ))}
          </Grid>
        </Grid>
        
        {/* NFCom Metrics */}
        {canViewFinancials && (
          <Grid item xs={12} md={5}>
            <Fade in={true} timeout={2000}>
              <PremiumCard>
                <Typography variant="h6" sx={{ fontWeight: 800, mb: 3, color: '#1e293b', fontFamily: '"Plus Jakarta Sans", sans-serif' }}>
                  Métricas de NFCom
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="body1" sx={{ fontWeight: 600, color: '#475569' }}>Notas Emitidas (Total)</Typography>
                    <Typography variant="h6" sx={{ fontWeight: 800, color: '#0f172a' }}>{stats.nfcom_emitidas || 0}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body1" sx={{ fontWeight: 600, color: '#475569' }}>Valor Faturado em Notas</Typography>
                    <Typography variant="h6" sx={{ fontWeight: 800, color: '#10b981' }}>{formatCurrency(stats.valor_total_nfcom)}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body1" sx={{ fontWeight: 600, color: '#475569' }}>Notas Pendentes de Sefaz</Typography>
                    <Typography variant="h6" sx={{ fontWeight: 800, color: '#f59e0b' }}>{dashboardData?.stats?.pendentes || 0}</Typography>
                  </Grid>
                </Grid>
              </PremiumCard>
            </Fade>
          </Grid>
        )}
      </Grid>
      
    </Box>
  );
};

export default Dashboard;