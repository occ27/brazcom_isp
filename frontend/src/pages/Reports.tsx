import React, { useState, useEffect } from 'react';
import { 
  Typography, Box, Grid, TextField, Button, 
  FormControl, InputLabel, Select, MenuItem, Divider,
  CircularProgress, Card, CardContent, Dialog, DialogContent
} from '@mui/material';
import { 
  DocumentTextIcon, 
  CurrencyDollarIcon,
  ArrowDownTrayIcon,
  AdjustmentsHorizontalIcon
} from '@heroicons/react/24/outline';
import { useCompany } from '../contexts/CompanyContext';
import reportService from '../services/reportService';
import servicoService, { Servico } from '../services/servicoService';
import { stringifyError } from '../utils/error';

const Reports: React.FC = () => {
  const { activeCompany } = useCompany();
  const [loading, setLoading] = useState<string | null>(null);
  const [services, setServices] = useState<Servico[]>([]);
  const [loadingServices, setLoadingServices] = useState(false);
  
  const [openPdfModal, setOpenPdfModal] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [reportTitle, setReportTitle] = useState('');
  
  // Filtros Globais
  const [globalFilters, setGlobalFilters] = useState({
    start_date: '',
    end_date: '',
    servico_id: '' as string | number
  });

  // Filtros Específicos
  const [contractStatus, setContractStatus] = useState('');
  const [financialStatus, setFinancialStatus] = useState('');
  const [financialDateType, setFinancialDateType] = useState('due_date');

  useEffect(() => {
    if (activeCompany) {
      loadServices();
    }
  }, [activeCompany]);

  const loadServices = async () => {
    if (!activeCompany) return;
    setLoadingServices(true);
    try {
      const data = await servicoService.getServicosByEmpresa(activeCompany.id);
      setServices(data);
    } catch (error) {
      console.error('Erro ao carregar serviços:', error);
    } finally {
      setLoadingServices(false);
    }
  };

  const cleanFilters = (filters: any) => {
    const cleaned = { ...filters };
    Object.keys(cleaned).forEach(key => {
      if (cleaned[key] === '') {
        delete cleaned[key];
      }
    });
    return cleaned;
  };

  const handleDownloadContracts = async () => {
    if (!activeCompany) return;
    setLoading('contracts');
    try {
      const params = cleanFilters({
        ...globalFilters,
        status: contractStatus
      });
      const blob = await reportService.generateContractsPdf(activeCompany.id, params);
      const url = window.URL.createObjectURL(blob);
      setPdfUrl(url);
      setReportTitle('Relatório de Contratos');
      setOpenPdfModal(true);
    } catch (error) {
      console.error(error);
      alert('Erro ao gerar relatório: ' + stringifyError(error));
    } finally {
      setLoading(null);
    }
  };

  const handleDownloadFinancial = async () => {
    if (!activeCompany) return;
    setLoading('financial');
    try {
      const params = cleanFilters({
        ...globalFilters,
        status: financialStatus,
        date_type: financialDateType
      });
      const blob = await reportService.generateFinancialPdf(activeCompany.id, params);
      const url = window.URL.createObjectURL(blob);
      setPdfUrl(url);
      setReportTitle('Relatório Financeiro');
      setOpenPdfModal(true);
    } catch (error) {
      console.error(error);
      alert('Erro ao gerar relatório: ' + stringifyError(error));
    } finally {
      setLoading(null);
    }
  };

  const handleDownloadClients = async () => {
    if (!activeCompany) return;
    setLoading('clients');
    try {
      const blob = await reportService.generateClientsPdf(activeCompany.id, {});
      const url = window.URL.createObjectURL(blob);
      setPdfUrl(url);
      setReportTitle('Relatório de Clientes');
      setOpenPdfModal(true);
    } catch (error) {
      console.error(error);
      alert('Erro ao gerar relatório: ' + stringifyError(error));
    } finally {
      setLoading(null);
    }
  };

  return (
    <Box sx={{ p: { xs: 2, md: 4 } }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight="800" color="primary.main">Centro de Relatórios</Typography>
        <Typography variant="body1" color="text.secondary">Gere relatórios gerenciais unificados e segmentados</Typography>
      </Box>

      {/* Filtros Globais */}
      <Card sx={{ mb: 4, borderRadius: 3, boxShadow: '0 4px 20px rgba(0,0,0,0.05)', overflow: 'visible' }}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
            <AdjustmentsHorizontalIcon className="w-6 h-6 text-indigo-600 mr-2" />
            <Typography variant="h6" fontWeight="700">Filtros Gerais (Emissão / Período e Plano)</Typography>
          </Box>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={4} md={3}>
              <TextField
                label="Data Início"
                type="date"
                fullWidth
                size="small"
                InputLabelProps={{ shrink: true }}
                value={globalFilters.start_date}
                onChange={(e) => setGlobalFilters({...globalFilters, start_date: e.target.value})}
              />
            </Grid>
            <Grid item xs={12} sm={4} md={3}>
              <TextField
                label="Data Fim"
                type="date"
                fullWidth
                size="small"
                InputLabelProps={{ shrink: true }}
                value={globalFilters.end_date}
                onChange={(e) => setGlobalFilters({...globalFilters, end_date: e.target.value})}
              />
            </Grid>
            <Grid item xs={12} sm={4} md={6}>
              <FormControl fullWidth size="small">
                <InputLabel>Plano / Serviço</InputLabel>
                <Select
                  value={globalFilters.servico_id}
                  label="Plano / Serviço"
                  onChange={(e) => setGlobalFilters({...globalFilters, servico_id: e.target.value})}
                  disabled={loadingServices}
                >
                  <MenuItem value="">Todos os Planos</MenuItem>
                  {services.map((s) => (
                    <MenuItem key={s.id} value={s.id}>{s.descricao}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Grid container spacing={4}>
        {/* Relatório de Contratos */}
        <Grid item xs={12} lg={6}>
          <Card sx={{ borderRadius: 3, boxShadow: '0 4px 20px rgba(0,0,0,0.05)', height: '100%' }}>
            <CardContent sx={{ p: 4 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <Box sx={{ p: 1.5, bgcolor: 'blue.50', borderRadius: 2, mr: 2 }}>
                  <DocumentTextIcon className="w-8 h-8 text-blue-600" />
                </Box>
                <Box>
                  <Typography variant="h6" fontWeight="700">Relatório de Contratos</Typography>
                  <Typography variant="caption" color="text.secondary">Visualização por status de contrato</Typography>
                </Box>
              </Box>
              
              <Divider sx={{ mb: 3 }} />
              
              <FormControl fullWidth size="small" sx={{ mb: 4 }}>
                <InputLabel>Status do Contrato</InputLabel>
                <Select
                  value={contractStatus}
                  label="Status do Contrato"
                  onChange={(e) => setContractStatus(e.target.value)}
                >
                  <MenuItem value="">Todos os Status</MenuItem>
                  <MenuItem value="ATIVO">Ativo</MenuItem>
                  <MenuItem value="SUSPENSO">Suspenso</MenuItem>
                  <MenuItem value="CANCELADO">Cancelado</MenuItem>
                </Select>
              </FormControl>

              <Button 
                variant="contained" 
                fullWidth 
                size="large"
                startIcon={loading === 'contracts' ? <CircularProgress size={20} color="inherit" /> : <ArrowDownTrayIcon className="w-5 h-5" />}
                onClick={handleDownloadContracts}
                disabled={!!loading}
                sx={{ borderRadius: 2, py: 1.5, textTransform: 'none', fontWeight: 600 }}
              >
                {loading === 'contracts' ? 'Gerando...' : 'Visualizar Contratos'}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Relatório Financeiro */}
        <Grid item xs={12} lg={6}>
          <Card sx={{ borderRadius: 3, boxShadow: '0 4px 20px rgba(0,0,0,0.05)', height: '100%' }}>
            <CardContent sx={{ p: 4 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <Box sx={{ p: 1.5, bgcolor: 'green.50', borderRadius: 2, mr: 2 }}>
                  <CurrencyDollarIcon className="w-8 h-8 text-green-600" />
                </Box>
                <Box>
                  <Typography variant="h6" fontWeight="700">Relatório Financeiro</Typography>
                  <Typography variant="caption" color="text.secondary">Fluxo de cobranças e recebimentos</Typography>
                </Box>
              </Box>
              
              <Divider sx={{ mb: 3 }} />

              <Grid container spacing={2} sx={{ mb: 4 }}>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Data de</InputLabel>
                    <Select
                      value={financialDateType}
                      label="Data de"
                      onChange={(e) => setFinancialDateType(e.target.value)}
                    >
                      <MenuItem value="due_date">Vencimento</MenuItem>
                      <MenuItem value="paid_at">Pagamento</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Status</InputLabel>
                    <Select
                      value={financialStatus}
                      label="Status"
                      onChange={(e) => setFinancialStatus(e.target.value)}
                    >
                      <MenuItem value="">Todas</MenuItem>
                      <MenuItem value="OPEN">Aberta</MenuItem>
                      <MenuItem value="PAID">Paga</MenuItem>
                      <MenuItem value="CANCELLED">Cancelada</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>

              <Button 
                variant="contained" 
                fullWidth 
                size="large"
                color="success"
                startIcon={loading === 'financial' ? <CircularProgress size={20} color="inherit" /> : <ArrowDownTrayIcon className="w-5 h-5" />}
                onClick={handleDownloadFinancial}
                disabled={!!loading}
                sx={{ borderRadius: 2, py: 1.5, textTransform: 'none', fontWeight: 600 }}
              >
                {loading === 'financial' ? 'Gerando...' : 'Visualizar Financeiro'}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Relatório de Clientes */}
        <Grid item xs={12} lg={6}>
          <Card sx={{ borderRadius: 3, boxShadow: '0 4px 20px rgba(0,0,0,0.05)', height: '100%' }}>
            <CardContent sx={{ p: 4 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <Box sx={{ p: 1.5, bgcolor: 'orange.50', borderRadius: 2, mr: 2 }}>
                  <AdjustmentsHorizontalIcon className="w-8 h-8 text-orange-600" />
                </Box>
                <Box>
                  <Typography variant="h6" fontWeight="700">Relatório de Clientes</Typography>
                  <Typography variant="caption" color="text.secondary">Listagem geral da base de clientes</Typography>
                </Box>
              </Box>
              
              <Divider sx={{ mb: 3 }} />
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
                Gera uma listagem completa de todos os clientes cadastrados na empresa, incluindo CPF/CNPJ, contato e localização.
              </Typography>

              <Button 
                variant="contained" 
                color="warning"
                fullWidth 
                size="large"
                startIcon={loading === 'clients' ? <CircularProgress size={20} color="inherit" /> : <ArrowDownTrayIcon className="w-5 h-5" />}
                onClick={handleDownloadClients}
                disabled={!!loading}
                sx={{ borderRadius: 2, py: 1.5, textTransform: 'none', fontWeight: 600 }}
              >
                {loading === 'clients' ? 'Gerando...' : 'Visualizar Clientes'}
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Modal PDF */}
      <Dialog open={openPdfModal} onClose={() => { setOpenPdfModal(false); setPdfUrl(null); }} maxWidth="lg" fullWidth>
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', bgcolor: 'primary.main', color: 'white' }}>
          <Typography variant="h6" fontWeight="700">{reportTitle}</Typography>
          <Button color="inherit" onClick={() => { setOpenPdfModal(false); setPdfUrl(null); }}>Fechar</Button>
        </Box>
        <DialogContent sx={{ p: 0, height: '80vh' }}>
          {pdfUrl && <iframe src={pdfUrl} width="100%" height="100%" style={{ border: 'none' }} title="Relatório PDF" />}
        </DialogContent>
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'flex-end', gap: 2, bgcolor: '#f5f5f5' }}>
          <Button variant="outlined" onClick={() => window.open(pdfUrl!, '_blank')}>Abrir em Nova Aba</Button>
          <Button variant="contained" onClick={() => {
            const link = document.createElement('a');
            link.href = pdfUrl!;
            link.setAttribute('download', `${reportTitle.toLowerCase().replace(/ /g, '_')}_${new Date().getTime()}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.remove();
          }}>Baixar PDF</Button>
        </Box>
      </Dialog>
    </Box>
  );
};

export default Reports;