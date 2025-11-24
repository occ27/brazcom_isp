jest.mock('../services/authService', () => ({
  default: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  },
}));

import { clientService } from '../services/clientService';
import api from '../services/authService';

describe('clientService', () => {
  let mockGet: jest.SpyInstance;

  beforeEach(() => {
    jest.clearAllMocks();
    mockGet = jest.spyOn(api, 'get');
  });

  describe('getClientsByCompany', () => {
    it('should return clients array when API returns raw array', async () => {
      const mockClients = [
        { id: 1, nome_razao_social: 'Cliente 1' },
        { id: 2, nome_razao_social: 'Cliente 2' },
      ];

      mockGet.mockResolvedValue({ data: mockClients });

      const result = await clientService.getClientsByCompany(1, 1, 10);

      expect(mockGet).toHaveBeenCalledWith('/clientes/empresa/1', {
        params: { skip: 0, limit: 10 },
      });
      expect(result).toEqual({ total: 2, clientes: mockClients });
    });

    it('should return clients array when API returns object with clientes property', async () => {
      const mockResponse = {
        clientes: [
          { id: 1, nome_razao_social: 'Cliente 1' },
          { id: 2, nome_razao_social: 'Cliente 2' },
        ],
        total: 2,
      };

      mockGet.mockResolvedValue({ data: mockResponse });

      const result = await clientService.getClientsByCompany(1, 1, 10);

      expect(result).toEqual(mockResponse);
    });

    it('should return empty array when API returns unexpected format', async () => {
      mockGet.mockResolvedValue({ data: null });

      const result = await clientService.getClientsByCompany(1, 1, 10);

      expect(result).toEqual({ total: 0, clientes: [] });
    });

    it('should return empty array when clientes property is not an array', async () => {
      const mockResponse = {
        clientes: 'invalid',
        total: 0,
      };

      mockGet.mockResolvedValue({ data: mockResponse });

      const result = await clientService.getClientsByCompany(1, 1, 10);

      expect(result).toEqual({ total: 0, clientes: [] });
    });
  });

  describe('formatCpfCnpj', () => {
    it('should format CPF correctly', () => {
      expect(clientService.formatCpfCnpj('12345678901')).toBe('123.456.789-01');
      expect(clientService.formatCpfCnpj('123456789')).toBe('123456789');
    });

    it('should format CNPJ correctly', () => {
      expect(clientService.formatCpfCnpj('12345678000123')).toBe('12.345.678/0001-23');
      expect(clientService.formatCpfCnpj('123456780001')).toBe('123456780001');
    });

    it('should return original value for invalid lengths', () => {
      expect(clientService.formatCpfCnpj('123')).toBe('123');
      expect(clientService.formatCpfCnpj('123456789012345')).toBe('123456789012345');
    });
  });

  describe('formatCpfCnpjInput', () => {
    it('should format CPF input correctly', () => {
      expect(clientService.formatCpfCnpjInput('12345678901')).toBe('123.456.789-01');
    });

    it('should format CNPJ input correctly', () => {
      expect(clientService.formatCpfCnpjInput('12345678000123')).toBe('12.345.678/0001-23');
    });

    it('should handle partial input', () => {
      expect(clientService.formatCpfCnpjInput('123')).toBe('123');
      expect(clientService.formatCpfCnpjInput('12345')).toBe('123.45');
    });
  });

  describe('formatPhoneInput', () => {
    it('should format phone number correctly', () => {
      expect(clientService.formatPhoneInput('11987654321')).toBe('(11) 98765-4321');
    });

    it('should handle partial input', () => {
      expect(clientService.formatPhoneInput('11')).toBe('(11) ');
      expect(clientService.formatPhoneInput('11987')).toBe('(11) 987');
    });
  });

  describe('validateCPF', () => {
    it('should validate correct CPF', () => {
      expect(clientService.validateCPF('12345678909')).toBe(true); // CPF válido para teste
    });

    it('should reject invalid CPF', () => {
      expect(clientService.validateCPF('11111111111')).toBe(false); // CPF com dígitos repetidos
      expect(clientService.validateCPF('123')).toBe(false); // CPF muito curto
    });
  });

  describe('validateEmail', () => {
    it('should validate correct email', () => {
      expect(clientService.validateEmail('test@example.com')).toBe(true);
    });

    it('should reject invalid email', () => {
      expect(clientService.validateEmail('invalid-email')).toBe(false);
      expect(clientService.validateEmail('')).toBe(false);
    });
  });

  describe('validatePhone', () => {
    it('should validate correct phone number', () => {
      expect(clientService.validatePhone('11987654321')).toBe(true);
    });

    it('should reject invalid phone number', () => {
      expect(clientService.validatePhone('123')).toBe(false);
      expect(clientService.validatePhone('')).toBe(false);
    });
  });
});