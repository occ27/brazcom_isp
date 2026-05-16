import React, { useState, useEffect } from 'react';
import { 
    Typography, Box, Paper, Table, TableBody, TableCell, 
    TableContainer, TableHead, TableRow, Button, Chip, 
    CircularProgress, Alert, IconButton, Tabs, Tab,
    Dialog, DialogTitle, DialogContent, DialogActions, TextField,
    MenuItem, FormControl, InputLabel, Select
} from '@mui/material';
import { 
    CheckIcon, NoSymbolIcon, PlusIcon,
    TableCellsIcon, ClockIcon, BuildingOfficeIcon
} from '@heroicons/react/24/outline';
import { licenseService, License, LicensePlan, LicenseStatus, LicensePricingPlan } from '../services/licenseService';
import { stringifyError } from '../utils/error';
import { 
    Cog6ToothIcon, TrashIcon, PencilSquareIcon
} from '@heroicons/react/24/outline';

const AdminLicenses: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [tab, setTab] = useState(0);
    const [licenses, setLicenses] = useState<License[]>([]);
    const [companies, setCompanies] = useState<any[]>([]);
    const [pricingPlans, setPricingPlans] = useState<LicensePricingPlan[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [processingId, setProcessingId] = useState<number | null>(null);

    // Modal State
    const [modalOpen, setModalOpen] = useState(false);
    const [planModalOpen, setPlanModalOpen] = useState(false);
    const [selectedCompany, setSelectedCompany] = useState<any>(null);
    const [editingPlan, setEditingPlan] = useState<LicensePricingPlan | null>(null);
    
    const [formData, setFormData] = useState({
        plan_id: 0,
        status: 'ATIVA' as LicenseStatus,
        end_date: ''
    });

    const [planFormData, setPlanFormData] = useState({
        name: '',
        description: '',
        price: 0,
        duration_months: 12,
        is_active: true,
        is_highlighted: false
    });

    useEffect(() => {
        loadData();
    }, [tab]);

    const loadData = async () => {
        try {
            setLoading(true);
            setError(null);
            if (tab === 0) {
                const data = await licenseService.getPendingLicenses();
                setLicenses(data);
            } else if (tab === 1) {
                // Precisamos dos planos aqui para o modal de Liberação Manual
                const [companiesData, plansData] = await Promise.all([
                    licenseService.getAdminCompaniesStatus(),
                    licenseService.getAllPlans()
                ]);
                setCompanies(companiesData);
                setPricingPlans(plansData);
            } else if (tab === 2) {
                const data = await licenseService.getAllLicenses();
                setLicenses(data);
            } else if (tab === 3) {
                const data = await licenseService.getAllPlans();
                setPricingPlans(data);
            }
        } catch (err) {
            setError(stringifyError(err));
        } finally {
            setLoading(false);
        }
    };

    const handleApprove = async (id: number) => {
        if (!window.confirm("Confirmar recebimento do pagamento e liberar acesso da empresa?")) return;
        try {
            setProcessingId(id);
            await licenseService.approveLicense(id);
            loadData();
        } catch (err) {
            setError(stringifyError(err));
        } finally {
            setProcessingId(null);
        }
    };

    const handleCancel = async (id: number) => {
        if (!window.confirm("Deseja realmente CANCELAR esta licença? O acesso da empresa será bloqueado.")) return;
        try {
            setProcessingId(id);
            await licenseService.cancelLicense(id);
            loadData();
        } catch (err) {
            setError(stringifyError(err));
        } finally {
            setProcessingId(null);
        }
    };

    const handleOpenManualModal = (company: any) => {
        setSelectedCompany(company);
        setFormData({
            plan_id: pricingPlans.length > 0 ? pricingPlans[0].id : 0,
            status: 'ATIVA',
            end_date: new Date(new Date().setFullYear(new Date().getFullYear() + 1)).toISOString().split('T')[0]
        });
        setModalOpen(true);
    };

    const handleSubmitManual = async () => {
        try {
            setProcessingId(selectedCompany.id);
            await licenseService.createLicense(selectedCompany.id, formData.plan_id);
            // Se o status for ATIVA, precisamos aprovar imediatamente
            // Nota: createLicense cria como PENDENTE. Vamos buscar a licença recém criada e aprovar.
            // Mas para simplificar, o admin pode aprovar na aba pendente, ou podemos criar uma rota manual_create_active
            
            // Vamos usar o fluxo padrão: criar e depois recarregar
            setModalOpen(false);
            loadData();
            setError("Licença solicitada com sucesso. Agora aprove-a na aba 'Solicitações Pendentes'.");
        } catch (err) {
            setError(stringifyError(err));
        } finally {
            setProcessingId(null);
        }
    };

    const handleOpenPlanModal = (plan?: LicensePricingPlan) => {
        if (plan) {
            setEditingPlan(plan);
            setPlanFormData({
                name: plan.name,
                description: plan.description || '',
                price: plan.price,
                duration_months: plan.duration_months,
                is_active: plan.is_active,
                is_highlighted: plan.is_highlighted
            });
        } else {
            setEditingPlan(null);
            setPlanFormData({
                name: '',
                description: '',
                price: 0,
                duration_months: 12,
                is_active: true,
                is_highlighted: false
            });
        }
        setPlanModalOpen(true);
    };

    const handleSubmitPlan = async () => {
        try {
            if (editingPlan) {
                await licenseService.updatePlan(editingPlan.id, planFormData);
            } else {
                await licenseService.createPlan(planFormData);
            }
            setPlanModalOpen(false);
            loadData();
        } catch (err) {
            setError(stringifyError(err));
        }
    };

    const handleDeletePlan = async (id: number) => {
        if (!window.confirm("Deseja realmente deletar este plano? Isso não afetará licenças já vendidas.")) return;
        try {
            await licenseService.deletePlan(id);
            loadData();
        } catch (err) {
            setError(stringifyError(err));
        }
    };

    const renderPlans = () => (
        <Box>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
                <Button variant="contained" startIcon={<PlusIcon className="w-5 h-5" />} onClick={() => handleOpenPlanModal()}>
                    Novo Plano de Venda
                </Button>
            </Box>
            <TableContainer component={Paper} sx={{ borderRadius: 2 }}>
                <Table>
                    <TableHead sx={{ bgcolor: 'grey.50' }}>
                        <TableRow>
                            <TableCell sx={{ fontWeight: 'bold' }}>Nome do Plano</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Preço</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Duração</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Status</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 'bold' }}>Ações</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {pricingPlans.map((p) => (
                            <TableRow key={p.id} hover>
                                <TableCell>
                                    <Typography variant="body2" fontWeight="bold">{p.name}</Typography>
                                    <Typography variant="caption" color="text.secondary">{p.description}</Typography>
                                    {p.is_highlighted && <Chip label="Destaque" size="small" color="primary" sx={{ ml: 1, height: 18, fontSize: '0.6rem' }} />}
                                </TableCell>
                                <TableCell>R$ {p.price.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</TableCell>
                                <TableCell>{p.duration_months} meses</TableCell>
                                <TableCell>
                                    <Chip label={p.is_active ? "Ativo" : "Inativo"} size="small" color={p.is_active ? "success" : "default"} />
                                </TableCell>
                                <TableCell align="right">
                                    <IconButton size="small" onClick={() => handleOpenPlanModal(p)} color="primary">
                                        <PencilSquareIcon className="w-5 h-5" />
                                    </IconButton>
                                    <IconButton size="small" onClick={() => handleDeletePlan(p.id)} color="error">
                                        <TrashIcon className="w-5 h-5" />
                                    </IconButton>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>
        </Box>
    );

    const renderPending = () => (
        <TableContainer component={Paper} sx={{ borderRadius: 2, boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}>
            <Table>
                <TableHead sx={{ bgcolor: 'grey.50' }}>
                    <TableRow>
                        <TableCell sx={{ fontWeight: 'bold' }}>Empresa (ID)</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Plano / Valor</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Solicitado em</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 'bold' }}>Ações</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {licenses.length === 0 ? (
                        <TableRow><TableCell colSpan={4} align="center" sx={{ py: 4 }}>Nenhuma solicitação pendente</TableCell></TableRow>
                    ) : licenses.map((s) => (
                        <TableRow key={s.id} hover>
                            <TableCell>Empresa ID: {s.empresa_id}</TableCell>
                            <TableCell>
                                <Chip label={s.plan} size="small" variant="outlined" sx={{ mr: 1, fontWeight: 'bold' }} />
                                R$ {s.price.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                            </TableCell>
                            <TableCell>{new Date(s.created_at).toLocaleString('pt-BR')}</TableCell>
                            <TableCell align="right">
                                <Button
                                    variant="contained"
                                    color="success"
                                    size="small"
                                    startIcon={processingId === s.id ? <CircularProgress size={16} color="inherit" /> : <CheckIcon className="w-4 h-4" />}
                                    onClick={() => handleApprove(s.id)}
                                    disabled={processingId !== null}
                                    sx={{ fontWeight: 'bold' }}
                                >
                                    Aprovar Pagamento
                                </Button>
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
    );

    const renderCompanies = () => (
        <TableContainer component={Paper} sx={{ borderRadius: 2, boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}>
            <Table>
                <TableHead sx={{ bgcolor: 'grey.50' }}>
                    <TableRow>
                        <TableCell sx={{ fontWeight: 'bold' }}>Empresa</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>CNPJ</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Status Empresa</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Status Licença</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Vencimento</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 'bold' }}>Ações</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {companies.map((c) => (
                        <TableRow key={c.id} hover>
                            <TableCell sx={{ fontWeight: 'medium' }}>{c.razao_social}</TableCell>
                            <TableCell>{c.cnpj}</TableCell>
                            <TableCell>
                                <Chip 
                                    label={c.is_active ? "ATIVA" : "INATIVA"} 
                                    size="small" 
                                    color={c.is_active ? "success" : "default"} 
                                    sx={{ fontWeight: 'bold' }}
                                />
                            </TableCell>
                            <TableCell>
                                <Chip 
                                    label={c.license_status} 
                                    size="small" 
                                    color={c.license_status === 'ATIVA' ? 'success' : c.license_status === 'PENDENTE' ? 'warning' : 'error'} 
                                    sx={{ fontWeight: 'bold' }}
                                />
                            </TableCell>
                            <TableCell>
                                {c.end_date ? new Date(c.end_date).toLocaleDateString('pt-BR') : '-'}
                            </TableCell>
                            <TableCell align="right">
                                <Button
                                    variant="outlined"
                                    size="small"
                                    sx={{ fontWeight: 'bold', color: '#4f46e5', borderColor: '#4f46e5' }}
                                    startIcon={<PlusIcon className="w-4 h-4" />}
                                    onClick={() => handleOpenManualModal(c)}
                                >
                                    Liberar Manual
                                </Button>
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
    );

    const renderHistory = () => (
        <TableContainer component={Paper} sx={{ borderRadius: 2, boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}>
            <Table>
                <TableHead sx={{ bgcolor: 'grey.50' }}>
                    <TableRow>
                        <TableCell sx={{ fontWeight: 'bold' }}>Empresa (ID)</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Plano / Valor</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Status</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Vencimento</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 'bold' }}>Ações</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {licenses.map((s) => (
                        <TableRow key={s.id} hover>
                            <TableCell>ID: {s.empresa_id}</TableCell>
                            <TableCell>{s.plan} (R$ {s.price.toLocaleString('pt-BR', { minimumFractionDigits: 2 })})</TableCell>
                            <TableCell>
                                <Chip label={s.status} size="small" color={s.status === 'ATIVA' ? 'success' : 'default'} sx={{ fontWeight: 'bold' }} />
                            </TableCell>
                            <TableCell>{s.end_date ? new Date(s.end_date).toLocaleDateString('pt-BR') : '-'}</TableCell>
                            <TableCell align="right">
                                {s.status === 'ATIVA' && (
                                    <IconButton color="error" size="small" onClick={() => handleCancel(s.id)} title="Cancelar Licença">
                                        <NoSymbolIcon className="w-5 h-5" />
                                    </IconButton>
                                )}
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
    );

    return (
        <Box sx={{ p: 1 }}>
            <Typography variant="h4" sx={{ mb: 4, fontWeight: 'bold', color: 'indigo.700' }}>
                Painel Administrativo: Licenças
            </Typography>

            <Tabs value={tab} onChange={(e, v) => setTab(v)} sx={{ mb: 3, borderBottom: 1, borderColor: 'divider' }} textColor="primary" indicatorColor="primary">
                <Tab label="Solicitações Pendentes" icon={<ClockIcon className="w-5 h-5" />} iconPosition="start" sx={{ fontWeight: 'bold' }} />
                <Tab label="Monitoramento de Empresas" icon={<BuildingOfficeIcon className="w-5 h-5" />} iconPosition="start" sx={{ fontWeight: 'bold' }} />
                <Tab label="Histórico Geral" icon={<TableCellsIcon className="w-5 h-5" />} iconPosition="start" sx={{ fontWeight: 'bold' }} />
                <Tab label="Configurar Planos" icon={<Cog6ToothIcon className="w-5 h-5" />} iconPosition="start" sx={{ fontWeight: 'bold' }} />
            </Tabs>

            {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

            {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 10 }}>
                    <CircularProgress color="primary" />
                </Box>
            ) : (
                <Box sx={{ mt: 2 }}>
                    {tab === 0 && renderPending()}
                    {tab === 1 && renderCompanies()}
                    {tab === 2 && renderHistory()}
                    {tab === 3 && renderPlans()}
                </Box>
            )}

            {/* Modal de Licença Manual */}
            <Dialog open={modalOpen} onClose={() => setModalOpen(false)} maxWidth="sm" fullWidth PaperProps={{ sx: { borderRadius: 2 } }}>
                <DialogTitle sx={{ fontWeight: 'bold', bgcolor: 'indigo.50' }}>Liberar Licença Manual: {selectedCompany?.razao_social}</DialogTitle>
                <DialogContent>
                    <Box sx={{ mt: 3, display: 'flex', flexDirection: 'column', gap: 3 }}>
                        <TextField
                            select
                            label="Escolher Plano"
                            value={formData.plan_id}
                            onChange={(e) => setFormData({...formData, plan_id: Number(e.target.value)})}
                            fullWidth
                        >
                            {pricingPlans.map(p => (
                                <MenuItem key={p.id} value={p.id}>
                                    {p.name} - R$ {p.price.toLocaleString('pt-BR')}
                                </MenuItem>
                            ))}
                        </TextField>
                        
                        {pricingPlans.length === 0 && (
                            <Alert severity="warning" sx={{ mt: 1 }}>
                                Nenhum plano de venda cadastrado. Cadastre um plano na aba "Configurar Planos" primeiro.
                            </Alert>
                        )}
                        
                        <Typography variant="caption" color="text.secondary">
                            * Ao confirmar, uma solicitação será criada. Você precisará aprová-la na aba de pendências para liberar o acesso.
                        </Typography>

                        <FormControl fullWidth>
                            <InputLabel>Status Inicial</InputLabel>
                            <Select
                                value={formData.status}
                                label="Status Inicial"
                                onChange={(e) => setFormData({...formData, status: e.target.value as LicenseStatus})}
                            >
                                <MenuItem value="PENDENTE">Pendente (Recomendado)</MenuItem>
                            </Select>
                        </FormControl>
                    </Box>
                </DialogContent>
                <DialogActions sx={{ p: 3, bgcolor: 'grey.50' }}>
                    <Button onClick={() => setModalOpen(false)} color="inherit">Cancelar</Button>
                    <Button 
                        onClick={handleSubmitManual} 
                        variant="contained" 
                        disabled={processingId !== null}
                        startIcon={processingId !== null && <CircularProgress size={16} color="inherit" />}
                        sx={{ fontWeight: 'bold', bgcolor: '#4f46e5', '&:hover': { bgcolor: '#4338ca' } }}
                    >
                        Confirmar e Liberar Empresa
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Modal de Configuração de Plano */}
            <Dialog open={planModalOpen} onClose={() => setPlanModalOpen(false)} maxWidth="xs" fullWidth>
                <DialogTitle>{editingPlan ? 'Editar Plano' : 'Novo Plano de Licenciamento'}</DialogTitle>
                <DialogContent>
                    <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <TextField 
                            label="Nome do Plano" 
                            fullWidth 
                            value={planFormData.name}
                            onChange={(e) => setPlanFormData({...planFormData, name: e.target.value})}
                        />
                        <TextField 
                            label="Descrição" 
                            fullWidth 
                            multiline
                            rows={2}
                            value={planFormData.description}
                            onChange={(e) => setPlanFormData({...planFormData, description: e.target.value})}
                        />
                        <TextField 
                            label="Preço (R$)" 
                            type="number"
                            fullWidth 
                            value={planFormData.price}
                            onChange={(e) => setPlanFormData({...planFormData, price: Number(e.target.value)})}
                        />
                        <TextField 
                            label="Duração (Meses)" 
                            type="number"
                            fullWidth 
                            value={planFormData.duration_months}
                            onChange={(e) => setPlanFormData({...planFormData, duration_months: Number(e.target.value)})}
                        />
                        <FormControl fullWidth sx={{ mt: 1 }}>
                            <Box sx={{ display: 'flex', gap: 2 }}>
                                <Button 
                                    variant={planFormData.is_active ? "contained" : "outlined"}
                                    onClick={() => setPlanFormData({...planFormData, is_active: !planFormData.is_active})}
                                    fullWidth
                                    color={planFormData.is_active ? "success" : "inherit"}
                                >
                                    {planFormData.is_active ? "Plano Ativo" : "Plano Inativo"}
                                </Button>
                                <Button 
                                    variant={planFormData.is_highlighted ? "contained" : "outlined"}
                                    onClick={() => setPlanFormData({...planFormData, is_highlighted: !planFormData.is_highlighted})}
                                    fullWidth
                                    color={planFormData.is_highlighted ? "warning" : "inherit"}
                                >
                                    {planFormData.is_highlighted ? "Com Destaque" : "Sem Destaque"}
                                </Button>
                            </Box>
                        </FormControl>
                    </Box>
                </DialogContent>
                <DialogActions sx={{ p: 2 }}>
                    <Button onClick={() => setPlanModalOpen(false)}>Cancelar</Button>
                    <Button onClick={handleSubmitPlan} variant="contained" color="primary">Salvar Plano</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default AdminLicenses;
