"""
Summarize the create_contracts_for_empresa report CSV.

Usage:
  python migrations/summarize_create_contracts_report.py <report.csv>

Prints counts of actions and a small sample.
"""
import sys
import csv

def summarize(path):
    counts = {}
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            action = r.get('action') or 'unknown'
            counts[action] = counts.get(action, 0) + 1
            rows.append(r)
    print('Report:', path)
    for k in sorted(counts):
        print(f'  {k}: {counts[k]}')
    print('\nSample rows (first 10):')
    for r in rows[:10]:
        print(' ', r)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: python summarize_create_contracts_report.py <report.csv>')
        sys.exit(1)
    summarize(sys.argv[1])
