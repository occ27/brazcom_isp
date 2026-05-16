import api from './api';

export type LicenseStatus = 'PENDENTE' | 'ATIVA' | 'EXPIRADA' | 'CANCELADA';
export type LicensePlan = 'ANUAL' | 'BIANUAL';

export interface License {
    id: number;
    empresa_id: number;
    user_id: number;
    plan: LicensePlan;
    status: LicenseStatus;
    price: number;
    start_date?: string;
    end_date?: string;
    payment_date?: string;
    created_at: string;
}

export interface LicensePricingPlan {
    id: number;
    name: string;
    description?: string;
    price: number;
    duration_months: number;
    is_active: boolean;
    is_highlighted: boolean;
}

export const licenseService = {
    // --- Dynamic Plans ---
    getActivePlans: async (): Promise<LicensePricingPlan[]> => {
        const response = await api.get('/license-plans/');
        return response.data;
    },

    getAllPlans: async (): Promise<LicensePricingPlan[]> => {
        const response = await api.get('/license-plans/admin/all');
        return response.data;
    },

    createPlan: async (data: any): Promise<LicensePricingPlan> => {
        const response = await api.post('/license-plans/', data);
        return response.data;
    },

    updatePlan: async (id: number, data: any): Promise<LicensePricingPlan> => {
        const response = await api.put(`/license-plans/${id}`, data);
        return response.data;
    },

    deletePlan: async (id: number): Promise<void> => {
        await api.delete(`/license-plans/${id}`);
    },

    // --- Licenses ---
    createLicense: async (empresa_id: number, plan_id: number): Promise<License> => {
        const response = await api.post('/licenses/', { empresa_id, plan_id });
        return response.data;
    },

    getCompanyLicenses: async (empresa_id: number): Promise<License[]> => {
        const response = await api.get(`/licenses/my-company/${empresa_id}`);
        return response.data;
    },

    getPendingLicenses: async (): Promise<License[]> => {
        const response = await api.get('/licenses/admin/pending');
        return response.data;
    },

    approveLicense: async (license_id: number): Promise<License> => {
        const response = await api.post(`/licenses/${license_id}/approve`);
        return response.data;
    },

    checkStatus: async (empresa_id: number): Promise<{ is_active: boolean, license: License | null }> => {
        const response = await api.get(`/licenses/check-status/${empresa_id}`);
        return response.data;
    },

    // --- Admin Methods ---
    getAllLicenses: async (params?: { skip?: number, limit?: number, status?: string }): Promise<License[]> => {
        const response = await api.get('/licenses/admin/all', { params });
        return response.data;
    },

    createManualLicense: async (data: any): Promise<License> => {
        const response = await api.post('/licenses/admin/manual', data);
        return response.data;
    },

    updateLicense: async (id: number, data: any): Promise<License> => {
        const response = await api.put(`/licenses/admin/${id}`, data);
        return response.data;
    },

    cancelLicense: async (id: number): Promise<License> => {
        const response = await api.post(`/licenses/admin/${id}/cancel`);
        return response.data;
    },

    getAdminCompaniesStatus: async (): Promise<any[]> => {
        const response = await api.get('/licenses/admin/companies-status');
        return response.data;
    }
};
