# tests/test_repositories.py
"""
Unit tests cho CLORepository, RubricRepository, NoiDungRepository.
Dùng in-memory SQLite để test độc lập, không ảnh hưởng DB thật.
"""
import unittest
import sqlite3
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Schema DDL cho in-memory DB ──────────────────────────────────────────────
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS CLO_Standard (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ma_hp TEXT,
    ma_clo TEXT,
    mo_ta TEXT,
    plo_id INTEGER,
    muc_giang_day TEXT,
    thu_tu INTEGER
);

CREATE TABLE IF NOT EXISTS MucTieu_HP (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ma_hp TEXT,
    ma_mt TEXT,
    mo_ta TEXT,
    plo_id INTEGER,
    thu_tu INTEGER
);

CREATE TABLE IF NOT EXISTS Rubric (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ma_hp TEXT,
    ma_rubric TEXT,
    ten TEXT,
    clo_id INTEGER,
    bdg_id INTEGER
);

CREATE TABLE IF NOT EXISTS Rubric_TieuChi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rubric_id INTEGER REFERENCES Rubric(id) ON DELETE CASCADE,
    tieu_chi TEXT,
    trong_so REAL,
    xuat_sac TEXT,
    tot TEXT,
    dat TEXT,
    chua_dat TEXT,
    thu_tu INTEGER
);

CREATE TABLE IF NOT EXISTS NoiDung_LT (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ma_hp TEXT,
    stt INTEGER,
    tieu_de TEXT,
    gio_lt INTEGER DEFAULT 0,
    gio_bt INTEGER DEFAULT 0,
    gio_th_tn INTEGER DEFAULT 0,
    hoat_dong_day TEXT,
    hoat_dong_hoc TEXT,
    clo_ids TEXT,
    bai_dg_ma TEXT,
    tai_lieu_ref TEXT,
    is_header INTEGER DEFAULT 0,
    parent_id INTEGER
);

CREATE TABLE IF NOT EXISTS NoiDung_TH (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ma_hp TEXT,
    stt INTEGER,
    ten_bai TEXT,
    gio_lt INTEGER DEFAULT 0,
    gio_bt INTEGER DEFAULT 0,
    gio_th_tn INTEGER DEFAULT 0,
    hoat_dong_day TEXT,
    hoat_dong_hoc TEXT,
    clo_ids TEXT,
    bai_dg_ma TEXT
);

CREATE TABLE IF NOT EXISTS TaiLieu_Standard (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ma_hp TEXT,
    loai TEXT,
    thu_tu INTEGER,
    tac_gia TEXT,
    nam_xb TEXT,
    ten_tl TEXT,
    nxb TEXT,
    link TEXT
);

CREATE TABLE IF NOT EXISTS LichSu_CapNhat_Standard (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ma_hp TEXT,
    lan INTEGER,
    noi_dung TEXT,
    ngay TEXT,
    nguoi_cap_nhat TEXT
);

CREATE TABLE IF NOT EXISTS BaiDanhGia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ma_hp TEXT,
    ma_bdg TEXT,
    ten TEXT,
    hinh_thuc TEXT,
    trong_so REAL,
    loai_bieu TEXT
);

CREATE TABLE IF NOT EXISTS BaiDanhGia_CLO (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bdg_id INTEGER,
    clo_id INTEGER,
    diem_toida REAL,
    trong_so_cr REAL
);
"""


class FakeDB:
    """Minimal wrapper để BaseRepository nhận self.db.conn."""
    def __init__(self, conn):
        self.conn = conn


def _make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_SQL)
    return conn


# ═════════════════════════════════════════════════════════════════════════════
# 1. CLORepository Tests
# ═════════════════════════════════════════════════════════════════════════════
class TestCLORepository(unittest.TestCase):

    def setUp(self):
        self.conn = _make_conn()
        self.fake_db = FakeDB(self.conn)
        from repositories.clo_repository import CLORepository
        self.repo = CLORepository(self.fake_db)

    def tearDown(self):
        self.conn.close()

    # ── insert & get_all ─────────────────────────────────────────────────
    def test_insert_and_get_all(self):
        clo_id = self.repo.insert({
            'ma_hp': 'HP001', 'ma_clo': 'CLO1',
            'mo_ta': 'Mô tả CLO1', 'thu_tu': 1
        })
        self.assertIsNotNone(clo_id)
        rows = self.repo.get_all('HP001')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['ma_clo'], 'CLO1')

    def test_get_all_empty(self):
        rows = self.repo.get_all('NONEXIST')
        self.assertEqual(len(rows), 0)

    def test_get_all_ordered_by_thu_tu(self):
        self.repo.insert({'ma_hp': 'HP001', 'ma_clo': 'CLO2', 'mo_ta': 'B', 'thu_tu': 2})
        self.repo.insert({'ma_hp': 'HP001', 'ma_clo': 'CLO1', 'mo_ta': 'A', 'thu_tu': 1})
        rows = self.repo.get_all('HP001')
        self.assertEqual(rows[0]['ma_clo'], 'CLO1')
        self.assertEqual(rows[1]['ma_clo'], 'CLO2')

    # ── get_by_id ────────────────────────────────────────────────────────
    def test_get_by_id(self):
        clo_id = self.repo.insert({
            'ma_hp': 'HP001', 'ma_clo': 'CLO1', 'mo_ta': 'Test', 'thu_tu': 1
        })
        row = self.repo.get_by_id(clo_id)
        self.assertIsNotNone(row)
        self.assertEqual(row['ma_clo'], 'CLO1')

    def test_get_by_id_not_found(self):
        row = self.repo.get_by_id(9999)
        self.assertIsNone(row)

    # ── update ───────────────────────────────────────────────────────────
    def test_update(self):
        clo_id = self.repo.insert({
            'ma_hp': 'HP001', 'ma_clo': 'CLO1', 'mo_ta': 'Old', 'thu_tu': 1
        })
        self.repo.update(clo_id, {'mo_ta': 'New', 'muc_giang_day': 'I'})
        row = self.repo.get_by_id(clo_id)
        self.assertEqual(row['mo_ta'], 'New')
        self.assertEqual(row['muc_giang_day'], 'I')

    def test_update_partial(self):
        clo_id = self.repo.insert({
            'ma_hp': 'HP001', 'ma_clo': 'CLO1', 'mo_ta': 'Keep', 'thu_tu': 1
        })
        self.repo.update(clo_id, {'thu_tu': 5})
        row = self.repo.get_by_id(clo_id)
        self.assertEqual(row['mo_ta'], 'Keep')
        self.assertEqual(row['thu_tu'], 5)

    # ── delete ───────────────────────────────────────────────────────────
    def test_delete(self):
        clo_id = self.repo.insert({
            'ma_hp': 'HP001', 'ma_clo': 'CLO1', 'mo_ta': 'Del', 'thu_tu': 1
        })
        self.repo.delete(clo_id)
        self.assertIsNone(self.repo.get_by_id(clo_id))

    def test_delete_nonexistent(self):
        # Should not raise
        self.repo.delete(9999)

    # ── isolation by ma_hp ───────────────────────────────────────────────
    def test_isolation_by_ma_hp(self):
        self.repo.insert({'ma_hp': 'HP001', 'ma_clo': 'CLO1', 'mo_ta': 'A', 'thu_tu': 1})
        self.repo.insert({'ma_hp': 'HP002', 'ma_clo': 'CLO1', 'mo_ta': 'B', 'thu_tu': 1})
        self.assertEqual(len(self.repo.get_all('HP001')), 1)
        self.assertEqual(len(self.repo.get_all('HP002')), 1)

    # ── MucTieu_HP ───────────────────────────────────────────────────────
    def test_insert_muc_tieu(self):
        mt_id = self.repo.insert_muc_tieu({
            'ma_hp': 'HP001', 'ma_mt': 'MT1',
            'mo_ta': 'Mục tiêu 1', 'thu_tu': 1
        })
        self.assertIsNotNone(mt_id)
        rows = self.repo.get_all_muc_tieu('HP001')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['ma_mt'], 'MT1')

    def test_muc_tieu_ordered(self):
        self.repo.insert_muc_tieu({'ma_hp': 'HP001', 'ma_mt': 'MT2', 'mo_ta': 'B', 'thu_tu': 2})
        self.repo.insert_muc_tieu({'ma_hp': 'HP001', 'ma_mt': 'MT1', 'mo_ta': 'A', 'thu_tu': 1})
        rows = self.repo.get_all_muc_tieu('HP001')
        self.assertEqual(rows[0]['ma_mt'], 'MT1')

    def test_muc_tieu_empty(self):
        self.assertEqual(len(self.repo.get_all_muc_tieu('NONE')), 0)

    def test_multiple_clo_insert(self):
        for i in range(5):
            self.repo.insert({
                'ma_hp': 'HP001', 'ma_clo': f'CLO{i+1}',
                'mo_ta': f'Desc {i+1}', 'thu_tu': i+1
            })
        self.assertEqual(len(self.repo.get_all('HP001')), 5)

    def test_plo_id_field(self):
        clo_id = self.repo.insert({
            'ma_hp': 'HP001', 'ma_clo': 'CLO1',
            'mo_ta': 'Test PLO', 'plo_id': 42, 'thu_tu': 1
        })
        row = self.repo.get_by_id(clo_id)
        self.assertEqual(row['plo_id'], 42)


# ═════════════════════════════════════════════════════════════════════════════
# 2. RubricRepository Tests
# ═════════════════════════════════════════════════════════════════════════════
class TestRubricRepository(unittest.TestCase):

    def setUp(self):
        self.conn = _make_conn()
        self.fake_db = FakeDB(self.conn)
        from repositories.rubric_repository import RubricRepository
        self.repo = RubricRepository(self.fake_db)

    def tearDown(self):
        self.conn.close()

    # ── insert & get_all ─────────────────────────────────────────────────
    def test_insert_and_get_all(self):
        rid = self.repo.insert({
            'ma_hp': 'HP001', 'ma_rubric': 'R1',
            'ten': 'Rubric 1', 'clo_id': 1
        })
        self.assertIsNotNone(rid)
        rows = self.repo.get_all('HP001')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['ma_rubric'], 'R1')

    def test_get_all_empty(self):
        self.assertEqual(len(self.repo.get_all('NONE')), 0)

    def test_multiple_rubrics(self):
        self.repo.insert({'ma_hp': 'HP001', 'ma_rubric': 'R1', 'ten': 'A'})
        self.repo.insert({'ma_hp': 'HP001', 'ma_rubric': 'R2', 'ten': 'B'})
        self.assertEqual(len(self.repo.get_all('HP001')), 2)

    # ── tieu_chi ─────────────────────────────────────────────────────────
    def test_insert_tieu_chi(self):
        rid = self.repo.insert({
            'ma_hp': 'HP001', 'ma_rubric': 'R1', 'ten': 'Rubric 1'
        })
        tc_id = self.repo.insert_tieu_chi({
            'rubric_id': rid, 'tieu_chi': 'TC1',
            'trong_so': 0.4, 'xuat_sac': 'Tốt',
            'tot': 'Khá', 'dat': 'TB', 'chua_dat': 'Yếu',
            'thu_tu': 1
        })
        self.assertIsNotNone(tc_id)
        rows = self.repo.get_tieu_chi(rid)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['tieu_chi'], 'TC1')
        self.assertAlmostEqual(rows[0]['trong_so'], 0.4)

    def test_tieu_chi_ordered(self):
        rid = self.repo.insert({'ma_hp': 'HP001', 'ma_rubric': 'R1', 'ten': 'R'})
        self.repo.insert_tieu_chi({'rubric_id': rid, 'tieu_chi': 'TC2', 'thu_tu': 2})
        self.repo.insert_tieu_chi({'rubric_id': rid, 'tieu_chi': 'TC1', 'thu_tu': 1})
        rows = self.repo.get_tieu_chi(rid)
        self.assertEqual(rows[0]['tieu_chi'], 'TC1')
        self.assertEqual(rows[1]['tieu_chi'], 'TC2')

    def test_tieu_chi_empty(self):
        self.assertEqual(len(self.repo.get_tieu_chi(9999)), 0)

    def test_cascade_delete_tieu_chi(self):
        """Xóa Rubric → tiêu chí con bị cascade."""
        rid = self.repo.insert({'ma_hp': 'HP001', 'ma_rubric': 'R1', 'ten': 'R'})
        self.repo.insert_tieu_chi({'rubric_id': rid, 'tieu_chi': 'TC1', 'thu_tu': 1})
        self.repo.insert_tieu_chi({'rubric_id': rid, 'tieu_chi': 'TC2', 'thu_tu': 2})
        self.assertEqual(len(self.repo.get_tieu_chi(rid)), 2)
        # Xóa rubric
        self.conn.execute("DELETE FROM Rubric WHERE id=?", (rid,))
        self.conn.commit()
        self.assertEqual(len(self.repo.get_tieu_chi(rid)), 0)

    def test_isolation_by_ma_hp(self):
        self.repo.insert({'ma_hp': 'HP001', 'ma_rubric': 'R1', 'ten': 'A'})
        self.repo.insert({'ma_hp': 'HP002', 'ma_rubric': 'R1', 'ten': 'B'})
        self.assertEqual(len(self.repo.get_all('HP001')), 1)
        self.assertEqual(len(self.repo.get_all('HP002')), 1)

    def test_rubric_with_bdg_id(self):
        rid = self.repo.insert({
            'ma_hp': 'HP001', 'ma_rubric': 'R1',
            'ten': 'Rubric', 'bdg_id': 99
        })
        row = self.conn.execute("SELECT * FROM Rubric WHERE id=?", (rid,)).fetchone()
        self.assertEqual(row['bdg_id'], 99)

    def test_tieu_chi_all_levels(self):
        rid = self.repo.insert({'ma_hp': 'HP001', 'ma_rubric': 'R1', 'ten': 'R'})
        tc_id = self.repo.insert_tieu_chi({
            'rubric_id': rid, 'tieu_chi': 'Hiểu khái niệm',
            'trong_so': 0.3, 'thu_tu': 1,
            'xuat_sac': '9-10', 'tot': '7-8.9',
            'dat': '5-6.9', 'chua_dat': '0-4.9'
        })
        row = self.repo.get_tieu_chi(rid)[0]
        self.assertEqual(row['xuat_sac'], '9-10')
        self.assertEqual(row['chua_dat'], '0-4.9')


# ═════════════════════════════════════════════════════════════════════════════
# 3. NoiDungRepository Tests
# ═════════════════════════════════════════════════════════════════════════════
class TestNoiDungRepository(unittest.TestCase):

    def setUp(self):
        self.conn = _make_conn()
        self.fake_db = FakeDB(self.conn)
        from repositories.noidung_repository import NoiDungRepository
        self.repo = NoiDungRepository(self.fake_db)

    def tearDown(self):
        self.conn.close()

    # ── NoiDung_LT ───────────────────────────────────────────────────────
    def test_insert_lt_and_get(self):
        lt_id = self.repo.insert_lt({
            'ma_hp': 'HP001', 'stt': 1,
            'tieu_de': 'Chương 1: Tổng quan', 'gio_lt': 3
        })
        self.assertIsNotNone(lt_id)
        rows = self.repo.get_lt_all('HP001')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['tieu_de'], 'Chương 1: Tổng quan')
        self.assertEqual(rows[0]['gio_lt'], 3)

    def test_lt_ordered_by_stt(self):
        self.repo.insert_lt({'ma_hp': 'HP001', 'stt': 2, 'tieu_de': 'Ch2'})
        self.repo.insert_lt({'ma_hp': 'HP001', 'stt': 1, 'tieu_de': 'Ch1'})
        rows = self.repo.get_lt_all('HP001')
        self.assertEqual(rows[0]['tieu_de'], 'Ch1')

    def test_lt_empty(self):
        self.assertEqual(len(self.repo.get_lt_all('NONE')), 0)

    def test_update_lt(self):
        lt_id = self.repo.insert_lt({
            'ma_hp': 'HP001', 'stt': 1, 'tieu_de': 'Old', 'gio_lt': 2
        })
        self.repo.update_lt(lt_id, {'tieu_de': 'New', 'gio_lt': 5})
        rows = self.repo.get_lt_all('HP001')
        self.assertEqual(rows[0]['tieu_de'], 'New')
        self.assertEqual(rows[0]['gio_lt'], 5)

    def test_delete_lt(self):
        lt_id = self.repo.insert_lt({
            'ma_hp': 'HP001', 'stt': 1, 'tieu_de': 'Del'
        })
        self.repo.delete_lt(lt_id)
        self.assertEqual(len(self.repo.get_lt_all('HP001')), 0)

    # ── NoiDung_TH ───────────────────────────────────────────────────────
    def test_insert_th_and_get(self):
        th_id = self.repo.insert_th({
            'ma_hp': 'HP001', 'stt': 1,
            'ten_bai': 'Bài TH 1', 'gio_th_tn': 4
        })
        self.assertIsNotNone(th_id)
        rows = self.repo.get_th_all('HP001')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['ten_bai'], 'Bài TH 1')

    def test_th_ordered_by_stt(self):
        self.repo.insert_th({'ma_hp': 'HP001', 'stt': 2, 'ten_bai': 'TH2'})
        self.repo.insert_th({'ma_hp': 'HP001', 'stt': 1, 'ten_bai': 'TH1'})
        rows = self.repo.get_th_all('HP001')
        self.assertEqual(rows[0]['ten_bai'], 'TH1')

    # ── clo_ids JSON serialize/deserialize ───────────────────────────────
    def test_clo_ids_json_serialize(self):
        clo_ids = json.dumps([1, 2, 3])
        self.repo.insert_lt({
            'ma_hp': 'HP001', 'stt': 1, 'tieu_de': 'Ch1',
            'clo_ids': clo_ids
        })
        row = self.repo.get_lt_all('HP001')[0]
        parsed = json.loads(row['clo_ids'])
        self.assertEqual(parsed, [1, 2, 3])

    def test_clo_ids_empty_json(self):
        self.repo.insert_lt({
            'ma_hp': 'HP001', 'stt': 1, 'tieu_de': 'Ch1',
            'clo_ids': '[]'
        })
        row = self.repo.get_lt_all('HP001')[0]
        self.assertEqual(json.loads(row['clo_ids']), [])

    def test_clo_ids_null(self):
        self.repo.insert_lt({'ma_hp': 'HP001', 'stt': 1, 'tieu_de': 'Ch1'})
        row = self.repo.get_lt_all('HP001')[0]
        self.assertIsNone(row['clo_ids'])

    # ── is_header & parent_id ────────────────────────────────────────────
    def test_header_and_children(self):
        parent_id = self.repo.insert_lt({
            'ma_hp': 'HP001', 'stt': 1,
            'tieu_de': 'Chương 1', 'is_header': 1
        })
        self.repo.insert_lt({
            'ma_hp': 'HP001', 'stt': 2,
            'tieu_de': '1.1 Mục con', 'parent_id': parent_id
        })
        rows = self.repo.get_lt_all('HP001')
        parent = [r for r in rows if r['is_header'] == 1][0]
        child = [r for r in rows if r['parent_id'] == parent_id][0]
        self.assertEqual(parent['tieu_de'], 'Chương 1')
        self.assertEqual(child['tieu_de'], '1.1 Mục con')

    # ── isolation by ma_hp ───────────────────────────────────────────────
    def test_lt_isolation(self):
        self.repo.insert_lt({'ma_hp': 'HP001', 'stt': 1, 'tieu_de': 'A'})
        self.repo.insert_lt({'ma_hp': 'HP002', 'stt': 1, 'tieu_de': 'B'})
        self.assertEqual(len(self.repo.get_lt_all('HP001')), 1)
        self.assertEqual(len(self.repo.get_lt_all('HP002')), 1)

    def test_default_gio_values(self):
        self.repo.insert_lt({'ma_hp': 'HP001', 'stt': 1, 'tieu_de': 'Ch1'})
        row = self.repo.get_lt_all('HP001')[0]
        self.assertEqual(row['gio_lt'], 0)
        self.assertEqual(row['gio_bt'], 0)
        self.assertEqual(row['gio_th_tn'], 0)

    def test_bulk_insert_lt(self):
        for i in range(10):
            self.repo.insert_lt({
                'ma_hp': 'HP001', 'stt': i + 1,
                'tieu_de': f'Chương {i + 1}'
            })
        self.assertEqual(len(self.repo.get_lt_all('HP001')), 10)


# ═════════════════════════════════════════════════════════════════════════════
# 4. TaiLieuRepository Tests (bonus)
# ═════════════════════════════════════════════════════════════════════════════
class TestTaiLieuRepository(unittest.TestCase):

    def setUp(self):
        self.conn = _make_conn()
        self.fake_db = FakeDB(self.conn)
        from repositories.tailieu_repository import TaiLieuRepository
        self.repo = TaiLieuRepository(self.fake_db)

    def tearDown(self):
        self.conn.close()

    def test_insert_and_get(self):
        tid = self.repo.insert({
            'ma_hp': 'HP001', 'loai': 'Giáo trình',
            'thu_tu': 1, 'tac_gia': 'Nguyễn A',
            'ten_tl': 'Giáo trình Python', 'nam_xb': '2024'
        })
        self.assertIsNotNone(tid)
        rows = self.repo.get_all('HP001')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['ten_tl'], 'Giáo trình Python')

    def test_ordered_by_loai_thu_tu(self):
        self.repo.insert({'ma_hp': 'HP001', 'loai': 'Tham khảo', 'thu_tu': 1, 'ten_tl': 'TK1'})
        self.repo.insert({'ma_hp': 'HP001', 'loai': 'Giáo trình', 'thu_tu': 1, 'ten_tl': 'GT1'})
        rows = self.repo.get_all('HP001')
        self.assertEqual(rows[0]['loai'], 'Giáo trình')


# ═════════════════════════════════════════════════════════════════════════════
# 5. BaiDanhGiaRepository Tests (bonus)
# ═════════════════════════════════════════════════════════════════════════════
class TestBaiDanhGiaRepository(unittest.TestCase):

    def setUp(self):
        self.conn = _make_conn()
        self.fake_db = FakeDB(self.conn)
        from repositories.baidanhgia_repository import BaiDanhGiaRepository
        self.repo = BaiDanhGiaRepository(self.fake_db)

    def tearDown(self):
        self.conn.close()

    def test_insert_and_get(self):
        bid = self.repo.insert({
            'ma_hp': 'HP001', 'ma_bdg': 'BDG1',
            'ten': 'Bài kiểm tra GK', 'trong_so': 0.3
        })
        rows = self.repo.get_all('HP001')
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]['trong_so'], 0.3)

    def test_insert_clo_link(self):
        bid = self.repo.insert({
            'ma_hp': 'HP001', 'ma_bdg': 'BDG1', 'ten': 'GK'
        })
        self.repo.insert_clo_link({
            'bdg_id': bid, 'clo_id': 1,
            'diem_toida': 10.0, 'trong_so_cr': 0.5
        })
        row = self.conn.execute(
            "SELECT * FROM BaiDanhGia_CLO WHERE bdg_id=?", (bid,)
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertAlmostEqual(row['trong_so_cr'], 0.5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
