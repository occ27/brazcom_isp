import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { TextField, Button, Paper, Typography, Box, Alert, Container, Dialog, DialogTitle, DialogContent, DialogActions } from '@mui/material';
import api from '../services/api';
import { stringifyError } from '../utils/error';
import { useAuth } from '../contexts/AuthContext';

const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login, error } = useAuth();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [errors, setErrors] = useState<{ [key: string]: string }>({});
  const [isLoading, setIsLoading] = useState(false);
  // Password reset UI state
  const [resetOpen, setResetOpen] = useState(false);
  const [resetStep, setResetStep] = useState<number>(1);
  const [resetEmail, setResetEmail] = useState('');
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

    if (!formData.email.trim()) {
      newErrors.email = 'Email é obrigatório';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Email inválido';
    }

    if (!formData.password) {
      newErrors.password = 'Senha é obrigatória';
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
    try {
      await login(formData.email, formData.password);
      navigate('/dashboard');
    } catch (error) {
      // Error is handled by AuthContext
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
            src="/logo_retangular.PNG"
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
            Entrar na sua conta
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
              id="email"
              label="Email"
              name="email"
              autoComplete="email"
              autoFocus
              value={formData.email}
              onChange={handleChange}
              error={!!errors.email}
              helperText={errors.email}
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
              {isLoading ? 'Entrando...' : 'Entrar'}
            </Button>

            <Box sx={{ textAlign: 'center', mt: 1 }}>
              <Button
                size="small"
                onClick={() => { setResetOpen(true); setResetStep(1); setResetEmail(formData.email || ''); setResetMessage(null); setResetError(null); }}
                sx={{ textTransform: 'none', fontSize: { xs: '0.8rem', sm: '0.875rem' } }}
              >
                Esqueci a senha
              </Button>
            </Box>

            <Box sx={{ textAlign: 'center', mt: 1 }}>
              <Link to="/register" style={{ textDecoration: 'none' }}>
                <Typography variant="body2" color="primary" sx={{ fontSize: { xs: '0.8rem', sm: '0.875rem' } }}>
                  Não tem uma conta? Cadastre-se
                </Typography>
              </Link>
            </Box>
          </Box>
        </Paper>
      </Box>
    </Container>

      {/* Dialog de redefinição de senha */}
      <Dialog open={resetOpen} onClose={() => setResetOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Redefinir senha</DialogTitle>
        <DialogContent>
          {resetMessage && <Alert severity="success" sx={{ mb: 2 }}>{resetMessage}</Alert>}
          {resetError && <Alert severity="error" sx={{ mb: 2 }}>{resetError}</Alert>}

          {resetStep === 1 && (
            <Box>
              <Typography variant="body2" sx={{ mb: 1 }}>Informe o email cadastrado para receber o código de redefinição.</Typography>
              <TextField
                margin="normal"
                fullWidth
                id="resetEmail"
                label="Email"
                name="resetEmail"
                autoComplete="email"
                value={resetEmail}
                onChange={(e) => setResetEmail(e.target.value)}
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
          {resetStep === 1 && (
            <Button variant="contained" onClick={async () => {
              setResetError(null); setResetMessage(null); setResetLoading(true);
              try {
                await api.post('/auth/password-reset/request', { email: resetEmail });
                setResetMessage('Código enviado (se o email existir). Verifique sua caixa de entrada.');
                setResetStep(2);
              } catch (e: any) {
                setResetError(stringifyError(e) || 'Erro ao solicitar código');
              } finally { setResetLoading(false); }
            }}>Enviar código</Button>
          )}

          {resetStep === 2 && (
            <Button variant="contained" onClick={async () => {
              setResetError(null); setResetMessage(null); setResetLoading(true);
              try {
                await api.post('/auth/password-reset/verify', { email: resetEmail, code: resetCode });
                setResetMessage('Código verificado. Informe a nova senha.');
                setResetStep(3);
              } catch (e: any) {
                setResetError(stringifyError(e) || 'Código inválido ou expirado');
              } finally { setResetLoading(false); }
            }}>Verificar código</Button>
          )}

          {resetStep === 3 && (
            <Button variant="contained" onClick={async () => {
              setResetError(null); setResetMessage(null);
              if (!newPassword || newPassword.length < 6) { setResetError('Senha deve ter ao menos 6 caracteres'); return; }
              if (newPassword !== confirmPassword) { setResetError('As senhas não coincidem'); return; }
              setResetLoading(true);
              try {
                await api.post('/auth/password-reset/confirm', { email: resetEmail, code: resetCode, new_password: newPassword });
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

export default Login;