import sqlite3

def check_tables():
    conn = sqlite3.connect('qlctdt.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    print("Tables:", ", ".join(tables))
    
    for t in tables:
        cursor.execute(f"PRAGMA table_info({t});")
        cols = [row[1] for row in cursor.fetchall()]
        print(f"Table {t} columns: {', '.join(cols)}")
        
    conn.close()

if __name__ == "__main__":
    check_tables()
