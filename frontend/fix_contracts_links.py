import sys

# 1. Update Receivables.tsx
file1 = "/Users/orlando/python/FastAPI/brazcom_isp/frontend/src/pages/Receivables.tsx"
with open(file1, "r") as f:
    content1 = f.read()

# Replace TableHead
target1_head = """
                <TableCell>Emissão</TableCell>
                <TableCell>Vencimento</TableCell>
                <TableCell>Pagamento</TableCell>
"""
replacement1_head = """
                <TableCell>Emissão</TableCell>
                <TableCell>Vencimento</TableCell>
                <TableCell>Contrato</TableCell>
                <TableCell>Pagamento</TableCell>
"""
if target1_head.strip() in content1:
    content1 = content1.replace(target1_head.strip(), replacement1_head.strip())
else:
    # Just in case whitespace differs
    content1 = content1.replace("<TableCell>Vencimento</TableCell>\n                <TableCell>Pagamento</TableCell>", "<TableCell>Vencimento</TableCell>\n                <TableCell>Contrato</TableCell>\n                <TableCell>Pagamento</TableCell>")

# Replace TableBody
target1_body = """
                  <TableCell>{new Date(r.issue_date).toLocaleDateString('pt-BR')}</TableCell>
                  <TableCell>{new Date(r.due_date).toLocaleDateString('pt-BR')}</TableCell>
                  <TableCell>{r.paid_at ? new Date(r.paid_at).toLocaleDateString('pt-BR') : '-'}</TableCell>
"""
replacement1_body = """
                  <TableCell>{new Date(r.issue_date).toLocaleDateString('pt-BR')}</TableCell>
                  <TableCell>{new Date(r.due_date).toLocaleDateString('pt-BR')}</TableCell>
                  <TableCell>
                    {r.servico_contratado_id ? (
                      <Button 
                        variant="text" 
                        size="small" 
                        onClick={(e) => { e.stopPropagation(); navigate('/contracts', { state: { editContractId: r.servico_contratado_id } }); }}
                        sx={{ minWidth: 0, p: 0, textTransform: 'none', fontWeight: 'bold' }}
                      >
                        #{r.servico_contratado_id}
                      </Button>
                    ) : (
                      <Typography variant="body2" color="text.secondary">Avulso</Typography>
                    )}
                  </TableCell>
                  <TableCell>{r.paid_at ? new Date(r.paid_at).toLocaleDateString('pt-BR') : '-'}</TableCell>
"""
if target1_body.strip() in content1:
    content1 = content1.replace(target1_body.strip(), replacement1_body.strip())
else:
    content1 = content1.replace("<TableCell>{new Date(r.due_date).toLocaleDateString('pt-BR')}</TableCell>\n                  <TableCell>{r.paid_at ? new Date(r.paid_at).toLocaleDateString('pt-BR') : '-'}</TableCell>", replacement1_body.replace("                  <TableCell>{new Date(r.issue_date).toLocaleDateString('pt-BR')}</TableCell>\n", "").strip())

# Fix Colspan from 10 to 11
content1 = content1.replace('<TableCell colSpan={10} align="center"', '<TableCell colSpan={11} align="center"')

with open(file1, "w") as f:
    f.write(content1)


# 2. Update Clients.tsx
file2 = "/Users/orlando/python/FastAPI/brazcom_isp/frontend/src/pages/Clients.tsx"
with open(file2, "r") as f:
    content2 = f.read()

target2 = "<TableCell>{r.servico_contratado_id ? `#${r.servico_contratado_id}` : 'Avulso'}</TableCell>"
replacement2 = """
                              <TableCell>
                                {r.servico_contratado_id ? (
                                  <Button 
                                    variant="text" 
                                    size="small" 
                                    onClick={(e) => { e.stopPropagation(); navigate('/contracts', { state: { editContractId: r.servico_contratado_id } }); }}
                                    sx={{ minWidth: 0, p: 0, textTransform: 'none', fontWeight: 'bold' }}
                                  >
                                    #{r.servico_contratado_id}
                                  </Button>
                                ) : 'Avulso'}
                              </TableCell>
"""
content2 = content2.replace(target2, replacement2.strip())

with open(file2, "w") as f:
    f.write(content2)

