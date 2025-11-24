import csv
from collections import Counter

with open('john.csv', encoding='utf-8-sig') as f:
    r = csv.DictReader(f)
    cpfs = [row['cpf_cnpj'].strip() for row in r if row.get('cpf_cnpj')]

c = Counter(cpfs)
dups = {k: v for k, v in c.items() if v > 1}

print(f'Total linhas com CPF: {len(cpfs)}')
print(f'CPFs únicos: {len(c)}')
print(f'CPFs duplicados: {len(dups)}')
print(f'Total de duplicatas (linhas extras): {sum(v-1 for v in dups.values())}')

if len(dups) <= 20:
    print('\nCPFs duplicados:')
    for cpf, count in sorted(dups.items(), key=lambda x: x[1], reverse=True):
        print(f'  {cpf}: {count} vezes')
