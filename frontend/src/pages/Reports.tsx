import React, { useState } from 'react';
import { 
  Typography, Box, Paper, Grid, TextField, Button, 
  FormControl, InputLabel, Select, MenuItem, Divider,
  CircularProgress, Card, CardContent, Dialog, DialogContent
} from '@mui/material';
import { 
  DocumentTextIcon, 
  CurrencyDollarIcon,
  ArrowDownTrayIcon,
  FunnelIcon
} from '@heroicons/react/24/outline';
import { useCompany } from '../contexts/CompanyContext';
import reportService from '../services/reportService';
import { stringifyError } from '../utils/error';

const Reports: React.FC = () => {
  const { activeCompany } = useCompany();
  const [loading, setLoading] = useState<string | null>(null);
  const [openPdfModal, setOpenPdfModal] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [reportTitle, setReportTitle] = useState('');
  
  const [contractFilters, setContractFilters] = useState({
    start_date: '',
    end_date: '',
    status: ''
  });

  const [financialFilters, setFinancialFilters] = useState({
    start_date: '',
    end_date: '',
    status: '',
    date_type: 'due_date'
  });

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
      const params = cleanFilters(contractFilters);
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
      const params = cleanFilters(financialFilters);
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

  return (
    <Box sx={{ p: { xs: 2, md: 4 } }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight="800" color="primary.main">Centro de Relatórios</Typography>
        <Typography variant="body1" color="text.secondary">Gere relatórios gerenciais e administrativos em PDF</Typography>
      </Box>

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
                  <Typography variant="caption" color="text.secondary">Visão geral de assinaturas e status</Typography>
                </Box>
              </Box>
              
              <Divider sx={{ mb: 3 }} />
              
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
                <FunnelIcon className="w-4 h-4 text-gray-400" />
                <Typography variant="subtitle2" color="text.secondary">Filtros</Typography>
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Data Início"
                    type="date"
                    fullWidth
                    size="small"
                    InputLabelProps={{ shrink: true }}
                    value={contractFilters.start_date}
                    onChange={(e) => setContractFilters({...contractFilters, start_date: e.target.value})}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Data Fim"
                    type="date"
                    fullWidth
                    size="small"
                    InputLabelProps={{ shrink: true }}
                    value={contractFilters.end_date}
                    onChange={(e) => setContractFilters({...contractFilters, end_date: e.target.value})}
                  />
                </Grid>
                <Grid item xs={12}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Status do Contrato</InputLabel>
                    <Select
                      value={contractFilters.status}
                      label="Status do Contrato"
                      onChange={(e) => setContractFilters({...contractFilters, status: e.target.value})}
                    >
                      <MenuItem value="">Todos</MenuItem>
                      <MenuItem value="ATIVO">Ativo</MenuItem>
                      <MenuItem value="SUSPENSO">Suspenso</MenuItem>
                      <MenuItem value="CANCELADO">Cancelado</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>

              <Box sx={{ mt: 4 }}>
                <Button 
                  variant="contained" 
                  fullWidth 
                  size="large"
                  startIcon={loading === 'contracts' ? <CircularProgress size={20} color="inherit" /> : <ArrowDownTrayIcon className="w-5 h-5" />}
                  onClick={handleDownloadContracts}
                  disabled={!!loading}
                  sx={{ borderRadius: 2, py: 1.5, textTransform: 'none', fontWeight: 600 }}
                >
                  {loading === 'contracts' ? 'Gerando PDF...' : 'Visualizar Relatório'}
                </Button>
              </Box>
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
                  <Typography variant="caption" color="text.secondary">Fluxo de caixa, cobranças e recebimentos</Typography>
                </Box>
              </Box>
              
              <Divider sx={{ mb: 3 }} />

              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
                <FunnelIcon className="w-4 h-4 text-gray-400" />
                <Typography variant="subtitle2" color="text.secondary">Filtros</Typography>
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Data Início"
                    type="date"
                    fullWidth
                    size="small"
                    InputLabelProps={{ shrink: true }}
                    value={financialFilters.start_date}
                    onChange={(e) => setFinancialFilters({...financialFilters, start_date: e.target.value})}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Data Fim"
                    type="date"
                    fullWidth
                    size="small"
                    InputLabelProps={{ shrink: true }}
                    value={financialFilters.end_date}
                    onChange={(e) => setFinancialFilters({...financialFilters, end_date: e.target.value})}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Filtrar por Data de</InputLabel>
                    <Select
                      value={financialFilters.date_type}
                      label="Filtrar por Data de"
                      onChange={(e) => setFinancialFilters({...financialFilters, date_type: e.target.value})}
                    >
                      <MenuItem value="due_date">Vencimento</MenuItem>
                      <MenuItem value="paid_at">Pagamento</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Status da Cobrança</InputLabel>
                    <Select
                      value={financialFilters.status}
                      label="Status da Cobrança"
                      onChange={(e) => setFinancialFilters({...financialFilters, status: e.target.value})}
                    >
                      <MenuItem value="">Todas</MenuItem>
                      <MenuItem value="OPEN">Aberta</MenuItem>
                      <MenuItem value="PAID">Paga</MenuItem>
                      <MenuItem value="CANCELLED">Cancelada</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>

              <Box sx={{ mt: 4 }}>
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
                  {loading === 'financial' ? 'Gerando PDF...' : 'Visualizar Relatório'}
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Modal PDF */}
      <Dialog 
        open={openPdfModal} 
        onClose={() => { setOpenPdfModal(false); setPdfUrl(null); }} 
        maxWidth="lg" 
        fullWidth
      >
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', bgcolor: 'primary.main', color: 'white' }}>
          <Typography variant="h6" fontWeight="700">{reportTitle}</Typography>
          <Button color="inherit" onClick={() => { setOpenPdfModal(false); setPdfUrl(null); }}>Fechar</Button>
        </Box>
        <DialogContent sx={{ p: 0, height: '80vh' }}>
          {pdfUrl && (
            <iframe 
              src={pdfUrl} 
              width="100%" 
              height="100%" 
              style={{ border: 'none' }} 
              title="Relatório PDF" 
            />
          )}
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