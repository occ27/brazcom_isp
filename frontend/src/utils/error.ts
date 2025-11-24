export function stringifyError(e: any): string {
  try {
    const detail = e?.response?.data?.detail ?? e?.message ?? e;
    if (!detail) return 'Erro desconhecido';
    if (Array.isArray(detail)) {
      return detail.map(d => (typeof d === 'string' ? d : (d?.msg || JSON.stringify(d)))).join('; ');
    }
    if (typeof detail === 'object') {
      return detail.msg || detail.message || JSON.stringify(detail);
    }
    return String(detail);
  } catch (err) {
    return 'Erro ao processar mensagem de erro';
  }
}
