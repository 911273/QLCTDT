# tmp_uat_stats.py
import sys
import sqlite3
from services.stats_service import StatsService
from db import Database

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

def test_stats():
    print("--- 5. STATISTICS & ANALYTICS UAT ---")
    db = Database()
    svc = StatsService(db)
    
    try:
        stats = svc.get_overall_dashboard_stats()
        print("[PASS] Dashboard stats calculated")
        print(f"  - Total HP: {stats.get('total_hp')}")
        print(f"  - Digital HP: {stats.get('digital_hp')}")
        
        # Check audit consistency
        hp_id = db.conn.execute("SELECT id FROM hoc_phan LIMIT 1").fetchone()
        if hp_id:
            from services.validation_service import ValidationService
            val = ValidationService()
            issues = val.audit_full_consistency(db, hp_id[0])
            print(f"[PASS] Full audit run for HP {hp_id[0]}: {len(issues)} issues found")
            
    except Exception as e:
        print(f"[CRITICAL] Stats failed: {e}")

if __name__ == "__main__":
    test_stats()
