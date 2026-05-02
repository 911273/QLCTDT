import sys
sys.stdout.reconfigure(encoding='utf-8')
lines=open(r'g:\My Drive\01. Working\EPU\EPU Utis\QLCTDT Anti\V1.4.7_DCCT Mẫu  mới\db.py', encoding='utf-8').readlines()
print('\n'.join([f'{i+1}: {l.strip()}' for i, l in enumerate(lines) if 'def ' in l and 'ctdt' in l.lower()]))
