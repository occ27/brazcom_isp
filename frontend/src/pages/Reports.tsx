import React, { useState, useEffect, useCallback } from 'react';
import { 
  Typography, Box, Grid, TextField, Button, 
  FormControl, InputLabel, Select, MenuItem, Divider,
  CircularProgress, Card, CardContent, Dialog, DialogContent,
  Checkbox, ListItemText, Autocomplete
} from '@mui/material';
import api from '../services/authService';
import { 
  DocumentTextIcon, 
  CurrencyDollarIcon,
  ArrowDownTrayIcon,
  AdjustmentsHorizontalIcon
} from '@heroicons/react/24/outline';
import { useCompany } from '../contexts/CompanyContext';
import { reportService, ContractsFiltersData } from '../services/reportService';
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
  const [searchClients, setSearchClients] = useState<any[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [clientSearchTerm, setClientSearchTerm] = useState('');
  const [selectedClient, setSelectedClient] = useState<any | null>(null);

  // Filtros de Rede (Contratos)
  const [contractsFiltersData, setContractsFiltersData] = useState<ContractsFiltersData>({
    routers: [],
    ip_classes: [],
    interfaces: []
  });
  const [selectedRouter, setSelectedRouter] = useState<number | ''>('');
  const [selectedInterface, setSelectedInterface] = useState<number | ''>('');
  const [selectedIPClass, setSelectedIPClass] = useState<number | ''>('');

  // Filtros de Clientes
  const [locations, setLocations] = useState<Record<string, string[]>>({});
  const [selectedCity, setSelectedCity] = useState('');
  const [selectedNeighborhoods, setSelectedNeighborhoods] = useState<string[]>([]);
  const [loadingLocations, setLoadingLocations] = useState(false);

  // Computar cidades e bairros disponíveis com base na seleção
  const clientCities = Object.keys(locations).sort();
  const clientNeighborhoods = selectedCity 
    ? (locations[selectedCity] || [])
    : Array.from(new Set(Object.values(locations).flat())).sort();

  useEffect(() => {
    if (activeCompany) {
      loadServices();
      loadClientLocations();
      loadContractsFilters();
    }
  }, [activeCompany]);

  const loadContractsFilters = async () => {
    if (!activeCompany) return;
    try {
      const data = await reportService.getContractsFilters(activeCompany.id);
      setContractsFiltersData(data);
    } catch (error) {
      console.error('Erro ao carregar filtros de rede para contratos:', error);
    }
  };

  const handleRouterChange = (routerId: number | '') => {
    setSelectedRouter(routerId);
    setSelectedInterface('');
  };

  const filteredInterfaces = selectedRouter
    ? contractsFiltersData.interfaces.filter(i => i.router_id === selectedRouter)
    : contractsFiltersData.interfaces;

  const loadClientLocations = async () => {
    if (!activeCompany) return;
    setLoadingLocations(true);
    try {
      const data = await reportService.getClientsLocations(activeCompany.id);
      setLocations(data);
    } catch (error) {
      console.error('Erro ao carregar localizações de clientes:', error);
    } finally {
      setLoadingLocations(false);
    }
  };

  const handleCityChange = (city: string) => {
    setSelectedCity(city);
    // Se mudou a cidade, filtra os bairros mantendo apenas aqueles que pertencem à nova cidade
    if (city && locations[city]) {
      const allowed = locations[city];
      setSelectedNeighborhoods(prev => prev.filter(b => allowed.includes(b)));
    } else if (!city) {
      // Se limpou a cidade, limpa também a seleção de bairros para manter o padrão intuitivo
      setSelectedNeighborhoods([]);
    }
  };

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

  const fetchClients = useCallback(async (search: string) => {
    if (!activeCompany) return;
    setSearchLoading(true);
    try {
      const res = await api.get(`/clientes/autocomplete/${activeCompany.id}?q=${search}&limit=20`);
      setSearchClients(res.data || []);
    } catch (e) {
      console.error('Erro ao buscar clientes', e);
    } finally {
      setSearchLoading(false);
    }
  }, [activeCompany]);

  useEffect(() => {
    if (clientSearchTerm.length >= 3) {
      const timer = setTimeout(() => {
        fetchClients(clientSearchTerm);
      }, 500);
      return () => clearTimeout(timer);
    } else if (clientSearchTerm.length === 0) {
      setSearchClients([]);
    }
  }, [clientSearchTerm, fetchClients]);

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
        status: contractStatus,
        municipio: selectedCity || undefined,
        bairro: selectedNeighborhoods.length > 0 ? selectedNeighborhoods : undefined,
        router_id: selectedRouter || undefined,
        interface_id: selectedInterface || undefined,
        ip_class_id: selectedIPClass || undefined
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
        date_type: financialDateType,
        q: selectedClient ? selectedClient.nome_razao_social : undefined,
        municipio: selectedCity || undefined,
        bairro: selectedNeighborhoods.length > 0 ? selectedNeighborhoods : undefined
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
      const params = cleanFilters({
        municipio: selectedCity,
        bairro: selectedNeighborhoods.length > 0 ? selectedNeighborhoods : undefined
      });
      const blob = await reportService.generateClientsPdf(activeCompany.id, params);
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
            <Typography variant="h6" fontWeight="700">Filtros Gerais (Filtro por Localidade, Período e Plano)</Typography>
          </Box>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6} md={3}>
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
            <Grid item xs={12} sm={6} md={3}>
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
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Cidade</InputLabel>
                <Select
                  value={selectedCity}
                  label="Cidade"
                  onChange={(e) => handleCityChange(e.target.value as string)}
                  disabled={loadingLocations}
                >
                  <MenuItem value="">Todas as Cidades</MenuItem>
                  {clientCities.map((cidade) => (
                    <MenuItem key={cidade} value={cidade}>{cidade}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Bairros</InputLabel>
                <Select
                  multiple
                  value={selectedNeighborhoods}
                  label="Bairros"
                  onChange={(e) => {
                    const value = e.target.value;
                    setSelectedNeighborhoods(
                      typeof value === 'string' ? value.split(',') : (value as string[])
                    );
                  }}
                  disabled={loadingLocations}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.length === 0 ? (
                        'Todos os Bairros'
                      ) : selected.length > 2 ? (
                        <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>
                          {selected.length} bairros
                        </Typography>
                      ) : (
                        selected.map((value) => (
                          <Typography 
                            key={value} 
                            variant="caption" 
                            sx={{ 
                              bgcolor: 'primary.light', 
                              color: 'primary.contrastText', 
                              px: 1, 
                              py: 0.2, 
                              borderRadius: 1,
                              fontWeight: 600
                            }}
                          >
                            {value}
                          </Typography>
                        ))
                      )}
                    </Box>
                  )}
                >
                  {clientNeighborhoods.map((bairro) => (
                    <MenuItem key={bairro} value={bairro}>
                      <Checkbox checked={selectedNeighborhoods.includes(bairro)} />
                      <ListItemText primary={bairro} />
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
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
              
              <Grid container spacing={2} sx={{ mb: 4 }}>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth size="small">
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
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Classe de IP</InputLabel>
                    <Select
                      value={selectedIPClass}
                      label="Classe de IP"
                      onChange={(e) => setSelectedIPClass(e.target.value as number | '')}
                    >
                      <MenuItem value="">Todas as Classes</MenuItem>
                      {contractsFiltersData.ip_classes.map((ipc) => (
                        <MenuItem key={ipc.id} value={ipc.id}>{ipc.name}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Concentrador (Router)</InputLabel>
                    <Select
                      value={selectedRouter}
                      label="Concentrador (Router)"
                      onChange={(e) => handleRouterChange(e.target.value as number | '')}
                    >
                      <MenuItem value="">Todos os Roteadores</MenuItem>
                      {contractsFiltersData.routers.map((r) => (
                        <MenuItem key={r.id} value={r.id}>{r.nome}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Interface</InputLabel>
                    <Select
                      value={selectedInterface}
                      label="Interface"
                      onChange={(e) => setSelectedInterface(e.target.value as number | '')}
                    >
                      <MenuItem value="">Todas as Interfaces</MenuItem>
                      {filteredInterfaces.map((i) => (
                        <MenuItem key={i.id} value={i.id}>{i.name}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>

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
                        <MenuItem value="PENDING">Pendente</MenuItem>
                        <MenuItem value="REGISTERED">Registrada</MenuItem>
                        <MenuItem value="PAID">Paga</MenuItem>
                        <MenuItem value="REGISTRATION_FAILED">Falha no Registro</MenuItem>
                        <MenuItem value="CANCELLED">Cancelada</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12}>
                  <Autocomplete
                    options={searchClients}
                    loading={searchLoading}
                    value={selectedClient}
                    getOptionLabel={(o) => o.nome_razao_social || ''}
                    onInputChange={(_, value) => setClientSearchTerm(value)}
                    filterOptions={(x) => x}
                    onChange={(_, v) => setSelectedClient(v)}
                    isOptionEqualToValue={(option, val) => option.id === val.id}
                    renderOption={(props, option) => (
                      <li {...props} key={option.id}>
                        <Box>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>{option.nome_razao_social}</Typography>
                          <Typography variant="caption" color="text.secondary">{option.cpf_cnpj}</Typography>
                        </Box>
                      </li>
                    )}
                    renderInput={(p) => (
                      <TextField
                        {...p}
                        label="Localizar Cliente"
                        fullWidth
                        size="small"
                        variant="outlined"
                        placeholder="Digite nome ou documento..."
                        InputProps={{
                          ...p.InputProps,
                          endAdornment: (
                            <>
                              {searchLoading ? <CircularProgress color="inherit" size={20} /> : null}
                              {p.InputProps.endAdornment}
                            </>
                          ),
                        }}
                      />
                    )}
                  />
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
                Gera uma listagem completa de todos os clientes cadastrados na empresa, filtrados conforme a localidade (Cidade e Bairros) definida nos Filtros Gerais acima, incluindo CPF/CNPJ, contato e endereço.
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