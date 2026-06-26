import sys
import os

from import_pronect import parse_pronect_csv

rows = parse_pronect_csv('/Users/orlando/Downloads/Pronect/Logins.csv')
print("Headers:", rows[0])
if len(rows) > 1:
    print("Row 1:", rows[1])
