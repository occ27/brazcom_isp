import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { TextField, Button, Paper, Typography, Box, Alert, Container, Dialog, DialogTitle, DialogContent, DialogActions } from '@mui/material';
import api from '../services/api';
import { stringifyError } from '../utils/error';
import { useAuth } from '../contexts/AuthContext';
import * as authService from '../services/authService';

const ClientLogin: React.FC = () => {
  const navigate = useNavigate();
  const { loadUserInfo } = useAuth();
  const [formData, setFormData] = useState({
    cpf_cnpj: '',
    password: '',
    empresa_id: '',
  });
  const [errors, setErrors] = useState<{ [key: string]: string }>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Password reset UI state
  const [resetOpen, setResetOpen] = useState(false);
  const [resetStep, setResetStep] = useState<number>(1);
  const [resetCpfCnpj, setResetCpfCnpj] = useState('');
  const [resetEmail, setResetEmail] = useState('');
  const [resetEmpresaId, setResetEmpresaId] = useState('');
  const [resetCode, setResetCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [resetMessage, setResetMessage] = useState<string | null>(null);
  const [resetError, setResetError] = useState<string | null>(null);
  const [resetLoading, setResetLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Limpar erro do campo quando usuário começa a digitar
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const validateForm = () => {
    const newErrors: { [key: string]: string } = {};

    if (!formData.cpf_cnpj.trim()) {
      newErrors.cpf_cnpj = 'CPF/CNPJ é obrigatório';
    }

    if (!formData.password) {
      newErrors.password = 'Senha é obrigatória';
    }

    if (!formData.empresa_id.trim()) {
      newErrors.empresa_id = 'ID da empresa é obrigatório';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Usar o authService para fazer login
      await authService.clientLogin(formData.cpf_cnpj, formData.password, parseInt(formData.empresa_id));

      // Carregar informações do usuário no AuthContext
      await loadUserInfo();

      // O redirecionamento será feito pelo RedirectHandler
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erro ao fazer login';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
    <Container component="main" maxWidth="sm" sx={{ px: { xs: 1, sm: 2, md: 3 } }}>
      <Box
        sx={{
          marginTop: { xs: 2, sm: 4, md: 8 },
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          minHeight: '100vh',
          justifyContent: 'center',
          py: { xs: 1, sm: 2, md: 0 }
        }}
      >
        <Paper
          elevation={3}
          sx={{
            padding: { xs: 2, sm: 3, md: 4 },
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            width: '100%',
            maxWidth: '100%'
          }}
        >
          <Box
            component="img"
            src={process.env.PUBLIC_URL + '/logo_retangular.png'}
            alt="Brazcom ISP Logo"
            sx={{
              height: { xs: 50, sm: 50, md: 80 },
              width: 'auto',
              mr: { xs: 0, sm: 2 },
              mb: { xs: 1, sm: 2 },
              display: 'block',
            }}
          />
          <Typography
            component="h2"
            variant="h5"
            sx={{
              mb: 0,
              fontSize: { xs: '1.125rem', sm: '1.25rem', md: '1.5rem' }
            }}
          >
            Portal do Cliente
          </Typography>
          <Typography
            variant="body2"
            color="textSecondary"
            sx={{
              mb: 2,
              textAlign: 'center',
              fontSize: { xs: '0.8rem', sm: '0.875rem' }
            }}
          >
            Acesse sua conta usando CPF/CNPJ e senha
          </Typography>

          {error && (
            <Alert severity="error" sx={{ width: '100%', mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1, width: '100%' }}>
            <TextField
              margin="normal"
              required
              fullWidth
              id="cpf_cnpj"
              label="CPF ou CNPJ"
              name="cpf_cnpj"
              autoComplete="username"
              autoFocus
              value={formData.cpf_cnpj}
              onChange={handleChange}
              error={!!errors.cpf_cnpj}
              helperText={errors.cpf_cnpj}
              disabled={isLoading}
              sx={{
                '& .MuiInputBase-input': {
                  fontSize: { xs: '0.9rem', sm: '1rem' }
                },
                '& .MuiInputLabel-root': {
                  fontSize: { xs: '0.9rem', sm: '1rem' }
                }
              }}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              name="password"
              label="Senha"
              type="password"
              id="password"
              autoComplete="current-password"
              value={formData.password}
              onChange={handleChange}
              error={!!errors.password}
              helperText={errors.password}
              disabled={isLoading}
              sx={{
                '& .MuiInputBase-input': {
                  fontSize: { xs: '0.9rem', sm: '1rem' }
                },
                '& .MuiInputLabel-root': {
                  fontSize: { xs: '0.9rem', sm: '1rem' }
                }
              }}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              id="empresa_id"
              label="ID da Empresa"
              name="empresa_id"
              type="number"
              value={formData.empresa_id}
              onChange={handleChange}
              error={!!errors.empresa_id}
              helperText={errors.empresa_id}
              disabled={isLoading}
              sx={{
                '& .MuiInputBase-input': {
                  fontSize: { xs: '0.9rem', sm: '1rem' }
                },
                '& .MuiInputLabel-root': {
                  fontSize: { xs: '0.9rem', sm: '1rem' }
                }
              }}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{
                mt: 2,
                mb: 1,
                py: { xs: 1, sm: 1.25, md: 1.5 },
                fontSize: { xs: '0.9rem', sm: '1rem' },
                minHeight: { xs: '44px', sm: 'auto' }
              }}
              disabled={isLoading}
            >
              {isLoading ? 'Entrando...' : 'Entrar no Portal'}
            </Button>

            <Box sx={{ textAlign: 'center', mt: 1 }}>
              <Button
                size="small"
                onClick={() => {
                  setResetOpen(true);
                  setResetStep(1);
                  setResetCpfCnpj(formData.cpf_cnpj || '');
                  setResetEmail(''); // Limpar email
                  setResetEmpresaId(formData.empresa_id || '');
                  setResetCode(''); // Limpar o campo código
                  setNewPassword(''); // Limpar nova senha
                  setConfirmPassword(''); // Limpar confirmação
                  setResetMessage(null);
                  setResetError(null);
                }}
                sx={{ textTransform: 'none', fontSize: { xs: '0.8rem', sm: '0.875rem' } }}
              >
                Esqueci a senha
              </Button>
            </Box>

            <Box sx={{ textAlign: 'center', mt: 1 }}>
              <Link to="/" style={{ textDecoration: 'none' }}>
                <Typography variant="body2" color="primary" sx={{ fontSize: { xs: '0.8rem', sm: '0.875rem' } }}>
                  ← Voltar ao início
                </Typography>
              </Link>
            </Box>
          </Box>
        </Paper>
      </Box>
    </Container>

      {/* Dialog de redefinição de senha */}
      <Dialog open={resetOpen} onClose={() => setResetOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Redefinir senha do cliente</DialogTitle>
        <DialogContent>
          {resetMessage && <Alert severity="success" sx={{ mb: 2 }}>{resetMessage}</Alert>}
          {resetError && <Alert severity="error" sx={{ mb: 2 }}>{resetError}</Alert>}

          {resetStep === 1 && (
            <Box>
              <Typography variant="body2" sx={{ mb: 1 }}>Informe seu CPF/CNPJ, email e o ID da empresa para receber o código de redefinição.</Typography>
              <TextField
                margin="normal"
                fullWidth
                id="resetCpfCnpj"
                label="CPF ou CNPJ"
                name="resetCpfCnpj"
                autoComplete="username"
                value={resetCpfCnpj}
                onChange={(e) => setResetCpfCnpj(e.target.value)}
                disabled={resetLoading}
              />
              <TextField
                margin="normal"
                fullWidth
                id="resetEmail"
                label="Email"
                name="resetEmail"
                type="email"
                autoComplete="email"
                value={resetEmail}
                onChange={(e) => setResetEmail(e.target.value)}
                disabled={resetLoading}
              />
              <TextField
                margin="normal"
                fullWidth
                id="resetEmpresaId"
                label="ID da Empresa"
                name="resetEmpresaId"
                type="number"
                value={resetEmpresaId}
                onChange={(e) => setResetEmpresaId(e.target.value)}
                disabled={resetLoading}
              />
            </Box>
          )}

          {resetStep === 2 && (
            <Box>
              <Typography variant="body2" sx={{ mb: 1 }}>Digite o código enviado por email.</Typography>
              <TextField
                margin="normal"
                fullWidth
                id="resetCode"
                label="Código"
                name="resetCode"
                value={resetCode}
                onChange={(e) => setResetCode(e.target.value)}
                disabled={resetLoading}
              />
            </Box>
          )}

          {resetStep === 3 && (
            <Box>
              <Typography variant="body2" sx={{ mb: 1 }}>Informe sua nova senha.</Typography>
              <TextField
                margin="normal"
                fullWidth
                id="newPassword"
                label="Nova senha"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                disabled={resetLoading}
              />
              <TextField
                margin="normal"
                fullWidth
                id="confirmPassword"
                label="Confirme a nova senha"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={resetLoading}
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setResetOpen(false)} disabled={resetLoading}>Fechar</Button>
          {resetStep > 1 && (
            <Button 
              onClick={() => {
                setResetStep(prev => prev - 1);
                setResetError(null);
                setResetMessage(null);
              }} 
              disabled={resetLoading}
            >
              Voltar
            </Button>
          )}
          {resetStep === 1 && (
            <Button variant="contained" onClick={async () => {
              if (!resetCpfCnpj.trim()) {
                setResetError('Por favor, digite o CPF/CNPJ');
                return;
              }
              if (!resetEmail.trim()) {
                setResetError('Por favor, digite o email');
                return;
              }
              if (!resetEmpresaId.trim()) {
                setResetError('Por favor, digite o ID da empresa');
                return;
              }
              setResetError(null); setResetMessage(null); setResetLoading(true);
              try {
                await api.post('/client-auth/forgot-password', {
                  cpf_cnpj: resetCpfCnpj,
                  email: resetEmail,
                  empresa_id: parseInt(resetEmpresaId)
                });
                setResetMessage('Código enviado (se o CPF/CNPJ existir, o email estiver cadastrado e corresponder ao informado). Verifique sua caixa de entrada.');
                setResetStep(2);
              } catch (e: any) {
                setResetError(stringifyError(e) || 'Erro ao solicitar código');
              } finally { setResetLoading(false); }
            }}>Enviar código</Button>
          )}

          {resetStep === 2 && (
            <Button variant="contained" onClick={() => {
              if (!resetCode.trim()) {
                setResetError('Por favor, digite o código enviado por email');
                return;
              }
              setResetError(null);
              setResetMessage('Agora defina sua nova senha.');
              setResetStep(3);
            }}>Continuar</Button>
          )}

          {resetStep === 3 && (
            <Button variant="contained" onClick={async () => {
              if (!newPassword || !confirmPassword) {
                setResetError('Por favor, preencha todos os campos');
                return;
              }
              if (newPassword !== confirmPassword) {
                setResetError('As senhas não coincidem');
                return;
              }
              if (newPassword.length < 6) {
                setResetError('A senha deve ter pelo menos 6 caracteres');
                return;
              }

              setResetError(null); setResetMessage(null); setResetLoading(true);
              try {
                await api.post('/client-auth/reset-password', {
                  cpf_cnpj: resetCpfCnpj,
                  reset_code: resetCode,
                  new_password: newPassword,
                  empresa_id: parseInt(resetEmpresaId)
                });
                setResetMessage('Senha alterada com sucesso. Você já pode fazer login com a nova senha');
                setResetStep(1);
                // close after short delay
                setTimeout(() => setResetOpen(false), 1200);
              } catch (e: any) {
                setResetError(stringifyError(e) || 'Erro ao alterar senha');
              } finally { setResetLoading(false); }
            }}>Alterar senha</Button>
          )}
        </DialogActions>
      </Dialog>
    </>
  );
};

export default ClientLogin;