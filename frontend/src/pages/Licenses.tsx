import React, { useState, useEffect } from 'react';
import { 
    Typography, Box, Paper, Button, Grid, Card, CardContent, 
    Divider, Alert, CircularProgress, Chip
} from '@mui/material';
import { 
    CheckCircleIcon, ClockIcon, InformationCircleIcon
} from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/AuthContext';
import { useCompany } from '../contexts/CompanyContext';
import { licenseService, License, LicensePricingPlan } from '../services/licenseService';
import { stringifyError } from '../utils/error';

const Licenses: React.FC = () => {
    const { user } = useAuth();
    const { activeCompany } = useCompany();
    const [loading, setLoading] = useState(true);
    const [licenses, setLicenses] = useState<License[]>([]);
    const [pricingPlans, setPricingPlans] = useState<LicensePricingPlan[]>([]);
    const [activeLicense, setActiveLicense] = useState<License | null>(null);
    const [error, setError] = useState<string | null>(null);

    const PIX_KEY = "345295fd-e0b4-4943-9651-5cdf1ba537a0";
    const PIX_NAME = "Orlando Carlos Do Carmo";

    useEffect(() => {
        if (activeCompany) {
            loadLicenses();
        }
    }, [activeCompany]);

    const loadLicenses = async () => {
        if (!activeCompany) return;
        try {
            setLoading(true);
            const [licenseData, plansData] = await Promise.all([
                licenseService.getCompanyLicenses(activeCompany.id),
                licenseService.getActivePlans()
            ]);
            
            setLicenses(licenseData);
            setPricingPlans(plansData);
            
            const active = licenseData.find(s => s.status === 'ATIVA' && new Date(s.end_date!) > new Date());
            setActiveLicense(active || null);
            setError(null);
        } catch (err) {
            setError(stringifyError(err));
        } finally {
            setLoading(false);
        }
    };

    const handleRequestLicense = async (planId: number) => {
        if (!activeCompany) return;
        try {
            await licenseService.createLicense(activeCompany.id, planId);
            loadLicenses();
        } catch (err) {
            setError(stringifyError(err));
        }
    };

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 5 }}>
                <CircularProgress />
            </Box>
        );
    }

    const pendingLicense = licenses.find(s => s.status === 'PENDENTE');

    return (
        <Box sx={{ maxWidth: 1200, mx: 'auto', p: 2 }}>
            <Typography variant="h4" sx={{ mb: 4, fontWeight: 'bold', color: '#4338ca' }}>
                Gestão de Licença do Software
            </Typography>

            {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

            <Grid container spacing={4}>
                <Grid item xs={12} md={8}>
                    <Paper sx={{ p: 3, mb: 3, borderRadius: 2, boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}>
                        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', fontWeight: 'bold' }}>
                            <InformationCircleIcon className="w-5 h-5 mr-2 text-indigo-500" />
                            Status Atual da Empresa
                        </Typography>
                        <Divider sx={{ mb: 2 }} />
                        
                        {activeLicense ? (
                            <Box sx={{ py: 2 }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                    <Typography variant="subtitle1">Plano Ativo:</Typography>
                                    <Chip label={activeLicense.plan} color="success" sx={{ fontWeight: 'bold' }} />
                                </Box>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                    <Typography variant="subtitle1">Vencimento da Licença:</Typography>
                                    <Typography variant="body1" fontWeight="bold" color="success.main">
                                        {new Date(activeLicense.end_date!).toLocaleDateString('pt-BR')}
                                    </Typography>
                                </Box>
                                <Alert severity="success" icon={<CheckCircleIcon className="w-5 h-5" />} sx={{ borderRadius: 2 }}>
                                    Sua licença está em dia. Todos os recursos do Brazcom ISP estão liberados.
                                </Alert>
                            </Box>
                        ) : pendingLicense ? (
                            <Box sx={{ py: 2 }}>
                                <Alert severity="warning" icon={<ClockIcon className="w-5 h-5" />} sx={{ mb: 3, borderRadius: 2 }}>
                                    Aguardando confirmação de pagamento para o plano {pendingLicense.plan}.
                                </Alert>
                                <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>Instruções para Pagamento via PIX</Typography>
                                <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 2 }}>
                                    <Typography variant="body2" gutterBottom>1. Abra o app do seu banco</Typography>
                                    <Typography variant="body2" gutterBottom>2. Escolha pagar via PIX (Copia e Cola ou Chave)</Typography>
                                    <Typography variant="body2" gutterBottom>3. Digite a chave abaixo:</Typography>
                                    <Box sx={{ my: 2, p: 2, bgcolor: 'white', border: '1px dashed #6366f1', textAlign: 'center', borderRadius: 1 }}>
                                        <Typography variant="h6" sx={{ letterSpacing: 1, fontWeight: 'bold', color: 'indigo.600' }}>{PIX_KEY}</Typography>
                                    </Box>
                                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center' }}>
                                        Beneficiário: <strong>{PIX_NAME}</strong> | Valor: <strong>R$ {pendingLicense.price.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</strong>
                                    </Typography>
                                </Paper>
                                <Typography variant="body2" sx={{ mt: 3, fontStyle: 'italic', color: 'gray.600' }}>
                                    Após realizar o pagamento, nossa equipe financeira validará o comprovante e liberará seu acesso em até 24 horas úteis.
                                </Typography>
                            </Box>
                        ) : (
                            <Box sx={{ py: 2 }}>
                                <Alert severity="error" sx={{ borderRadius: 2 }}>
                                    A empresa <strong>{activeCompany?.razao_social}</strong> não possui uma licença de uso ativa. O acesso aos módulos administrativos está bloqueado.
                                </Alert>
                                <Typography variant="body2" sx={{ mt: 2 }}>
                                    Escolha um dos planos abaixo para regularizar seu acesso imediatamente.
                                </Typography>
                            </Box>
                        )}
                    </Paper>

                    {!activeLicense && !pendingLicense && (
                        <Box sx={{ mt: 2 }}>
                            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>Planos Disponíveis</Typography>
                            <Grid container spacing={2}>
                                {pricingPlans.map((plan) => (
                                    <Grid item xs={12} sm={6} key={plan.id}>
                                        <Card 
                                            variant="outlined" 
                                            sx={{ 
                                                height: '100%', 
                                                display: 'flex',
                                                flexDirection: 'column',
                                                borderColor: plan.is_highlighted ? 'indigo.500' : 'indigo.200', 
                                                borderWidth: 2, 
                                                borderRadius: 2, 
                                                transition: 'transform 0.2s', 
                                                '&:hover': { transform: 'scale(1.02)' },
                                                position: 'relative'
                                            }}
                                        >
                                            {plan.is_highlighted && (
                                                <Box sx={{ 
                                                    bgcolor: '#4f46e5', 
                                                    color: 'white', 
                                                    py: 0.5, 
                                                    fontSize: '0.75rem', 
                                                    fontWeight: 'bold', 
                                                    textAlign: 'center',
                                                    textTransform: 'uppercase',
                                                    letterSpacing: 1
                                                }}>
                                                    MAIS POPULAR
                                                </Box>
                                            )}
                                            <CardContent sx={{ textAlign: 'center', p: 3, flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                                                <Typography variant="h6" color="text.secondary" sx={{ textTransform: 'uppercase', fontSize: '0.9rem', fontWeight: 'bold' }}>
                                                    {plan.name}
                                                </Typography>
                                                <Typography variant="h4" sx={{ 
                                                    my: 2, 
                                                    fontWeight: 'bold', 
                                                    color: '#4338ca',
                                                    whiteSpace: 'nowrap' 
                                                }}>
                                                    R$ {plan.price.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                                                </Typography>
                                                <Typography variant="caption" sx={{ mb: 3, display: 'block' }}>
                                                    {plan.description || `Válido por ${plan.duration_months} meses de acesso`}
                                                </Typography>
                                                
                                                <Box sx={{ flexGrow: 1 }} />
                                                
                                                <Button 
                                                    variant="contained" 
                                                    fullWidth 
                                                    sx={{ mt: 'auto', py: 1.5, fontWeight: 'bold', bgcolor: '#4f46e5', '&:hover': { bgcolor: '#4338ca' } }}
                                                    onClick={() => handleRequestLicense(plan.id)}
                                                >
                                                    Solicitar Agora
                                                </Button>
                                            </CardContent>
                                        </Card>
                                    </Grid>
                                ))}
                            </Grid>
                        </Box>
                    )}
                </Grid>

                <Grid item xs={12} md={4}>
                    <Paper sx={{ p: 3, borderRadius: 2, boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}>
                        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', fontWeight: 'bold' }}>
                            <ClockIcon className="w-5 h-5 mr-2 text-indigo-500" />
                            Histórico de Pagamentos
                        </Typography>
                        <Divider sx={{ mb: 2 }} />
                        {licenses.length === 0 ? (
                            <Box sx={{ textAlign: 'center', py: 4 }}>
                                <Typography variant="body2" color="text.secondary">Nenhuma solicitação de licença encontrada.</Typography>
                            </Box>
                        ) : (
                            <Box sx={{ maxHeight: 500, overflowY: 'auto' }}>
                                {licenses.map((s) => (
                                    <Box key={s.id} sx={{ mb: 2, p: 2, borderRadius: 2, border: '1px solid', borderColor: 'divider', bgcolor: s.status === 'ATIVA' ? 'success.50' : 'inherit' }}>
                                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                            <Typography variant="body2" fontWeight="bold">Licença {s.plan}</Typography>
                                            <Chip 
                                                label={s.status} 
                                                size="small" 
                                                color={s.status === 'ATIVA' ? 'success' : s.status === 'PENDENTE' ? 'warning' : 'default'}
                                                sx={{ height: 20, fontSize: '0.65rem', fontWeight: 'bold' }}
                                            />
                                        </Box>
                                        <Typography variant="caption" color="text.secondary" display="block">
                                            Solicitado em: {new Date(s.created_at).toLocaleString('pt-BR')}
                                        </Typography>
                                        {s.end_date && (
                                            <Typography variant="caption" color="text.secondary" display="block">
                                                Validade: {new Date(s.end_date).toLocaleDateString('pt-BR')}
                                            </Typography>
                                        )}
                                        <Typography variant="body2" sx={{ mt: 1, fontWeight: 'bold', color: 'indigo.700' }}>
                                            R$ {s.price.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                                        </Typography>
                                    </Box>
                                ))}
                            </Box>
                        )}
                    </Paper>
                </Grid>
            </Grid>
        </Box>
    );
};

export default Licenses;
