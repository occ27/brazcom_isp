import api from './authService';

export interface MercadoPagoPaymentRequest {
    transaction_amount: number;
    payment_method_id: string;
    payer: {
        email: string;
        identification: {
            type: string;
            number: string;
        };
        first_name?: string;
        last_name?: string;
    };
    token?: string;
    issuer_id?: string;
    installments?: number;
    receivable_ids: number[];
    discount_amount?: number;
}

export interface MercadoPagoResponse {
    payment_id: string;
    status: string;
    detail: any;
}

export const mercadopagoService = {
    async getPublicKey(empresaId: number): Promise<string> {
        const response = await api.get(`/mercadopago/public-key/${empresaId}`);
        return response.data.public_key;
    },

    async processPayment(payload: MercadoPagoPaymentRequest): Promise<MercadoPagoResponse> {
        const response = await api.post('/mercadopago/process', payload);
        return response.data;
    },

    async getReceivableByToken(token: string): Promise<any> {
        const response = await api.get(`/mercadopago/receivable/${token}`);
        return response.data;
    }
};

export default mercadopagoService;
