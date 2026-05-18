import React, { useState, useEffect } from 'react';
import {
  Typography,
  Box,
  Paper,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  TextField,
  Chip,
  Alert,
  Snackbar,
  CircularProgress,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  SelectChangeEvent,
  useMediaQuery,
  useTheme
} from '@mui/material';
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  BuildingOfficeIcon
} from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/AuthContext';
import { API_BASE_URL } from '../services/api';
import { companyService, CompanyCreate, CompanyUpdate } from '../services/companyService';
import bankAccountService, { BankAccount } from '../services/bankAccountService';
import { stringifyError } from '../utils/error';
import { Company } from '../types';
import FileUploader from '../components/FileUploader';

const Companies: React.FC = () => {
  const { user } = useAuth();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [cepLoading, setCepLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("basic");
  const [editingCompany, setEditingCompany] = useState<Company | null>(null);
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [certificateFile, setCertificateFile] = useState<File | null>(null);
  const [signatureFile, setSignatureFile] = useState<File | null>(null);
  const [testingSMTP, setTestingSMTP] = useState(false);
  const [smtpPasswordConfigured, setSmtpPasswordConfigured] = useState(false);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [isNumbersOpen, setIsNumbersOpen] = useState(true);
  const [isIntegrationOpen, setIsIntegrationOpen] = useState(false);
  const [isSecurityOpen, setIsSecurityOpen] = useState(true);
  const [newIpInput, setNewIpInput] = useState('');
  const [whatsappConnected, setWhatsappConnected] = useState<boolean | null>(null);
  const [loadingWhatsAppState, setLoadingWhatsAppState] = useState(false);
  const [whatsappQrCode, setWhatsappQrCode] = useState<string | null>(null);
  const [loadingQrCode, setLoadingQrCode] = useState(false);
  const [isGatewayOpen, setIsGatewayOpen] = useState(false);
  const [showExternalIntegration, setShowExternalIntegration] = useState(false);

  const [formData, setFormData] = useState<CompanyCreate>({
    razao_social: '',
    nome_fantasia: '',
    cnpj: '',
    inscricao_estadual: '',
    endereco: '',     // Agora obrigatório
    numero: '',       // Agora obrigatório
    complemento: '',
    bairro: '',       // Agora obrigatório
    municipio: '',    // Agora obrigatório
    uf: '',           // Agora obrigatório
    codigo_ibge: '',  // Agora obrigatório
    cep: '',          // Agora obrigatório
    telefone: '',
    email: '',        // Agora obrigatório
    regime_tributario: '',
    cnae_principal: '', // Novo campo opcional
    
    // Configuração de cobrança: conta bancária padrão (opcional)
    default_bank_account_id: undefined,
    
    // Novos campos para logo, certificado e email
    logo_url: '',
    certificado_path: '',
    certificado_senha: '',
    smtp_server: '',
    smtp_port: undefined,
    smtp_user: '',
    smtp_password: '',
    
    // Preferência de ambiente padrão
    ambiente_nfcom: 'producao',
    
    // Mensagem de suspensão personalizada (ISP)
    suspension_message: '',
    suspension_url: '',
    dias_bloqueio_inadimplentes: 15,
    
    // Informações para contratos ISP
    ato_autorizacao: '',
    contrato_registro_num: '',
    site: '',
    email_contato: '',
    assinatura_digital_url: '',
    // Mercado Pago Config
    mp_access_token: '',
    mp_public_key: '',
    mp_allow_boleto: true,
    mp_allow_pix: true,
    mp_allow_credit_card: true,

    // WhatsApp Integration Config
    send_method_email: true,
    send_method_whatsapp: false,
    whatsapp_api_system: 'MK Auth',
    whatsapp_api_user: '',
    whatsapp_api_server: '',
    whatsapp_api_password: '',
    whatsapp_api_ips: '',
    whatsapp_api_instance: ''
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success' as 'success' | 'error' | 'warning'
  });

  const isSuperUser = user?.tipo === 'admin';

  useEffect(() => {
    loadCompanies();
  }, []);

  const loadCompanies = async () => {
    try {
      setLoading(true);
      const data = await companyService.getCompanies();
      setCompanies(data);
    } catch (error) {
      console.error('Erro ao carregar empresas:', error);
      setSnackbar({
        open: true,
        message: 'Erro ao carregar empresas',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const loadBankAccounts = async (empresaId: number) => {
    try {
      const data = await bankAccountService.listBankAccounts(empresaId);
      setBankAccounts(data || []);
    } catch (error) {
      console.error('Erro ao carregar contas bancárias:', error);
      setSnackbar({
        open: true,
        message: 'Erro ao carregar contas bancárias',
        severity: 'error'
      });
    }
  };

  useEffect(() => {
    if (editingCompany) {
      loadBankAccounts(editingCompany.id);
    } else {
      setBankAccounts([]);
    }
  }, [editingCompany]);

  useEffect(() => {
    if (editingCompany && activeTab === "email" && formData.send_method_whatsapp) {
      setWhatsappConnected(null);
      setWhatsappQrCode(null);
      handleCheckWhatsAppConnection(editingCompany.id);
    }
  }, [editingCompany, activeTab, formData.send_method_whatsapp]);

  const handleOpenDialog = (company?: Company) => {
    setWhatsappConnected(null);
    setWhatsappQrCode(null);
    setLoadingWhatsAppState(false);
    setLoadingQrCode(false);
    if (company) {
      setEditingCompany(company);
      setSmtpPasswordConfigured(!!company.smtp_password);
      setShowExternalIntegration(!!company.whatsapp_api_ips);
      setFormData({
        razao_social: company.razao_social,
        nome_fantasia: company.nome_fantasia || '',
        cnpj: companyService.formatCNPJ(company.cnpj),
        inscricao_estadual: company.inscricao_estadual || '',
        endereco: company.endereco || '', // Agora obrigatório
        numero: company.numero || '',     // Agora obrigatório
        complemento: company.complemento || '',
        bairro: company.bairro || '',     // Agora obrigatório
        municipio: company.municipio || '', // Agora obrigatório
        uf: company.uf || '',             // Agora obrigatório
        codigo_ibge: company.codigo_ibge || '', // Agora obrigatório
        cep: companyService.formatCEP(company.cep || ''), // Agora obrigatório
        telefone: company.telefone || '',
        email: company.email || '',       // Agora obrigatório
        regime_tributario: company.regime_tributario || '',
        cnae_principal: company.cnae_principal || '', // Novo campo
        
        // Configuração de cobrança: conta bancária padrão (opcional)
        default_bank_account_id: company.default_bank_account_id,
        
        // Novos campos
        logo_url: company.logo_url || '',
        certificado_path: company.certificado_path || '',
        certificado_senha: company.certificado_senha || '',
        smtp_server: company.smtp_server || '',
        smtp_port: company.smtp_port,
        smtp_user: company.smtp_user || '',
        // Do not prefill the password field with masked/stored value.
        // If the company already has a password configured, leave the field
        // empty and show a helper message. The backend will not overwrite
        // the stored password when an empty value is submitted.
        smtp_password: '',
        ambiente_nfcom: company.ambiente_nfcom || 'producao',
        suspension_message: company.suspension_message || '',
        suspension_url: company.suspension_url || '',
        dias_bloqueio_inadimplentes: company.dias_bloqueio_inadimplentes ?? 15,
        ato_autorizacao: company.ato_autorizacao || '',
        contrato_registro_num: company.contrato_registro_num || '',
        site: company.site || '',
        email_contato: company.email_contato || '',
        assinatura_digital_url: company.assinatura_digital_url || '',
        mp_access_token: company.mp_access_token || '',
        mp_public_key: company.mp_public_key || '',
        mp_allow_boleto: company.mp_allow_boleto !== false, // Default to true if undefined
        mp_allow_pix: company.mp_allow_pix !== false,
        mp_allow_credit_card: company.mp_allow_credit_card !== false,
        
        // WhatsApp Integration Config
        send_method_email: company.send_method_email !== false,
        send_method_whatsapp: !!company.send_method_whatsapp,
        whatsapp_api_system: company.whatsapp_api_system || 'MK Auth',
        whatsapp_api_user: company.whatsapp_api_user || 'usr_' + Math.random().toString(36).substring(2, 10),
        whatsapp_api_server: company.whatsapp_api_server || '',
        whatsapp_api_password: company.whatsapp_api_password || 'tok_' + Math.random().toString(36).substring(2, 14),
        whatsapp_api_ips: company.whatsapp_api_ips || '',
        whatsapp_api_instance: company.whatsapp_api_instance || ''
      });
    } else {
      setEditingCompany(null);
      setShowExternalIntegration(false);
      const randomUser = 'usr_' + Math.random().toString(36).substring(2, 10);
      const randomPassword = 'tok_' + Math.random().toString(36).substring(2, 14);
      setFormData({
        razao_social: '',
        nome_fantasia: '',
        cnpj: '',
        inscricao_estadual: '',
        endereco: '',
        numero: '',
        complemento: '',
        bairro: '',
        municipio: '',
        uf: '',
        codigo_ibge: '',
        cep: '',
        telefone: '',
        email: '',
        regime_tributario: '',
        cnae_principal: '',
        
        // Novos campos
        logo_url: '',
        certificado_path: '',
        certificado_senha: '',
        smtp_server: '',
        smtp_port: undefined,
        smtp_user: '',
        smtp_password: '',
        
        ambiente_nfcom: 'producao',
        suspension_message: '',
        suspension_url: '',
        dias_bloqueio_inadimplentes: 15,
        ato_autorizacao: '',
        contrato_registro_num: '',
        site: '',
        email_contato: '',
        assinatura_digital_url: '',
        mp_access_token: '',
        mp_public_key: '',
        mp_allow_boleto: true,
        mp_allow_pix: true,
        mp_allow_credit_card: true,

        // WhatsApp Integration Config
        send_method_email: true,
        send_method_whatsapp: false,
        whatsapp_api_system: 'MK Auth',
        whatsapp_api_user: randomUser,
        whatsapp_api_server: '',
        whatsapp_api_password: randomPassword,
        whatsapp_api_ips: '',
        whatsapp_api_instance: ''
      });
    }
    setErrors({});
    setActiveTab("basic");
    setLogoFile(null);
    setCertificateFile(null);
    setOpen(true);
  };

  const handleCloseDialog = () => {
    setWhatsappConnected(null);
    setWhatsappQrCode(null);
    setLoadingWhatsAppState(false);
    setLoadingQrCode(false);
    setOpen(false);
    setEditingCompany(null);
    setFormData({
      razao_social: '',
      nome_fantasia: '',
      cnpj: '',
      inscricao_estadual: '',
      endereco: '',
      numero: '',
      complemento: '',
      bairro: '',
      municipio: '',
      uf: '',
      codigo_ibge: '',
      cep: '',
      telefone: '',
      email: '',
      regime_tributario: '',
      cnae_principal: '',
      
      // Novos campos
      logo_url: '',
      certificado_path: '',
      certificado_senha: '',
      smtp_server: '',
      smtp_port: undefined,
      smtp_user: '',
      smtp_password: '',
      dias_bloqueio_inadimplentes: 15,
      whatsapp_api_instance: '',
      whatsapp_api_server: ''
    });
    setErrors({});
    setLogoFile(null);
    setCertificateFile(null);
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.razao_social.trim()) {
      newErrors.razao_social = 'Razão social é obrigatória';
    }

    if (!formData.cnpj.trim()) {
      newErrors.cnpj = 'CNPJ é obrigatório';
    } else if (!companyService.validateCNPJ(formData.cnpj)) {
      newErrors.cnpj = 'CNPJ inválido';
    }

    if (!formData.endereco.trim()) {
      newErrors.endereco = 'Endereço é obrigatório';
    }

    if (!formData.numero.trim()) {
      newErrors.numero = 'Número é obrigatório';
    }

    if (!formData.bairro.trim()) {
      newErrors.bairro = 'Bairro é obrigatório';
    }

    if (!formData.municipio.trim()) {
      newErrors.municipio = 'Município é obrigatório';
    }

    if (!formData.uf.trim()) {
      newErrors.uf = 'UF é obrigatória';
    }

    if (!formData.codigo_ibge.trim()) {
      newErrors.codigo_ibge = 'Código IBGE é obrigatório';
    }

    if (!formData.cep.trim()) {
      newErrors.cep = 'CEP é obrigatório';
    } else if (!companyService.validateCEP(formData.cep)) {
      newErrors.cep = 'CEP inválido';
    }

    if (!formData.email.trim()) {
      newErrors.email = 'E-mail é obrigatório';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'E-mail inválido';
    }

    if (formData.inscricao_estadual && !companyService.validateInscricaoEstadual(formData.inscricao_estadual, formData.uf)) {
      newErrors.inscricao_estadual = 'Inscrição estadual inválida (ou use "ISENTO")';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;

    try {
      const submitData = {
        ...formData,
        cnpj: formData.cnpj.replace(/\D/g, ''),
        cep: formData.cep.replace(/\D/g, '')
      };

      let companyId: number;

      // Determinar o ID da empresa (existente ou nova)

      if (editingCompany) {
        companyId = editingCompany.id;
      } else {
        // Criar nova empresa primeiro
        const newCompany = await companyService.createCompany(submitData);
        companyId = newCompany.id;
      }

      // Fazer upload dos arquivos para obter os caminhos
      let finalLogoUrl = formData.logo_url;
      let finalCertPath = formData.certificado_path;
      let finalSignatureUrl = formData.assinatura_digital_url;

      if (logoFile) {
        try {
          const uploadResult = await companyService.uploadCompanyLogo(companyId, logoFile);
          finalLogoUrl = uploadResult.file_path;
        } catch (error) {
          console.error('Erro ao fazer upload do logo:', error);
          setSnackbar({
            open: true,
            message: 'Erro ao enviar logo',
            severity: 'error'
          });
          return; // Interrompe se houver erro no upload
        }
      }

      if (certificateFile) {
        try {
          const uploadResult = await companyService.uploadCompanyCertificate(companyId, certificateFile);
          finalCertPath = uploadResult.file_path;
        } catch (error) {
          console.error('Erro ao fazer upload do certificado:', error);
          setSnackbar({
            open: true,
            message: 'Erro ao enviar certificado',
            severity: 'error'
          });
          return; // Interrompe se houver erro no upload
        }
      }
      if (signatureFile) {
        try {
          const uploadResult = await companyService.uploadCompanySignature(companyId, signatureFile);
          finalSignatureUrl = uploadResult.file_path;
        } catch (error) {
          console.error('Erro ao fazer upload da assinatura:', error);
          setSnackbar({
            open: true,
            message: 'Erro ao enviar assinatura',
            severity: 'error'
          });
          return; // Interrompe se houver erro no upload
        }
      }

      // Atualizar empresa com os caminhos finais dos arquivos (sempre atualizar para garantir consistência)
      const finalSubmitData = {
        ...submitData,
        logo_url: finalLogoUrl,
        certificado_path: finalCertPath,
        assinatura_digital_url: finalSignatureUrl
      };

      await companyService.updateCompany(companyId, finalSubmitData as CompanyUpdate);

      setSnackbar({
        open: true,
        message: editingCompany ? 'Empresa atualizada com sucesso' : 'Empresa criada com sucesso',
        severity: 'success'
      });

      handleCloseDialog();
      loadCompanies();
    } catch (error: any) {
      console.error('Erro ao salvar empresa:', error);
      const errorMessage = stringifyError(error) || 'Erro ao salvar empresa';
      setSnackbar({
        open: true,
        message: errorMessage,
        severity: 'error'
      });
    }
  };

  const handleCopyToClipboard = (text: string, label: string) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setSnackbar({
      open: true,
      message: `${label} copiado para a área de transferência!`,
      severity: 'success'
    });
  };

  const handleAddIp = (newIp: string) => {
    if (!newIp.trim()) return;
    // Validação simples de formato de IP
    const ipPattern = /^([0-9]{1,3}\.){3}[0-9]{1,3}$/;
    if (!ipPattern.test(newIp.trim())) {
      setSnackbar({
        open: true,
        message: 'Por favor, informe um endereço IP válido.',
        severity: 'warning'
      });
      return;
    }
    const currentIps = formData.whatsapp_api_ips ? formData.whatsapp_api_ips.split(',').map(ip => ip.trim()).filter(Boolean) : [];
    if (currentIps.includes(newIp.trim())) return;
    currentIps.push(newIp.trim());
    handleInputChange('whatsapp_api_ips', currentIps.join(', '));
  };

  const handleRemoveIp = (ipToRemove: string) => {
    const currentIps = formData.whatsapp_api_ips ? formData.whatsapp_api_ips.split(',').map(ip => ip.trim()).filter(Boolean) : [];
    const updatedIps = currentIps.filter(ip => ip !== ipToRemove);
    handleInputChange('whatsapp_api_ips', updatedIps.join(', '));
  };

  const handleCheckWhatsAppConnection = async (companyId: number) => {
    setLoadingWhatsAppState(true);
    try {
      const result = await companyService.getWhatsAppConnectionState(companyId);
      setWhatsappConnected(result.connected);
      if (result.connected) {
        setWhatsappQrCode(null);
      }
    } catch (e) {
      console.error('Erro ao verificar conexão WhatsApp:', e);
      setWhatsappConnected(false);
    } finally {
      setLoadingWhatsAppState(false);
    }
  };

  const handleGetWhatsAppQrCode = async (companyId: number) => {
    setLoadingQrCode(true);
    setWhatsappQrCode(null);
    try {
      const result = await companyService.getWhatsAppQrCode(companyId);
      if (result.success && result.base64) {
        setWhatsappQrCode(result.base64);
      } else {
        setSnackbar({
          open: true,
          message: result.message || 'Erro ao gerar QR Code de conexão',
          severity: 'error'
        });
      }
    } catch (e) {
      console.error('Erro ao gerar QR Code WhatsApp:', e);
      setSnackbar({
        open: true,
        message: 'Falha de conexão com a API de WhatsApp',
        severity: 'error'
      });
    } finally {
      setLoadingQrCode(false);
    }
  };

  const handleDisconnectWhatsApp = async (companyId: number) => {
    setLoadingWhatsAppState(true);
    try {
      const result = await companyService.disconnectWhatsApp(companyId);
      if (result.success) {
        setWhatsappConnected(false);
        setWhatsappQrCode(null);
        setSnackbar({
          open: true,
          message: 'WhatsApp desconectado com sucesso!',
          severity: 'success'
        });
      }
    } catch (e) {
      console.error('Erro ao desconectar WhatsApp:', e);
      setSnackbar({
        open: true,
        message: 'Erro ao desconectar WhatsApp',
        severity: 'error'
      });
    } finally {
      setLoadingWhatsAppState(false);
    }
  };

  const handleTestSMTP = async () => {
    if (!editingCompany) {
      setSnackbar({
        open: true,
        message: 'Salve a empresa primeiro para testar o SMTP',
        severity: 'warning'
      });
      return;
    }

    if (!formData.smtp_server || !formData.smtp_port || !formData.smtp_user || !formData.smtp_password) {
      setSnackbar({
        open: true,
        message: 'Preencha todos os campos SMTP antes de testar',
        severity: 'warning'
      });
      return;
    }

    setTestingSMTP(true);
    try {
      const smtpData = {
        smtp_server: formData.smtp_server,
        smtp_port: formData.smtp_port,
        smtp_user: formData.smtp_user,
        smtp_password: formData.smtp_password
      };
      const result = await companyService.testSMTPConfig(editingCompany.id, smtpData);
      setSnackbar({
        open: true,
        message: result.message,
        severity: result.success ? 'success' : 'error'
      });
    } catch (error: any) {
      console.error('Erro ao testar SMTP:', error);
      const errorMessage = stringifyError(error) || 'Erro ao testar configuração SMTP';
      setSnackbar({
        open: true,
        message: errorMessage,
        severity: 'error'
      });
    } finally {
      setTestingSMTP(false);
    }
  };

  const handleDelete = async (company: Company) => {
    if (!window.confirm(`Tem certeza que deseja excluir a empresa "${company.razao_social}"?`)) {
      return;
    }

    try {
      await companyService.deleteCompany(company.id);
      setSnackbar({
        open: true,
        message: 'Empresa excluída com sucesso',
        severity: 'success'
      });
      loadCompanies();
    } catch (error: any) {
      console.error('Erro ao excluir empresa:', error);
      const errorMessage = stringifyError(error) || 'Erro ao excluir empresa';
      setSnackbar({
        open: true,
        message: errorMessage,
        severity: 'error'
      });
    }
  };

  const handleInputChange = (field: string, value: string | number | boolean | undefined) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const handleCepChange = async (value: string) => {
    const formattedCep = companyService.formatCEPInput(value);
    handleInputChange('cep', formattedCep);

    // Buscar endereço automaticamente quando CEP estiver completo
    const cepClean = formattedCep.replace(/\D/g, '');
    if (cepClean.length === 8 && companyService.validateCEP(formattedCep)) {
      setCepLoading(true);
      try {
        const addressData = await companyService.searchCEP(formattedCep);
        if (addressData) {
          setFormData(prev => ({
            ...prev,
            endereco: addressData.endereco,
            bairro: addressData.bairro,
            municipio: addressData.municipio,
            uf: addressData.uf,
            codigo_ibge: addressData.codigo_ibge
          }));
        }
      } catch (error) {
        console.error('Erro ao buscar CEP:', error);
        // Não mostra erro para usuário, apenas log
      } finally {
        setCepLoading(false);
      }
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ 
        display: 'flex', 
        flexDirection: 'row',
        justifyContent: 'space-between', 
        alignItems: 'center',
        gap: 1,
        mb: 1
      }}>
        <Typography variant="h5" component="h1" sx={{ fontWeight: 'bold' }}>
          Empresas
        </Typography>
        {isSuperUser && (
          <Button
            variant="outlined"
            size="small"
            startIcon={<PlusIcon className="w-3 h-3" />}
            onClick={() => handleOpenDialog()}
            sx={{ py: 0.5, px: 1.5, fontSize: '0.8rem', minWidth: 'auto' }}
          >
            {isMobile ? 'Nova' : 'Nova Empresa'}
          </Button>
        )}
      </Box>

      {companies.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <BuildingOfficeIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <Typography variant="h6" gutterBottom>
            Nenhuma empresa cadastrada
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            {isSuperUser
              ? 'Comece cadastrando sua primeira empresa para emitir NFCom.'
              : 'Entre em contato com um administrador para cadastrar empresas.'
            }
          </Typography>
          {isSuperUser && (
            <Button
              variant="outlined"
              startIcon={<PlusIcon className="w-5 h-5" />}
              onClick={() => handleOpenDialog()}
            >
              Cadastrar Primeira Empresa
            </Button>
          )}
        </Paper>
      ) : (
        <>
          {isMobile ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, p: 1 }}>
              {companies.map(company => (
                <Paper key={company.id} elevation={2} sx={{ p: 2, borderRadius: 2 }}>
                  {/* Nome da empresa */}
                  <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
                    {company.razao_social}
                  </Typography>

                  {/* Nome Fantasia se existir */}
                  {company.nome_fantasia && (
                    <Typography variant="caption" color="text.secondary" sx={{ mb: 1 }}>
                      {company.nome_fantasia}
                    </Typography>
                  )}

                  {/* Detalhes */}
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="caption" sx={{ fontWeight: 500, mb: 0.5, whiteSpace: 'nowrap' }}>
                      CNPJ: {companyService.formatCNPJ(company.cnpj)}
                    </Typography>
                    {company.municipio && company.uf && (
                      <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
                        {company.municipio}/{company.uf}
                      </Typography>
                    )}
                  </Box>

                  {/* Ações */}
                  <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, alignItems: 'center' }}>
                    <IconButton
                      size="small"
                      onClick={() => handleOpenDialog(company)}
                      title="Editar"
                    >
                      <PencilIcon className="w-4 h-4" />
                    </IconButton>
                    {isSuperUser && (
                      <IconButton
                        size="small"
                        onClick={() => handleDelete(company)}
                        color="error"
                        title="Excluir"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </IconButton>
                    )}
                    <Chip
                      label={company.is_active ? 'Ativa' : 'Inativa'}
                      color={company.is_active ? 'success' : 'default'}
                      size="small"
                      variant="outlined"
                      sx={{ fontSize: '0.7rem', height: '20px', marginLeft: 'auto' }}
                    />
                  </Box>
                </Paper>
              ))}
            </Box>
          ) : (
            <Paper sx={{ p: 0 }}>
              <TableContainer sx={{ overflowX: 'auto' }}>
                <Table sx={{ minWidth: 600 }}>
                  <TableHead>
                    <TableRow>
                      <TableCell>Logo</TableCell>
                      <TableCell>Empresa</TableCell>
                      <TableCell>CNPJ</TableCell>
                      <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }}>Cidade/UF</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell align="right">Ações</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {companies.map((company) => (
                      <TableRow key={company.id} hover>
                        <TableCell>
                          {company.logo_url ? (
                              <Box
                              component="img"
                              src={`${API_BASE_URL}${company.logo_url}`}
                              alt={`Logo ${company.razao_social}`}
                              sx={{
                                width: 40,
                                height: 40,
                                objectFit: 'contain',
                                borderRadius: 1,
                                border: '1px solid',
                                borderColor: 'divider'
                              }}
                              onError={(e) => {
                                const target = e.target as HTMLImageElement;
                                target.style.display = 'none';
                              }}
                            />
                          ) : (
                            <Box
                              sx={{
                                width: 40,
                                height: 40,
                                borderRadius: 1,
                                border: '1px solid',
                                borderColor: 'divider',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                bgcolor: 'action.hover'
                              }}
                            >
                              <BuildingOfficeIcon className="w-6 h-6 text-text-muted" />
                            </Box>
                          )}
                        </TableCell>
                        <TableCell>
                          <Box>
                            <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                              {company.razao_social}
                            </Typography>
                            {company.nome_fantasia && (
                              <Typography variant="caption" color="text.secondary">
                                {company.nome_fantasia}
                              </Typography>
                            )}
                          </Box>
                        </TableCell>
                        <TableCell>{companyService.formatCNPJ(company.cnpj)}</TableCell>
                        <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }}>
                          {company.municipio && company.uf
                            ? `${company.municipio}/${company.uf}`
                            : 'Não informado'
                          }
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={company.is_active ? 'Ativa' : 'Inativa'}
                            color={company.is_active ? 'success' : 'error'}
                            size="small"
                          />
                        </TableCell>
                        <TableCell align="right">
                          <IconButton
                            size="small"
                            onClick={() => handleOpenDialog(company)}
                            title="Editar"
                          >
                            <PencilIcon className="w-4 h-4" />
                          </IconButton>
                          {isSuperUser && (
                            <IconButton
                              size="small"
                              onClick={() => handleDelete(company)}
                              color="error"
                              title="Excluir"
                            >
                            <TrashIcon className="w-4 h-4" />
                          </IconButton>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          )}
        </>
      )}      {/* Modal para criar/editar empresa */}
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-0 sm:p-4">
          {/* Overlay */}
          <div
            className="absolute inset-0 bg-gradient-to-br from-black/60 via-black/50 to-black/70 backdrop-blur-md"
            onClick={handleCloseDialog}
          />

          {/* Modal */}
          <div className="relative bg-gradient-to-br from-white via-gray-50 to-blue-50 border border-borderLight rounded-2xl sm:rounded-3xl shadow-modern-hover w-full max-w-sm sm:max-w-md lg:max-w-4xl h-full sm:h-auto max-h-screen sm:max-h-[90vh] flex flex-col overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between p-3 sm:p-6 border-b border-borderLight bg-gradient-to-r from-white to-blue-50/30 flex-shrink-0">
              <div className="flex items-center space-x-2 sm:space-x-3">
                <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg sm:rounded-xl flex items-center justify-center shadow-lg">
                  <BuildingOfficeIcon className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-base sm:text-2xl font-bold text-text bg-gradient-to-r from-blue-700 to-blue-600 bg-clip-text text-transparent">
                    {editingCompany ? 'Editar Empresa' : 'Nova Empresa'}
                  </h2>
                  <p className="text-xs sm:text-sm text-textLight hidden sm:block">
                    {editingCompany ? 'Atualize as informações da empresa' : 'Cadastre uma nova empresa no sistema'}
                  </p>
                </div>
              </div>
              <button
                onClick={handleCloseDialog}
                className="p-2 hover:bg-red-50 rounded-xl transition-all duration-200 flex items-center justify-center flex-shrink-0 shadow-sm hover:shadow-md group"
                style={{ minWidth: 40, minHeight: 40 }}
                aria-label="Fechar"
              >
                <svg
                  className="w-5 h-5 sm:w-6 sm:h-6 text-red-400 group-hover:text-red-600 transition-colors"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            {/* Tabs */}
            <div className="relative border-b border-borderLight bg-surfaceElevated shadow-modern flex-shrink-0">
              <div className="flex overflow-x-auto scrollbar-thin">
                {[
                  { id: "basic", label: "Dados Básicos", icon: "📋", color: "blue" },
                  { id: "address", label: "Endereço", icon: "📍", color: "green" },
                  { id: "billing", label: "Cobrança", icon: "💳", color: "teal" },
                  { id: "files", label: "Arquivos", icon: "📁", color: "purple" },
                  { id: "email", label: "Canais & Notificações", icon: "💬", color: "orange" },
                  { id: "isp", label: "ISP / Contratos", icon: "📄", color: "indigo" },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center space-x-1 sm:space-x-2 px-3 sm:px-6 py-3 sm:py-5 font-medium tab-transition whitespace-nowrap flex-shrink-0 relative rounded-t-lg ${
                      activeTab === tab.id
                        ? `tab-gradient-${tab.color} text-${tab.color === 'blue' ? 'blue' : tab.color === 'green' ? 'green' : tab.color === 'purple' ? 'purple' : 'orange'}-700 shadow-modern-hover`
                        : `text-textLight hover:text-text hover:bg-surface/70 tab-hover-scale`
                    }`}
                  >
                    <span className="text-sm sm:text-base">{tab.icon}</span>
                    <span className="text-xs sm:text-sm font-semibold">{tab.label}</span>
                    {activeTab === tab.id && (
                      <div className={`absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r ${
                        tab.color === 'blue' ? 'from-blue-500 to-blue-600' :
                        tab.color === 'green' ? 'from-green-500 to-green-600' :
                        tab.color === 'purple' ? 'from-purple-500 to-purple-600' :
                        'from-orange-500 to-orange-600'
                      } rounded-t-sm`} />
                    )}
                  </button>
                ))}
              </div>
              {/* Indicador de scroll para mobile */}
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2 sm:hidden">
                <div className="w-1.5 h-8 bg-gradient-to-b from-border to-borderLight rounded-full opacity-60 shadow-sm"></div>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-3 sm:p-6 min-h-0 bg-gradient-to-b from-white to-gray-50/30">
              {activeTab === "basic" && (
                <div className="space-y-4 sm:space-y-6">
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-blue-100">
                    <h3 className="text-lg sm:text-xl font-bold text-blue-800 mb-1 sm:mb-2 flex items-center">
                      <span className="mr-2 text-base sm:text-lg">📋</span>
                      <span className="text-sm sm:text-base">Informações Básicas</span>
                    </h3>
                    <p className="text-xs sm:text-sm text-blue-600 hidden sm:block">
                      Dados principais da empresa necessários para cadastro.
                    </p>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                    <div className="sm:col-span-2">
                      <TextField
                        fullWidth
                        label="Razão Social *"
                        value={formData.razao_social}
                        onChange={(e) => handleInputChange('razao_social', e.target.value)}
                        error={!!errors.razao_social}
                        helperText={errors.razao_social}
                        size="small"
                      />
                    </div>
                    <div>
                      <TextField
                        fullWidth
                        label="CNPJ *"
                        value={formData.cnpj}
                        onChange={(e) => handleInputChange('cnpj', companyService.formatCNPJInput(e.target.value))}
                        error={!!errors.cnpj}
                        helperText={errors.cnpj}
                        placeholder="00.000.000/0000-00"
                        size="small"
                      />
                    </div>
                    <div>
                      <TextField
                        fullWidth
                        label="Nome Fantasia"
                        value={formData.nome_fantasia}
                        onChange={(e) => handleInputChange('nome_fantasia', e.target.value)}
                        size="small"
                      />
                    </div>
                    <div>
                      <TextField
                        fullWidth
                        label="Inscrição Estadual"
                        value={formData.inscricao_estadual}
                        onChange={(e) => handleInputChange('inscricao_estadual', e.target.value.toUpperCase())}
                        error={!!errors.inscricao_estadual}
                        helperText={errors.inscricao_estadual}
                        placeholder="Digite a IE ou 'ISENTO'"
                        size="small"
                      />
                    </div>
                    <div>
                      <FormControl fullWidth size="small">
                        <InputLabel>Regime Tributário</InputLabel>
                        <Select
                          value={formData.regime_tributario}
                          onChange={(e) => handleInputChange('regime_tributario', e.target.value)}
                          label="Regime Tributário"
                        >
                          <MenuItem value="Simples Nacional">Simples Nacional</MenuItem>
                          <MenuItem value="Lucro Presumido">Lucro Presumido</MenuItem>
                          <MenuItem value="Lucro Real">Lucro Real</MenuItem>
                        </Select>
                      </FormControl>
                    </div>
                    <div>
                      <FormControl fullWidth size="small">
                        <InputLabel>Ambiente NFCom</InputLabel>
                        <Select
                          value={formData.ambiente_nfcom}
                          onChange={(e) => handleInputChange('ambiente_nfcom', e.target.value)}
                          label="Ambiente NFCom"
                        >
                          <MenuItem value="producao">Produção</MenuItem>
                          <MenuItem value="homologacao">Homologação</MenuItem>
                        </Select>
                      </FormControl>
                    </div>
                    <div>
                      <TextField
                        fullWidth
                        label="CNAE Principal"
                        value={formData.cnae_principal}
                        onChange={(e) => handleInputChange('cnae_principal', e.target.value)}
                        placeholder="Ex: 6201-5/00"
                        size="small"
                      />
                    </div>
                    <div>
                      <TextField
                        fullWidth
                        label="Telefone"
                        value={formData.telefone}
                        onChange={(e) => handleInputChange('telefone', companyService.formatPhoneInput(e.target.value))}
                        size="small"
                      />
                    </div>
                    <div>
                      <TextField
                        fullWidth
                        label="E-mail *"
                        type="email"
                        value={formData.email}
                        onChange={(e) => handleInputChange('email', e.target.value)}
                        error={!!errors.email}
                        helperText={errors.email}
                        size="small"
                      />
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "address" && (
                <div className="space-y-4 sm:space-y-6">
                  <div className="bg-gradient-to-r from-green-50 to-emerald-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-green-100">
                    <h3 className="text-lg sm:text-xl font-bold text-green-800 mb-1 sm:mb-2 flex items-center">
                      <span className="mr-2 text-base sm:text-lg">📍</span>
                      <span className="text-sm sm:text-base">Endereço da Empresa</span>
                    </h3>
                    <p className="text-xs sm:text-sm text-green-600 hidden sm:block">
                      Informe o endereço completo. O CEP preenche automaticamente os outros campos.
                    </p>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                    <div>
                      <TextField
                        fullWidth
                        label="CEP *"
                        value={formData.cep}
                        onChange={(e) => handleCepChange(e.target.value)}
                        error={!!errors.cep}
                        helperText={errors.cep}
                        placeholder="00000-000"
                        InputProps={{
                          endAdornment: cepLoading ? <CircularProgress size={16} /> : null,
                        }}
                        size="small"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <TextField
                        fullWidth
                        label="Endereço *"
                        value={formData.endereco}
                        onChange={(e) => handleInputChange('endereco', e.target.value)}
                        error={!!errors.endereco}
                        helperText={errors.endereco}
                        size="small"
                      />
                    </div>
                    <div>
                      <TextField
                        fullWidth
                        label="Número *"
                        value={formData.numero}
                        onChange={(e) => handleInputChange('numero', e.target.value)}
                        error={!!errors.numero}
                        helperText={errors.numero}
                        size="small"
                      />
                    </div>
                    <div>
                      <TextField
                        fullWidth
                        label="Complemento"
                        value={formData.complemento}
                        onChange={(e) => handleInputChange('complemento', e.target.value)}
                        size="small"
                      />
                    </div>
                    <div>
                      <TextField
                        fullWidth
                        label="Bairro *"
                        value={formData.bairro}
                        onChange={(e) => handleInputChange('bairro', e.target.value)}
                        error={!!errors.bairro}
                        helperText={errors.bairro}
                        size="small"
                      />
                    </div>
                    <div>
                      <TextField
                        fullWidth
                        label="Município *"
                        value={formData.municipio}
                        InputProps={{
                          readOnly: true,
                        }}
                        error={!!errors.municipio}
                        helperText={errors.municipio || "Preenchido automaticamente pelo CEP"}
                        size="small"
                      />
                    </div>
                    <div>
                      <TextField
                        fullWidth
                        label="UF *"
                        value={formData.uf}
                        InputProps={{
                          readOnly: true,
                        }}
                        error={!!errors.uf}
                        helperText={errors.uf || "Preenchido automaticamente"}
                        size="small"
                      />
                    </div>
                    <div>
                      <TextField
                        fullWidth
                        label="Código IBGE *"
                        value={formData.codigo_ibge}
                        InputProps={{
                          readOnly: true,
                        }}
                        error={!!errors.codigo_ibge}
                        helperText={errors.codigo_ibge || "Código do município"}
                        size="small"
                      />
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "billing" && (
                <div className="space-y-4 sm:space-y-6">
                  <div className="bg-gradient-to-r from-teal-50 to-cyan-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-teal-100">
                    <h3 className="text-lg sm:text-xl font-bold text-teal-800 mb-1 sm:mb-2 flex items-center">
                      <span className="mr-2 text-base sm:text-lg">💳</span>
                      <span className="text-sm sm:text-base">Configurações de Cobrança</span>
                    </h3>
                    <p className="text-xs sm:text-sm text-teal-600 hidden sm:block">
                      Configure a conta bancária padrão para cobranças desta empresa.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                    <div>
                      <FormControl fullWidth size="small">
                        <InputLabel>Conta Bancária Padrão</InputLabel>
                        <Select
                          value={formData.default_bank_account_id?.toString() || ''}
                          onChange={(e: SelectChangeEvent) => handleInputChange('default_bank_account_id', e.target.value === '' ? undefined : parseInt(e.target.value))}
                          label="Conta Bancária Padrão"
                        >
                          <MenuItem value="">
                            <em>Nenhuma</em>
                          </MenuItem>
                          {bankAccounts.map((bankAccount) => (
                            <MenuItem key={bankAccount.id} value={bankAccount.id.toString()}>
                              {bankAccount.bank} - {bankAccount.agencia}/{bankAccount.conta}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                      <p className="text-xs text-gray-500 mt-1">
                        Conta bancária usada por padrão em novos contratos desta empresa.
                      </p>
                    </div>

                    <div>
                      <TextField
                        fullWidth
                        label="Prazo de Bloqueio Automático (Dias)"
                        type="number"
                        variant="outlined"
                        value={formData.dias_bloqueio_inadimplentes ?? 15}
                        onChange={(e) => handleInputChange('dias_bloqueio_inadimplentes', e.target.value === '' ? undefined : parseInt(e.target.value))}
                        size="small"
                        InputProps={{ inputProps: { min: 0 } }}
                        helperText="Prazo em dias após o vencimento da fatura para o sistema bloquear o cliente automaticamente."
                      />
                    </div>

                    <div className="sm:col-span-2">
                      <TextField
                        fullWidth
                        label="Mensagem de Suspensão"
                        multiline
                        rows={3}
                        value={formData.suspension_message || ''}
                        onChange={(e) => handleInputChange('suspension_message', e.target.value)}
                        placeholder="Mensagem para exibir ao usuário suspenso..."
                        size="small"
                        helperText="Mensagem personalizada para exibir na página de aviso de bloqueio por falta de pagamento."
                      />
                    </div>

                    <div className="sm:col-span-2">
                      <TextField
                        fullWidth
                        label="URL de Aviso de Suspensão"
                        variant="outlined"
                        value={formData.suspension_url || ''}
                        onChange={(e) => handleInputChange('suspension_url', e.target.value)}
                        placeholder="http://seuprovedor.com.br/aviso"
                        size="small"
                        helperText="Se vazio, usará a página padrão do sistema."
                      />
                    </div>
                  </div>

                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-blue-100 mt-6">
                    <h3 className="text-lg sm:text-xl font-bold text-blue-800 mb-1 sm:mb-2 flex items-center">
                      <span className="mr-2 text-base sm:text-lg">🤝</span>
                      <span className="text-sm sm:text-base">Integração Mercado Pago</span>
                    </h3>
                    <p className="text-xs sm:text-sm text-blue-600 hidden sm:block">
                      Habilite pagamentos via Pix, Cartão e Boleto através do Mercado Pago.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                    <div className="sm:col-span-2">
                      <TextField
                        fullWidth
                        label="Access Token"
                        type="password"
                        value={formData.mp_access_token || ''}
                        onChange={(e) => handleInputChange('mp_access_token', e.target.value)}
                        size="small"
                        helperText="Token de acesso (Access Token) do Mercado Pago."
                        inputProps={{ autoComplete: 'new-password' }}
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <TextField
                        fullWidth
                        label="Public Key"
                        value={formData.mp_public_key || ''}
                        onChange={(e) => handleInputChange('mp_public_key', e.target.value)}
                        size="small"
                        helperText="Chave pública (Public Key) do Mercado Pago."
                        inputProps={{ autoComplete: 'new-password' }}
                      />
                    </div>
                    
                    <div className="sm:col-span-2 bg-white/50 p-3 rounded-lg border border-blue-100/50">
                      <Typography variant="subtitle2" sx={{ mb: 1.5, color: 'text.secondary', fontWeight: 600 }}>
                        Métodos de Pagamento Permitidos:
                      </Typography>
                      <div className="flex flex-wrap gap-4">
                        <label className="flex items-center space-x-2 cursor-pointer group">
                          <input
                            type="checkbox"
                            checked={formData.mp_allow_pix}
                            onChange={(e) => handleInputChange('mp_allow_pix', e.target.checked)}
                            className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500 transition-all cursor-pointer"
                          />
                          <span className="text-sm text-text group-hover:text-blue-600 transition-colors">Pix</span>
                        </label>
                        
                        <label className="flex items-center space-x-2 cursor-pointer group">
                          <input
                            type="checkbox"
                            checked={formData.mp_allow_credit_card}
                            onChange={(e) => handleInputChange('mp_allow_credit_card', e.target.checked)}
                            className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500 transition-all cursor-pointer"
                          />
                          <span className="text-sm text-text group-hover:text-blue-600 transition-colors">Cartão de Crédito</span>
                        </label>

                        <label className="flex items-center space-x-2 cursor-pointer group">
                          <input
                            type="checkbox"
                            checked={formData.mp_allow_boleto}
                            onChange={(e) => handleInputChange('mp_allow_boleto', e.target.checked)}
                            className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500 transition-all cursor-pointer"
                          />
                          <span className="text-sm text-text group-hover:text-blue-600 transition-colors">Boleto</span>
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "files" && (
                <div className="space-y-4 sm:space-y-6">
                  <div className="bg-gradient-to-r from-purple-50 to-violet-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-purple-100">
                    <h3 className="text-lg sm:text-xl font-bold text-purple-800 mb-1 sm:mb-2 flex items-center">
                      <span className="mr-2 text-base sm:text-lg">📁</span>
                      <span className="text-sm sm:text-base">Arquivos e Certificado</span>
                    </h3>
                    <p className="text-xs sm:text-sm text-purple-600 hidden sm:block">
                      Configure logo e certificado para NFCom
                    </p>
                  </div>

                  {/* Seção do Logo */}
                  <div className="space-y-2 sm:space-y-3 lg:space-y-4">
                    <h4 className="text-sm sm:text-base lg:text-md font-medium text-text">Logo da Empresa</h4>
                    <div className="pl-0 sm:pl-4">
                      <FileUploader
                        label=""
                        accept="image/*"
                        maxSize={5}
                        currentFile={formData.logo_url}
                        onFileSelect={setLogoFile}
                        placeholder="Nenhum logo selecionado"
                        instructions={[
                          "PNG transparente recomendado",
                          "Ideal: 200x80px"
                        ]}
                      />
                    </div>
                  </div>

                  {/* Seção do Certificado */}
                  <div className="space-y-2 sm:space-y-3 lg:space-y-4">
                    <h4 className="text-sm sm:text-base lg:text-md font-medium text-text">Certificado Digital</h4>
                    <div className="pl-0 sm:pl-4 space-y-2 sm:space-y-3 lg:space-y-4">
                      <FileUploader
                        label=""
                        accept=".p12,.pfx"
                        maxSize={10}
                        currentFile={formData.certificado_path}
                        onFileSelect={setCertificateFile}
                        placeholder="Nenhum certificado selecionado"
                        instructions={[
                          "Formatos: .p12 ou .pfx",
                          "Certificado A1/A3 válido"
                        ]}
                      />

                      <div className="max-w-md">
                        <TextField
                          fullWidth
                          label="Senha do Certificado"
                          type="password"
                          value={formData.certificado_senha}
                          onChange={(e) => handleInputChange('certificado_senha', e.target.value)}
                          placeholder="Digite a senha do certificado"
                          size="small"
                          helperText="Necessária para usar o certificado"
                          inputProps={{ autoComplete: 'new-password' }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "email" && (
                <div className="space-y-6">
                  {/* Título da Seção */}
                  <div className="bg-gradient-to-r from-orange-50 to-amber-50 p-4 rounded-2xl border border-orange-100/70 shadow-sm">
                    <h3 className="text-lg font-bold text-orange-800 mb-1 flex items-center">
                      <span className="mr-2 text-xl">💬</span>
                      <span>Canais de Comunicação & Notificações</span>
                    </h3>
                    <p className="text-xs sm:text-sm text-orange-600">
                      Escolha como as faturas e contratos da sua empresa serão disparados para os clientes.
                    </p>
                  </div>

                  {/* Seleção de Métodos Ativos */}
                  <div className="bg-white p-5 rounded-2xl border border-borderLight shadow-sm">
                    <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary', fontWeight: 600, fontSize: '0.875rem' }}>
                      Métodos de Disparo Ativos:
                    </Typography>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {/* E-mail Toggle Card */}
                      <label className={`flex items-start p-4 rounded-xl border-2 transition-all cursor-pointer select-none group ${
                        formData.send_method_email
                          ? 'border-orange-500 bg-orange-50/30'
                          : 'border-gray-200 hover:border-gray-300 bg-white'
                      }`}>
                        <input
                          type="checkbox"
                          checked={formData.send_method_email}
                          onChange={(e) => handleInputChange('send_method_email', e.target.checked)}
                          className="w-5 h-5 text-orange-600 rounded border-gray-300 focus:ring-orange-500 transition-all cursor-pointer mt-0.5"
                        />
                        <div className="ml-3">
                          <span className="font-bold text-sm text-text flex items-center gap-1.5">
                            📧 Enviar por E-mail
                          </span>
                          <span className="block text-xs text-textLight mt-1">
                            Dispara cobranças e links de assinatura diretamente para o e-mail do cliente usando SMTP próprio.
                          </span>
                        </div>
                      </label>

                      {/* WhatsApp Toggle Card */}
                      <label className={`flex items-start p-4 rounded-xl border-2 transition-all cursor-pointer select-none group ${
                        formData.send_method_whatsapp
                          ? 'border-green-500 bg-green-50/20'
                          : 'border-gray-200 hover:border-gray-300 bg-white'
                      }`}>
                        <input
                          type="checkbox"
                          checked={formData.send_method_whatsapp}
                          onChange={(e) => handleInputChange('send_method_whatsapp', e.target.checked)}
                          className="w-5 h-5 text-green-600 rounded border-gray-300 focus:ring-green-500 transition-all cursor-pointer mt-0.5"
                        />
                        <div className="ml-3">
                          <span className="font-bold text-sm text-text flex items-center gap-1.5">
                            <svg className="w-4 h-4 text-green-500 fill-current" viewBox="0 0 448 512">
                              <path d="M380.9 97.1C339 55.1 283.2 32 223.9 32c-122.4 0-222 99.6-222 222 0 39.1 10.2 77.3 29.6 111L3 480l117.7-30.9c32.4 17.7 68.9 27 106.1 27h.1c122.3 0 224.1-99.6 224.1-222 0-59.3-25.2-115-67.1-157zm-157 341.6c-33.2 0-65.7-8.9-94-25.7l-6.7-4-69.8 18.3L72 359.2l-4.4-7c-18.5-29.4-28.2-63.3-28.2-98.2 0-101.7 82.8-184.5 184.6-184.5 49.3 0 95.6 19.2 130.4 54.1 34.8 34.9 56.2 81.2 56.1 130.5 0 101.8-84.9 184.6-186.6 184.6zm101.2-138.2c-5.5-2.8-32.8-16.2-37.9-18-5.1-1.9-8.8-2.8-12.5 2.8-3.7 5.6-14.3 18-17.6 21.8-3.2 3.7-6.5 4.2-12 1.4-32.6-16.3-54-29.1-75.5-66-5.7-9.8 5.7-9.1 16.3-30.3 1.8-3.7 .9-6.9-.5-9.7-1.4-2.8-12.5-30.1-17.1-41.2-4.5-10.8-9.1-9.3-12.5-9.5-3.2-.2-6.9-.2-10.6-.2-3.7 0-9.7 1.4-14.8 6.9-5.1 5.6-19.4 19-19.4 46.3 0 27.3 19.9 53.7 22.6 57.4 2.8 3.7 39.1 59.7 94.8 83.8 35.2 15.2 49 16.5 66.6 13.9 10.7-1.6 32.8-13.4 37.4-26.4 4.6-13 4.6-24.1 3.2-26.4-1.3-2.5-5-3.9-10.5-6.6z"/>
                            </svg>
                            <span>Enviar por WhatsApp</span>
                          </span>
                          <span className="block text-xs text-textLight mt-1">
                            Notifica os clientes e envia links de assinatura do termo e chaves Pix diretamente para o celular via WhatsApp.
                          </span>
                        </div>
                      </label>
                    </div>
                  </div>

                  {/* CONFIGURAÇÃO DE EMAIL SMTP */}
                  {formData.send_method_email && (
                    <div className="bg-white p-5 rounded-2xl border border-borderLight shadow-sm space-y-4 transition-all">
                      <div className="flex items-center space-x-2 pb-2 border-b border-gray-100">
                        <span className="text-lg">📧</span>
                        <h4 className="font-bold text-sm text-text">Configuração de E-mail (SMTP)</h4>
                      </div>
                      
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <TextField
                          fullWidth
                          label="Servidor SMTP"
                          value={formData.smtp_server || ''}
                          onChange={(e) => handleInputChange('smtp_server', e.target.value)}
                          placeholder="smtp.gmail.com"
                          size="small"
                        />
                        <TextField
                          fullWidth
                          label="Porta SMTP"
                          type="number"
                          value={formData.smtp_port || ''}
                          onChange={(e) => handleInputChange('smtp_port', e.target.value ? parseInt(e.target.value) : undefined)}
                          placeholder="587"
                          inputProps={{ min: 1, max: 65535 }}
                          size="small"
                        />
                        <TextField
                          fullWidth
                          label="Usuário SMTP"
                          value={formData.smtp_user || ''}
                          onChange={(e) => handleInputChange('smtp_user', e.target.value)}
                          placeholder="seu-email@gmail.com"
                          size="small"
                        />
                        <TextField
                          fullWidth
                          label="Senha SMTP"
                          type="password"
                          value={formData.smtp_password || ''}
                          onChange={(e) => handleInputChange('smtp_password', e.target.value)}
                          placeholder="Senha do email"
                          size="small"
                          helperText={smtpPasswordConfigured ? 'Senha já configurada — deixe em branco para manter' : ''}
                          inputProps={{ autoComplete: 'new-password' }}
                        />
                      </div>
                      
                      <div className="flex justify-end pt-2">
                        <button
                          type="button"
                          onClick={handleTestSMTP}
                          disabled={testingSMTP}
                          className="px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-xl hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50 transition-all duration-200 font-semibold text-xs shadow-md hover:shadow-lg flex items-center gap-1.5"
                        >
                          {testingSMTP ? (
                            <>
                              <CircularProgress size={12} color="inherit" />
                              <span>Testando...</span>
                            </>
                          ) : (
                            <>
                              <span>⚡</span>
                              <span>Testar SMTP</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* CONFIGURAÇÃO DE WHATSAPP API */}
                  {formData.send_method_whatsapp && (
                    <div className="space-y-4 transition-all">
                      {/* CARD 1: NÚMEROS DE DISPARO */}
                      <div className="bg-white rounded-2xl border border-borderLight shadow-sm overflow-hidden transition-all duration-200">
                        <button
                          type="button"
                          onClick={() => setIsNumbersOpen(!isNumbersOpen)}
                          className="w-full flex items-center justify-between p-4 bg-gradient-to-r from-gray-50 to-white hover:from-gray-100/50 transition-colors border-b border-borderLight"
                        >
                          <div className="flex items-center space-x-2.5">
                            <span className="text-lg">📲</span>
                            <span className="font-bold text-sm text-text">Números de disparo</span>
                          </div>
                          <span className={`transform transition-transform duration-200 text-gray-400 ${isNumbersOpen ? 'rotate-180' : ''}`}>
                            ▼
                          </span>
                        </button>

                        {isNumbersOpen && (
                          <div className="p-5 space-y-4">
                            {!editingCompany ? (
                              <div className="p-4 rounded-xl border border-blue-100 bg-blue-50/50 text-center">
                                <span className="text-xl block mb-1">📋</span>
                                <span className="font-bold text-xs text-blue-800 block">Empresa Não Salva</span>
                                <span className="text-2xs sm:text-xs text-blue-600">
                                  Cadastre e salve a empresa primeiro para poder vincular um número de WhatsApp.
                                </span>
                              </div>
                            ) : (
                              <div className="space-y-4">
                                {!formData.whatsapp_api_instance ? (
                                  <div className="p-6 rounded-2xl border-2 border-dashed border-gray-200 bg-gray-50/50 text-center space-y-4">
                                    <div className="w-12 h-12 rounded-full bg-orange-50 flex items-center justify-center mx-auto shadow-sm">
                                      <span className="text-xl">📲</span>
                                    </div>
                                    <div className="space-y-1">
                                      <span className="font-bold text-sm text-text block">Nenhuma Instância Vinculada</span>
                                      <p className="text-xs text-textLight max-w-sm mx-auto">
                                        Vincule uma nova instância de WhatsApp para esta empresa para poder conectar o dispositivo e habilitar notificações.
                                      </p>
                                    </div>
                                    <div className="flex max-w-md mx-auto gap-2 pt-2">
                                      <TextField
                                        size="small"
                                        fullWidth
                                        placeholder="Ex: minha-empresa-zap"
                                        id="new-instance-input"
                                        inputProps={{ style: { fontSize: '0.75rem' } }}
                                        label="Nome da Nova Instância"
                                        variant="outlined"
                                      />
                                      <button
                                        type="button"
                                        onClick={async () => {
                                          const el = document.getElementById('new-instance-input') as HTMLInputElement;
                                          const val = el?.value?.trim();
                                          if (!val) {
                                            setSnackbar({
                                              open: true,
                                              message: 'Digite um nome válido para a instância',
                                              severity: 'error'
                                            });
                                            return;
                                          }
                                          handleInputChange('whatsapp_api_instance', val);
                                          if (editingCompany) {
                                            try {
                                              await companyService.updateCompany(editingCompany.id, {
                                                ...formData,
                                                whatsapp_api_instance: val
                                              } as any);
                                              setSnackbar({
                                                open: true,
                                                message: 'Instância adicionada com sucesso!',
                                                severity: 'success'
                                              });
                                            } catch (e) {
                                              console.error(e);
                                              setSnackbar({
                                                open: true,
                                                message: 'Erro ao salvar a nova instância no banco.',
                                                severity: 'error'
                                              });
                                            }
                                          }
                                        }}
                                        className="px-4 py-2 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white rounded-xl text-xs font-bold transition-all shadow-md whitespace-nowrap self-stretch flex items-center justify-center"
                                      >
                                        Adicionar Instância
                                      </button>
                                    </div>
                                  </div>
                                ) : (
                                  <div className="space-y-4">
                                    <div className="overflow-hidden border border-gray-200 rounded-xl bg-white shadow-sm">
                                      <table className="min-w-full divide-y divide-gray-200">
                                        <thead className="bg-gray-50/70">
                                          <tr>
                                            <th scope="col" className="px-4 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Instância</th>
                                            <th scope="col" className="px-4 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Telefone</th>
                                            <th scope="col" className="px-4 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Status</th>
                                            <th scope="col" className="px-4 py-3 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">Ações</th>
                                          </tr>
                                        </thead>
                                        <tbody className="bg-white divide-y divide-gray-200">
                                          <tr className="hover:bg-gray-50/40 transition-colors">
                                            <td className="px-4 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">
                                              {formData.whatsapp_api_instance}
                                            </td>
                                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 font-medium">
                                              {formData.telefone || 'Não cadastrado'}
                                            </td>
                                            <td className="px-4 py-4 whitespace-nowrap">
                                              {loadingWhatsAppState ? (
                                                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                                                  <CircularProgress size={12} color="inherit" />
                                                  <span>Verificando...</span>
                                                </div>
                                              ) : whatsappConnected ? (
                                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100">
                                                  <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-emerald-500 animate-ping" />
                                                  Conectado
                                                </span>
                                              ) : (
                                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-100">
                                                  Desconectado
                                                </span>
                                              )}
                                            </td>
                                            <td className="px-4 py-4 whitespace-nowrap text-right text-sm font-medium">
                                              <div className="flex justify-end gap-2">
                                                <button
                                                  type="button"
                                                  onClick={() => handleCheckWhatsAppConnection(editingCompany.id)}
                                                  disabled={loadingWhatsAppState}
                                                  className="px-3 py-1.5 border border-gray-300 bg-white hover:bg-gray-50 text-gray-700 rounded-lg text-xs font-bold transition-all disabled:opacity-50 shadow-sm"
                                                >
                                                  🔄 Verificar
                                                </button>
                                                
                                                {whatsappConnected ? (
                                                  <button
                                                    type="button"
                                                    onClick={() => handleDisconnectWhatsApp(editingCompany.id)}
                                                    className="px-3 py-1.5 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg text-xs font-bold transition-all shadow-sm"
                                                  >
                                                    Desconectar
                                                  </button>
                                                ) : (
                                                  <>
                                                    {!whatsappQrCode && !loadingQrCode && (
                                                      <button
                                                        type="button"
                                                        onClick={() => handleGetWhatsAppQrCode(editingCompany.id)}
                                                        className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-bold transition-all shadow-sm"
                                                      >
                                                        📲 Conectar
                                                      </button>
                                                    )}
                                                  </>
                                                )}

                                                <button
                                                  type="button"
                                                  onClick={async () => {
                                                    if (window.confirm("Tem certeza que deseja excluir esta instância? A sessão do WhatsApp será encerrada na Brazcom API e desvinculada desta empresa.")) {
                                                      try {
                                                        // Desconecta da Brazcom API primeiro
                                                        await handleDisconnectWhatsApp(editingCompany.id);
                                                      } catch (e) {
                                                        console.warn("Brazcom API logout failed/already offline:", e);
                                                      }
                                                      
                                                      handleInputChange('whatsapp_api_instance', '');
                                                      try {
                                                        await companyService.updateCompany(editingCompany.id, {
                                                          ...formData,
                                                          whatsapp_api_instance: ''
                                                        } as any);
                                                        setWhatsappConnected(null);
                                                        setWhatsappQrCode(null);
                                                        setSnackbar({
                                                          open: true,
                                                          message: 'Instância excluída com sucesso!',
                                                          severity: 'success'
                                                        });
                                                      } catch (e) {
                                                        console.error('Erro ao atualizar empresa:', e);
                                                      }
                                                    }
                                                  }}
                                                  className="px-3 py-1.5 border border-red-200 hover:bg-red-50 text-red-600 rounded-lg text-xs font-bold transition-all shadow-sm"
                                                >
                                                  ❌ Excluir Instância
                                                </button>
                                              </div>
                                            </td>
                                          </tr>
                                        </tbody>
                                      </table>
                                    </div>

                                    {loadingQrCode && (
                                      <div className="flex flex-col items-center justify-center p-6 space-y-2 border border-gray-100 rounded-xl bg-gray-50/50">
                                        <CircularProgress size={24} color="success" />
                                        <span className="text-xs text-textLight font-semibold">Gerando QR Code na Brazcom API...</span>
                                      </div>
                                    )}

                                    {whatsappQrCode && !loadingQrCode && (
                                      <div className="p-4 border border-gray-200 rounded-xl bg-white space-y-4 text-center">
                                        <h5 className="font-bold text-sm text-text">Escaneie o QR Code abaixo</h5>
                                        <img
                                          src={whatsappQrCode}
                                          alt="WhatsApp QR Code"
                                          className="w-48 h-48 mx-auto border border-gray-200 rounded-lg shadow-sm p-1 bg-white"
                                        />
                                        <div className="text-2xs sm:text-xs text-textLight text-left space-y-1 max-w-sm mx-auto bg-gray-50 p-3 rounded-lg">
                                          <p className="font-semibold text-text">Passo a passo:</p>
                                          <p>1. Abra o WhatsApp no seu smartphone.</p>
                                          <p>2. Toque em <strong>Mais Opções / Configurações</strong> e selecione <strong>Aparelhos Conectados</strong>.</p>
                                          <p>3. Clique em <strong>Conectar um Aparelho</strong> e aponte a câmera para esta tela.</p>
                                        </div>
                                        <button
                                          type="button"
                                          onClick={() => handleCheckWhatsAppConnection(editingCompany.id)}
                                          className="px-4 py-2 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white text-xs font-bold rounded-xl shadow-md transition-all"
                                        >
                                          ✅ Já escaneei (Confirmar Conexão)
                                        </button>
                                      </div>
                                    )}

                                    {/* Campo de edição do ID do Dispositivo */}
                                    <div className="pt-2">
                                      <TextField
                                        fullWidth
                                        label="Editar Nome da Instância"
                                        value={formData.whatsapp_api_instance || ''}
                                        onChange={(e) => handleInputChange('whatsapp_api_instance', e.target.value)}
                                        placeholder="mega-net-telecom"
                                        size="small"
                                        helperText="Nome identificador único da sua instância (ex. nome-da-empresa) para controle no gateway."
                                      />
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                  </div>

                      {/* CARD GRUPADO: CONFIGURAÇÕES AVANÇADAS & INTEGRAÇÕES EXTERNAS */}
                      <div className="bg-white rounded-2xl border border-borderLight shadow-sm overflow-hidden transition-all duration-200">
                        <button
                          type="button"
                          onClick={() => setIsIntegrationOpen(!isIntegrationOpen)}
                          className="w-full flex items-center justify-between p-4 bg-gradient-to-r from-gray-50 to-white hover:from-gray-100/50 transition-colors border-b border-borderLight"
                        >
                          <div className="flex items-center space-x-2.5">
                            <span className="text-lg">⚙️</span>
                            <span className="font-bold text-sm text-text">Configurações Avançadas de API & Gateway (Opcional)</span>
                          </div>
                          <span className={`transform transition-transform duration-200 text-gray-400 ${isIntegrationOpen ? 'rotate-180' : ''}`}>
                            ▼
                          </span>
                        </button>

                        {isIntegrationOpen && (
                          <div className="p-5 space-y-6 bg-gray-50/30">
                            {/* SUB-SEÇÃO 1: GATEWAY DE WHATSAPP PRIVADO */}
                            <div className="bg-white p-4 rounded-xl border border-gray-200 space-y-3">
                              <h5 className="font-bold text-xs text-text uppercase tracking-wider flex items-center gap-1.5">
                                <span>🌐</span> Servidor de Gateway Privado
                              </h5>
                              <p className="text-2xs sm:text-xs text-textLight">
                                Por padrão, o Brazcom ISP Suite utiliza o servidor Brazcom API centralizado da plataforma (configurado no seu Docker/Mac). Configure os campos abaixo <strong>apenas</strong> se você deseja usar um servidor Brazcom API privado para esta empresa específica.
                              </p>

                              {/* Elementos ocultos para capturar e anular o preenchimento automático agressivo dos navegadores */}
                              <input type="text" name="prevent_autofill_user" style={{ display: 'none' }} autoComplete="off" />
                              <input type="password" name="prevent_autofill_pass" style={{ display: 'none' }} autoComplete="off" />

                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <TextField
                                  fullWidth
                                  label="URL do Servidor Brazcom API"
                                  value={formData.whatsapp_api_server || ''}
                                  onChange={(e) => handleInputChange('whatsapp_api_server', e.target.value)}
                                  placeholder="http://seu-servidor:8080"
                                  size="small"
                                  helperText="Deixe em branco para usar o gateway padrão."
                                  inputProps={{ autoComplete: 'new-password' }}
                                />
                                <TextField
                                  fullWidth
                                  label="API Key / Token da API"
                                  type="password"
                                  value={formData.whatsapp_api_password || ''}
                                  onChange={(e) => handleInputChange('whatsapp_api_password', e.target.value)}
                                  placeholder="Token do seu gateway"
                                  size="small"
                                  helperText="Deixe em branco para usar a chave padrão."
                                  inputProps={{ autoComplete: 'new-password' }}
                                />
                              </div>
                            </div>

                            {/* SWITCH DE INTEGRAÇÃO EXTERNA */}
                            <label className="flex items-center space-x-3 cursor-pointer p-4 rounded-xl border border-blue-100 bg-blue-50/10 hover:bg-blue-50/20 transition-all select-none">
                              <input
                                type="checkbox"
                                checked={showExternalIntegration}
                                onChange={(e) => setShowExternalIntegration(e.target.checked)}
                                className="w-5 h-5 text-blue-600 rounded border-gray-300 focus:ring-blue-500 cursor-pointer transition-all"
                              />
                              <div>
                                <span className="font-bold text-sm text-text block">Ativar Integrações com Sistemas Externos (Opcional)</span>
                                <span className="text-2xs sm:text-xs text-textLight block mt-0.5">
                                  Marque esta opção se você possui um financeiro externo (como MK-Auth, IXC, SGP) e quer que ele faça disparos de WhatsApp através do Brazcom ISP Suite.
                                </span>
                              </div>
                            </label>

                            {showExternalIntegration && (
                              <>
                                {/* SUB-SEÇÃO 2: DADOS PARA INTEGRAÇÃO EXTERNA (MK-Auth, SGP, etc.) */}
                                <div className="bg-white p-4 rounded-xl border border-gray-200 space-y-3">
                                  <h5 className="font-bold text-xs text-text uppercase tracking-wider flex items-center gap-1.5">
                                    <span>🔌</span> Integração com Sistemas Externos (ex: MK-Auth, IXC, SGP)
                                  </h5>
                                  <p className="text-2xs sm:text-xs text-textLight">
                                    Credenciais de webhook geradas para integrar sistemas de cobrança externos à API de disparos do Brazcom ISP Suite.
                                  </p>
                                  <div>
                                    <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700, mb: 1, display: 'block' }}>
                                      Sistema de integração:
                                    </Typography>
                                    <div className="flex flex-wrap gap-2">
                                      {[
                                        'MK Solutions', 'IXC', 'SGP', 'MK Auth', 'Vigo', 'Controllr', 'RouterBox', 'ISPCloud', 'API'
                                      ].map((sys) => (
                                        <button
                                          key={sys}
                                          type="button"
                                          onClick={() => handleInputChange('whatsapp_api_system', sys)}
                                          className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all ${
                                            formData.whatsapp_api_system === sys
                                              ? 'border-blue-500 bg-blue-50 text-blue-700 font-bold'
                                              : 'border-gray-200 bg-white hover:bg-gray-50 text-textLight'
                                          }`}
                                        >
                                          {sys}
                                        </button>
                                      ))}
                                    </div>
                                  </div>

                                  <div className="grid grid-cols-1 gap-3 pt-2">
                                    <div className="flex items-center gap-2">
                                      <TextField
                                        fullWidth
                                        label="Usar"
                                        value={formData.whatsapp_api_user || ''}
                                        size="small"
                                        InputProps={{ readOnly: true }}
                                      />
                                      <button
                                        type="button"
                                        onClick={() => handleCopyToClipboard(formData.whatsapp_api_user || '', 'Usuário')}
                                        className="w-9 h-9 flex items-center justify-center border border-gray-200 hover:bg-gray-50 rounded-lg text-sm"
                                      >
                                        📋
                                      </button>
                                    </div>
                                    <div className="flex items-center gap-2">
                                      <TextField
                                        fullWidth
                                        label="Servidor"
                                        value={formData.whatsapp_api_server || ''}
                                        size="small"
                                        InputProps={{ readOnly: true }}
                                      />
                                      <button
                                        type="button"
                                        onClick={() => handleCopyToClipboard(formData.whatsapp_api_server || '', 'URL do Servidor')}
                                        className="w-9 h-9 flex items-center justify-center border border-gray-200 hover:bg-gray-50 rounded-lg text-sm"
                                      >
                                        📋
                                      </button>
                                    </div>
                                    <div className="flex items-center gap-2">
                                      <TextField
                                        fullWidth
                                        label="Senha"
                                        value={formData.whatsapp_api_password || ''}
                                        size="small"
                                        InputProps={{ readOnly: true }}
                                      />
                                      <button
                                        type="button"
                                        onClick={() => handleCopyToClipboard(formData.whatsapp_api_password || '', 'Senha de Integração')}
                                        className="w-9 h-9 flex items-center justify-center border border-gray-200 hover:bg-gray-50 rounded-lg text-sm"
                                      >
                                        📋
                                      </button>
                                    </div>
                                  </div>

                                  <div className="pt-1 flex flex-col sm:flex-row gap-2 items-center justify-between">
                                    <a
                                      href="https://wa.me/5549999251349?text=Ol%C3%A1%2C+gostaria+de+solicitar+um+novo+sistema+de+gerenciamento+de+provedores+para+o+MK+Mensagens."
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-600 font-bold text-xs rounded-lg transition-all decoration-none border border-blue-100"
                                    >
                                      🚀 Solicitar novo sistema
                                    </a>
                                    <span className="text-2xs text-amber-600 bg-amber-50 px-2.5 py-1 rounded-lg border border-amber-100 font-semibold">
                                      ⚠️ O campo <strong>Conta</strong> no seu SGP/MK-Auth deve ficar vazio!
                                    </span>
                                  </div>
                                </div>

                                {/* SUB-SEÇÃO 3: SEGURANÇA (IP WHITELIST) */}
                                <div className="bg-white p-4 rounded-xl border border-gray-200 space-y-3">
                                  <h5 className="font-bold text-xs text-text uppercase tracking-wider flex items-center gap-1.5">
                                    <span>🔒</span> Segurança (Whitelist de IPs)
                                  </h5>
                                  <p className="text-2xs sm:text-xs text-textLight">
                                    Se configurado, apenas requisições originadas destes IPs poderão efetuar disparos usando estas credenciais de integração.
                                  </p>
                                  <div className="flex items-center gap-2">
                                    <TextField
                                      fullWidth
                                      label="Novo IP (ex: 200.123.45.67)"
                                      value={newIpInput}
                                      onChange={(e) => setNewIpInput(e.target.value)}
                                      placeholder="Digite o IP do servidor"
                                      size="small"
                                      onKeyDown={(e) => {
                                        if (e.key === 'Enter') {
                                          e.preventDefault();
                                          handleAddIp(newIpInput);
                                          setNewIpInput('');
                                        }
                                      }}
                                    />
                                    <button
                                      type="button"
                                      onClick={() => {
                                        handleAddIp(newIpInput);
                                        setNewIpInput('');
                                      }}
                                      className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-all font-semibold text-xs shadow-sm flex-shrink-0"
                                      style={{ height: '40px' }}
                                    >
                                      Adicionar
                                    </button>
                                  </div>

                                  <div className="flex flex-wrap gap-2 pt-1">
                                    {formData.whatsapp_api_ips
                                      ? formData.whatsapp_api_ips.split(',').map(ip => ip.trim()).filter(Boolean).map((ip) => (
                                          <div
                                            key={ip}
                                            className="flex items-center space-x-1.5 px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded-full border border-gray-200 transition-colors text-xs font-semibold text-text"
                                          >
                                            <span>🌐 {ip}</span>
                                            <button
                                              type="button"
                                              onClick={() => handleRemoveIp(ip)}
                                              className="text-red-500 hover:text-red-700 font-bold ml-1 cursor-pointer focus:outline-none"
                                              title="Remover IP"
                                            >
                                              ×
                                            </button>
                                          </div>
                                        ))
                                      : (
                                          <div className="w-full text-center p-3 border border-dashed border-gray-200 rounded-xl bg-gray-50/50">
                                            <span className="text-xs text-textLight italic">Nenhum IP restrito. Conexões aceitas de qualquer IP.</span>
                                          </div>
                                        )
                                    }
                                  </div>
                                </div>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeTab === "isp" && (
                <div className="space-y-4 sm:space-y-6">
                  <div className="bg-gradient-to-r from-indigo-50 to-blue-50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-indigo-100">
                    <h3 className="text-lg sm:text-xl font-bold text-indigo-800 mb-1 sm:mb-2 flex items-center">
                      <span className="mr-2 text-base sm:text-lg">📄</span>
                      <span className="text-sm sm:text-base">Informações ISP / Contratos</span>
                    </h3>
                    <p className="text-xs sm:text-sm text-indigo-600 hidden sm:block">
                      Dados regulatórios e informações que aparecerão nos termos de adesão.
                    </p>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                    <div>
                      <TextField
                        fullWidth
                        label="Ato de Autorização nº"
                        value={formData.ato_autorizacao}
                        onChange={(e) => handleInputChange('ato_autorizacao', e.target.value)}
                        placeholder="Ex: 6.792/2011"
                        size="small"
                        helperText="Número do ato da ANATEL"
                      />
                    </div>
                    <div>
                      <TextField
                        fullWidth
                        label="Nº Registro em Cartório"
                        value={formData.contrato_registro_num}
                        onChange={(e) => handleInputChange('contrato_registro_num', e.target.value)}
                        placeholder="Ex: 27.505"
                        size="small"
                        helperText="Número de registro do contrato em cartório"
                      />
                    </div>
                    <div>
                      <TextField
                        fullWidth
                        label="Site da Empresa"
                        value={formData.site}
                        onChange={(e) => handleInputChange('site', e.target.value)}
                        placeholder="Ex: isp.brazcom.com.br"
                        size="small"
                      />
                    </div>
                    <div>
                      <TextField
                        fullWidth
                        label="E-mail para Contratos"
                        value={formData.email_contato}
                        onChange={(e) => handleInputChange('email_contato', e.target.value)}
                        placeholder="Ex: contratos@brazcom.com.br"
                        size="small"
                        helperText="Email que aparecerá no corpo do contrato"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <TextField
                        fullWidth
                        label="Mensagem de Suspensão"
                        value={formData.suspension_message}
                        onChange={(e) => handleInputChange('suspension_message', e.target.value)}
                        placeholder="Ex: Sua conexão está suspensa por falta de pagamento."
                        multiline
                        rows={2}
                        size="small"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <TextField
                        fullWidth
                        label="URL de Suspensão"
                        value={formData.suspension_url}
                        onChange={(e) => handleInputChange('suspension_url', e.target.value)}
                        placeholder="Ex: https://isp.brazcom.com.br"
                        size="small"
                        helperText="URL para onde o cliente será redirecionado se estiver bloqueado"
                      />
                    </div>

                    <div className="sm:col-span-2 space-y-2 sm:space-y-3 lg:space-y-4 pt-4">
                      <h4 className="text-sm sm:text-base lg:text-md font-medium text-text">Assinatura Digital do Representante</h4>
                      <div className="pl-0 sm:pl-4">
                        <FileUploader
                          label=""
                          accept="image/*"
                          maxSize={2}
                          currentFile={formData.assinatura_digital_url}
                          onFileSelect={(file) => setSignatureFile(file)}
                          onRemove={async () => {
                            if (editingCompany && formData.assinatura_digital_url) {
                              try {
                                await companyService.deleteCompanySignature(editingCompany.id);
                                handleInputChange('assinatura_digital_url', '');
                              } catch (error) {
                                console.error('Erro ao excluir assinatura:', error);
                                setSnackbar({
                                  open: true,
                                  message: 'Erro ao excluir assinatura',
                                  severity: 'error'
                                });
                              }
                            } else {
                              setSignatureFile(null);
                            }
                          }}
                          placeholder="Clique ou arraste a assinatura do representante legal (PNG/JPG)"
                        />
                        <p className="text-xs text-gray-500 mt-2">
                          * Recomendado: Imagem com fundo transparente (PNG) de aprox. 400x150 pixels.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-2 sm:gap-3 p-3 sm:p-6 border-t border-borderLight bg-gradient-to-r from-gray-50 to-blue-50/30 flex-shrink-0 shadow-modern">
              <div className="hidden sm:flex items-center space-x-2 text-xs sm:text-sm text-blue-600 text-center sm:text-left">
                <span className="text-xs sm:text-lg">💡</span>
                <p className="leading-tight font-normal text-xs">
                  Navegue pelas abas para preencher informações
                </p>
              </div>
              <div className="flex gap-2 sm:gap-3 justify-center sm:justify-end">
                <button
                  onClick={handleCloseDialog}
                  className="px-4 sm:px-5 py-2 sm:py-2.5 btn-secondary rounded-lg sm:rounded-xl shadow-sm hover:shadow-md transition-all duration-200 font-semibold flex-shrink-0 text-sm sm:text-sm"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleSubmit}
                  className="px-4 sm:px-5 py-2 sm:py-2.5 btn-primary rounded-lg sm:rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 font-semibold flex-shrink-0 text-sm sm:text-sm bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700"
                >
                  <span className="hidden sm:inline">
                    {editingCompany ? 'Atualizar Empresa' : 'Criar Empresa'}
                  </span>
                  <span className="sm:hidden">
                    {editingCompany ? 'Atualizar' : 'Criar'}
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Snackbar para mensagens */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
      >
        <Alert
          onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Companies;