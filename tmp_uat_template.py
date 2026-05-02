# tmp_uat_template.py
import os
import sys
import sqlite3
from services.template_service import TemplateService
from services.template_engine import TemplateEngine
from db import Database

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

def test_template_rendering():
    print("--- 3. TEMPLATE ENGINE UAT ---")
    db = Database()
    svc = TemplateService(db)
    
    # Try to get context for any HP
    hp_id = db.conn.execute("SELECT id FROM hoc_phan LIMIT 1").fetchone()
    if not hp_id:
        print("[SKIP] No course data to test template context.")
        return
    
    hp_id = hp_id[0]
    try:
        context = svc.engine.build_context(hp_id)
        print(f"[PASS] Template context generated for HP ID {hp_id}")
        # Verify key fields
        required_keys = ['CourseName', 'CourseCode', 'CLOs', 'ContentLT']
        missing = [k for k in required_keys if k not in context]
        if not missing:
            print("[PASS] All core fields present in context")
        else:
            print(f"[FAIL] Missing fields in context: {missing}")
    except Exception as e:
        print(f"[CRITICAL] Template context generation failed: {e}")

if __name__ == "__main__":
    test_template_rendering()
