import React, { useState, useEffect, useCallback } from 'react';
import {
  Autocomplete, TextField, CircularProgress, Box, Typography
} from '@mui/material';
import { UserIcon } from '@heroicons/react/24/outline';
import { useCompany } from '../contexts/CompanyContext';
import contratoService, { Contrato } from '../services/contratoService';

interface ContractAutocompleteProps {
  value: Contrato | null;
  onChange: (contrato: Contrato | null) => void;
  label?: string;
  placeholder?: string;
  error?: boolean;
  helperText?: string;
  required?: boolean;
  disabled?: boolean;
}

const ContractAutocomplete: React.FC<ContractAutocompleteProps> = ({
  value,
  onChange,
  label = "Contrato do Cliente",
  placeholder = "Busque por nome do cliente, telefone, contrato ou endereço...",
  error = false,
  helperText = "",
  required = false,
  disabled = false
}) => {
  const { activeCompany } = useCompany();
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<Contrato[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const searchContracts = useCallback(async (query: string) => {
    if (!activeCompany || query.length < 2) {
      setOptions([]);
      return;
    }

    setLoading(true);
    try {
      const response = await contratoService.getContratosByEmpresaPaginated(
        activeCompany.id,
        1,
        20,
        query
      );
      setOptions(response.contratos || []);
    } catch (error) {
      console.error('Erro ao buscar contratos:', error);
      setOptions([]);
    } finally {
      setLoading(false);
    }
  }, [activeCompany]);

  useEffect(() => {
    if (searchTerm) {
      const timeoutId = setTimeout(() => {
        searchContracts(searchTerm);
      }, 300); // Debounce de 300ms

      return () => clearTimeout(timeoutId);
    } else {
      setOptions([]);
    }
  }, [searchTerm, searchContracts]);

  const handleInputChange = (event: React.SyntheticEvent, newInputValue: string) => {
    setSearchTerm(newInputValue);
  };

  const getOptionLabel = (option: Contrato) => {
    const parts = [];
    if (option.cliente_nome) {
      parts.push(option.cliente_nome);
    }
    
    const address = option.endereco_instalacao || [
      option.cliente_endereco ? `${option.cliente_endereco}${option.cliente_numero ? `, ${option.cliente_numero}` : ''}` : '',
      option.cliente_bairro,
      option.cliente_municipio ? `${option.cliente_municipio}${option.cliente_uf ? ` - ${option.cliente_uf}` : ''}` : ''
    ].filter(Boolean).join(', ');

    if (address) {
      parts.push(address);
    } else if (option.numero_contrato) {
      parts.push(`Contrato: #${option.numero_contrato}`);
    }
    return parts.length > 0 ? parts.join(' | ') : `Contrato #${option.id}`;
  };

  const renderOption = (props: React.HTMLAttributes<HTMLLIElement>, option: Contrato) => {
    const address = option.endereco_instalacao || [
      option.cliente_endereco ? `${option.cliente_endereco}${option.cliente_numero ? `, ${option.cliente_numero}` : ''}` : '',
      option.cliente_bairro,
      option.cliente_municipio ? `${option.cliente_municipio}${option.cliente_uf ? ` - ${option.cliente_uf}` : ''}` : ''
    ].filter(Boolean).join(', ');

    return (
      <li {...props} key={option.id} style={{ whiteSpace: 'normal', padding: '8px 16px' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, width: '100%' }}>
          <UserIcon style={{ width: 18, height: 18, color: '#666', flexShrink: 0 }} />
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="body2" fontWeight="semibold" sx={{ color: 'text.primary' }}>
              {option.cliente_nome} {option.numero_contrato ? `(Contrato: #${option.numero_contrato})` : `(ID Contrato: #${option.id})`}
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
              {address ? (
                <strong style={{ color: '#1976d2' }}>Endereço: {address}</strong>
              ) : (
                <span style={{ color: '#d32f2f' }}>Sem endereço cadastrado</span>
              )}
              {option.cliente_telefone && ` | Tel: ${option.cliente_telefone}`}
            </Typography>
          </Box>
        </Box>
      </li>
    );
  };

  return (
    <Autocomplete
      open={open}
      onOpen={() => setOpen(true)}
      onClose={() => setOpen(false)}
      options={options}
      value={value}
      onChange={(event, newValue) => onChange(newValue)}
      onInputChange={handleInputChange}
      getOptionLabel={getOptionLabel}
      renderOption={renderOption}
      loading={loading}
      disabled={disabled || !activeCompany}
      filterOptions={(x) => x} // Desabilitar filtro do MUI, usamos nossa própria busca
      renderInput={(params) => (
        <TextField
          {...params}
          label={label}
          placeholder={placeholder}
          required={required}
          error={error}
          helperText={helperText || (!activeCompany ? "Selecione uma empresa primeiro para buscar contratos" : "")}
          InputProps={{
            ...params.InputProps,
            endAdornment: (
              <>
                {loading ? <CircularProgress color="inherit" size={20} /> : null}
                {params.InputProps.endAdornment}
              </>
            ),
          }}
        />
      )}
    />
  );
};

export default ContractAutocomplete;
