# tests/test_repositories.py
"""
Unit tests cho Repositories (HocPhan, CLO, NoiDung, etc.)
Dùng in-memory SQLite để test độc lập.
"""
import unittest
import sqlite3
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Schema DDL (Matching Production Tables) ──────────────────────────────────
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS khoa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ma TEXT UNIQUE,
    ten TEXT
);

CREATE TABLE IF NOT EXISTS hoc_phan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ma TEXT,
    ten_viet TEXT,
    ten_anh TEXT,
    khoa_id INTEGER REFERENCES khoa(id),
    ngay_tao TEXT,
    ngay_cap_nhat TEXT,
    tong_gio REAL DEFAULT 0,
    trang_thai TEXT DEFAULT 'nhap',
    gio_lt REAL DEFAULT 0,
    gio_bt REAL DEFAULT 0,
    gio_th REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS clo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hp_id INTEGER REFERENCES hoc_phan(id) ON DELETE CASCADE,
    ma TEXT,
    mo_ta TEXT,
    cdr_ma TEXT,
    level_irm TEXT,
    nhom TEXT,
    la_tieu_de_nhom INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS muc_tieu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hp_id INTEGER REFERENCES hoc_phan(id) ON DELETE CASCADE,
    ma_mt TEXT,
    mo_ta TEXT,
    cdr_ma TEXT,
    thu_tu INTEGER
);

CREATE TABLE IF NOT EXISTS noi_dung (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hp_id INTEGER REFERENCES hoc_phan(id) ON DELETE CASCADE,
    phan TEXT, -- 'LT' / 'TH'
    tieu_de TEXT,
    cap_do INTEGER DEFAULT 1,
    parent_id INTEGER,
    gio_lt REAL DEFAULT 0,
    gio_bt REAL DEFAULT 0,
    gio_th REAL DEFAULT 0,
    clo_ids TEXT
);

CREATE TABLE IF NOT EXISTS hoc_lieu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hp_id INTEGER REFERENCES hoc_phan(id) ON DELETE CASCADE,
    loai TEXT,
    ten_tl TEXT,
    thu_tu INTEGER
);

CREATE TABLE IF NOT EXISTS ke_hoach_kiem_tra (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hp_id INTEGER REFERENCES hoc_phan(id) ON DELETE CASCADE,
    ma_bdg TEXT,
    thu_tu INTEGER
);

CREATE TABLE IF NOT EXISTS ctdt_hoc_phan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hp_id INTEGER REFERENCES hoc_phan(id) ON DELETE CASCADE,
    ctdt_id INTEGER
);

CREATE TABLE IF NOT EXISTS temp_draft (
    hp_id INTEGER PRIMARY KEY REFERENCES hoc_phan(id) ON DELETE CASCADE,
    data_json TEXT,
    updated_at TEXT
);
"""

class FakeDB:
    def __init__(self, conn):
        self.conn = conn
    
    def transaction(self):
        class Transaction:
            def __enter__(self): return None
            def __exit__(self, exc_type, exc_val, exc_tb): pass
        return Transaction()

def _make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_SQL)
    # Mock unaccent function
    conn.create_function("unaccent", 1, lambda s: s if s else "")
    return conn

# ═════════════════════════════════════════════════════════════════════════════
# Tests for HocPhanRepository
# ═════════════════════════════════════════════════════════════════════════════
class TestHocPhanRepository(unittest.TestCase):
    def setUp(self):
        self.conn = _make_conn()
        from repositories.hoc_phan_repository import HocPhanRepository
        self.repo = HocPhanRepository(FakeDB(self.conn))
    
    def test_create_and_get(self):
        hp_id = self.repo.create({'ma': 'CS101', 'ten_viet': 'Lập trình C'})
        hp = self.repo.get_by_id(hp_id)
        self.assertIsNotNone(hp)
        self.assertEqual(hp['ma'], 'CS101')
    
    def test_update_hours(self):
        hp_id = self.repo.create({'ten_viet': 'Test'})
        self.repo.update(hp_id, {'gio_lt': 30, 'gio_bt': 15})
        hp = self.repo.get_by_id(hp_id)
        self.assertEqual(hp['tong_gio'], 45)

    def test_clone(self):
        hp_id = self.repo.create({'ma': 'ORIG', 'ten_viet': 'Original'})
        self.conn.execute("INSERT INTO clo (hp_id, ma) VALUES (?, ?)", (hp_id, 'CLO1'))
        
        new_id = self.repo.clone(hp_id)
        new_hp = self.repo.get_by_id(new_id)
        self.assertIn("(Bản sao)", new_hp['ten_viet'])
        
        clos = self.conn.execute("SELECT * FROM clo WHERE hp_id=?", (new_id,)).fetchall()
        self.assertEqual(len(clos), 1)

# ═════════════════════════════════════════════════════════════════════════════
# Tests for CLORepository
# ═════════════════════════════════════════════════════════════════════════════
class TestCLORepository(unittest.TestCase):
    def setUp(self):
        self.conn = _make_conn()
        from repositories.clo_repository import CLORepository
        self.repo = CLORepository(FakeDB(self.conn))
        # Create parent HP to satisfy FK
        self.hp_id = self.conn.execute("INSERT INTO hoc_phan (ten_viet) VALUES ('Parent')").lastrowid
    
    def test_set_all(self):
        self.repo.set_all(self.hp_id, [{'ma': 'CLO1'}, {'ma': 'CLO2'}])
        rows = self.repo.get_by_hp(self.hp_id)
        self.assertEqual(len(rows), 2)

# ═════════════════════════════════════════════════════════════════════════════
# Tests for NoiDungRepository
# ═════════════════════════════════════════════════════════════════════════════
class TestNoiDungRepository(unittest.TestCase):
    def setUp(self):
        self.conn = _make_conn()
        from repositories.noidung_repository import NoiDungRepository
        self.repo = NoiDungRepository(FakeDB(self.conn))
        # Create parent HP
        self.hp_id = self.conn.execute("INSERT INTO hoc_phan (ten_viet) VALUES ('Parent')").lastrowid
    
    def test_set_all_and_get(self):
        self.repo.set_all(self.hp_id, 'LT', [{'tieu_de': 'C1'}, {'tieu_de': 'C2'}])
        rows = self.repo.get_by_hp(self.hp_id, 'LT')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['tieu_de'], 'C1')

    def test_recursive_delete(self):
        p_id = self.conn.execute("INSERT INTO noi_dung (hp_id, tieu_de) VALUES (?, 'Parent')", (self.hp_id,)).lastrowid
        self.conn.execute("INSERT INTO noi_dung (hp_id, tieu_de, parent_id) VALUES (?, 'Child', ?)", (self.hp_id, p_id))
        
        self.repo.delete_recursive(p_id)
        count = self.conn.execute("SELECT COUNT(*) FROM noi_dung").fetchone()[0]
        self.assertEqual(count, 0)

if __name__ == '__main__':
    unittest.main()
