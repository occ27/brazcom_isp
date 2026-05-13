import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { 
  Box, Typography, Button, Paper, Container, 
  Divider, Alert, IconButton, Tooltip, TextField 
} from '@mui/material';
import { 
  CheckCircleIcon, 
  XCircleIcon, 
  ClockIcon,
  ArrowLeftIcon,
  ClipboardDocumentIcon,
  ArrowTopRightOnSquareIcon
} from '@heroicons/react/24/outline';

const PaymentStatus: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { payment } = location.state || {};

  if (!payment) {
    return (
      <Container maxWidth="sm" sx={{ mt: 8, textAlign: 'center' }}>
        <Paper sx={{ p: 4, borderRadius: 3 }}>
          <Typography variant="h6" gutterBottom>Informação de pagamento não encontrada</Typography>
          <Button variant="contained" onClick={() => navigate('/receivables')} sx={{ mt: 2 }}>
            Voltar para Cobranças
          </Button>
        </Paper>
      </Container>
    );
  }

  const { status, detail } = payment;
  const mpId = payment.payment_id;

  const renderStatusIcon = () => {
    switch (status) {
      case 'approved':
        return <CheckCircleIcon className="w-20 h-20 text-green-500 mx-auto" />;
      case 'pending':
      case 'in_process':
        return <ClockIcon className="w-20 h-20 text-warning-main mx-auto" />;
      case 'rejected':
        return <XCircleIcon className="w-20 h-20 text-red-500 mx-auto" />;
      default:
        return <ClockIcon className="w-20 h-20 text-gray-400 mx-auto" />;
    }
  };

  const getStatusTitle = () => {
    switch (status) {
      case 'approved': return 'Pagamento Aprovado!';
      case 'pending': return 'Pagamento Pendente';
      case 'in_process': return 'Estamos processando seu pagamento';
      case 'rejected': return 'Pagamento Rejeitado';
      default: return 'Status do Pagamento';
    }
  };

  const getStatusMessage = () => {
    switch (status) {
      case 'approved': return 'Seu pagamento foi confirmado com sucesso. O serviço será liberado automaticamente em alguns minutos.';
      case 'pending': 
        if (detail.payment_method_id === 'pix') return 'Aguardando o pagamento do PIX. Utilize o código ou QR Code abaixo.';
        if (detail.payment_method_id === 'bolbradesco') return 'Boleto gerado com sucesso. O prazo de compensação é de até 2 dias úteis.';
        return 'Seu pagamento está aguardando confirmação.';
      case 'rejected': return 'Infelizmente o pagamento não foi aprovado. Por favor, tente outra forma de pagamento.';
      default: return 'Verificando situação do pagamento...';
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    // Poderia adicionar um snackbar aqui
  };

  return (
    <Container maxWidth="sm" sx={{ py: { xs: 4, md: 8 } }}>
      <Paper sx={{ p: { xs: 3, md: 6 }, borderRadius: 4, textAlign: 'center', boxShadow: '0 10px 30px rgba(0,0,0,0.08)' }}>
        <Box sx={{ mb: 3 }}>
          {renderStatusIcon()}
        </Box>
        
        <Typography variant="h4" fontWeight="800" gutterBottom>
          {getStatusTitle()}
        </Typography>
        
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          {getStatusMessage()}
        </Typography>

        <Divider sx={{ my: 4 }} />

        <Box sx={{ textAlign: 'left', mb: 4 }}>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>Detalhes da Transação</Typography>
          <Box sx={{ bgcolor: 'grey.50', p: 2, borderRadius: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="caption" fontWeight="600">ID da Transação:</Typography>
              <Typography variant="caption" fontFamily="monospace">{mpId}</Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="caption" fontWeight="600">Método:</Typography>
              <Typography variant="caption" sx={{ textTransform: 'uppercase' }}>{detail.payment_method_id}</Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="caption" fontWeight="600">Valor Total:</Typography>
              <Typography variant="caption" fontWeight="700">
                {(detail.transaction_amount || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
              </Typography>
            </Box>
          </Box>
        </Box>

        {/* Informações específicas de PIX */}
        {status === 'pending' && detail.payment_method_id === 'pix' && detail.point_of_interaction?.transaction_data && (
          <Box sx={{ mb: 4 }}>
             <Typography variant="subtitle1" fontWeight="700" gutterBottom>Código PIX (Copia e Cola)</Typography>
             <Box sx={{ position: 'relative', mb: 2 }}>
                <TextField
                  fullWidth
                  multiline
                  rows={2}
                  value={detail.point_of_interaction.transaction_data.qr_code}
                  InputProps={{ readOnly: true, sx: { fontSize: '0.75rem', bgcolor: 'grey.50' } }}
                />
                <Tooltip title="Copiar Código">
                    <IconButton 
                        sx={{ position: 'absolute', right: 8, top: 8 }}
                        onClick={() => copyToClipboard(detail.point_of_interaction.transaction_data.qr_code)}
                    >
                        <ClipboardDocumentIcon className="w-5 h-5" />
                    </IconButton>
                </Tooltip>
             </Box>
             
             {detail.point_of_interaction.transaction_data.qr_code_base64 && (
                <Box sx={{ mt: 2, textAlign: 'center' }}>
                    <img 
                        src={`data:image/jpeg;base64,${detail.point_of_interaction.transaction_data.qr_code_base64}`} 
                        alt="QR Code PIX"
                        style={{ maxWidth: '200px', margin: '0 auto', border: '8px solid #f5f5f5', borderRadius: '12px' }}
                    />
                </Box>
             )}
          </Box>
        )}

        {/* Link para Boleto */}
        {status === 'pending' && detail.payment_method_id === 'bolbradesco' && detail.transaction_details?.external_resource_url && (
          <Box sx={{ mb: 4 }}>
             <Button 
                variant="contained" 
                color="primary" 
                fullWidth
                size="large"
                startIcon={<ArrowTopRightOnSquareIcon className="w-5 h-5" />}
                onClick={() => window.open(detail.transaction_details.external_resource_url, '_blank')}
             >
                Visualizar Boleto
             </Button>
          </Box>
        )}

        <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
            <Button 
                fullWidth 
                variant="outlined" 
                startIcon={<ArrowLeftIcon className="w-4 h-4" />}
                onClick={() => navigate('/receivables')}
            >
                Voltar
            </Button>
            {status === 'rejected' && (
                <Button 
                    fullWidth 
                    variant="contained" 
                    onClick={() => navigate(-1)}
                >
                    Tentar Novamente
                </Button>
            )}
        </Box>
      </Paper>
    </Container>
  );
};

export default PaymentStatus;
