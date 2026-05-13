import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { 
  Box, Typography, CircularProgress, Alert, Button, 
  Paper, Divider, Container, Grid 
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { mercadopagoService } from '../services/mercadopagoService';
import receivableService, { Receivable } from '../services/receivableService';

declare global {
  interface Window {
    MercadoPago: any;
  }
}

const Checkout: React.FC = () => {
  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  // Get receivable IDs from state or query
  const [receivableIds, setReceivableIds] = useState<number[]>(
    (location.state?.receivableIds as number[]) || []
  );

  const [receivables, setReceivables] = useState<Receivable[]>([]);
  const [totalAmount, setTotalAmount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mpPublicKey, setMpPublicKey] = useState<string | null>(null);
  const [clientEmail, setClientEmail] = useState('');
  const [clientNome, setClientNome] = useState('');

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        let ids = receivableIds;
        let email = user?.email || '';
        let nome = user?.full_name || '';

        // If we have a token, fetch the receivable info publicly
        if (token && receivableIds.length === 0) {
           const data = await mercadopagoService.getReceivableByToken(token);
           if (data.status === 'PAID') {
               setError('Esta fatura já foi paga. Obrigado!');
               setLoading(false);
               return;
           }
           ids = [data.id];
           setReceivableIds(ids);
           email = data.cliente_email;
           nome = data.cliente_nome;
        } else if (token && receivableIds.length > 0) {
           // Já carregamos os dados via token ou temos IDs, apenas garantir email/nome se vazios
           if (!clientEmail || !clientNome) {
             const data = await mercadopagoService.getReceivableByToken(token);
             email = data.cliente_email;
             nome = data.cliente_nome;
           }
        }

        if (!ids || ids.length === 0) {
          setError('Nenhuma cobrança selecionada para pagamento');
          setLoading(false);
          return;
        }

        setClientEmail(email);
        setClientNome(nome);

        // Fetch details of receivables
        let data: Receivable[] = [];
        if (token) {
          // If we have a token, we already have the main receivable data
          // Just need to fetch the public key and we are good
          const mpData = await mercadopagoService.getReceivableByToken(token);
          data = [mpData as any];
          setReceivables(data);
          
          const total = mpData.amount;
          setTotalAmount(total);

          const publicKey = await mercadopagoService.getPublicKey(mpData.empresa_id);
          setMpPublicKey(publicKey);
        } else {
          // Normal flow for logged in users with multiple IDs
          data = await Promise.all(ids.map(id => receivableService.getReceivable(id)));
          setReceivables(data);
          const total = data.reduce((acc, curr) => acc + curr.amount, 0);
          setTotalAmount(total);

          const empresaId = data[0].empresa_id;
          const publicKey = await mercadopagoService.getPublicKey(empresaId);
          setMpPublicKey(publicKey);
        }

      } catch (err: any) {
        console.error(err);
        const msg = err.response?.data?.detail || 'Erro ao carregar dados para pagamento.';
        setError(msg);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [token, receivableIds, user]);

  useEffect(() => {
    if (mpPublicKey && !loading && receivables.length > 0) {
      loadPaymentBrick();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mpPublicKey, loading, receivables]);

  const loadPaymentBrick = () => {
    const loadScript = (callback: () => void) => {
      if (window.MercadoPago) {
        callback();
        return;
      }
      const script = document.createElement('script');
      script.src = "https://sdk.mercadopago.com/js/v2";
      script.onload = callback;
      document.body.appendChild(script);
    };

    loadScript(() => {
      const container = document.getElementById('paymentBrick_container');
      if (!container) return;

      // Clean container before creating new brick
      container.innerHTML = '';

      const mp = new window.MercadoPago(mpPublicKey, { locale: 'pt-BR' });
      const bricksBuilder = mp.bricks();

      bricksBuilder.create('payment', 'paymentBrick_container', {
        initialization: {
          amount: totalAmount,
          payer: {
            email: clientEmail || user?.email || '',
          }
        },
        customization: {
          visual: {
            style: { theme: 'default' }
          },
          paymentMethods: {
            creditCard: 'all',
            ticket: 'all',
            bankTransfer: 'all',
          }
        },
        callbacks: {
          onReady: () => {
            setLoading(false);
          },
          onSubmit: async (param: any) => {
             const { formData } = param;
             try {
               const response = await mercadopagoService.processPayment({
                 ...formData,
                 receivable_ids: receivableIds,
                 transaction_amount: totalAmount,
                 payer: {
                    ...formData.payer,
                    email: formData.payer.email || clientEmail || user?.email,
                    first_name: formData.payer.first_name || clientNome?.split(' ')[0],
                    last_name: formData.payer.last_name || clientNome?.split(' ').slice(1).join(' '),
                 }
               });
               
               // Redirect to status page
               navigate(`/payment-status`, { state: { payment: response } });
             } catch (err: any) {
               console.error('Erro ao processar pagamento:', err);
               // O Brick cuida da exibição do erro internamente na maioria dos casos
               throw err;
             }
          },
          onError: (error: any) => {
            console.error('Erro no Brick:', error);
          }
        }
      });
    });
  };

  if (loading && !mpPublicKey) {
     return (
       <Box display="flex" flexDirection="column" justifyContent="center" alignItems="center" minHeight="60vh">
         <CircularProgress size={60} />
         <Typography sx={{ mt: 2 }} color="text.secondary">Iniciando ambiente de pagamento...</Typography>
       </Box>
     );
  }

  if (error) {
    return (
      <Container maxWidth="sm" sx={{ mt: 4 }}>
        <Paper sx={{ p: 4, borderRadius: 3, textAlign: 'center' }}>
          <Alert severity="error" variant="filled" sx={{ mb: 3 }}>{error}</Alert>
          <Button variant="contained" onClick={() => navigate(-1)}>Voltar</Button>
        </Paper>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: { xs: 2, md: 6 } }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight="800" color="primary.main">Checkout Seguro</Typography>
        <Typography variant="body1" color="text.secondary">Finalize seu pagamento de forma rápida e protegida</Typography>
      </Box>
      
      <Grid container spacing={4}>
        <Grid item xs={12} md={5} lg={4}>
          <Paper sx={{ p: 3, borderRadius: 3, border: '1px solid', borderColor: 'divider', position: 'sticky', top: 20 }}>
            <Typography variant="h6" gutterBottom fontWeight="700">Resumo do Pedido</Typography>
            <Divider sx={{ mb: 2 }} />
            <Box sx={{ maxHeight: '300px', overflowY: 'auto', pr: 1 }}>
                {receivables.map(r => (
                <Box key={r.id} sx={{ display: 'flex', justifyContent: 'space-between', mb: 1.5 }}>
                    <Box>
                        <Typography variant="body2" fontWeight="600">Fatura #{r.id}</Typography>
                        <Typography variant="caption" color="text.secondary">Vencimento: {new Date(r.due_date).toLocaleDateString()}</Typography>
                    </Box>
                    <Typography variant="body2" fontWeight="700">
                    {r.amount.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                    </Typography>
                </Box>
                ))}
            </Box>
            <Divider sx={{ my: 2 }} />
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6" fontWeight="800">Total a Pagar</Typography>
              <Typography variant="h5" fontWeight="800" color="primary.main">
                {totalAmount.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
              </Typography>
            </Box>
            
            <Box sx={{ mt: 3, p: 2, bgcolor: 'grey.50', borderRadius: 2, display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <span style={{ fontSize: '24px' }}>🛡️</span>
                <Typography variant="caption" color="text.secondary">
                    Pagamento processado com segurança pelo Mercado Pago. Seus dados estão protegidos.
                </Typography>
            </Box>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={7} lg={8}>
          <Paper sx={{ p: { xs: 1, sm: 3 }, borderRadius: 3, border: '1px solid', borderColor: 'divider' }}>
             <div id="paymentBrick_container"></div>
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
};

export default Checkout;
