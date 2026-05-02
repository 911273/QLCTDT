# /tmp/uat_test_db.py
import sqlite3
import os

DB_PATH = 'qlctdt.db'

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

def test_schema():
    print("--- 1. DATABASE SCHEMA CHECK ---")
    if not os.path.exists(DB_PATH):
        print("FAIL: qlctdt.db NOT FOUND")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check new tables
    required_tables = ['de_cuong_version', 'word_template_v2', 'template_field_map']
    tables = [t[0] for t in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    for t in required_tables:
        status = "PASS" if t in tables else "FAIL"
        print(f"[{status}] Table: {t}")

    # Check CLO column
    cols = [x[1] for x in c.execute("PRAGMA table_info(clo)").fetchall()]
    status = "PASS" if 'cap_do_bloom' in cols else "FAIL"
    print(f"[{status}] Column 'cap_do_bloom' in 'clo'")
    
    conn.close()

def test_business_logic():
    print("\n--- 2. BUSINESS LOGIC CHECK ---")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    weighted_hps = c.execute("SELECT DISTINCT hp_id FROM ke_hoach_kiem_tra").fetchall()
    print(f"Checking {len(weighted_hps)} courses for assessment weights...")
    issues_weight = 0
    for row in weighted_hps:
        hp_id = row['hp_id']
        res = c.execute("SELECT SUM(trong_so) FROM ke_hoach_kiem_tra WHERE hp_id = ?", (hp_id,)).fetchone()
        total_weight = res[0]
        if total_weight and abs(total_weight - 100) > 0.1:
            issues_weight += 1
    
    if issues_weight == 0:
        print("[PASS] All assessment weights sum to 100%")
    else:
        print(f"[FAIL] {issues_weight} courses have invalid weight summation (!= 100%)")

    unmapped_clos = c.execute("SELECT COUNT(*) FROM clo WHERE cdr_ma IS NULL OR cdr_ma = ''").fetchone()[0]
    if unmapped_clos == 0:
        print("[PASS] 100% CLOs are mapped to PLO/PI")
    else:
        print(f"[MAJOR] {unmapped_clos} CLOs NOT mapped to PLO/PI")

    conn.close()

if __name__ == "__main__":
    test_schema()
    test_business_logic()
