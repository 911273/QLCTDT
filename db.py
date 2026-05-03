# db.py — Database layer cho QLCTDT
import sqlite3
import os
import shutil
import threading
import re
import json
from datetime import datetime, timedelta
from core.logger import logger
from contextlib import contextmanager


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qlctdt.db')

def unaccent_vietnamese(s):
    if not s: return ""
    if not isinstance(s, str): s = str(s)
    s = s.lower()
    s = re.sub('[áàảãạâấầẩẫậăắằẳẵặ]', 'a', s)
    s = re.sub('[éèẻẽẹêếềểễệ]', 'e', s)
    s = re.sub('[íìỉĩị]', 'i', s)
    s = re.sub('[óòỏõọôốồổỗộơớờởỡợ]', 'o', s)
    s = re.sub('[úùủũụưứừửữự]', 'u', s)
    s = re.sub('[ýỳỷỹỵ]', 'y', s)
    s = re.sub('đ', 'd', s)
    return s

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    version INTEGER NOT NULL UNIQUE, -- FIXED: P2-4: Added UNIQUE
    updated_at TEXT NOT NULL
);



CREATE TABLE IF NOT EXISTS khoa (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    ma   TEXT,
    ten  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS giang_vien (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ho_ten   TEXT NOT NULL,
    hoc_vi   TEXT,
    sdt      TEXT,
    email    TEXT,
    khoa_id  INTEGER REFERENCES khoa(id),
    -- New fields for Model 2
    ngay_sinh           TEXT,
    cmnd_cccd           TEXT,
    chuc_danh           TEXT,
    nam_phong_chuc_danh TEXT,
    trinh_do_chuyen_mon TEXT,
    co_so_dao_tao       TEXT,
    nam_tot_nghiep      INTEGER,
    nganh_dao_tao       TEXT,
    ngay_tuyen_dung     TEXT,
    ma_so_bao_hiem      TEXT,
    so_nam_kinh_nghiem  INTEGER,
    -- NEW: Fields for Staff Info
    ma_can_bo           TEXT,
    gioi_tinh           TEXT,
    chuc_vu             TEXT,
    dia_chi             TEXT
);

CREATE TABLE IF NOT EXISTS cdr_ctdt (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ma       TEXT NOT NULL,
    mo_ta    TEXT,
    trinh_do TEXT DEFAULT 'Đại học'
);

CREATE TABLE IF NOT EXISTS hoc_phan (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    ma                   TEXT,
    ten_viet             TEXT NOT NULL,
    ten_anh              TEXT,
    trinh_do             TEXT DEFAULT 'Đại học',
    khoa_id              INTEGER REFERENCES khoa(id),
    so_tin_chi           INTEGER DEFAULT 3,
    loai                 TEXT DEFAULT 'Bắt buộc',
    tinh_chat            TEXT DEFAULT 'Hỗn hợp',
    gio_lt               INTEGER DEFAULT 0,
    gio_bt               INTEGER DEFAULT 0,
    gio_tl               INTEGER DEFAULT 0,
    gio_th_tn            INTEGER DEFAULT 0,
    gio_th               REAL DEFAULT 0,
    gio_bt_th            REAL DEFAULT 0,
    gio_kt               REAL DEFAULT 0,
    gio_tieu_luan        INTEGER DEFAULT 0,
    gio_thuc_tap         INTEGER DEFAULT 0,
    gio_tu_hoc           INTEGER DEFAULT 0,
    tong_gio             INTEGER DEFAULT 0,
    hp_tien_quyet        TEXT,
    hp_thay_the          TEXT,
    mo_ta                TEXT,
    pp_day_hoc           TEXT,
    nhiem_vu_sv_len_lop  TEXT,
    nhiem_vu_sv_bai_tap  TEXT,
    nhiem_vu_sv_dung_cu  TEXT,
    nhiem_vu_sv_khac     TEXT,
    ngay_tao             TEXT,
    ngay_cap_nhat        TEXT,
    -- New fields for Model 2
    co_thuc_hanh         INTEGER DEFAULT 1,
    dia_diem_ky          TEXT,
    ngay_ky              TEXT,
    chuc_danh_ky_trai    TEXT,
    ho_ten_ky_trai       TEXT,
    chuc_danh_ky_phai    TEXT,
    ho_ten_ky_phai       TEXT,
    nganh                TEXT,
    chuyen_nganh         TEXT,
    khoi_kien_thuc       TEXT,
    quy_dinh_hp          TEXT,
    co_so_vat_chat       TEXT,
    phu_luc              TEXT,
    trang_thai           TEXT DEFAULT 'nhap' -- FIXED: P2-1: Added to baseline schema
);

CREATE TABLE IF NOT EXISTS hp_giang_vien (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    hp_id        INTEGER REFERENCES hoc_phan(id) ON DELETE CASCADE,
    gv_id        INTEGER REFERENCES giang_vien(id),
    ho_ten       TEXT,       -- Để lưu tên nếu không link gv_id
    hoc_ham_vi   TEXT,       -- Học hàm, học vị
    don_vi       TEXT,       -- Đơn vị công tác
    email        TEXT,
    sdt          TEXT,
    vai_tro      TEXT DEFAULT 'tham_gia',
    thu_tu       INTEGER DEFAULT 1,
    -- NEW: Fields for Staff Info
    ma_can_bo    TEXT,
    gioi_tinh    TEXT,
    chuc_vu      TEXT,
    dia_chi      TEXT
);

CREATE TABLE IF NOT EXISTS muc_tieu (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    hp_id      INTEGER REFERENCES hoc_phan(id) ON DELETE CASCADE,
    so_thu_tu  INTEGER,
    mo_ta      TEXT,
    cdr_ma     TEXT,
    -- New fields
    nhom             TEXT,
    la_tieu_de_nhom  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS clo (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    hp_id INTEGER REFERENCES hoc_phan(id) ON DELETE CASCADE,
    ma    TEXT,
    mo_ta TEXT,
    cdr_ma TEXT,
    level_irm TEXT,   -- New: I/R/M
    -- New fields
    nhom             TEXT,
    la_tieu_de_nhom  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tai_lieu (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    ten               TEXT NOT NULL,
    tac_gia           TEXT,
    nam_xb            INTEGER,
    nha_xb            TEXT,
    loai              TEXT DEFAULT 'Giáo trình', -- 'Giáo trình', 'Tài liệu tham khảo', 'Khác'
    so_luong_thu_vien INTEGER DEFAULT 0,
    nuoc_xb           TEXT
);

CREATE TABLE IF NOT EXISTS hoc_lieu (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    hp_id      INTEGER REFERENCES hoc_phan(id) ON DELETE CASCADE,
    loai       TEXT,
    so_thu_tu  INTEGER,
    noi_dung   TEXT,
    tai_lieu_id INTEGER REFERENCES tai_lieu(id) -- Link to shared bank
);

CREATE TABLE IF NOT EXISTS noi_dung (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    hp_id     INTEGER REFERENCES hoc_phan(id) ON DELETE CASCADE,
    phan      TEXT DEFAULT 'lt',
    parent_id INTEGER REFERENCES noi_dung(id),
    cap_do    INTEGER DEFAULT 1,
    thu_tu    INTEGER DEFAULT 1,
    ten       TEXT,
    in_dam    INTEGER DEFAULT 0,
    gio_lt    REAL,
    gio_bt    REAL,
    gio_tl    REAL,
    gio_th_tn REAL,
    gio_th    REAL,
    gio_bt_th REAL,
    gio_kt    REAL,
    gio_tu_hoc REAL,
    yeu_cau   TEXT,
    cdr_ma    TEXT,
    -- New fields
    loai            TEXT DEFAULT 'thuong',
    pp_day          TEXT,
    pp_hoc          TEXT,
    bai_danh_gia    TEXT
);

CREATE TABLE IF NOT EXISTS ke_hoach_kiem_tra (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    hp_id           INTEGER REFERENCES hoc_phan(id) ON DELETE CASCADE,
    nhom            TEXT,
    ty_trong_nhom   REAL,
    thu_tu          INTEGER,
    noi_dung        TEXT,
    hinh_thuc       TEXT,
    thoi_gian       TEXT,
    thang_diem      REAL,
    cap_do_dap_ung  TEXT,
    clo_lien_quan   TEXT,
    ty_trong        REAL,
    tieu_chi_danh_gia TEXT,
    diem_toi_da_cdr  TEXT,
    trong_so_cdr     TEXT
);

CREATE TABLE IF NOT EXISTS lich_su_cap_nhat (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    hp_id           INTEGER REFERENCES hoc_phan(id) ON DELETE CASCADE,
    lan             INTEGER,
    noi_dung        TEXT,
    quyet_dinh      TEXT,
    nguoi_cap_nhat  TEXT,
    truong_khoa     TEXT,
    ngay_cap_nhat   TEXT
);

CREATE TABLE IF NOT EXISTS word_template (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ten         TEXT NOT NULL,
    mo_ta       TEXT,
    file_path   TEXT,
    config_json TEXT,
    la_mac_dinh INTEGER DEFAULT 0,
    ngay_tao    TEXT
);

CREATE TABLE IF NOT EXISTS rubric_danh_gia (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    hp_id       INTEGER REFERENCES hoc_phan(id) ON DELETE CASCADE,
    ten         TEXT,       -- Tên rubric, VD: "Rubric R1 - Bài tập tự luận"
    ky_hieu     TEXT,       -- Ký hiệu ngắn, VD: "R1"
    mo_ta       TEXT,       -- Mô tả ngắn
    thu_tu      INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS rubric_tieu_chi (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    rubric_id         INTEGER REFERENCES rubric_danh_gia(id) ON DELETE CASCADE,
    tieu_chi          TEXT,   -- Tên tiêu chí, VD: "Hiểu bản chất, khái niệm"
    trong_so          TEXT,   -- Trọng số, VD: "40%"
    muc_xuat_sac      TEXT,   -- Mức Xuất sắc (9.0-10)
    muc_tot           TEXT,   -- Mức Tốt (7.0-8.9)
    muc_dat           TEXT,   -- Mức Đạt (5.0-6.9)
    muc_chua_dat      TEXT,   -- Mức Chưa đạt (0-4.9)
    thu_tu            INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS chuong_trinh_dao_tao (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ten      TEXT NOT NULL,
    bac      TEXT DEFAULT 'Đại học',
    khoa_id  INTEGER REFERENCES khoa(id)
);

CREATE TABLE IF NOT EXISTS chuyen_nganh (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ctdt_id  INTEGER REFERENCES chuong_trinh_dao_tao(id) ON DELETE CASCADE,
    ten      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ctdt_hoc_phan (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ctdt_id         INTEGER REFERENCES chuong_trinh_dao_tao(id) ON DELETE CASCADE,
    hp_id           INTEGER REFERENCES hoc_phan(id) ON DELETE CASCADE,
    khoi_kien_thuc  TEXT,
    chuyen_nganh    TEXT,
    thu_tu          INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS ctdt_po (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ctdt_id  INTEGER REFERENCES chuong_trinh_dao_tao(id) ON DELETE CASCADE,
    ma       TEXT NOT NULL,
    mo_ta    TEXT
);

CREATE TABLE IF NOT EXISTS ctdt_plo (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ctdt_id  INTEGER REFERENCES chuong_trinh_dao_tao(id) ON DELETE CASCADE,
    ma       TEXT NOT NULL,
    mo_ta    TEXT
);

CREATE TABLE IF NOT EXISTS ctdt_pi (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    plo_id   INTEGER REFERENCES ctdt_plo(id) ON DELETE CASCADE,
    ma       TEXT NOT NULL,
    mo_ta    TEXT
);

CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS temp_draft (
    hp_id        INTEGER PRIMARY KEY,
    data_json    TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    expires_at   TEXT -- FIXED: P3-1: Added to baseline schema
);

CREATE TABLE IF NOT EXISTS audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    hp_id        INTEGER,
    table_name   TEXT,
    record_id    INTEGER,
    action       TEXT, -- 'UPDATE', 'INSERT', 'DELETE'
    details      TEXT, -- JSON data
    created_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_hp_ma_ten ON hoc_phan(ma, ten_viet);
CREATE INDEX IF NOT EXISTS idx_hp_tinh_chat ON hoc_phan(tinh_chat);
CREATE INDEX IF NOT EXISTS idx_hp_khoa ON hoc_phan(khoa_id);
CREATE INDEX IF NOT EXISTS idx_ctdt_hp_id ON ctdt_hoc_phan(hp_id);
CREATE INDEX IF NOT EXISTS idx_ctdt_hp_ctdt ON ctdt_hoc_phan(ctdt_id);
CREATE INDEX IF NOT EXISTS idx_ctdt_hp_khoi ON ctdt_hoc_phan(khoi_kien_thuc);
CREATE INDEX IF NOT EXISTS idx_ctdt_bac_ten ON chuong_trinh_dao_tao(bac, ten);
CREATE INDEX IF NOT EXISTS idx_ctdt_ctdt_id ON ctdt_hoc_phan(ctdt_id);
CREATE INDEX IF NOT EXISTS idx_noi_dung_hp_phan ON noi_dung(hp_id, phan);
CREATE INDEX IF NOT EXISTS idx_clo_hp ON clo(hp_id);
CREATE INDEX IF NOT EXISTS idx_muc_tieu_hp ON muc_tieu(hp_id);

-- FIXED: P2-2: Added missing indexes
CREATE INDEX IF NOT EXISTS idx_rubric_hp ON rubric_danh_gia(hp_id);
CREATE INDEX IF NOT EXISTS idx_khkt_hp ON ke_hoach_kiem_tra(hp_id);
CREATE INDEX IF NOT EXISTS idx_hpgv_hp ON hp_giang_vien(hp_id);
CREATE INDEX IF NOT EXISTS idx_lscu_hp ON lich_su_cap_nhat(hp_id);
CREATE INDEX IF NOT EXISTS idx_audit_hp ON audit_log(hp_id);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(created_at);
"""


class Database:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.conn = None # FIXED: P1-3: Duplicate self.conn = None removed
        self._lock = threading.RLock()
        self._table_columns = {} # P1-6: Cache for table columns
        self._connect()
        self._create_tables()
        self._run_migrations()
        self._init_defaults()
        self._cache = {}


        # Repositories (Lazy initialization or pre-init)
        from repositories.khoa_repository import KhoaRepository
        from repositories.giang_vien_repository import GiangVienRepository
        from repositories.hoc_phan_repository import HocPhanRepository
        from repositories.ctdt_repository import CTDTRepository
        from repositories.clo_repository import CLORepository
        from repositories.tailieu_repository import TaiLieuRepository
        from repositories.noidung_repository import NoiDungRepository
        from repositories.rubric_repository import RubricRepository

        self.khoa_repo = KhoaRepository(self)
        self.gv_repo = GiangVienRepository(self)
        self.hp_repo = HocPhanRepository(self)
        self.ctdt_repo = CTDTRepository(self)
        self.clo_repo = CLORepository(self)
        self.tailieu_repo = TaiLieuRepository(self)
        self.noidung_repo = NoiDungRepository(self)
        self.rubric_repo = RubricRepository(self)

        # P2-3: Background thread for auto_backup
        logger.info("Initializing background services...")
        t = threading.Thread(target=self.auto_backup, daemon=True)
        t.start()
        
        # P3-1: Cleanup expired drafts on startup
        self.cleanup_expired_drafts()


    def _init_defaults(self):
        """Khởi tạo các tham số hệ thống mặc định nếu chưa có."""
        defaults = {
            'clo_groups': 'Kiến thức, Kỹ năng, Mức tự chủ và trách nhiệm',
            'hp_natures': 'Lý thuyết, Thực hành, Hỗn hợp, Đồ án',
            'hp_types': 'Bắt buộc, Tự chọn',
            'trinh_do': 'Đại học, Cao đẳng, Sau đại học',
            'abbr_po': 'PO',
            'abbr_plo': 'PLO',
            'abbr_pi': 'PI',
            'abbr_mt': 'MT',
            'abbr_clo': 'CLO'
        }
        for k, v in defaults.items():
            if self.get_config(k) is None:
                self.set_config(k, v)



    # ── Section Management ────────────────────────────────────────────────────



    def _connect(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        # Đăng ký hàm unaccent để hỗ trợ tìm kiếm không dấu
        self.conn.create_function("unaccent", 1, unaccent_vietnamese)
        
        # Bật chế độ WAL để hỗ trợ đọc/ghi đồng thời tốt hơn
        try:
            self.conn.execute("PRAGMA journal_mode = WAL")
            self.conn.execute("PRAGMA synchronous = NORMAL")
            self.conn.execute("PRAGMA cache_size = -64000") # 64MB cache
            self.conn.execute("PRAGMA temp_store = MEMORY")
        except sqlite3.OperationalError:
            pass

    @contextmanager
    def transaction(self):
        """Context manager cho việc thực hiện các thao tác trong 1 transaction.
        Hỗ trợ nested transaction bằng SAVEPOINT.
        """
        import time
        with self._lock:
            # Nếu đang trong transaction, dùng SAVEPOINT
            if self.conn.in_transaction:
                sp_id = str(int(time.time() * 1000))[-6:]
                sp_name = f"nested_sp_{sp_id}"
                self.conn.execute(f"SAVEPOINT {sp_name}")
                try:
                    yield self.conn
                    self.conn.execute(f"RELEASE SAVEPOINT {sp_name}")
                except Exception as e:
                    logger.error(f"Transaction failed, rolling back to {sp_name}: {e}")
                    self.conn.execute(f"ROLLBACK TO SAVEPOINT {sp_name}")
                    raise e
            else:
                try:
                    self.conn.execute("BEGIN TRANSACTION")
                    yield self.conn
                    self.conn.commit()
                except Exception as e:
                    logger.error(f"Transaction failed, rolling back: {e}")
                    self.conn.rollback()
                    raise e

    def log_change(self, hp_id, table, field, old_val, new_val):
        """Ghi nhận thay đổi vào nhật ký hệ thống."""
        details = {
            'field': field,
            'old': old_val,
            'new': new_val
        }
        if hasattr(self, 'hp_repo'):
            self.hp_repo._log_audit("UPDATE", table, hp_id, details)

    def save_extra_data(self, hp_id, section_key, data):
        """Lưu dữ liệu bổ sung (stub)."""
        pass

    def get_config(self, key, default=None):
        """Lấy cấu hình hệ thống (từ bảng config)."""
        try:
            row = self.conn.execute("SELECT val FROM config WHERE key=?", (key,)).fetchone()
            return row[0] if row else default
        except:
            return default

    def set_config(self, key, val):
        """Lưu cấu hình hệ thống."""
        self.conn.execute("INSERT OR REPLACE INTO config (key, val) VALUES (?, ?)", (key, str(val)))
        self.conn.commit()

    def _get_schema_version(self):
        # FIXED: P2-4: Robust versioning (SELECT MAX)
        row = self.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        return row[0] if row and row[0] else 0

    def _run_migrations(self):
        from core.migrations import run_migrations
        run_migrations(self)

    def close(self):
        if self.conn:
            self.conn.close()

    def backup(self, dest_path):
        """Sao lưu file database hiện tại ra vị trí khác."""
        try:
            # Tạo thư mục nếu chưa có
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            # Dùng sqlite3 backup API để đảm bảo tính nhất quán ngay cả khi đang có người đọc
            with sqlite3.connect(dest_path) as b_conn:
                self.conn.backup(b_conn)
            return True
        except Exception as e:
            logger.error(f"Lỗi sao lưu: {e}")
            return False

    def auto_backup(self):
        """Tự động sao lưu định kỳ mỗi ngày."""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            last_backup = self.get_config('last_backup_date')

            if last_backup != today:
                backup_dir = os.path.join(os.path.dirname(self.db_path), 'backups')
                # FIXED N-05: Tạo thư mục backups nếu chưa có
                os.makedirs(backup_dir, exist_ok=True)
                backup_file = os.path.join(backup_dir, f"qlctdt_backup_{today.replace('-', '')}.db")

                if self.backup(backup_file):
                    self.set_config('last_backup_date', today)
                    print(f"Auto-backup thành công: {backup_file}")

                    # Giữ lại tối đa 7 bản backup gần nhất
                    backups = sorted(
                        [f for f in os.listdir(backup_dir) if f.startswith('qlctdt_backup_')],
                        reverse=True
                    )
                    for old_f in backups[7:]:
                        try:
                            os.remove(os.path.join(backup_dir, old_f))
                        except Exception:
                            pass
        except Exception as e:
            print(f"Lỗi auto-backup: {e}")

    # P1-6: Helper for whitelisting columns
    def _safe_fields(self, table_name: str, data: dict) -> dict:
        """Filter input dict to only include columns that exist in the database table."""
        if table_name not in self._table_columns:
            cursor = self.conn.execute(f"PRAGMA table_info({table_name})")
            self._table_columns[table_name] = [row['name'] for row in cursor.fetchall()]
        
        valid_cols = self._table_columns[table_name]
        return {k: v for k, v in data.items() if k in valid_cols}

    def _create_tables(self):
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def _clear_cache(self, prefix=None):
        if prefix:
            keys_to_del = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_del: self._cache.pop(k, None)
        else:
            self._cache.clear()

    def _get_cached(self, key, query_fn, *args):
        if key not in self._cache:
            self._cache[key] = query_fn(*args)
        return self._cache[key]

    # ------------------------------------------------------------------ KHOA
    def get_all_khoa(self):
        return self.khoa_repo.get_all()

    def add_khoa(self, ma, ten):
        return self.khoa_repo.create(ma, ten)

    def update_khoa(self, id, ma, ten):
        return self.khoa_repo.update(id, ma, ten)

    def delete_khoa(self, id):
        return self.khoa_repo.delete(id)



    def get_all_giang_vien(self):
        return self.gv_repo.get_all()

    def add_giang_vien(self, data: dict):
        return self.gv_repo.create(data)

    def update_giang_vien(self, id, data: dict):
        return self.gv_repo.update(id, data)

    def delete_giang_vien(self, id):
        return self.gv_repo.delete(id)

    def search_giang_vien(self, keyword):
        return self.gv_repo.search(keyword)



    def get_all_cdr_ctdt(self):
        return self.ctdt_repo.get_all_cdr()

    def add_cdr_ctdt(self, ma, mo_ta='', trinh_do='Đại học'):
        return self.ctdt_repo.create_cdr(ma, mo_ta, trinh_do)

    def update_cdr_ctdt(self, id, ma, mo_ta='', trinh_do='Đại học'):
        return self.ctdt_repo.update_cdr(id, ma, mo_ta, trinh_do)

    def delete_cdr_ctdt(self, id):
        return self.ctdt_repo.delete_cdr(id)


    # ------------------------------------------------------------ HOC PHAN
    def get_all_hoc_phan(self):
        return self.hp_repo.get_all()

    def get_hoc_phan(self, id):
        return self.hp_repo.get_by_id(id)

    def search_hoc_phan(self, keyword):
        return self.hp_repo.search(keyword)

    def add_hoc_phan(self, data: dict) -> int:
        return self.hp_repo.create(data)

    def update_hoc_phan(self, id, data: dict):
        return self.hp_repo.update(id, data)

    def delete_hoc_phan(self, id):
        return self.hp_repo.delete(id)



    def get_gv_of_hp(self, hp_id):
        return self.gv_repo.get_by_hp(hp_id)

    def set_gv_of_hp(self, hp_id, gv_list):
        return self.gv_repo.set_for_hp(hp_id, gv_list)

        
    # FIXED: P2-1: Status management methods
    def update_trang_thai(self, hp_id: int, trang_thai: str) -> bool:
        if trang_thai not in ('nhap', 'cho_duyet', 'da_duyet', 'can_sua'):
            return False
        with self.transaction():
            self.conn.execute("UPDATE hoc_phan SET trang_thai=? WHERE id=?", (trang_thai, hp_id))
            return True

    def get_hp_by_trang_thai(self, trang_thai: str) -> list:
        return self.conn.execute("SELECT * FROM hoc_phan WHERE trang_thai=? ORDER BY ten_viet", (trang_thai,)).fetchall()

    # ----------------------------------------------------------- MUC TIEU
    def get_muc_tieu(self, hp_id):
        return self.clo_repo.get_muc_tieu_by_hp(hp_id)

    def set_muc_tieu(self, hp_id, items):
        return self.clo_repo.set_muc_tieu_all(hp_id, items)

    def add_muc_tieu(self, hp_id, data):
        data['hp_id'] = hp_id
        return self.clo_repo.create_muc_tieu(data)


    # ------------------------------------------------------------------ CLO
    def get_clo(self, hp_id):
        return self.clo_repo.get_by_hp(hp_id)

    def set_clo(self, hp_id, items):
        return self.clo_repo.set_all(hp_id, items)

    def add_lich_su_cap_nhat(self, hp_id, data):
        data['hp_id'] = hp_id
        return self.hp_repo.add_lich_su_cap_nhat(data)

        

    # --------------------------------------------------------------- HOC LIEU
    def get_hoc_lieu(self, hp_id, loai=None):
        return self.tailieu_repo.get_by_hp(hp_id)

    def set_hoc_lieu(self, hp_id, items):
        return self.tailieu_repo.set_all(hp_id, items)



    def get_all_tai_lieu(self):
        return self.conn.execute("SELECT * FROM tai_lieu ORDER BY ten").fetchall()

    def add_tai_lieu(self, data: dict):
        with self.transaction():
            # FIXED: P1-6: Whitelisted fields
            safe_data = self._safe_fields('tai_lieu', data)
            fields = list(safe_data.keys())
            # P0: Quoting identifiers
            fields_escaped = [f"[{f}]" for f in fields]
            sql = f"INSERT INTO [tai_lieu]({','.join(fields_escaped)}) VALUES({','.join(['?']*len(fields))})"
            cur = self.conn.execute(sql, list(safe_data.values()))
            return cur.lastrowid


    def update_tai_lieu(self, id, data: dict):
        with self.transaction():
            # FIXED: P1-6: Whitelisted fields
            safe_data = self._safe_fields('tai_lieu', data)
            # P0: Quoting identifiers
            sets = ','.join(f"[{k}]=?" for k in safe_data.keys())
            self.conn.execute(f"UPDATE [tai_lieu] SET {sets} WHERE id=?", list(safe_data.values()) + [id])

        

    def delete_tai_lieu(self, id):
        with self.transaction():
            self.conn.execute("DELETE FROM tai_lieu WHERE id=?", (id,))
        

    # ----------------------------------------------------------- NOI DUNG (tree)
    def get_noi_dung(self, hp_id, phan=None):
        return self.noidung_repo.get_by_hp(hp_id, phan)

    def add_noi_dung(self, data: dict) -> int:
        return self.noidung_repo.create(data)

    def update_noi_dung(self, id, data: dict):
        return self.noidung_repo.update(id, data)

        

    def delete_noi_dung_recursive(self, id, depth=0):
        return self.noidung_repo.delete_recursive(id)

    def delete_noi_dung_hp(self, hp_id, phan):
        return self.noidung_repo.delete_by_hp(hp_id, phan)



    def get_ke_hoach_kt(self, hp_id):
        return self.hp_repo.get_ke_hoach_kt(hp_id)

    def set_ke_hoach_kt(self, hp_id, items):
        return self.hp_repo.set_ke_hoach_kt(hp_id, items)

        

    # --------------------------------------------------- LICH SU CAP NHAT
    def get_lich_su(self, hp_id):
        return self.hp_repo.get_lich_su(hp_id)

    def set_lich_su(self, hp_id, items):
        return self.hp_repo.set_lich_su(hp_id, items)


    # ------------------------------------------------------------- RUBRICS
    def get_rubric_by_hp(self, hp_id):
        return self.rubric_repo.get_by_hp(hp_id)

    def get_rubrics(self, hp_id):
        return self.rubric_repo.get_by_hp(hp_id)

    def get_rubric_tieu_chi(self, rubric_id):
        return self.rubric_repo.get_tieu_chi(rubric_id)

    def get_rubric_full(self, hp_id):
        return self.rubric_repo.get_full(hp_id)


    def set_rubrics_full(self, hp_id, rubric_list):
        """rubric_list: [{'ten','ky_hieu','mo_ta','thu_tu','tieu_chi_list':[...]}]"""
        with self.transaction():
            # Xóa cũ (Cascade sẽ xóa tiêu chí)
            self.conn.execute("DELETE FROM rubric_danh_gia WHERE hp_id=?", (hp_id,))
            for rb in rubric_list:
                cur = self.conn.execute("""
                    INSERT INTO rubric_danh_gia(hp_id, ten, ky_hieu, mo_ta, thu_tu)
                    VALUES(?,?,?,?,?)
                """, (hp_id, rb.get('ten'), rb.get('ky_hieu'), rb.get('mo_ta'), rb.get('thu_tu', 1)))
                rb_id = cur.lastrowid
                
                for tc in rb.get('tieu_chi_list', []):
                    self.conn.execute("""
                        INSERT INTO rubric_tieu_chi(rubric_id, tieu_chi, trong_so, 
                                                   muc_xuat_sac, muc_tot, muc_dat, muc_chua_dat, thu_tu)
                        VALUES(?,?,?,?,?,?,?,?)
                    """, (rb_id, tc.get('tieu_chi'), tc.get('trong_so'),
                         tc.get('muc_xuat_sac'), tc.get('muc_tot'), tc.get('muc_dat'), tc.get('muc_chua_dat'),
                         tc.get('thu_tu', 1)))
        

    # FIXED: P1-1: Restored set_rubric which was accidentally removed.
    def set_rubric(self, hp_id, items):
        """Lưu danh sách rubric (xóa cũ rồi insert mới).
        items: list of dict {ten, ky_hieu, mo_ta, thu_tu, tieu_chi_list}
        """
        with self.transaction():
            self.conn.execute("DELETE FROM rubric_danh_gia WHERE hp_id=?", (hp_id,))
            for item in items:
                cur = self.conn.execute(
                    "INSERT INTO rubric_danh_gia(hp_id,ten,ky_hieu,mo_ta,thu_tu) VALUES(?,?,?,?,?)",
                    (hp_id, item.get('ten'), item.get('ky_hieu'),
                     item.get('mo_ta'), item.get('thu_tu', 1))
                )
                rubric_id = cur.lastrowid
                for tc in item.get('tieu_chi_list', []):
                    self.conn.execute("""
                        INSERT INTO rubric_tieu_chi
                        (rubric_id,tieu_chi,trong_so,muc_xuat_sac,muc_tot,muc_dat,muc_chua_dat,thu_tu)
                        VALUES(?,?,?,?,?,?,?,?)
                    """, (
                        rubric_id, tc.get('tieu_chi'), tc.get('trong_so'),
                        tc.get('muc_xuat_sac'), tc.get('muc_tot'),
                        tc.get('muc_dat'), tc.get('muc_chua_dat'), tc.get('thu_tu', 1)
                    ))

    # --------------------------------------------------------- WORD TEMPLATE
    def get_all_templates(self):
        rows = self.conn.execute("SELECT * FROM word_template_v2 ORDER BY la_mac_dinh DESC, ten").fetchall()
        return [dict(r) for r in rows]

    def add_template(self, ten, mo_ta='', file_path='', config_json='{}', la_mac_dinh=0):
        with self.transaction():
            ngay = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur = self.conn.execute(
                "INSERT INTO word_template(ten,mo_ta,file_path,config_json,la_mac_dinh,ngay_tao)"
                " VALUES(?,?,?,?,?,?)",
                (ten, mo_ta, file_path, config_json, la_mac_dinh, ngay)
            )
        
            return cur.lastrowid

    def update_template(self, id, ten, mo_ta='', file_path='', config_json='{}', la_mac_dinh=0):
        with self.transaction():
            self.conn.execute(
                "UPDATE word_template SET ten=?,mo_ta=?,file_path=?,config_json=?,la_mac_dinh=? WHERE id=?",
                (ten, mo_ta, file_path, config_json, la_mac_dinh, id)
            )
        

    def delete_template(self, id):
        with self.transaction():
            self.conn.execute("DELETE FROM word_template WHERE id=?", (id,))
        
    # --------------------------------------------------------- CTDT
    def get_all_ctdt(self):
        def _fetch():
            return self.conn.execute("""
                SELECT c.*, k.ten AS ten_khoa
                FROM chuong_trinh_dao_tao c
                LEFT JOIN khoa k ON c.khoa_id = k.id
                ORDER BY c.bac, c.ten
            """).fetchall()
        return self._get_cached('all_ctdt', _fetch)

    def get_ctdt(self, id):
        row = self.conn.execute("""
            SELECT c.*, k.ten AS ten_khoa
            FROM chuong_trinh_dao_tao c
            LEFT JOIN khoa k ON c.khoa_id = k.id
            WHERE c.id = ?
        """, (id,)).fetchone()
        return dict(row) if row else None

    def get_ctdt_stats(self, ctdt_id):
        # Đếm số học phần
        hp_count = self.conn.execute("SELECT COUNT(*) FROM ctdt_hoc_phan WHERE ctdt_id=?", (ctdt_id,)).fetchone()[0]
        # Tính tổng tín chỉ
        tc_sum = self.conn.execute("""
            SELECT SUM(hp.so_tin_chi)
            FROM hoc_phan hp
            JOIN ctdt_hoc_phan ch ON hp.id = ch.hp_id
            WHERE ch.ctdt_id = ?
        """, (ctdt_id,)).fetchone()[0] or 0
        # Đếm PO/PLO
        po_count = self.conn.execute("SELECT COUNT(*) FROM ctdt_po WHERE ctdt_id=?", (ctdt_id,)).fetchone()[0]
        plo_count = self.conn.execute("SELECT COUNT(*) FROM ctdt_plo WHERE ctdt_id=?", (ctdt_id,)).fetchone()[0]
        
        return {
            'hp_count': hp_count,
            'tc_sum': tc_sum,
            'po_count': po_count,
            'plo_count': plo_count
        }

    def add_ctdt(self, ten, bac='Đại học', khoa_id=None):
        with self.transaction():
            cur = self.conn.execute(
                "INSERT INTO chuong_trinh_dao_tao(ten,bac,khoa_id) VALUES(?,?,?)",
                (ten, bac, khoa_id)
            )
            self._clear_cache('all_ctdt')
            return cur.lastrowid

    def update_ctdt(self, id, ten, bac, khoa_id):
        with self.transaction():
            self.conn.execute(
                "UPDATE chuong_trinh_dao_tao SET ten=?, bac=?, khoa_id=? WHERE id=?",
                (ten, bac, khoa_id, id)
            )
            self._clear_cache('all_ctdt')

    def delete_ctdt(self, id):
        with self.transaction():
            self.conn.execute("DELETE FROM chuong_trinh_dao_tao WHERE id=?", (id,))
            self._clear_cache('all_ctdt')

    # --------------------------------------------------------- CHUYÊN NGÀNH
    def get_chuyen_nganh_by_ctdt(self, ctdt_id):
        return self.conn.execute(
            "SELECT * FROM chuyen_nganh WHERE ctdt_id=? ORDER BY ten", (ctdt_id,)).fetchall()

    def add_chuyen_nganh(self, ctdt_id, ten):
        with self.transaction():
            cur = self.conn.execute("INSERT INTO chuyen_nganh(ctdt_id, ten) VALUES(?,?)", (ctdt_id, ten))
        
            return cur.lastrowid

    def update_chuyen_nganh(self, id, ten):
        with self.transaction():
            self.conn.execute("UPDATE chuyen_nganh SET ten=? WHERE id=?", (ten, id))
        

    def delete_chuyen_nganh(self, id):
        with self.transaction():
            self.conn.execute("DELETE FROM chuyen_nganh WHERE id=?", (id,))
        

    # --------------------------------------------------------- CTDT HOC PHAN
    def get_hp_of_ctdt(self, ctdt_id):
        return self.conn.execute("""
            SELECT ch.*, hp.ma, hp.ten_viet, k.ten AS khoa_quan_ly
            FROM ctdt_hoc_phan ch
            JOIN hoc_phan hp ON ch.hp_id = hp.id
            LEFT JOIN khoa k ON hp.khoa_id = k.id
            WHERE ch.ctdt_id = ?
            ORDER BY ch.khoi_kien_thuc, ch.chuyen_nganh, ch.thu_tu
        """, (ctdt_id,)).fetchall()

    def set_hp_to_ctdt(self, ctdt_id, hp_list):
        """hp_list: list of dict {hp_id, khoi_kien_thuc, chuyen_nganh, thu_tu}"""
        with self.transaction():
            self.conn.execute("DELETE FROM ctdt_hoc_phan WHERE ctdt_id=?", (ctdt_id,))
            for item in hp_list:
                self.conn.execute("""
                    INSERT INTO ctdt_hoc_phan(ctdt_id, hp_id, khoi_kien_thuc, chuyen_nganh, thu_tu)
                    VALUES(?,?,?,?,?)
                """, (ctdt_id, item['hp_id'], item.get('khoi_kien_thuc'), item.get('chuyen_nganh'), item.get('thu_tu', 1)))
        

    def get_ctdt_of_hp(self, hp_id):
        return self.conn.execute("""
            SELECT ch.*, c.ten AS ten_ctdt, c.bac
            FROM ctdt_hoc_phan ch
            JOIN chuong_trinh_dao_tao c ON ch.ctdt_id = c.id
            WHERE ch.hp_id = ?
        """, (hp_id,)).fetchall()

    def update_hp_ctdt_links(self, hp_id, ctdt_links):
        """ctdt_links: list of dict {ctdt_id, khoi_kien_thuc, chuyen_nganh}"""
        with self.transaction():
            self.conn.execute("DELETE FROM ctdt_hoc_phan WHERE hp_id=?", (hp_id,))
            for link in ctdt_links:
                self.conn.execute("""
                    INSERT INTO ctdt_hoc_phan(ctdt_id, hp_id, khoi_kien_thuc, chuyen_nganh)
                    VALUES(?,?,?,?)
                """, (link['ctdt_id'], hp_id, link.get('khoi_kien_thuc'), link.get('chuyen_nganh')))
        

    # --------------------------------------------------------- PO / PLO / PI
    def get_po_by_ctdt(self, ctdt_id):
        return self.conn.execute("SELECT * FROM ctdt_po WHERE ctdt_id=? ORDER BY ma", (ctdt_id,)).fetchall()

    def add_po(self, ctdt_id, ma, mo_ta):
        with self.transaction():
            cur = self.conn.execute("INSERT INTO ctdt_po(ctdt_id, ma, mo_ta) VALUES(?,?,?)", (ctdt_id, ma, mo_ta))
        
            return cur.lastrowid

    def update_po(self, id, ma, mo_ta):
        with self.transaction():
            self.conn.execute("UPDATE ctdt_po SET ma=?, mo_ta=? WHERE id=?", (ma, mo_ta, id))
        

    def delete_po(self, id):
        with self.transaction():
            self.conn.execute("DELETE FROM ctdt_po WHERE id=?", (id,))
        

    def get_plo_by_ctdt(self, ctdt_id):
        return self.conn.execute("SELECT * FROM ctdt_plo WHERE ctdt_id=? ORDER BY ma", (ctdt_id,)).fetchall()

    def add_plo(self, ctdt_id, ma, mo_ta):
        cur = self.conn.execute("INSERT INTO ctdt_plo(ctdt_id, ma, mo_ta) VALUES(?,?,?)", (ctdt_id, ma, mo_ta))
        self.conn.commit()
        return cur.lastrowid

    def update_plo(self, id, ma, mo_ta):
        self.conn.execute("UPDATE ctdt_plo SET ma=?, mo_ta=? WHERE id=?", (ma, mo_ta, id))
        self.conn.commit()

    def delete_plo(self, id):
        self.conn.execute("DELETE FROM ctdt_plo WHERE id=?", (id,))
        self.conn.commit()

    def get_pi_by_plo(self, plo_id):
        return self.conn.execute("SELECT * FROM ctdt_pi WHERE plo_id=? ORDER BY ma", (plo_id,)).fetchall()

    def add_pi(self, plo_id, ma, mo_ta):
        cur = self.conn.execute("INSERT INTO ctdt_pi(plo_id, ma, mo_ta) VALUES(?,?,?)", (plo_id, ma, mo_ta))
        self.conn.commit()
        return cur.lastrowid

    def update_pi(self, id, ma, mo_ta):
        self.conn.execute("UPDATE ctdt_pi SET ma=?, mo_ta=? WHERE id=?", (ma, mo_ta, id))
        self.conn.commit()

    def delete_pi(self, id):
        self.conn.execute("DELETE FROM ctdt_pi WHERE id=?", (id,))
        self.conn.commit()


    # --------------------------------------------------------- NÂNG CAO (SMART & CONVENIENCE)
    # FIXED: P3-3: Enhanced dashboard stats
    def get_dashboard_stats(self):
        """Lấy dữ liệu thống kê cho Dashboard."""
        stats = {}
        with self.transaction():
            # Tổng số học phần
            stats['total_hp'] = self.conn.execute("SELECT COUNT(*) FROM hoc_phan").fetchone()[0] or 0
            # Thống kê trạng thái
            stats['hp_by_trang_thai'] = {
                'nhap': self.conn.execute("SELECT COUNT(*) FROM hoc_phan WHERE trang_thai='nhap'").fetchone()[0] or 0,
                'cho_duyet': self.conn.execute("SELECT COUNT(*) FROM hoc_phan WHERE trang_thai='cho_duyet'").fetchone()[0] or 0,
                'da_duyet': self.conn.execute("SELECT COUNT(*) FROM hoc_phan WHERE trang_thai='da_duyet'").fetchone()[0] or 0,
                'can_sua': self.conn.execute("SELECT COUNT(*) FROM hoc_phan WHERE trang_thai='can_sua'").fetchone()[0] or 0
            }
            # Số lượng theo khoa
            rows_khoa = self.conn.execute("""
                SELECT k.ten, COUNT(hp.id) as count 
                FROM khoa k LEFT JOIN hoc_phan hp ON k.id = hp.khoa_id 
                GROUP BY k.id HAVING count > 0
            """).fetchall()
            stats['by_khoa'] = [dict(r) for r in rows_khoa]
            
            # Tổng giảng viên, CTĐT
            stats['total_gv'] = self.conn.execute("SELECT COUNT(*) FROM giang_vien").fetchone()[0] or 0
            stats['total_ctdt'] = self.conn.execute("SELECT COUNT(*) FROM chuong_trinh_dao_tao").fetchone()[0] or 0
            
            # HP thiếu dữ liệu (Danh sách chi tiết)
            rows_missing_clo = self.conn.execute("""
                SELECT id, ten_viet FROM hoc_phan WHERE id NOT IN (SELECT DISTINCT hp_id FROM clo) LIMIT 5
            """).fetchall()
            stats['hp_missing_clo'] = [dict(r) for r in rows_missing_clo]
            
            rows_missing_nd = self.conn.execute("""
                SELECT id, ten_viet FROM hoc_phan WHERE id NOT IN (SELECT DISTINCT hp_id FROM noi_dung) LIMIT 5
            """).fetchall()
            stats['hp_missing_content'] = [dict(r) for r in rows_missing_nd]
            
            stats['count_missing_clo'] = self.conn.execute("""
                SELECT COUNT(*) FROM hoc_phan WHERE id NOT IN (SELECT DISTINCT hp_id FROM clo)
            """).fetchone()[0] or 0
            stats['count_missing_content'] = self.conn.execute("""
                SELECT COUNT(*) FROM hoc_phan WHERE id NOT IN (SELECT DISTINCT hp_id FROM noi_dung)
            """).fetchone()[0] or 0
            
            # Học phần mới cập nhật
            rows_recent = self.conn.execute("""
                SELECT id, ten_viet, ma, ngay_cap_nhat 
                FROM hoc_phan ORDER BY ngay_cap_nhat DESC LIMIT 5
            """).fetchall()
            stats['recent'] = [dict(r) for r in rows_recent]
            
        return stats

    # FIXED: P2-5: Validation methods
    def validate_ke_hoach_kt(self, hp_id: int) -> dict:
        """Validate assessment weights and CLO coverage."""
        errors = []
        rows = self.get_ke_hoach_kt(hp_id)
        
        # 1. Total weight check
        tong_ty_trong = sum(float(r['ty_trong'] or 0) for r in rows)
        if abs(tong_ty_trong - 1.0) > 0.0001:
            errors.append(f"Tổng trọng số các bài đánh giá = {tong_ty_trong*100:.1f}%, cần = 100%")
            
        # 2. CLO coverage check
        clos = self.get_clo(hp_id)
        clo_codes = [c['ma'] for c in clos if not c['la_tieu_de_nhom']]
        covered_clos = set()
        for r in rows:
            if r['clo_lien_quan']:
                for code in r['clo_lien_quan'].replace(',', ' ').split():
                    covered_clos.add(code.strip())
        
        missing_clos = [c for c in clo_codes if c not in covered_clos]
        if missing_clos:
            errors.append(f"Có {len(missing_clos)} CLO chưa có bài đánh giá: {', '.join(missing_clos)}")
            
        return {
            'valid': len(errors) == 0,
            'tong_ty_trong': tong_ty_trong,
            'errors': errors
        }

    def validate_gio_hoc(self, hp_id: int) -> dict:
        """Validate content hours against credits (1 TC = 15 contact periods)."""
        hp = self.get_hoc_phan(hp_id)
        if not hp: return {'valid': False, 'errors': ['Học phần không tồn tại']}
        
        tc = int(hp.get('so_tin_chi', 3) or 3)
        tong_gio_expect = tc * 15
        
        rows = self.get_noi_dung(hp_id)
        tong_gio_nd = sum(float(r['gio_lt'] or 0) + float(r['gio_bt'] or 0) + float(r['gio_th_tn'] or 0) for r in rows)
        
        errors = []
        if tong_gio_nd != tong_gio_expect:
            errors.append(f"Tổng giờ giảng dạy (LT+BT+TH) = {tong_gio_nd}, theo tín chỉ ({tc} TC) cần = {tong_gio_expect}")
            
        return {
            'valid': len(errors) == 0,
            'tong_gio_nd': tong_gio_nd,
            'tong_gio_expect': tong_gio_expect,
            'errors': errors
        }

    def calculate_and_update_hours(self, hp_id):
        """Tính tổng giờ từ Mục 6 (noi_dung) và cập nhật vào Mục 1 (hoc_phan)."""
        res = self.conn.execute("""
            SELECT SUM(gio_lt) as lt, SUM(gio_bt) as bt, SUM(gio_tl) as tl, 
                   SUM(gio_th_tn) as th_tn, SUM(gio_th) as th, SUM(gio_bt_th) as bt_th, 
                   SUM(gio_kt) as kt, SUM(gio_tu_hoc) as tu_hoc
            FROM noi_dung WHERE hp_id = ?
        """, (hp_id,)).fetchone()
        
        if res and any(res):
            lt = res['lt'] or 0
            bt = res['bt'] or 0
            tl = res['tl'] or 0
            th_tn = res['th_tn'] or 0
            th = res['th'] or 0
            bt_th = res['bt_th'] or 0
            kt = res['kt'] or 0
            tu_hoc = res['tu_hoc'] or 0
            tong = lt + bt + tl + th_tn + th + bt_th + kt
            
            with self.transaction():
                self.conn.execute("""
                    UPDATE hoc_phan SET 
                        gio_lt=?, gio_bt=?, gio_tl=?, gio_th_tn=?, gio_th=?, 
                        gio_bt_th=?, gio_kt=?, gio_tu_hoc=?, tong_gio=?
                    WHERE id=?
                """, (lt, bt, tl, th_tn, th, bt_th, kt, tu_hoc, tong, hp_id))
            
            return True
        return False

    def clone_hoc_phan(self, hp_id):
        from repositories.hocphanrepository import HocPhanRepository
        return HocPhanRepository(self).clone(hp_id)


    def get_hp_ids_by_nature(self, nature):
        """Lấy danh sách ID học phần theo tính chất (Lý thuyết, Thực hành...)."""
        rows = self.conn.execute("SELECT id FROM hoc_phan WHERE tinh_chat = ?", (nature,)).fetchall()
        return [r['id'] for r in rows]

    # ------------------------------------------------------------- CONFIG / SETTINGS
    def get_config(self, key, default=None):
        """Lấy giá trị cấu hình từ bảng config."""
        res = self.conn.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
        return res['value'] if res else default

    def set_config(self, key, value):
        """Lưu hoặc cập nhật giá trị cấu hình."""
        with self.transaction():
            self.conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, str(value)))
        

    # ── Accuracy & Integrity (Audit Trail) ───────────────────────────────────
    # FIXED: P3-2: Structured audit log
    def log_audit(self, hp_id, table_name, field_name, old_val, new_val, action='UPDATE'):
        """Ghi lại lịch sử thay đổi dữ liệu một cách có cấu trúc."""
        try:
            with self.transaction():
                sql = """
                    INSERT INTO audit_log (hp_id, table_name, field_name, old_value, new_value, action, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                self.conn.execute(sql, (
                    hp_id, table_name, field_name, 
                    str(old_val) if old_val is not None else None, 
                    str(new_val) if new_val is not None else None,
                    action, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
        except Exception as e:
            print(f"Lỗi ghi audit_log: {e}")

    def get_audit_history(self, hp_id=None, limit=100):
        """Lấy lịch sử thay đổi."""
        if hp_id:
            return self.conn.execute(
                "SELECT * FROM audit_log WHERE hp_id=? ORDER BY updated_at DESC LIMIT ?", (hp_id, limit)
            ).fetchall()
        return self.conn.execute(
            "SELECT * FROM audit_log ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        

    # ── Auto-Save (Drafts) ──────────────────────────────────────────────────
    def save_draft(self, hp_id, data_json):
        """Lưu bản nháp với thời gian hết hạn (P3-1: 7 ngày)."""
        with self.transaction():
            now = datetime.now()
            expires = (now + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
            sql = "INSERT OR REPLACE INTO temp_draft (hp_id, data_json, updated_at, expires_at) VALUES (?, ?, ?, ?)"
            self.conn.execute(sql, (hp_id, data_json, now.strftime('%Y-%m-%d %H:%M:%S'), expires))
        
    def cleanup_expired_drafts(self):
        """Xóa các bản nháp đã quá hạn (P3-1)."""
        try:
            with self.transaction():
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.conn.execute("DELETE FROM temp_draft WHERE expires_at < ?", (now,))
        except Exception as e:
            print(f"Lỗi dọn dẹp bản nháp: {e}")
        

    def get_draft(self, hp_id):
        """Lấy bản nháp."""
        row = self.conn.execute("SELECT * FROM temp_draft WHERE hp_id = ?", (hp_id,)).fetchone()
        return dict(row) if row else None

    def delete_draft(self, hp_id):
        """Xóa bản nháp."""
        with self.transaction():
            self.conn.execute("DELETE FROM temp_draft WHERE hp_id = ?", (hp_id,))
        
    # ── Import/Export History ──────────────────────────────────────────────
    def add_import_export_log(self, type, total, success, error, details_json, user_action=''):
        """Ghi lại lịch sử nhập/xuất."""
        with self.transaction():
            self.conn.execute("""
                INSERT INTO import_export_history 
                (type, timestamp, total_files, success_count, error_count, details_json, user_action)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (type, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                  total, success, error, details_json, user_action))

    def get_import_export_history(self, limit=50):
        """Lấy danh sách lịch sử."""
        rows = self.conn.execute(
            "SELECT * FROM import_export_history ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ── ui_field_meta ──────────────────────────────────────────────────────

    def get_field_meta(self, section_key: str) -> dict:
        """
        Trả về dict {field_key: {nhan_tuy_bien, thu_tu, an_truong}}
        cho toàn bộ section. Dùng để overlay lên widget gốc.
        """
        self.conn.row_factory = sqlite3.Row
        rows = self.conn.execute(
            "SELECT field_key, nhan_tuy_bien, thu_tu, an_truong "
            "FROM ui_field_meta WHERE section_key=?",
            (section_key,)
        ).fetchall()
        return {
            r['field_key']: {
                'nhan_tuy_bien': r['nhan_tuy_bien'],
                'thu_tu': r['thu_tu'],
                'an_truong': bool(r['an_truong'])
            }
            for r in rows
        }

    # ── Legacy UI Management Removed ───────────────────────────────────────
    # All methods related to ui_sections, ui_field_meta, and ui_field_extra 
    # have been removed as part of the system cleanup.
