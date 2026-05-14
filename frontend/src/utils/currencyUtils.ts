/**
 * Formata um número para o padrão de moeda brasileira (BRL)
 */
export const formatCurrency = (value: number | undefined | null): string => {
  if (value === undefined || value === null) return '';
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);
};

/**
 * Converte uma string formatada em moeda para um número
 */
export const parseCurrency = (value: string): number => {
  // Remove R$, espaços e pontos de milhar, substitui vírgula por ponto
  const cleanValue = value
    .replace(/[R$\s.]/g, '')
    .replace(',', '.');
  
  const parsed = parseFloat(cleanValue);
  return isNaN(parsed) ? 0 : parsed;
};

/**
 * Formata entrada de texto em tempo real para moeda
 */
export const maskCurrency = (value: string): string => {
  let cleanValue = value.replace(/\D/g, '');
  if (!cleanValue || parseInt(cleanValue) === 0) return '';
  
  const numberValue = parseInt(cleanValue) / 100;
  
  if (isNaN(numberValue)) return '';
  
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(numberValue);
};

/**
 * Converte string de máscara para número
 */
export const unmaskCurrency = (value: string): number => {
  let cleanValue = value.replace(/\D/g, '');
  return parseInt(cleanValue) / 100 || 0;
};
