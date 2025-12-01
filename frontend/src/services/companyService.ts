import api from './authService';
import { Company } from '../types';

export interface CompanyCreate {
  razao_social: string;
  nome_fantasia?: string;
  cnpj: string;
  inscricao_estadual?: string;
  endereco: string;  // Agora obrigatório
  numero: string;    // Agora obrigatório
  complemento?: string;
  bairro: string;    // Agora obrigatório
  municipio: string; // Agora obrigatório
  uf: string;        // Agora obrigatório
  codigo_ibge: string; // Agora obrigatório
  cep: string;       // Agora obrigatório
  telefone?: string;
  email: string;     // Agora obrigatório
  regime_tributario?: string;
  cnae_principal?: string; // Novo campo opcional
  
  // Configuração de cobrança: conta bancária padrão (opcional)
  default_bank_account_id?: number;
  
  // Novos campos opcionais
  logo_url?: string;
  certificado_path?: string;
  certificado_senha?: string;
  smtp_server?: string;
  smtp_port?: number;
  smtp_user?: string;
  smtp_password?: string;
  // Preferência de ambiente para transmissão NFCom: 'producao' | 'homologacao'
  ambiente_nfcom?: string;
}

export interface CompanyUpdate {
  razao_social?: string;
  nome_fantasia?: string;
  inscricao_estadual?: string;
  endereco?: string;
  numero?: string;
  complemento?: string;
  bairro?: string;
  municipio?: string;
  uf?: string;
  codigo_ibge?: string;
  cep?: string;
  telefone?: string;
  email?: string;
  regime_tributario?: string;
  cnae_principal?: string; // Novo campo opcional
  
  // Configuração de cobrança: conta bancária padrão (opcional)
  default_bank_account_id?: number;
  
  // Novos campos
  logo_url?: string;
  certificado_path?: string;
  certificado_senha?: string;
  smtp_server?: string;
  smtp_port?: number;
  smtp_user?: string;
  smtp_password?: string;
  ambiente_nfcom?: string;
  
  is_active?: boolean;
}

export const companyService = {
  // Listar empresas (com filtro baseado em permissões)
  async getCompanies(): Promise<Company[]> {
    const response = await api.get('/empresas/');
    return response.data;
  },

  // Obter empresa por ID
  async getCompany(id: number): Promise<Company> {
    const response = await api.get(`/empresas/${id}`);
    return response.data;
  },

  // Criar nova empresa (apenas superusuários)
  async createCompany(company: CompanyCreate): Promise<Company> {
    const response = await api.post('/empresas/', company);
    return response.data;
  },

  // Atualizar empresa
  async updateCompany(id: number, company: CompanyUpdate): Promise<Company> {
    const response = await api.put(`/empresas/${id}`, company);
    return response.data;
  },

  // Deletar empresa (apenas superusuários)
  async deleteCompany(id: number): Promise<void> {
    await api.delete(`/empresas/${id}`);
  },

  // Formatar CNPJ para exibição
  formatCNPJ(cnpj: string): string {
    const cleaned = cnpj.replace(/\D/g, '');
    if (cleaned.length !== 14) return cnpj;
    return `${cleaned.slice(0, 2)}.${cleaned.slice(2, 5)}.${cleaned.slice(5, 8)}/${cleaned.slice(8, 12)}-${cleaned.slice(12)}`;
  },

  // Formatar CEP para exibição
  formatCEP(cep: string): string {
    const cleaned = cep.replace(/\D/g, '');
    if (cleaned.length !== 8) return cep;
    return `${cleaned.slice(0, 5)}-${cleaned.slice(5)}`;
  },

  // Validar CEP
  validateCEP(cep: string): boolean {
    const cleaned = cep.replace(/\D/g, '');
    return cleaned.length === 8;
  },

  // Validar CNPJ
  validateCNPJ(cnpj: string): boolean {
    const cleaned = cnpj.replace(/\D/g, '');
    if (cleaned.length !== 14) return false;

    // Verificar se todos os dígitos são iguais
    if (/^(\d)\1+$/.test(cleaned)) return false;

    // Calcular primeiro dígito verificador
    let sum = 0;
    let weight = 5;
    for (let i = 0; i < 12; i++) {
      sum += parseInt(cleaned[i]) * weight;
      weight = weight === 2 ? 9 : weight - 1;
    }
    let digit = 11 - (sum % 11);
    if (digit >= 10) digit = 0;
    if (digit !== parseInt(cleaned[12])) return false;

    // Calcular segundo dígito verificador
    sum = 0;
    weight = 6;
    for (let i = 0; i < 13; i++) {
      sum += parseInt(cleaned[i]) * weight;
      weight = weight === 2 ? 9 : weight - 1;
    }
    digit = 11 - (sum % 11);
    if (digit >= 10) digit = 0;
    if (digit !== parseInt(cleaned[13])) return false;

    return true;
  },

  // Validar inscrição estadual (aceita "ISENTO" como válido)
  validateInscricaoEstadual(ie: string, uf?: string): boolean {
    if (!ie || !ie.trim()) return false;

    const ieClean = ie.replace(/\D/g, '').toUpperCase();
    const ieUpper = ie.toUpperCase().trim();

    // Algumas UFs não aceitam literal ISENTO (conforme manual NFCom)
    const ufsNaoPermitemIsento = new Set(['AM', 'BA', 'CE', 'GO', 'MG', 'MS', 'MT', 'PE', 'RN', 'SE', 'SP']);
    if (ieUpper === 'ISENTO') {
      if (uf) {
        const u = uf.toUpperCase().trim();
        if (ufsNaoPermitemIsento.has(u)) return false;
      }
      return true;
    }

    // Se não for ISENTO, deve ter pelo menos alguns dígitos
    return ieClean.length >= 8;
  },

  // Validar código IBGE (7 dígitos) e coerência com UF quando fornecida
  validateCodigoIBGE(codigo: string, uf?: string): boolean {
    if (!codigo) return false;
    const cleaned = codigo.replace(/\D/g, '');
    if (cleaned.length !== 7) return false;

    const ufToPrefix: Record<string, string> = {
      'RO': '11','AC':'12','AM':'13','RR':'14','PA':'15','AP':'16','TO':'17',
      'MA':'21','PI':'22','CE':'23','RN':'24','PB':'25','PE':'26','AL':'27','SE':'28','BA':'29',
      'MG':'31','ES':'32','RJ':'33','SP':'35','PR':'41','SC':'42','RS':'43','MS':'50','MT':'51','GO':'52','DF':'53'
    };
    if (uf) {
      const up = uf.toUpperCase().trim();
      const prefix = ufToPrefix[up];
      if (prefix && !cleaned.startsWith(prefix)) return false;
    }
    return true;
  },

  // Buscar endereço por CEP usando ViaCEP
  async searchCEP(cep: string): Promise<{
    endereco: string;
    bairro: string;
    municipio: string;
    uf: string;
    codigo_ibge: string;
  } | null> {
    try {
      const cepClean = cep.replace(/\D/g, '');
      if (cepClean.length !== 8) {
        throw new Error('CEP deve ter 8 dígitos');
      }

      const response = await fetch(`https://viacep.com.br/ws/${cepClean}/json/`);
      const data = await response.json();

      if (data.erro) {
        throw new Error('CEP não encontrado');
      }

      return {
        endereco: data.logradouro || '',
        bairro: data.bairro || '',
        municipio: data.localidade || '',
        uf: data.uf || '',
        codigo_ibge: data.ibge || ''
      };
    } catch (error) {
      console.error('Erro ao buscar CEP:', error);
      throw error;
    }
  },

  // Aplicar máscara de CNPJ
  formatCNPJInput(value: string): string {
    const cleaned = value.replace(/\D/g, '');
    const match = cleaned.match(/^(\d{0,2})(\d{0,3})(\d{0,3})(\d{0,4})(\d{0,2})$/);

    if (!match) return value;

    const formatted = [
      match[1] ? match[1] : '',
      match[2] ? '.' + match[2] : '',
      match[3] ? '.' + match[3] : '',
      match[4] ? '/' + match[4] : '',
      match[5] ? '-' + match[5] : ''
    ].join('');

    return formatted;
  },

  // Aplicar máscara de CEP
  formatCEPInput(value: string): string {
    const cleaned = value.replace(/\D/g, '');
    const match = cleaned.match(/^(\d{0,5})(\d{0,3})$/);

    if (!match) return value;

    return [
      match[1] ? match[1] : '',
      match[2] ? '-' + match[2] : ''
    ].join('');
  },

  // Testar configuração SMTP da empresa
  async testSMTPConfig(companyId: number, smtpData?: { smtp_server: string; smtp_port: number; smtp_user: string; smtp_password: string }): Promise<{ success: boolean; message: string }> {
    const response = await api.post(`/empresas/${companyId}/test-smtp`, smtpData);
    return response.data;
  },

  // Upload de logo da empresa
  async uploadCompanyLogo(companyId: number, file: File): Promise<{ file_path: string; file_name: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post(`/uploads/empresa/${companyId}/logo`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Upload de certificado digital da empresa
  async uploadCompanyCertificate(companyId: number, file: File): Promise<{ file_path: string; file_name: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post(`/uploads/empresa/${companyId}/certificado`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Deletar logo da empresa
  async deleteCompanyLogo(companyId: number): Promise<{ deleted_files: string[] }> {
    const response = await api.delete(`/uploads/empresa/${companyId}/logo`);
    return response.data;
  },

  // Deletar certificado da empresa
  async deleteCompanyCertificate(companyId: number): Promise<{ deleted_files: string[] }> {
    const response = await api.delete(`/uploads/empresa/${companyId}/certificado`);
    return response.data;
  },

  // Aplicar máscara de telefone
  formatPhoneInput(value: string): string {
    const cleaned = value.replace(/\D/g, '');
    const match = cleaned.match(/^(\d{0,2})(\d{0,5})(\d{0,4})$/);

    if (!match) return value;

    return [
      match[1] ? '(' + match[1] : '',
      match[2] ? ') ' + match[2] : '',
      match[3] ? '-' + match[3] : ''
    ].join('');
  }
};