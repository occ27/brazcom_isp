def tipo_from_cpfcnpj(cpfcnpj):
    if not cpfcnpj:
        return 'FISICA'
    cleaned = cpfcnpj.replace('.','').replace('/','').replace('-','').strip()
    return 'JURIDICA' if len(cleaned) > 11 else 'FISICA'

samples = ['688.672.719-20','12.345.678/0001-90', None, '']
for s in samples:
    print(s, '->', tipo_from_cpfcnpj(s))
