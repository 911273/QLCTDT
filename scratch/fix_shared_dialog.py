import re

path = r'g:\My Drive\01. Working\EPU\EPU Utis\QLCTDT Anti\V2.1\shared_data_dialog.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace for PO Manager (around line 954)
target_po = "tb.Button(bf, text='📥 Nhập từ Excel', command=self._import_excel, bootstyle='info-outline').pack(side='left', padx=4)"
replacement_po = target_po + "\n        tb.Button(bf, text='🔢 Tự đánh số', command=self._auto_number, bootstyle='warning-outline').pack(side='right', padx=4)"

# We need to find the FIRST occurrence (PO Manager)
content = content.replace(target_po, replacement_po, 1)

# Now find the NEXT occurrence (PLO Manager)
content = content.replace(target_po, replacement_po, 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
