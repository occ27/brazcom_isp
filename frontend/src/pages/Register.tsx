import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { TextField, Button, Paper, Typography, Box, Alert, Container } from '@mui/material';
import { useAuth } from '../contexts/AuthContext';

const Register: React.FC = () => {
  const navigate = useNavigate();
  const { register, error } = useAuth();
  const [formData, setFormData] = useState({
    nome: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [errors, setErrors] = useState<{ [key: string]: string }>({});
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

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

    if (!formData.nome.trim()) {
      newErrors.nome = 'Nome completo é obrigatório';
    } else if (formData.nome.trim().length < 3) {
      newErrors.nome = 'Nome deve ter pelo menos 3 caracteres';
    }

    if (!formData.email.trim()) {
      newErrors.email = 'Email é obrigatório';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Email inválido';
    }

    if (!formData.password) {
      newErrors.password = 'Senha é obrigatória';
    } else if (formData.password.length < 6) {
      newErrors.password = 'Senha deve ter pelo menos 6 caracteres';
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Confirmação de senha é obrigatória';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'As senhas não coincidem';
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
      await register({
        nome: formData.nome,
        email: formData.email,
        password: formData.password,
      });
      setSuccessMessage('Conta criada com sucesso! Você será redirecionado para o login.');
      setTimeout(() => {
        navigate('/login');
      }, 2000);
    } catch (error) {
      // Error is handled by AuthContext
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Container component="main" maxWidth="sm" sx={{ px: { xs: 1, sm: 2, md: 3 } }}>
      <Box
        sx={{
          marginTop: { xs: 1, sm: 2, md: 8 },
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
            Criar nova conta
          </Typography>

          {error && (
            <Alert severity="error" sx={{ width: '100%', mb: 2 }}>
              {error}
            </Alert>
          )}

          {successMessage && (
            <Alert severity="success" sx={{ width: '100%', mb: 2 }}>
              {successMessage}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1, width: '100%' }}>
            <TextField
              margin="normal"
              required
              fullWidth
              id="nome"
              label="Nome completo"
              name="nome"
              autoComplete="name"
              autoFocus
              value={formData.nome}
              onChange={handleChange}
              error={!!errors.nome}
              helperText={errors.nome}
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
              id="email"
              label="Email"
              name="email"
              autoComplete="email"
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
              autoComplete="new-password"
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
              name="confirmPassword"
              label="Confirmar senha"
              type="password"
              id="confirmPassword"
              autoComplete="new-password"
              value={formData.confirmPassword}
              onChange={handleChange}
              error={!!errors.confirmPassword}
              helperText={errors.confirmPassword}
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
              {isLoading ? 'Criando conta...' : 'Criar conta'}
            </Button>

            <Box sx={{ textAlign: 'center', mt: 1 }}>
              <Link to="/login" style={{ textDecoration: 'none' }}>
                <Typography variant="body2" color="primary" sx={{ fontSize: { xs: '0.8rem', sm: '0.875rem' } }}>
                  Já tem uma conta? Faça login
                </Typography>
              </Link>
            </Box>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default Register;