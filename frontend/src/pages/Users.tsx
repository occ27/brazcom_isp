import React from 'react';
import { Typography, Box, Paper, Button } from '@mui/material';
import { PlusIcon, UserIcon } from '@heroicons/react/24/outline';

const Users: React.FC = () => {
  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold' }}>
          Usuários
        </Typography>
        <Button
          variant="contained"
          startIcon={<PlusIcon className="w-5 h-5" />}
          sx={{ py: 1.5 }}
        >
          Novo Usuário
        </Button>
      </Box>

      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <UserIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <Typography variant="h6" gutterBottom>
          Gerenciamento de Usuários
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Aqui você pode gerenciar usuários do sistema.
        </Typography>
        <Button variant="outlined" startIcon={<PlusIcon className="w-5 h-5" />}>
          Adicionar Usuário
        </Button>
      </Paper>
    </Box>
  );
};

export default Users;