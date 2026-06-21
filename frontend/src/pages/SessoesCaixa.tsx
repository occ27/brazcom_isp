import React, { useState, useEffect } from 'react';
import { 
  Box, Typography, Paper, Table, TableBody, TableCell, TableContainer, 
  TableHead, TableRow, TablePagination, TextField, Button, Chip, IconButton,
  MenuItem, Select, FormControl, InputLabel, CircularProgress, Tooltip, Dialog,
  DialogTitle, DialogContent, DialogActions
} from '@mui/material';
import { ArrowPathIcon, DocumentArrowDownIcon, EyeIcon } from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/AuthContext';
import { caixaService, CaixaSessao, CaixaMovimentacao } from '../services/caixaService';
import { useSnackbar } from 'notistack';

export default function SessoesCaixa() {
  const { user } = useAuth();
  const { enqueueSnackbar } = useSnackbar();
  
  const [sessoes, setSessoes] = useState<CaixaSessao[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalRows, setTotalRows] = useState(0);
  const [page, setPage] = useState(0);
  const [perPage, setPerPage] = useState(25);
  const [statusFilter, setStatusFilter] = useState('');
  
  // Extrato modal state
  const [openExtrato, setOpenExtrato] = useState(false);
  const [selectedSessao, setSelectedSessao] = useState<CaixaSessao | null>(null);
  const [extrato, setExtrato] = useState<CaixaMovimentacao[]>([]);
  const [loadingExtrato, setLoadingExtrato] = useState(false);
  const [downloading, setDownloading] = useState<number | null>(null);

  const loadSessoes = async () => {
    if (!user?.active_empresa_id) return;
    try {
      setLoading(true);
      const res = await caixaService.getSessoesHistorico(
        user.active_empresa_id,
        page + 1,
        perPage,
        statusFilter || undefined
      );
      setSessoes(res.data);
      setTotalRows(res.total);
    } catch (err) {
      console.error(err);
      enqueueSnackbar('Erro ao carregar caixas', { variant: 'error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessoes();
  }, [page, perPage, statusFilter, user?.active_empresa_id]);

  const handleDownloadPDF = async (sessaoId: number) => {
    try {
      setDownloading(sessaoId);
      await caixaService.downloadCaixaPDF(sessaoId);
      enqueueSnackbar('PDF gerado com sucesso', { variant: 'success' });
    } catch (err) {
      console.error(err);
      enqueueSnackbar('Erro ao gerar PDF', { variant: 'error' });
    } finally {
      setDownloading(null);
    }
  };

  const handleViewExtrato = async (sessao: CaixaSessao) => {
    setSelectedSessao(sessao);
    setOpenExtrato(true);
    setLoadingExtrato(true);
    try {
      const res = await caixaService.getExtrato(sessao.id);
      setExtrato(res);
    } catch (err) {
      console.error(err);
      enqueueSnackbar('Erro ao carregar extrato', { variant: 'error' });
    } finally {
      setLoadingExtrato(false);
    }
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1400, mx: 'auto' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: 'text.primary', mb: 1 }}>Histórico de Caixas</Typography>
          <Typography variant="body1" color="text.secondary">Consulta e relatório de sessões de caixa do provedor</Typography>
        </Box>
      </Box>

      <Paper sx={{ borderRadius: 3, overflow: 'hidden' }}>
        <Box sx={{ p: 2, display: 'flex', gap: 2, alignItems: 'center', bgcolor: 'background.paper', borderBottom: 1, borderColor: 'divider' }}>
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Status</InputLabel>
            <Select value={statusFilter} label="Status" onChange={(e) => setStatusFilter(e.target.value)}>
              <MenuItem value="">Todos</MenuItem>
              <MenuItem value="ABERTO">Aberto</MenuItem>
              <MenuItem value="FECHADO">Fechado</MenuItem>
            </Select>
          </FormControl>
          
          <IconButton onClick={loadSessoes} disabled={loading} color="primary">
            <ArrowPathIcon className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </IconButton>
        </Box>

        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: 'rgba(0,0,0,0.02)' }}>
                <TableCell>ID</TableCell>
                <TableCell>Operador</TableCell>
                <TableCell>Local</TableCell>
                <TableCell>Abertura</TableCell>
                <TableCell>Fechamento</TableCell>
                <TableCell align="right">Saldo Final</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Ações</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading && sessoes.length === 0 ? (
                <TableRow><TableCell colSpan={8} align="center" sx={{ py: 4 }}><CircularProgress /></TableCell></TableRow>
              ) : sessoes.length === 0 ? (
                <TableRow><TableCell colSpan={8} align="center" sx={{ py: 4 }}>Nenhum caixa encontrado</TableCell></TableRow>
              ) : sessoes.map((s) => (
                <TableRow key={s.id} hover>
                  <TableCell>#{s.id}</TableCell>
                  <TableCell>{s.usuario_nome}</TableCell>
                  <TableCell>{s.local_pagamento_nome}</TableCell>
                  <TableCell>{new Date(s.data_abertura).toLocaleString('pt-BR')}</TableCell>
                  <TableCell>{s.data_fechamento ? new Date(s.data_fechamento).toLocaleString('pt-BR') : '-'}</TableCell>
                  <TableCell align="right">
                    {s.saldo_final_informado !== null && s.saldo_final_informado !== undefined ? `R$ ${s.saldo_final_informado.toFixed(2)}` : '-'}
                  </TableCell>
                  <TableCell>
                    {s.status === 'ABERTO' 
                      ? <Chip label="Aberto" size="small" color="success" /> 
                      : <Chip label="Fechado" size="small" color="default" />}
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title="Ver Extrato">
                      <IconButton size="small" onClick={() => handleViewExtrato(s)} color="info">
                        <EyeIcon className="w-5 h-5" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Baixar Relatório">
                      <IconButton 
                        size="small" 
                        color="primary" 
                        onClick={() => handleDownloadPDF(s.id)}
                        disabled={downloading === s.id}
                      >
                        {downloading === s.id ? <CircularProgress size={20} /> : <DocumentArrowDownIcon className="w-5 h-5" />}
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          component="div"
          count={totalRows}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          rowsPerPage={perPage}
          onRowsPerPageChange={(e) => { setPerPage(parseInt(e.target.value, 10)); setPage(0); }}
          labelRowsPerPage="Linhas:"
        />
      </Paper>

      {/* Extrato Modal */}
      <Dialog open={openExtrato} onClose={() => setOpenExtrato(false)} maxWidth="md" fullWidth>
        <DialogTitle>Extrato de Caixa #{selectedSessao?.id}</DialogTitle>
        <DialogContent dividers>
          {loadingExtrato ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress /></Box>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Data/Hora</TableCell>
                  <TableCell>Tipo</TableCell>
                  <TableCell>Forma</TableCell>
                  <TableCell>Descrição</TableCell>
                  <TableCell align="right">Valor</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {extrato.map((m) => (
                  <TableRow key={m.id}>
                    <TableCell>{new Date(m.created_at).toLocaleString('pt-BR')}</TableCell>
                    <TableCell>{m.tipo}</TableCell>
                    <TableCell>{m.forma_pagamento_nome || '-'}</TableCell>
                    <TableCell>{m.descricao || '-'}</TableCell>
                    <TableCell align="right" sx={{ color: ['RECEBIMENTO', 'SUPRIMENTO'].includes(m.tipo) ? 'success.main' : 'error.main' }}>
                      {['RECEBIMENTO', 'SUPRIMENTO'].includes(m.tipo) ? '+' : '-'} R$ {m.valor.toFixed(2)}
                    </TableCell>
                  </TableRow>
                ))}
                {extrato.length === 0 && (
                  <TableRow><TableCell colSpan={5} align="center">Nenhuma movimentação</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </DialogContent>
        <DialogActions>
          {selectedSessao && (
            <Button 
              startIcon={downloading === selectedSessao.id ? <CircularProgress size={16} /> : <DocumentArrowDownIcon className="w-4 h-4" />} 
              onClick={() => handleDownloadPDF(selectedSessao.id)}
              disabled={downloading === selectedSessao.id}
            >
              Imprimir PDF
            </Button>
          )}
          <Button onClick={() => setOpenExtrato(false)}>Fechar</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
