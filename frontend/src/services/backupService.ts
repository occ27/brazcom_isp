import api from './authService';

export const backupService = {
  downloadBackup: async (empresaId: number): Promise<{ blob: Blob; filename: string }> => {
    const response = await api.get('/backup/export', {
      responseType: 'blob',
      headers: {
        'X-Active-Empresa': String(empresaId)
      }
    });

    let filename = `backup_empresa_${new Date().getTime()}.zip`;
    const disposition = response.headers['content-disposition'] || response.headers['Content-Disposition'];
    if (disposition && disposition.indexOf('attachment') !== -1) {
      const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
      const matches = filenameRegex.exec(disposition);
      if (matches != null && matches[1]) {
        filename = matches[1].replace(/['"]/g, '');
      }
    }

    return {
      blob: response.data,
      filename
    };
  }
};

export default backupService;
