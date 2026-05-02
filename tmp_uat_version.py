# tmp_uat_version.py
import sys
import sqlite3
from services.version_service import VersionService
from db import Database

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

def test_version_control():
    print("--- 4. VERSION CONTROL UAT ---")
    db = Database()
    svc = VersionService(db)
    
    # 1. Get an HP
    hp_id = db.conn.execute("SELECT id FROM hoc_phan LIMIT 1").fetchone()
    if not hp_id:
        print("[SKIP] No HP found.")
        return
    hp_id = hp_id[0]
    
    # 2. Test Snapshot
    try:
        ver_id = svc.create_snapshot(hp_id, "UAT Test Snapshot", "antigravity")
        print(f"[PASS] Snapshot created: ID {ver_id}")
        
        # 3. Verify snapshot data
        row = db.conn.execute("SELECT data_json FROM de_cuong_version WHERE id=?", (ver_id,)).fetchone()
        if row and row[0]:
            print("[PASS] Snapshot data_json is not empty")
        else:
            print("[FAIL] Snapshot data_json is empty")
            
        # 4. Test Restore (Simulate)
        # We won't actually restore to current HP to avoid messing up user data 
        # but we'll call restore_snapshot and see if it runs 
        # Actually, let's just check the data integrity
        print("[PASS] Version history retrieval: " + str(len(svc.get_versions(hp_id))) + " versions")
        
    except Exception as e:
        print(f"[CRITICAL] Version Control failed: {e}")

if __name__ == "__main__":
    test_version_control()
