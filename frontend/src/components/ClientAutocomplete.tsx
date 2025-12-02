import React, { useState, useEffect, useCallback } from 'react';
import {
  Autocomplete, TextField, CircularProgress, Box, Typography
} from '@mui/material';
import { UserIcon } from '@heroicons/react/24/outline';
import { useCompany } from '../contexts/CompanyContext';
import clientService, { ClientAutocomplete as ClientAutocompleteType } from '../services/clientService';

interface ClientAutocompleteProps {
  value: ClientAutocompleteType | null;
  onChange: (client: ClientAutocompleteType | null) => void;
  label?: string;
  placeholder?: string;
  error?: boolean;
  helperText?: string;
  required?: boolean;
  disabled?: boolean;
}

const ClientAutocomplete: React.FC<ClientAutocompleteProps> = ({
  value,
  onChange,
  label = "Cliente",
  placeholder = "Digite para buscar cliente...",
  error = false,
  helperText = "",
  required = false,
  disabled = false
}) => {
  const { activeCompany } = useCompany();
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<ClientAutocompleteType[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const searchClients = useCallback(async (query: string) => {
    if (!activeCompany || query.length < 2) {
      setOptions([]);
      return;
    }

    setLoading(true);
    try {
      const clients = await clientService.autocompleteClients(activeCompany.id, query, 10);
      setOptions(clients);
    } catch (error) {
      console.error('Erro ao buscar clientes:', error);
      setOptions([]);
    } finally {
      setLoading(false);
    }
  }, [activeCompany]);

  useEffect(() => {
    if (searchTerm) {
      const timeoutId = setTimeout(() => {
        searchClients(searchTerm);
      }, 300); // Debounce de 300ms

      return () => clearTimeout(timeoutId);
    } else {
      setOptions([]);
    }
  }, [searchTerm, searchClients]);

  const handleInputChange = (event: React.SyntheticEvent, newInputValue: string) => {
    setSearchTerm(newInputValue);
  };

  const getOptionLabel = (option: ClientAutocompleteType) => {
    const parts = [];
    parts.push(option.nome_razao_social);

    if (option.cpf_cnpj) {
      parts.push(`CPF/CNPJ: ${option.cpf_cnpj}`);
    } else if (option.idOutros) {
      parts.push(`ID: ${option.idOutros}`);
    }

    if (option.email) {
      parts.push(`Email: ${option.email}`);
    }

    if (option.telefone) {
      parts.push(`Tel: ${option.telefone}`);
    }

    return parts.join(' | ');
  };

  const renderOption = (props: React.HTMLAttributes<HTMLLIElement>, option: ClientAutocompleteType) => (
    <li {...props}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <UserIcon style={{ width: 16, height: 16, color: '#666' }} />
        <Box>
          <Typography variant="body2" fontWeight="medium">
            {option.nome_razao_social}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {option.cpf_cnpj && `CPF/CNPJ: ${option.cpf_cnpj}`}
            {option.idOutros && `ID: ${option.idOutros}`}
            {(option.email || option.telefone) && (
              <>
                {option.cpf_cnpj || option.idOutros ? ' | ' : ''}
                {option.email && `Email: ${option.email}`}
                {option.email && option.telefone && ' | '}
                {option.telefone && `Tel: ${option.telefone}`}
              </>
            )}
          </Typography>
        </Box>
      </Box>
    </li>
  );

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
          helperText={helperText || (!activeCompany ? "Selecione uma empresa primeiro para buscar clientes" : "")}
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

export default ClientAutocomplete;