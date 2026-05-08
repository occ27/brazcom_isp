import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Box, 
  Container, 
  Typography, 
  Paper, 
  CircularProgress,
  Button,
  useTheme,
  Fade,
  Stack,
  IconButton
} from '@mui/material';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong';
import axios, { API_BASE_URL } from '../services/api';

interface ContratoInfo {
  cliente_nome: string;
  empresa_nome: string;
  empresa_fantasia: string;
  empresa_logo: string;
  empresa_telefone: string;
  suspension_message?: string;
}

const SuspensionNotice: React.FC = () => {
  const { empresaId } = useParams<{ empresaId: string }>();
  const [info, setInfo] = useState<ContratoInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const theme = useTheme();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchInfo = async () => {
      try {
        // Busca informações da empresa e tenta identificar cliente pelo IP
        const response = await axios.get(`/servicos-contratados/public/aviso/empresa/${empresaId}`);
        setInfo(response.data);
      } catch (error) {
        console.error('Erro ao buscar informações:', error);
      } finally {
        setLoading(false);
      }
    };

    if (empresaId) {
      fetchInfo();
    } else {
      setLoading(false);
    }
  }, [empresaId]);

  if (loading) {
    return (
      <Box 
        display="flex" 
        flexDirection="column"
        justifyContent="center" 
        alignItems="center" 
        minHeight="100vh"
        sx={{ background: 'linear-gradient(135deg, #1a1a1a 0%, #333333 100%)' }}
      >
        <CircularProgress sx={{ color: '#ff4b2b' }} />
        <Typography sx={{ mt: 2, color: 'white', opacity: 0.7 }}>Identificando conexão...</Typography>
      </Box>
    );
  }

  const message = info?.suspension_message || 
    "Identificamos uma pendência financeira em seu cadastro que resultou na suspensão temporária dos seus serviços de internet. Para regularizar sua situação e restabelecer o acesso, por favor realize o pagamento da sua fatura em aberto.";

  return (
    <Box 
      sx={{ 
        minHeight: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)',
        position: 'relative',
        overflow: 'hidden',
        '&::before': {
          content: '""',
          position: 'absolute',
          top: -100,
          right: -100,
          width: 300,
          height: 300,
          borderRadius: '50%',
          background: 'rgba(255, 75, 43, 0.05)',
        },
        '&::after': {
          content: '""',
          position: 'absolute',
          bottom: -50,
          left: -50,
          width: 200,
          height: 200,
          borderRadius: '50%',
          background: 'rgba(0, 0, 0, 0.03)',
        }
      }}
    >
      <Fade in={true} timeout={800}>
        <Container maxWidth="sm" sx={{ position: 'relative', zIndex: 1 }}>
          <Paper 
            elevation={0} 
            sx={{ 
              p: { xs: 4, md: 6 }, 
              textAlign: 'center', 
              borderRadius: 6,
              background: 'rgba(255, 255, 255, 0.9)',
              backdropFilter: 'blur(10px)',
              border: '1px solid rgba(255, 255, 255, 0.3)',
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.1)',
              position: 'relative',
              overflow: 'hidden'
            }}
          >
            {/* Logo do Provedor */}
            <Box mb={4} sx={{ display: 'flex', justifyContent: 'center' }}>
              {info?.empresa_logo ? (
                <img 
                  src={info.empresa_logo.startsWith('http') ? info.empresa_logo : `${API_BASE_URL}${info.empresa_logo}`} 
                  alt={info.empresa_fantasia} 
                  style={{ maxHeight: '70px', filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.1))' }} 
                />
              ) : (
                <Typography variant="h5" sx={{ fontWeight: 800, letterSpacing: -1, color: '#2d3436' }}>
                  {info?.empresa_fantasia || info?.empresa_nome || 'PROVEDOR'}
                </Typography>
              )}
            </Box>

            {/* Ícone de Alerta Animado */}
            <Box 
              sx={{ 
                width: 80, 
                height: 80, 
                bgcolor: 'rgba(255, 75, 43, 0.1)', 
                borderRadius: '50%', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                mx: 'auto',
                mb: 3,
                animation: 'pulse 2s infinite'
              }}
            >
              <WarningAmberIcon sx={{ fontSize: 40, color: '#ff4b2b' }} />
            </Box>

            <Typography variant="h4" sx={{ fontWeight: 800, color: '#2d3436', mb: 1 }}>
              Acesso Suspenso
            </Typography>

            {info?.cliente_nome && (
              <Typography variant="subtitle1" sx={{ color: '#ff4b2b', fontWeight: 600, mb: 2 }}>
                Olá, {info.cliente_nome.split(' ')[0]}!
              </Typography>
            )}

            <Typography 
              variant="body1" 
              sx={{ 
                color: '#636e72', 
                lineHeight: 1.8, 
                mb: 4,
                fontSize: '1.05rem' 
              }}
            >
              {message}
            </Typography>

            <Stack spacing={2}>
              <Button 
                variant="contained" 
                fullWidth
                startIcon={<ReceiptLongIcon />}
                sx={{ 
                  py: 1.8, 
                  borderRadius: 3,
                  bgcolor: '#2d3436',
                  '&:hover': { bgcolor: '#000' },
                  textTransform: 'none',
                  fontSize: '1rem',
                  fontWeight: 600,
                  boxShadow: '0 10px 20px -5px rgba(0,0,0,0.3)'
                }}
                onClick={() => window.open('/client-login', '_blank')}
              >
                Ver Faturas / Segunda Via
              </Button>

              {info?.empresa_telefone && (
                <Button 
                  variant="outlined" 
                  fullWidth
                  startIcon={<WhatsAppIcon />}
                  sx={{ 
                    py: 1.8, 
                    borderRadius: 3,
                    borderColor: '#00b894',
                    color: '#00b894',
                    '&:hover': { borderColor: '#00b894', bgcolor: 'rgba(0, 184, 148, 0.05)' },
                    textTransform: 'none',
                    fontSize: '1rem',
                    fontWeight: 600
                  }}
                  onClick={() => window.open(`https://wa.me/${info.empresa_telefone.replace(/\D/g, '')}`, '_blank')}
                >
                  Falar com Suporte
                </Button>
              )}
            </Stack>

            <Typography variant="caption" sx={{ display: 'block', mt: 4, color: '#b2bec3' }}>
              Após a compensação do pagamento, seu sinal será restabelecido automaticamente.
            </Typography>
          </Paper>

          <Box sx={{ textAlign: 'center', mt: 4 }}>
            <Typography variant="caption" sx={{ color: '#636e72', fontWeight: 500 }}>
              &copy; {new Date().getFullYear()} {info?.empresa_fantasia || info?.empresa_nome} - Todos os direitos reservados.
            </Typography>
          </Box>
        </Container>
      </Fade>

      <style>
        {`
          @keyframes pulse {
            0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 75, 43, 0.4); }
            70% { transform: scale(1.05); box-shadow: 0 0 0 10px rgba(255, 75, 43, 0); }
            100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 75, 43, 0); }
          }
        `}
      </style>
    </Box>
  );
};

export default SuspensionNotice;
