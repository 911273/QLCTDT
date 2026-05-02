import sqlite3
import json

conn = sqlite3.connect('qlctdt.db')
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT * FROM ui_field_meta").fetchall()
for r in rows:
    print(dict(r))
conn.close()
