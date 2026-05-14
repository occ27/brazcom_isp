import React, { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import SignatureCanvas from 'react-signature-canvas';
import { 
  Box, 
  Container, 
  Paper, 
  Typography, 
  Button, 
  CircularProgress, 
  Alert, 
  Divider,
  Stack,
  IconButton
} from '@mui/material';
import { 
  Delete as DeleteIcon, 
  CheckCircle as CheckCircleIcon, 
  Create as CreateIcon 
} from '@mui/icons-material';
import { useSnackbar } from 'notistack';

const API_URL = import.meta.env.VITE_API_URL || '/api';

const PublicSignature: React.FC = () => {
    const { token } = useParams<{ token: string }>();
    const { enqueueSnackbar } = useSnackbar();
    
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [contract, setContract] = useState<any>(null);
    const [signing, setSigning] = useState(false);
    const [success, setSuccess] = useState(false);
    
    const sigPad = useRef<SignatureCanvas>(null);

    useEffect(() => {
        fetchContract();
    }, [token]);

    const fetchContract = async () => {
        try {
            setLoading(true);
            const response = await axios.get(`${API_URL}/public-contrato/${token}`);
            setContract(response.data);
            if (response.data.assinado) {
                setSuccess(true);
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Erro ao carregar contrato. O link pode estar expirado ou inválido.');
        } finally {
            setLoading(false);
        }
    };

    const clearSignature = () => {
        sigPad.current?.clear();
    };

    const handleSign = async () => {
        if (sigPad.current?.isEmpty()) {
            enqueueSnackbar('Por favor, faça sua assinatura no quadro abaixo.', { variant: 'warning' });
            return;
        }

        try {
            setSigning(true);
            // Usar getCanvas() em vez de getTrimmedCanvas() para evitar erro de importação da lib
            const canvas = sigPad.current?.getCanvas();
            const signatureData = canvas?.toDataURL('image/png');
            
            await axios.post(`${API_URL}/public-contrato/${token}/assinar`, {
                signature: signatureData
            });
            
            setSuccess(true);
            enqueueSnackbar('Contrato assinado com sucesso!', { variant: 'success' });
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } catch (err: any) {
            console.error('Erro ao assinar contrato:', err);
            enqueueSnackbar(err.response?.data?.detail || 'Erro ao processar assinatura.', { variant: 'error' });
        } finally {
            setSigning(false);
        }
    };

    if (loading) {
        return (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh" bgcolor="#f5f7fa">
                <CircularProgress />
            </Box>
        );
    }

    if (error) {
        return (
            <Container maxWidth="sm" sx={{ mt: 8 }}>
                <Alert severity="error" variant="filled">
                    {error}
                </Alert>
                <Box textAlign="center" mt={4}>
                    <Typography variant="body1">Entre em contato com o suporte do seu provedor.</Typography>
                </Box>
            </Container>
        );
    }

    if (success) {
        return (
            <Container maxWidth="sm" sx={{ mt: 8 }}>
                <Paper elevation={3} sx={{ p: 4, textAlign: 'center', borderRadius: 4, borderTop: '8px solid #4caf50' }}>
                    <CheckCircleIcon sx={{ fontSize: 80, color: '#4caf50', mb: 2 }} />
                    <Typography variant="h4" gutterBottom fontWeight="bold">Tudo Pronto!</Typography>
                    <Typography variant="h6" color="textSecondary" gutterBottom>
                        O contrato foi assinado digitalmente com sucesso.
                    </Typography>
                    <Divider sx={{ my: 3 }} />
                    <Typography variant="body1">
                        Agora nossa equipe já foi notificada e dará andamento ao seu pedido de {contract?.empresa_nome}.
                    </Typography>
                    
                    <Box mt={4} display="flex" justifyContent="center" gap={2} flexDirection={{ xs: 'column', sm: 'row' }}>
                        <Button 
                            variant="contained" 
                            color="success" 
                            onClick={() => window.print()}
                            startIcon={<CheckCircleIcon />}
                        >
                            Imprimir Comprovante
                        </Button>
                        <Button 
                            variant="outlined" 
                            onClick={() => window.open(`${API_URL}/public-contrato/${token}/visualizar`, '_blank')}
                        >
                            Ver Contrato Assinado
                        </Button>
                    </Box>

                    <Typography variant="body2" sx={{ mt: 4, color: 'text.secondary' }}>
                        Uma cópia do contrato assinado será enviada para o seu e-mail em breve.
                    </Typography>
                </Paper>
            </Container>
        );
    }

    return (
        <Box bgcolor="#f5f7fa" minHeight="100vh" py={4}>
            <Container maxWidth="md">
                <Paper elevation={2} sx={{ p: { xs: 2, md: 4 }, borderRadius: 3, mb: 4 }}>
                    {/* Header */}
                    <Box display="flex" alignItems="center" justifyContent="center" mb={3} flexDirection="column">
                        {contract?.empresa_logo && (
                            <Box component="img" src={contract.empresa_logo} sx={{ maxHeight: 60, mb: 2 }} />
                        )}
                        <Typography variant="h5" align="center" fontWeight="bold" color="primary">
                            Assinatura de Contrato Digital
                        </Typography>
                        <Typography variant="subtitle1" color="textSecondary">
                            {contract?.empresa_nome}
                        </Typography>
                    </Box>

                    <Alert severity="info" sx={{ mb: 4 }}>
                        Olá, <strong>{contract?.cliente_nome}</strong>. Por favor, leia atentamente o documento abaixo e faça sua assinatura ao final da página para confirmar a adesão ao serviço.
                    </Alert>

                    {/* Contract Preview */}
                    <Paper variant="outlined" sx={{ 
                        p: 3, 
                        maxHeight: '600px', 
                        overflowY: 'auto', 
                        bgcolor: '#fff',
                        mb: 4,
                        '& .section': { marginBottom: '20px' },
                        '& h1, & h2, & h3': { color: '#1a202c' },
                        '& table': { width: '100%', borderCollapse: 'collapse', margin: '10px 0' },
                        '& th, & td': { border: '1px solid #e2e8f0', padding: '8px' }
                    }}>
                        <div dangerouslySetInnerHTML={{ __html: contract?.html }} />
                    </Paper>

                    <Divider sx={{ my: 4 }}>
                        <Typography variant="overline" color="textSecondary">Área de Assinatura</Typography>
                    </Divider>

                    {/* Signature Area */}
                    <Box sx={{ maxWidth: 500, mx: 'auto' }}>
                        <Typography variant="body1" gutterBottom align="center" sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                            <CreateIcon fontSize="small" /> Assine seu nome no quadro abaixo:
                        </Typography>
                        
                        <Paper variant="outlined" sx={{ 
                            bgcolor: '#f8fafc', 
                            borderRadius: 2, 
                            position: 'relative',
                            overflow: 'hidden',
                            touchAction: 'none'
                        }}>
                            <SignatureCanvas 
                                ref={sigPad}
                                penColor="black"
                                canvasProps={{
                                    width: 500,
                                    height: 200,
                                    className: 'sigCanvas',
                                    style: { width: '100%', height: '200px' }
                                }}
                            />
                            <Box sx={{ position: 'absolute', top: 5, right: 5 }}>
                                <IconButton onClick={clearSignature} size="small" color="error" title="Limpar Assinatura">
                                    <DeleteIcon />
                                </IconButton>
                            </Box>
                        </Paper>

                        <Stack direction="row" spacing={2} sx={{ mt: 4 }}>
                            <Button 
                                fullWidth 
                                variant="outlined" 
                                color="inherit" 
                                onClick={clearSignature}
                                disabled={signing}
                            >
                                Limpar
                            </Button>
                            <Button 
                                fullWidth 
                                variant="contained" 
                                color="primary" 
                                size="large"
                                onClick={handleSign}
                                disabled={signing}
                                startIcon={signing ? <CircularProgress size={20} /> : <CheckCircleIcon />}
                                sx={{ fontWeight: 'bold' }}
                            >
                                {signing ? 'Processando...' : 'Confirmar e Assinar'}
                            </Button>
                        </Stack>
                        
                        <Typography variant="caption" display="block" align="center" sx={{ mt: 2, color: 'text.secondary' }}>
                            Ao clicar em "Confirmar e Assinar", você declara que concorda com todos os termos e condições do contrato acima identificado. Seu IP e data/hora serão registrados para validade jurídica.
                        </Typography>
                    </Box>
                </Paper>
            </Container>
        </Box>
    );
};

export default PublicSignature;
