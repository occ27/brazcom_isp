import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { 
  Box, 
  Container, 
  Typography, 
  Paper, 
  CircularProgress,
  Button,
  useTheme
} from '@mui/material';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import axios, { API_BASE_URL } from '../services/api';

interface EmpresaInfo {
  razao_social: string;
  nome_fantasia: string;
  logo_url: string;
  telefone: string;
  suspension_message?: string;
}

const SuspensionNotice: React.FC = () => {
  const { empresaId } = useParams<{ empresaId: string }>();
  const [empresa, setEmpresa] = useState<EmpresaInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const theme = useTheme();

  useEffect(() => {
    const fetchEmpresaInfo = async () => {
      try {
        let endpoint = '';
        if (empresaId) {
          endpoint = `${API_BASE_URL}/empresas/public/${empresaId}`;
        } else {
          // Detectar empresa pelo IP do cliente
          endpoint = `${API_BASE_URL}/servicos-contratados/whoami`;
        }
        
        const response = await axios.get(endpoint);
        setEmpresa(response.data);
      } catch (error) {
        console.error('Erro ao buscar informações da empresa:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchEmpresaInfo();
  }, [empresaId]);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  const message = empresa?.suspension_message || 
    "Identificamos uma pendência financeira em seu cadastro que resultou na suspensão temporária dos seus serviços de internet. Para regularizar sua situação e restabelecer o acesso, por favor entre em contato conosco ou realize o pagamento da sua fatura em aberto.";

  return (
    <Box 
      sx={{ 
        minHeight: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        bgcolor: '#f0f2f5',
        py: 4
      }}
    >
      <Container maxWidth="sm">
        <Paper 
          elevation={4} 
          sx={{ 
            p: 4, 
            textAlign: 'center', 
            borderRadius: 3,
            borderTop: `8px solid ${theme.palette.warning.main}`
          }}
        >
          {empresa?.logo_url ? (
            <Box mb={3}>
              <img 
                src={empresa.logo_url} 
                alt={empresa.nome_fantasia || empresa.razao_social} 
                style={{ maxHeight: '80px', maxWidth: '100%' }} 
              />
            </Box>
          ) : (
            <Typography variant="h5" fontWeight="bold" gutterBottom>
              {empresa?.nome_fantasia || empresa?.razao_social || 'Provedor de Internet'}
            </Typography>
          )}

          <Box sx={{ color: theme.palette.warning.main, mb: 2 }}>
            <WarningAmberIcon sx={{ fontSize: 64 }} />
          </Box>

          <Typography variant="h4" component="h1" gutterBottom fontWeight="bold">
            Acesso Suspenso
          </Typography>

          <Typography variant="body1" color="text.secondary" paragraph sx={{ fontSize: '1.1rem', lineHeight: 1.6 }}>
            {message}
          </Typography>

          <Box mt={4} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Button 
              variant="contained" 
              size="large" 
              fullWidth
              sx={{ py: 1.5, fontSize: '1.1rem' }}
              onClick={() => window.open('/client-login', '_blank')}
            >
              Acessar Portal do Cliente
            </Button>
            
            {empresa?.telefone && (
              <Typography variant="body2" color="text.secondary">
                Dúvidas? Entre em contato: <strong>{empresa.telefone}</strong>
              </Typography>
            )}
          </Box>
        </Paper>
        
        <Box mt={3} textAlign="center">
          <Typography variant="caption" color="text.secondary">
            Após o pagamento, o seu acesso será restabelecido automaticamente em alguns minutos.
          </Typography>
        </Box>
      </Container>
    </Box>
  );
};

export default SuspensionNotice;
