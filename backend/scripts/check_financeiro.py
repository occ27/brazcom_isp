import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from import_pronect import parse_pronect_csv

base_dir = '/Users/orlando/Downloads/Pronect'
if os.path.exists(f'{base_dir}/Financeiro.csv'):
    rows = parse_pronect_csv(f'{base_dir}/Financeiro.csv')
    print("Financeiro.csv Headers:", rows[0])
    if len(rows) > 1:
        print("Row 1:", rows[1])

if os.path.exists(f'{base_dir}/Planos.csv'):
    print("Planos.csv EXISTS!")
else:
    print("Planos.csv DOES NOT EXIST")
