import React from 'react';
import { Typography, Box, Paper, Grid } from '@mui/material';
import { ChartBarIcon, DocumentTextIcon } from '@heroicons/react/24/outline';

const Reports: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" component="h1" sx={{ mb: 4, fontWeight: 'bold' }}>
        Relatórios
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, textAlign: 'center', cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}>
            <ChartBarIcon className="w-12 h-12 text-blue-600 mx-auto mb-3" />
            <Typography variant="h6" gutterBottom>
              NFCom Emitidas
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Relatório de emissões por período
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, textAlign: 'center', cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}>
            <DocumentTextIcon className="w-12 h-12 text-green-600 mx-auto mb-3" />
            <Typography variant="h6" gutterBottom>
              Empresas
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Relatório de empresas cadastradas
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Reports;