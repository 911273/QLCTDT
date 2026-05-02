# db.py — Database layer cho QLCTDT
import sqlite3
import os
import shutil
import threading
import re
from datetime import datetime, timedelta
from contextlib import contextmanager
from modules.de_cuong.seed.migrate_full import migrate_full
from modules.de_cuong.db_bridge import DCDBBridge

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

CREATE TABLE IF NOT EXISTS ui_field_data (
    hp_id       INTEGER REFERENCES hoc_phan(id) ON DELETE CASCADE,
    section_key TEXT,
    field_key   TEXT,
    gia_tri     TEXT,
    PRIMARY KEY(hp_id, section_key, field_key)
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
    so_nam_kinh_nghiem  INTEGER
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
    thu_tu       INTEGER DEFAULT 1
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
    field_name   TEXT,
    old_value    TEXT,
    new_value    TEXT,
    action       TEXT, -- 'UPDATE', 'INSERT', 'DELETE'
    updated_at   TEXT NOT NULL
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
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(updated_at);
"""


class Database:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.conn = None # FIXED: P1-3: Duplicate self.conn = None removed
        self._lock = threading.RLock()
        self._table_columns = {} # P1-6: Cache for table columns
        self._connect()
        self._create_tables()
        self._create_customization_tables(self.conn)
        self._run_migrations()
        self._init_defaults()
        self._cache = {}
        # DCDBBridge for dynamic syllabus module
        self.dc_bridge = DCDBBridge(self)

        # P2-3: Background thread for auto_backup
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
            'trinh_do': 'Đại học, Cao đẳng, Sau đại học'
        }
        for k, v in defaults.items():
            if self.get_config(k) is None:
                self.set_config(k, v)

    def _create_customization_tables(self, conn):
        """
        Bảng metadata tùy biến giao diện. Không lưu dữ liệu đề cương,
        chỉ lưu cấu hình hiển thị (label, thứ tự, ẩn/hiện) của từng trường.
        """
        conn.executescript("""
        -- Bảng Mục (Section) tùy biến
        CREATE TABLE IF NOT EXISTS ui_sections (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            section_key   TEXT NOT NULL UNIQUE, -- e.g., 'extra_sec_16'
            label         TEXT NOT NULL,
            thu_tu        INTEGER DEFAULT 999,
            an_truong     INTEGER DEFAULT 0,
            ghi_chu       TEXT DEFAULT '',
            created_at    TEXT DEFAULT (datetime('now','localtime'))
        );

        -- Metadata cho từng trường trong từng section
        -- section_key = tên file không có .py, hoặc key từ ui_sections
        CREATE TABLE IF NOT EXISTS ui_field_meta (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            section_key   TEXT NOT NULL,
            field_key     TEXT NOT NULL,
            nhan_tuy_bien TEXT DEFAULT NULL,
            thu_tu        INTEGER DEFAULT 999,
            an_truong     INTEGER DEFAULT 0,
            ghi_chu       TEXT DEFAULT '',
            updated_at    TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(section_key, field_key)
        );

        -- Trường bổ sung do người dùng tạo thêm
        CREATE TABLE IF NOT EXISTS ui_field_extra (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            section_key   TEXT NOT NULL,
            field_key     TEXT NOT NULL,
            nhan          TEXT NOT NULL,
            kieu          TEXT DEFAULT 'text',
            options_json  TEXT DEFAULT '[]',
            thu_tu        INTEGER DEFAULT 999,
            an_truong     INTEGER DEFAULT 0,
            bat_buoc      INTEGER DEFAULT 0,
            gia_tri_mac_dinh TEXT DEFAULT '',
            created_at    TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(section_key, field_key)
        );

        CREATE INDEX IF NOT EXISTS idx_uis_order ON ui_sections(thu_tu);
        CREATE INDEX IF NOT EXISTS idx_uifm_sec ON ui_field_meta(section_key);
        CREATE INDEX IF NOT EXISTS idx_uife_sec ON ui_field_extra(section_key);
        """)

    # ── Section Management ────────────────────────────────────────────────────
    def list_sections(self, include_hidden=False):
        """Lấy danh sách các Mục tùy biến."""
        where = "" if include_hidden else "WHERE an_truong = 0"
        query = f"SELECT * FROM ui_sections {where} ORDER BY thu_tu ASC"
        with self._lock:
            return [dict(r) for r in self.conn.execute(query).fetchall()]

    def add_section(self, label, section_key=None, order=999):
        """Thêm một Mục mới."""
        import uuid
        if not section_key:
            section_key = f"dynamic_sec_{uuid.uuid4().hex[:8]}"
        with self._lock:
            self.conn.execute(
                "INSERT INTO ui_sections (section_key, label, thu_tu) VALUES (?, ?, ?)",
                (section_key, label, order)
            )
            self.conn.commit()
        return section_key

    def update_section(self, section_key, **kwargs):
        """Cập nhật thông tin Mục."""
        if not kwargs: return
        fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [section_key]
        with self._lock:
            self.conn.execute(f"UPDATE ui_sections SET {fields} WHERE section_key = ?", values)
            self.conn.commit()

    def delete_section(self, section_key):
        """Xóa một Mục và tất cả dữ liệu liên quan."""
        with self._lock:
            # Xóa cấu hình trường
            self.conn.execute("DELETE FROM ui_field_extra WHERE section_key = ?", (section_key,))
            self.conn.execute("DELETE FROM ui_field_meta WHERE section_key = ?", (section_key,))
            # Xóa dữ liệu giá trị
            self.conn.execute("DELETE FROM ui_field_data WHERE section_key = ?", (section_key,))
            # Xóa chính Mục
            self.conn.execute("DELETE FROM ui_sections WHERE section_key = ?", (section_key,))
            self.conn.commit()


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
                    self.conn.execute(f"ROLLBACK TO SAVEPOINT {sp_name}")
                    raise e
            else:
                try:
                    self.conn.execute("BEGIN TRANSACTION")
                    yield self.conn
                    self.conn.commit()
                except Exception as e:
                    self.conn.rollback()
                    raise e

    def _get_schema_version(self):
        # FIXED: P2-4: Robust versioning (SELECT MAX)
        row = self.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        return row[0] if row and row[0] else 0

    def _run_migrations(self):
        """Hệ thống migration theo phiên bản schema."""
        current_v = self._get_schema_version()
        
        # Danh sách các patch (SQL hoặc hàm python)
        patches = [
            # v1: Baseline (đã bao gồm trong SCHEMA_SQL cho máy mới)
            # v2: Thêm Unique Index cho hoc_phan.ma
            self._migration_v2,
            # v3: Thêm bảng lịch sử nhập xuất
            self._migration_v3,
            # v4: Thêm 3 cột mới trong ke_hoach_kiem_tra + 2 bảng rubric
            self._migration_v4,
            # v5: Thêm email, so_dien_thoai vào gv_hoc_phan
            self._migration_v5,
            # v6: Thêm level_irm vào bảng clo
            self._migration_v6,
            # v7: Thêm quy_dinh_hp và co_so_vat_chat
            self._migration_v7,
            # v8: Thêm phu_luc vào hoc_phan
            self._migration_v8,
            # v9: Thêm pp_day, pp_hoc, bai_danh_gia vào noi_dung
            self._migration_v9,
            # P1-2: Added migrate_v2 as _migration_v10
            self._migration_v10,
            # P2-1 & P2-2: Add trang_thai + triggers + missing indexes in migration
            self._migration_v11,
            # P3-1: Add expires_at to temp_draft
            self._migration_v12,
            # Phase 1 Upgrade: Version control, Template Engine v2, cleanup indexes
            self._migration_v13,
            # Phase 2: 2026 Template Upgrades (Chính sách, Checklist, Tiến sĩ)
            self._migration_v14,
            # Phase 3: Dynamic Schema V2.0
            self._migration_v15,
        ]
        
        for i, patch_fn in enumerate(patches):
            v_target = i + 1
            if current_v < v_target:
                print(f"Applying migration to version {v_target}...")
                with self.transaction():
                    patch_fn()
                    # FIXED: P2-4: Robust versioning (INSERT instead of REPLACE with ID=1)
                    self.conn.execute(
                        "INSERT INTO schema_version(version, updated_at) VALUES(?, ?)",
                        (v_target, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    )
                current_v = v_target

        # FIXED: P1-2: Deleted rogue self.migrate_v2() call. It's now in patches[].

    def _migration_v10(self):
        """
        FIXED: P1-2 & P1-4: Refactored migrate_v2 to _migration_v10.
        Removed internal transaction block as it is now wrapped by _run_migrations.
        """
        print("Running _migration_v10 (Previously migrate_v2)...")
        try:
            # 1. Bổ sung cột cho bảng hoc_phan (HocPhan)
                cols_to_add = [
                    ('ma_hp', 'TEXT'),
                    ('don_vi_ql', 'TEXT'),
                    ('loai_hp', 'TEXT'),
                    ('loai_hinh', 'TEXT'),
                    ('hp_song_hanh', 'TEXT')
                ]
                existing_cols = [c['name'] for c in self.conn.execute("PRAGMA table_info(hoc_phan)").fetchall()]
                for col_name, col_type in cols_to_add:
                    if col_name not in existing_cols:
                        self.conn.execute(f"ALTER TABLE hoc_phan ADD COLUMN {col_name} {col_type}")
                
                # 2. Bảng GiangVien_HP
                # Fix for FK mismatch: Remove FOREIGN KEY(ma_hp) REFERENCES hoc_phan(ma)
                # because hoc_phan(ma) is not a unique constraint (it's a partial index).
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS GiangVien_HP (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ma_hp TEXT,
                        gv_id INTEGER,
                        vai_tro TEXT,
                        thu_tu INTEGER
                    )
                """)
                # Corrective step for existing tables with the broken FK
                try:
                    fk_list = self.conn.execute("PRAGMA foreign_key_list(GiangVien_HP)").fetchall()
                    if any(fk['table'] == 'hoc_phan' and fk['to'] == 'ma' for fk in fk_list):
                        print("Fixing GiangVien_HP foreign key mismatch...")
                        self.conn.execute("ALTER TABLE GiangVien_HP RENAME TO GiangVien_HP_fix")
                        self.conn.execute("""
                            CREATE TABLE GiangVien_HP (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                ma_hp TEXT,
                                gv_id INTEGER,
                                vai_tro TEXT,
                                thu_tu INTEGER
                            )
                        """)
                        self.conn.execute("INSERT INTO GiangVien_HP (id, ma_hp, gv_id, vai_tro, thu_tu) SELECT id, ma_hp, gv_id, vai_tro, thu_tu FROM GiangVien_HP_fix")
                        self.conn.execute("DROP TABLE GiangVien_HP_fix")
                except Exception as e:
                    print(f"Warning fixing GiangVien_HP: {e}")

                # 3. Bảng MucTieu_HP
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS MucTieu_HP (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ma_hp TEXT,
                        ma_mt TEXT,
                        mo_ta TEXT,
                        plo_id INTEGER,
                        thu_tu INTEGER
                    )
                """)

                # 4. Bảng CLO (Mẫu chuẩn)
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS CLO_Standard (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ma_hp TEXT,
                        ma_clo TEXT,
                        mo_ta TEXT,
                        plo_id INTEGER,
                        muc_giang_day TEXT,
                        thu_tu INTEGER
                    )
                """)

                # 5. Bảng TaiLieu (Mẫu chuẩn)
                self.conn.execute("""
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
                    )
                """)

                # 6. Bảng NoiDung_LT
                self.conn.execute("""
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
                    )
                """)

                # 7. Bảng NoiDung_TH
                self.conn.execute("""
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
                    )
                """)

                # 8. Bảng BaiDanhGia
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS BaiDanhGia (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ma_hp TEXT,
                        ma_bdg TEXT,
                        ten TEXT,
                        hinh_thuc TEXT,
                        trong_so REAL,
                        loai_bieu TEXT
                    )
                """)

                # 9. Bảng BaiDanhGia_CLO
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS BaiDanhGia_CLO (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        bdg_id INTEGER,
                        clo_id INTEGER,
                        diem_toida REAL,
                        trong_so_cr REAL
                    )
                """)

                # 10. Bảng Rubric
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS Rubric (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ma_hp TEXT,
                        ma_rubric TEXT,
                        ten TEXT,
                        clo_id INTEGER,
                        bdg_id INTEGER
                    )
                """)

                # 11. Bảng Rubric_TieuChi
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS Rubric_TieuChi (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        rubric_id INTEGER,
                        tieu_chi TEXT,
                        trong_so REAL,
                        xuat_sac TEXT,
                        tot TEXT,
                        dat TEXT,
                        chua_dat TEXT,
                        thu_tu INTEGER
                    )
                """)

                # 12. Bảng LichSu_CapNhat (Chuẩn mới)
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS LichSu_CapNhat_Standard (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ma_hp TEXT,
                        lan INTEGER,
                        noi_dung TEXT,
                        ngay TEXT,
                        nguoi_cap_nhat TEXT
                    )
                """)
                
                print("migrate_v2 completed successfully.")
        except Exception as e:
            print(f"Error in migrate_v2: {e}")

    def _migration_v11(self):
        """
        FIXED: P2-1: Added trang_thai column and triggers.
        FIXED: P2-2: Applied missing indexes to existing database.
        """
        print("Running _migration_v11 (trang_thai + indexes)...")
        try:
            # Add trang_thai column
            try:
                self.conn.execute("ALTER TABLE hoc_phan ADD COLUMN trang_thai TEXT DEFAULT 'nhap'")
            except Exception: pass
            
            # Triggers for trang_thai constraints (SQLite ALTER TABLE doesn't support CHECK)
            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS check_trang_thai_insert
                BEFORE INSERT ON hoc_phan
                BEGIN
                    SELECT CASE WHEN NEW.trang_thai NOT IN ('nhap','cho_duyet','da_duyet','can_sua')
                    THEN RAISE(ABORT, 'trang_thai không hợp lệ') END;
                END;
            """)
            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS check_trang_thai_update
                BEFORE UPDATE ON hoc_phan
                BEGIN
                    SELECT CASE WHEN NEW.trang_thai NOT IN ('nhap','cho_duyet','da_duyet','can_sua')
                    THEN RAISE(ABORT, 'trang_thai không hợp lệ') END;
                END;
            """)
            
            # Missing indexes
            idx_commands = [
                "CREATE INDEX IF NOT EXISTS idx_rubric_hp ON rubric_danh_gia(hp_id)",
                "CREATE INDEX IF NOT EXISTS idx_khkt_hp ON ke_hoach_kiem_tra(hp_id)",
                "CREATE INDEX IF NOT EXISTS idx_hpgv_hp ON hp_giang_vien(hp_id)",
                "CREATE INDEX IF NOT EXISTS idx_lscu_hp ON lich_su_cap_nhat(hp_id)",
                "CREATE INDEX IF NOT EXISTS idx_audit_hp ON audit_log(hp_id)",
                "CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(updated_at)",
                "CREATE INDEX IF NOT EXISTS idx_hocphan_trangthai ON hoc_phan(trang_thai)"
            ]
            for cmd in idx_commands:
                self.conn.execute(cmd)
                
            print("_migration_v11 completed successfully.")
        except Exception as e:
            print(f"Error in _migration_v11: {e}")

    def _migration_v12(self):
        """FIXED: P3-1: Add expires_at to temp_draft."""
        print("Running _migration_v12 (temp_draft.expires_at)...")
        try:
            self.conn.execute("ALTER TABLE temp_draft ADD COLUMN expires_at TEXT")
        except Exception: pass

    def _migration_v13(self):
        """
        Phase 1 Upgrade v2.0:
        1. Bảng phiên bản đề cương (Version Control)
        2. Bảng template Word v2 linh hoạt (cho docxtpl Engine)
        3. Bảng mapping field → placeholder
        4. Index còn thiếu để tăng tốc query
        5. Thêm cap_do_bloom vào clo
        """
        print("Running _migration_v13 (v2.0 foundation)...")
        try:
            # 1. Bảng phiên bản đề cương
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS de_cuong_version (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    hp_id       INTEGER NOT NULL REFERENCES hoc_phan(id) ON DELETE CASCADE,
                    version_no  INTEGER NOT NULL DEFAULT 1,
                    ten_phien   TEXT,
                    data_json   TEXT NOT NULL,
                    nguoi_tao   TEXT,
                    ngay_tao    TEXT DEFAULT (datetime('now','localtime')),
                    ghi_chu     TEXT
                )
            """)
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_dc_version_hp ON de_cuong_version(hp_id, version_no)"
            )

            # 2. Bảng template Word v2
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS word_template_v2 (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    ten             TEXT NOT NULL,
                    mo_ta           TEXT,
                    file_path       TEXT,
                    placeholders    TEXT,
                    la_mac_dinh     INTEGER DEFAULT 0,
                    ngay_tao        TEXT DEFAULT (datetime('now','localtime')),
                    ngay_cap_nhat   TEXT
                )
            """)

            # 3. Bảng template field mapping
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS template_field_map (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id     INTEGER REFERENCES word_template_v2(id) ON DELETE CASCADE,
                    placeholder     TEXT NOT NULL,
                    db_field        TEXT NOT NULL,
                    transform       TEXT
                )
            """)

            # 4. Index còn thiếu
            extra_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_clo_hp_id2 ON clo(hp_id)",
                "CREATE INDEX IF NOT EXISTS idx_nd_hp_phan2 ON noi_dung(hp_id, phan)",
                "CREATE INDEX IF NOT EXISTS idx_kkkt_hp_nhom ON ke_hoach_kiem_tra(hp_id, nhom)",
                "CREATE INDEX IF NOT EXISTS idx_hl_hp_loai ON hoc_lieu(hp_id, loai)",
                "CREATE INDEX IF NOT EXISTS idx_hp_cap_nhat ON hoc_phan(ngay_cap_nhat DESC)",
                "CREATE INDEX IF NOT EXISTS idx_dc_ver_hp ON de_cuong_version(hp_id)",
            ]
            for idx_sql in extra_indexes:
                try:
                    self.conn.execute(idx_sql)
                except Exception:
                    pass

            # 5. Thêm cột cap_do_bloom vào clo (nếu chưa có)
            try:
                self.conn.execute("ALTER TABLE clo ADD COLUMN cap_do_bloom INTEGER DEFAULT 1")
            except Exception:
                pass

            print("_migration_v13 completed.")
        except Exception as e:
            print(f"Error in _migration_v13: {e}")

    def _migration_v14(self):
        """
        Nâng cấp cấu trúc chuẩn ĐCCTHP 2026:
        1. Bảng chinh_sach_hoc_phan (AI, Liêm chính)
        2. Bảng checklist_tu_kiem_tra
        3. Cập nhật nhóm học phần, điểm tối thiểu đạt, nhiệm vụ NCS
        """
        print("Running _migration_v14 (DCCTHP 2026 Upgrade)...")
        try:
            # 1. Bảng chính sách học phần
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS chinh_sach_hoc_phan (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hp_id INTEGER NOT NULL REFERENCES hoc_phan(id) ON DELETE CASCADE,
                    liem_chinh_ht TEXT,
                    su_dung_ai TEXT
                )
            """)
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_cshp_hp_id ON chinh_sach_hoc_phan(hp_id)")

            # 2. Bảng Checklist Tự Kiểm Tra (Wizard Touch)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS checklist_tu_kiem_tra (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hp_id INTEGER NOT NULL REFERENCES hoc_phan(id) ON DELETE CASCADE,
                    hinh_thuc INTEGER DEFAULT 0,
                    clo_bloom INTEGER DEFAULT 0,
                    gio_tu_hoc INTEGER DEFAULT 0,
                    rubric_match INTEGER DEFAULT 0,
                    giang_vien_xn INTEGER DEFAULT 0,
                    ghi_chu TEXT
                )
            """)
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_chk_hp_id ON checklist_tu_kiem_tra(hp_id)")

            # 3. Các cột mở rộng
            cols_to_add = [
                ("hoc_phan", "nhom_hp_dac_thu", "TEXT DEFAULT 'Thông thường'"),
                ("ke_hoach_kiem_tra", "diem_toi_thieu_dat", "REAL DEFAULT 0.0"),
                ("noi_dung", "nhiem_vu_ncs", "TEXT")
            ]
            for tbl, col, typ in cols_to_add:
                try:
                    self.conn.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {typ}")
                except Exception:
                    pass
            
            print("_migration_v14 completed.")
        except Exception as e:
            print(f"Error in _migration_v14: {e}")

    def _migration_v15(self):
        """Khởi tạo cấu trúc bảng Dynamic Syllabus (DCCTHP)."""
        print("Running _migration_v15 (Dynamic Schema)...")
        try:
            migrate_full(self.conn)
            print("_migration_v15 completed.")
        except Exception as e:
            print(f"Error in _migration_v15: {e}")

    def _migration_v2(self):
        """Thêm UNIQUE INDEX cho hoc_phan.ma and cleanup duplicates if any."""
        # 1. Kiểm tra xem có trùng mã không
        dups = self.conn.execute("""
            SELECT ma, COUNT(*) as c FROM hoc_phan 
            WHERE ma IS NOT NULL AND ma != '' 
            GROUP BY ma HAVING c > 1
        """).fetchall()
        
        if dups:
            print(f"Warning: Found duplicate course codes. Cleaning up before applying unique constraint...")
            for d in dups:
                print(f" - Duplicate code: {d['ma']} ({d['c']} instances)")
                # Logic: Giữ lại bản ghi ID lớn nhất (mới nhất), xóa các bản còn lại
                # Hoặc chỉ đơn giản là null mã của các bản cũ.
                # Ở đây ta sẽ null mã của các bản ghi cũ để tránh mất data chính.
                self.conn.execute("""
                    UPDATE hoc_phan SET ma = NULL 
                    WHERE ma = ? AND id NOT IN (SELECT MAX(id) FROM hoc_phan WHERE ma = ?)
                """, (d['ma'], d['ma']))
        
        # 2. Tạo Unique Index
        # Lưu ý: SQLite không cho ALTER ADD UNIQUE, nhưng có thể dùng CREATE UNIQUE INDEX
        self.conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_hp_ma_unique ON hoc_phan(ma) WHERE ma IS NOT NULL AND ma != ''")

    def _migration_v3(self):
        """Thêm bảng lịch sử nhập xuất."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS import_export_history (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                type         TEXT NOT NULL, -- 'IMPORT', 'EXPORT'
                timestamp    TEXT NOT NULL,
                total_files  INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                error_count  INTEGER DEFAULT 0,
                details_json TEXT,
                user_action  TEXT
            )
        """)

    def _migration_v4(self):
        """Thêm 3 cột mới vào ke_hoach_kiem_tra + 2 bảng Rubric (mẫu DCCTHP mới)."""
        # 1. Thêm cột tiêu_chi_danh_gia
        try:
            self.conn.execute("ALTER TABLE ke_hoach_kiem_tra ADD COLUMN tieu_chi_danh_gia TEXT")
        except Exception:
            pass  # Cột đã tồn tại
        # 2. Thêm cột diem_toi_da_cdr
        try:
            self.conn.execute("ALTER TABLE ke_hoach_kiem_tra ADD COLUMN diem_toi_da_cdr TEXT")
        except Exception:
            pass
        # 3. Thêm cột trong_so_cdr
        try:
            self.conn.execute("ALTER TABLE ke_hoach_kiem_tra ADD COLUMN trong_so_cdr TEXT")
        except Exception:
            pass
        # 4. Tạo bảng rubric_danh_gia
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS rubric_danh_gia (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                hp_id   INTEGER REFERENCES hoc_phan(id) ON DELETE CASCADE,
                ten     TEXT,
                ky_hieu TEXT,
                mo_ta   TEXT,
                thu_tu  INTEGER DEFAULT 1
            )
        """)
        # 5. Tạo bảng rubric_tieu_chi
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS rubric_tieu_chi (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                rubric_id     INTEGER REFERENCES rubric_danh_gia(id) ON DELETE CASCADE,
                tieu_chi      TEXT,
                trong_so      TEXT,
                muc_xuat_sac  TEXT,
                muc_tot       TEXT,
                muc_dat       TEXT,
                muc_chua_dat  TEXT,
                thu_tu        INTEGER DEFAULT 1
            )
        """)

    def _migration_v5(self):
        """Thêm các cột thông tin chi tiết vào hp_giang_vien."""
        cols = ['ho_ten', 'hoc_ham_vi', 'don_vi', 'email', 'sdt']
        for col in cols:
            try:
                self.conn.execute(f"ALTER TABLE hp_giang_vien ADD COLUMN {col} TEXT")
            except Exception:
                pass

    def _migration_v6(self):
        """Thêm level_irm vào bảng clo."""
        try:
            self.conn.execute("ALTER TABLE clo ADD COLUMN level_irm TEXT DEFAULT 'I'")
        except Exception:
            pass

    def _migration_v7(self):
        """Thêm quy_dinh_hp và co_so_vat_chat."""
        for col in [("quy_dinh_hp", "TEXT"), ("co_so_vat_chat", "TEXT")]:
            try:
                self.conn.execute(f"ALTER TABLE hoc_phan ADD COLUMN {col[0]} {col[1]}")
            except Exception:
                pass

    def _migration_v8(self):
        """Thêm phu_luc vào hoc_phan."""
        try:
            self.conn.execute("ALTER TABLE hoc_phan ADD COLUMN phu_luc TEXT")
        except Exception:
            pass

    def _migration_v9(self):
        """Thêm pp_day, pp_hoc, bai_danh_gia vào bảng noi_dung."""
        columns = [c['name'] for c in self.conn.execute("PRAGMA table_info(noi_dung)").fetchall()]
        if 'pp_day' not in columns:
            self.conn.execute("ALTER TABLE noi_dung ADD COLUMN pp_day TEXT")
        if 'pp_hoc' not in columns:
            self.conn.execute("ALTER TABLE noi_dung ADD COLUMN pp_hoc TEXT")
        if 'bai_danh_gia' not in columns:
            self.conn.execute("ALTER TABLE noi_dung ADD COLUMN bai_danh_gia TEXT")

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
            print(f"Lỗi sao lưu: {e}")
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
        return self._get_cached('all_khoa', lambda: self.conn.execute("SELECT * FROM khoa ORDER BY ten").fetchall())

    def add_khoa(self, ma, ten):
        with self.transaction():
            cur = self.conn.execute("INSERT INTO khoa(ma,ten) VALUES(?,?)", (ma, ten))
            self._clear_cache('all_khoa')
            return cur.lastrowid

    def update_khoa(self, id, ma, ten):
        with self.transaction():
            self.conn.execute("UPDATE khoa SET ma=?,ten=? WHERE id=?", (ma, ten, id))
            self._clear_cache('all_khoa')

    def delete_khoa(self, id):
        with self.transaction():
            self.conn.execute("DELETE FROM khoa WHERE id=?", (id,))
            self._clear_cache('all_khoa')

    # ------------------------------------------------------------ GIANG VIEN
    def get_all_giang_vien(self):
        def _fetch():
            return self.conn.execute("""
                SELECT gv.*, k.ten AS ten_khoa
                FROM giang_vien gv
                LEFT JOIN khoa k ON gv.khoa_id = k.id
                ORDER BY gv.ho_ten
            """).fetchall()
        return self._get_cached('all_gv', _fetch)

    def add_giang_vien(self, data: dict):
        with self.transaction():
            # FIXED: P1-6: Whitelisted fields
            safe_data = self._safe_fields('giang_vien', data)
            fields = list(safe_data.keys())
            sql = f"INSERT INTO giang_vien({','.join(fields)}) VALUES({','.join(['?']*len(fields))})"
            cur = self.conn.execute(sql, list(safe_data.values()))
            self._clear_cache('all_gv')
            return cur.lastrowid

    def update_giang_vien(self, id, data: dict):
        with self.transaction():
            # FIXED: P1-6: Whitelisted fields
            safe_data = self._safe_fields('giang_vien', data)
            sets = ','.join(f"{k}=?" for k in safe_data.keys())
            self.conn.execute(f"UPDATE giang_vien SET {sets} WHERE id=?", list(safe_data.values()) + [id])
            self._clear_cache('all_gv')

    def delete_giang_vien(self, id):
        with self.transaction():
            self.conn.execute("DELETE FROM giang_vien WHERE id=?", (id,))
            self._clear_cache('all_gv')

    def search_giang_vien(self, keyword):
        k = f"%{keyword}%"
        return self.conn.execute(
            "SELECT * FROM giang_vien WHERE ho_ten LIKE ? OR email LIKE ? ORDER BY ho_ten",
            (k, k)
        ).fetchall()

    # ------------------------------------------------------------ CDR CTDT
    def get_all_cdr_ctdt(self):
        return self._get_cached('all_cdr_ctdt', lambda: self.conn.execute("SELECT * FROM cdr_ctdt ORDER BY ma").fetchall())

    def add_cdr_ctdt(self, ma, mo_ta='', trinh_do='Đại học'):
        with self.transaction():
            cur = self.conn.execute(
                "INSERT INTO cdr_ctdt(ma,mo_ta,trinh_do) VALUES(?,?,?)",
                (ma, mo_ta, trinh_do)
            )
            self._clear_cache('all_cdr_ctdt')
            return cur.lastrowid

    def update_cdr_ctdt(self, id, ma, mo_ta='', trinh_do='Đại học'):
        with self.transaction():
            self.conn.execute(
                "UPDATE cdr_ctdt SET ma=?,mo_ta=?,trinh_do=? WHERE id=?",
                (ma, mo_ta, trinh_do, id)
            )
            self._clear_cache('all_cdr_ctdt')

    def delete_cdr_ctdt(self, id):
        with self.transaction():
            self.conn.execute("DELETE FROM cdr_ctdt WHERE id=?", (id,))
            self._clear_cache('all_cdr_ctdt')

    # ------------------------------------------------------------ HOC PHAN
    def get_all_hoc_phan(self):
        return self.conn.execute("""
            SELECT hp.*, k.ten AS ten_khoa
            FROM hoc_phan hp
            LEFT JOIN khoa k ON hp.khoa_id = k.id
            ORDER BY k.ten, hp.ten_viet
        """).fetchall()

    def get_hoc_phan(self, id):
        hp = self.conn.execute("""
            SELECT hp.*, k.ten AS ten_khoa
            FROM hoc_phan hp
            LEFT JOIN khoa k ON hp.khoa_id = k.id
            WHERE hp.id=?
        """, (id,)).fetchone()
        return dict(hp) if hp else None

    def search_hoc_phan(self, keyword):
        k = f"%{keyword}%"
        return self.conn.execute("""
            SELECT hp.*, k.ten AS ten_khoa
            FROM hoc_phan hp
            LEFT JOIN khoa k ON hp.khoa_id = k.id
            WHERE unaccent(hp.ten_viet) LIKE unaccent(?) 
               OR unaccent(hp.ma) LIKE unaccent(?) 
               OR unaccent(hp.ten_anh) LIKE unaccent(?)
            ORDER BY k.ten, hp.ten_viet
        """, (k, k, k)).fetchall()

    def add_hoc_phan(self, data: dict) -> int:
        with self.transaction():
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            data.setdefault('ngay_tao', now)
            data.setdefault('ngay_cap_nhat', now)
            # FIXED: P1-6: Whitelisted fields
            safe_data = self._safe_fields('hoc_phan', data)
            fields = list(safe_data.keys())
            sql = f"INSERT INTO hoc_phan({','.join(fields)}) VALUES({','.join(['?']*len(fields))})"
            cur = self.conn.execute(sql, list(safe_data.values()))
        
            return cur.lastrowid

    def update_hoc_phan(self, id, data: dict):
        with self.transaction():
            data['ngay_cap_nhat'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # FIXED: P2-6: Auto calculation of tong_gio
            gio_fields = ['gio_lt', 'gio_bt', 'gio_tl', 'gio_th_tn', 'gio_th', 'gio_bt_th',
                          'gio_kt', 'gio_tieu_luan', 'gio_thuc_tap', 'gio_tu_hoc']
            
            if any(f in data for f in gio_fields):
                hp_current = self.get_hoc_phan(id)
                if hp_current:
                    merged = {**{f: hp_current.get(f, 0) or 0 for f in gio_fields}, 
                              **{k: v for k, v in data.items() if k in gio_fields}}
                    data['tong_gio'] = sum(float(merged[f]) for f in gio_fields)

            # FIXED: P1-6: Whitelisted fields
            safe_data = self._safe_fields('hoc_phan', data)
            sets = ','.join(f"{k}=?" for k in safe_data.keys())
            self.conn.execute(f"UPDATE hoc_phan SET {sets} WHERE id=?", list(safe_data.values()) + [id])
        

    def delete_hoc_phan(self, id):
        with self.transaction():
            self.conn.execute("DELETE FROM hoc_phan WHERE id=?", (id,))
        

    # ------------------------------------------------------- HP GIANG VIEN
    def get_gv_of_hp(self, hp_id):
        return self.conn.execute("""
            SELECT hgv.*, gv.id AS master_gv_id
            FROM hp_giang_vien hgv
            LEFT JOIN giang_vien gv ON hgv.gv_id = gv.id
            WHERE hgv.hp_id=?
            ORDER BY hgv.thu_tu, hgv.vai_tro DESC
        """, (hp_id,)).fetchall()

    def set_gv_of_hp(self, hp_id, gv_list):
        """gv_list: list of dict {gv_id, ho_ten, hoc_ham_vi, don_vi, email, sdt, vai_tro, thu_tu}"""
        with self.transaction():
            self.conn.execute("DELETE FROM hp_giang_vien WHERE hp_id=?", (hp_id,))
            for item in gv_list:
                self.conn.execute("""
                    INSERT INTO hp_giang_vien(hp_id, gv_id, ho_ten, hoc_ham_vi, don_vi, email, sdt, vai_tro, thu_tu)
                    VALUES(?,?,?,?,?,?,?,?,?)
                """, (hp_id, item.get('gv_id'), item.get('ho_ten'), item.get('hoc_ham_vi'),
                     item.get('don_vi'), item.get('email'), item.get('sdt'),
                      item.get('vai_tro', 'tham_gia'), item.get('thu_tu', 1)))
        
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
        return self.conn.execute(
            "SELECT * FROM muc_tieu WHERE hp_id=? ORDER BY so_thu_tu", (hp_id,)
        ).fetchall()

    def set_muc_tieu(self, hp_id, items):
        with self.transaction():
            self.conn.execute("DELETE FROM muc_tieu WHERE hp_id=?", (hp_id,))
            for item in items:
                self.conn.execute(
                    "INSERT INTO muc_tieu(hp_id,so_thu_tu,mo_ta,cdr_ma,nhom,la_tieu_de_nhom) VALUES(?,?,?,?,?,?)",
                    (hp_id, item.get('so_thu_tu'), item.get('mo_ta'), item.get('cdr_ma'),
                     item.get('nhom'), item.get('la_tieu_de_nhom', 0))
                )
    def add_muc_tieu(self, hp_id, data):
        with self.transaction():
            self.conn.execute(
                "INSERT INTO muc_tieu(hp_id,so_thu_tu,mo_ta,cdr_ma,nhom,la_tieu_de_nhom) VALUES(?,?,?,?,?,?)",
                (hp_id, data.get('so_thu_tu'), data.get('mo_ta'), data.get('cdr_ma'),
                 data.get('nhom'), data.get('la_tieu_de_nhom', 0))
            )

    # ------------------------------------------------------------------ CLO
    def get_clo(self, hp_id):
        return self.conn.execute(
            "SELECT * FROM clo WHERE hp_id=? ORDER BY id", (hp_id,)
        ).fetchall()

    def set_clo(self, hp_id, items):
        with self.transaction():
            self.conn.execute("DELETE FROM clo WHERE hp_id=?", (hp_id,))
            for item in items:
                self.conn.execute(
                    "INSERT INTO clo(hp_id,ma,mo_ta,cdr_ma,level_irm,nhom,la_tieu_de_nhom) VALUES(?,?,?,?,?,?,?)",
                    (hp_id, item.get('ma'), item.get('mo_ta'), item.get('cdr_ma'),
                     item.get('level_irm'), item.get('nhom'), item.get('la_tieu_de_nhom', 0))
                )

    def add_lich_su_cap_nhat(self, hp_id, data):
        with self.transaction():
            self.conn.execute(
                "INSERT INTO lich_su_cap_nhat(hp_id,lan,noi_dung,nguoi_cap_nhat,ngay_cap_nhat) VALUES(?,?,?,?,?)",
                (hp_id, data.get('lan'), data.get('noi_dung'), data.get('nguoi_cap_nhat'), data.get('ngay_cap_nhat'))
            )
        

    # --------------------------------------------------------------- HOC LIEU
    def get_hoc_lieu(self, hp_id, loai=None):
        if loai:
             return self.conn.execute("""
                SELECT hl.*, tl.ten, tl.tac_gia, tl.nam_xb, tl.nha_xb, tl.loai AS tl_loai
                FROM hoc_lieu hl
                LEFT JOIN tai_lieu tl ON hl.tai_lieu_id = tl.id
                WHERE hl.hp_id=? AND hl.loai=?
                ORDER BY hl.so_thu_tu
            """, (hp_id, loai)).fetchall()
        return self.conn.execute("""
            SELECT hl.*, tl.ten, tl.tac_gia, tl.nam_xb, tl.nha_xb, tl.loai AS tl_loai
            FROM hoc_lieu hl
            LEFT JOIN tai_lieu tl ON hl.tai_lieu_id = tl.id
            WHERE hl.hp_id=?
            ORDER BY hl.loai, hl.so_thu_tu
        """, (hp_id,)).fetchall()

    def set_hoc_lieu(self, hp_id, items):
        with self.transaction():
            self.conn.execute("DELETE FROM hoc_lieu WHERE hp_id=?", (hp_id,))
            for item in items:
                self.conn.execute(
                    "INSERT INTO hoc_lieu(hp_id,loai,so_thu_tu,noi_dung,tai_lieu_id) VALUES(?,?,?,?,?)",
                    (hp_id, item.get('loai'), item.get('so_thu_tu'), item.get('noi_dung'), item.get('tai_lieu_id'))
                )
        

    # --------------------------------------------------------------- TAI LIEU BANK
    def get_all_tai_lieu(self):
        return self.conn.execute("SELECT * FROM tai_lieu ORDER BY ten").fetchall()

    def add_tai_lieu(self, data: dict):
        with self.transaction():
            # FIXED: P1-6: Whitelisted fields
            safe_data = self._safe_fields('tai_lieu', data)
            fields = list(safe_data.keys())
            sql = f"INSERT INTO tai_lieu({','.join(fields)}) VALUES({','.join(['?']*len(fields))})"
            cur = self.conn.execute(sql, list(safe_data.values()))
        
            return cur.lastrowid

    def update_tai_lieu(self, id, data: dict):
        with self.transaction():
            # FIXED: P1-6: Whitelisted fields
            safe_data = self._safe_fields('tai_lieu', data)
            sets = ','.join(f"{k}=?" for k in safe_data.keys())
            self.conn.execute(f"UPDATE tai_lieu SET {sets} WHERE id=?", list(safe_data.values()) + [id])
        

    def delete_tai_lieu(self, id):
        with self.transaction():
            self.conn.execute("DELETE FROM tai_lieu WHERE id=?", (id,))
        

    # ----------------------------------------------------------- NOI DUNG (tree)
    def get_noi_dung(self, hp_id, phan=None):
        if phan:
            return self.conn.execute(
                "SELECT * FROM noi_dung WHERE hp_id=? AND phan=? ORDER BY thu_tu", (hp_id, phan)
            ).fetchall()
        return self.conn.execute(
            "SELECT * FROM noi_dung WHERE hp_id=? ORDER BY phan, thu_tu", (hp_id,)
        ).fetchall()

    def add_noi_dung(self, data: dict) -> int:
        with self.transaction():
            # FIXED: P1-6: Whitelisted fields
            safe_data = self._safe_fields('noi_dung', data)
            fields = list(safe_data.keys())
            cur = self.conn.execute(
                f"INSERT INTO noi_dung({','.join(fields)}) VALUES({','.join(['?']*len(fields))})",
                list(safe_data.values())
            )
        
            return cur.lastrowid

    def update_noi_dung(self, id, data: dict):
        with self.transaction():
            # FIXED: P1-6: Whitelisted fields
            safe_data = self._safe_fields('noi_dung', data)
            sets = ','.join(f"{k}=?" for k in safe_data.keys())
            self.conn.execute(f"UPDATE noi_dung SET {sets} WHERE id=?", list(safe_data.values()) + [id])
        

    def delete_noi_dung_recursive(self, id, depth=0):
        # FIXED: P1-5: Guard recursion depth
        MAX_DEPTH = 50
        if depth >= MAX_DEPTH:
            raise ValueError("Cây nội dung quá sâu hoặc có vòng lặp")
            
        with self.transaction():
            children = self.conn.execute(
                "SELECT id FROM noi_dung WHERE parent_id=?", (id,)
            ).fetchall()
            for c in children:
                self.delete_noi_dung_recursive(c['id'], depth + 1)
            self.conn.execute("DELETE FROM noi_dung WHERE id=?", (id,))
        

    def delete_noi_dung_hp(self, hp_id, phan):
        with self.transaction():
            self.conn.execute(
                "DELETE FROM noi_dung WHERE hp_id=? AND phan=?", (hp_id, phan)
            )
        

    # ---------------------------------------------------- KE HOACH KIEM TRA
    def get_ke_hoach_kt(self, hp_id):
        return self.conn.execute(
            "SELECT * FROM ke_hoach_kiem_tra WHERE hp_id=? ORDER BY nhom, thu_tu", (hp_id,)
        ).fetchall()

    def set_ke_hoach_kt(self, hp_id, items):
        with self.transaction():
            self.conn.execute("DELETE FROM ke_hoach_kiem_tra WHERE hp_id=?", (hp_id,))
            for item in items:
                self.conn.execute("""
                    INSERT INTO ke_hoach_kiem_tra
                    (hp_id,nhom,ty_trong_nhom,thu_tu,noi_dung,hinh_thuc,
                     thoi_gian,thang_diem,cap_do_dap_ung,clo_lien_quan,ty_trong,
                     tieu_chi_danh_gia,diem_toi_da_cdr,trong_so_cdr)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    hp_id, item.get('nhom'), item.get('ty_trong_nhom'),
                    item.get('thu_tu'), item.get('noi_dung'), item.get('hinh_thuc'),
                    item.get('thoi_gian'), item.get('thang_diem'),
                    item.get('cap_do_dap_ung'), item.get('clo_lien_quan'), item.get('ty_trong'),
                    item.get('tieu_chi_danh_gia'), item.get('diem_toi_da_cdr'), item.get('trong_so_cdr')
                ))
        

    # --------------------------------------------------- LICH SU CAP NHAT
    def get_lich_su(self, hp_id):
        return self.conn.execute(
            "SELECT * FROM lich_su_cap_nhat WHERE hp_id=? ORDER BY lan", (hp_id,)
        ).fetchall()

    def set_lich_su(self, hp_id, items):
        with self.transaction():
            self.conn.execute("DELETE FROM lich_su_cap_nhat WHERE hp_id=?", (hp_id,))
            for item in items:
                self.conn.execute("""
                    INSERT INTO lich_su_cap_nhat
                    (hp_id,lan,noi_dung,quyet_dinh,nguoi_cap_nhat,truong_khoa,ngay_cap_nhat)
                    VALUES(?,?,?,?,?,?,?)
                """, (
                    hp_id, item.get('lan'), item.get('noi_dung'),
                    item.get('quyet_dinh'), item.get('nguoi_cap_nhat'),
                    item.get('truong_khoa'), item.get('ngay_cap_nhat')
                ))

    # ------------------------------------------------------------- RUBRICS
    def get_rubric_by_hp(self, hp_id):
        """FIXED: Restored original name expected by UI."""
        return self.conn.execute(
            "SELECT * FROM rubric_danh_gia WHERE hp_id=? ORDER BY thu_tu", (hp_id,)
        ).fetchall()

    def get_rubrics(self, hp_id):
        """Alias for compatibility."""
        return self.get_rubric_by_hp(hp_id)

    def get_rubric_tieu_chi(self, rubric_id):
        return self.conn.execute(
            "SELECT * FROM rubric_tieu_chi WHERE rubric_id=? ORDER BY thu_tu", (rubric_id,)
        ).fetchall()

    def get_rubric_full(self, hp_id):
        """Lấy toàn bộ rubric và tiêu chí của 1 HP."""
        rubrics = self.get_rubrics(hp_id)
        res = []
        for r in rubrics:
            rd = dict(r)
            rd['tieu_chi_list'] = [dict(tc) for tc in self.get_rubric_tieu_chi(r['id'])]
            res.append(rd)
        return res

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
        """Sao chép toàn bộ đề cương học phần, xử lý đệ quy cho nội dung chi tiết."""
        # 1. Lấy dữ liệu học phần gốc
        old_hp_row = self.conn.execute("SELECT * FROM hoc_phan WHERE id=?", (hp_id,)).fetchone()
        if not old_hp_row: return None
        
        old_hp = dict(old_hp_row)
        old_hp.pop('id')
        old_hp['ten_viet'] += " (Bản sao)"
        if old_hp['ma']: old_hp['ma'] += "_copy"
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        old_hp['ngay_tao'] = now_str
        old_hp['ngay_cap_nhat'] = now_str
        
        # 2. Tạo record học phần mới
        cols = ", ".join(old_hp.keys())
        qs = ", ".join(["?"] * len(old_hp))
        cur = self.conn.execute(f"INSERT INTO hoc_phan({cols}) VALUES({qs})", list(old_hp.values()))
        new_id = cur.lastrowid
        
        # 3. Sao chép các bảng phẳng đơn giản
        def copy_simple_table(table_name, foreign_key='hp_id'):
            rows = self.conn.execute(f"SELECT * FROM {table_name} WHERE {foreign_key}=?", (hp_id,)).fetchall()
            for r in rows:
                d = dict(r)
                d.pop('id')
                d[foreign_key] = new_id
                c = ", ".join(d.keys())
                q = ", ".join(["?"] * len(d))
                self.conn.execute(f"INSERT INTO {table_name}({c}) VALUES({q})", list(d.values()))
        
        for tbl in ['muc_tieu', 'clo', 'hoc_lieu', 'ke_hoach_kiem_tra', 'hp_giang_vien', 'lich_su_cap_nhat', 'ctdt_hoc_phan']:
            copy_simple_table(tbl)
            
        # 4. Sao chép bảng NOI_DUNG (có phân cấp parent_id)
        # Lấy tất cả nội dung của HP cũ
        old_nd_rows = self.conn.execute("SELECT * FROM noi_dung WHERE hp_id=?", (hp_id,)).fetchall()
        id_map = {None: None} # mapping old_id -> new_id
        
        # Sắp xếp theo cấp độ để đảm bảo cha luôn được tạo trước con (hoặc dùng strategy mapping)
        # Cách an toàn nhất: Insert cha trước. 1 -> 2 -> 3
        sorted_rows = sorted([dict(r) for r in old_nd_rows], key=lambda x: x.get('cap_do', 1))
        
        for r in sorted_rows:
            old_nd_id = r.pop('id')
            old_parent = r['parent_id']
            r['hp_id'] = new_id
            r['parent_id'] = id_map.get(old_parent) # Lấy ID mới của cha
            
            c = ", ".join(r.keys())
            q = ", ".join(["?"] * len(r))
            new_nd_cur = self.conn.execute(f"INSERT INTO noi_dung({c}) VALUES({qs})", list(r.values()))
            id_map[old_nd_id] = new_nd_cur.lastrowid
            
        self.conn.commit()
        return new_id

    def check_duplicates(self):
        """Kiểm tra mã HP, tên HP hoặc thông tin giảng viên trùng lặp."""
        issues = []
        # 1. Trùng mã HP
        dup_ma = self.conn.execute("""
            SELECT ma, COUNT(*) as c FROM hoc_phan 
            WHERE ma IS NOT NULL AND ma != '' 
            GROUP BY ma HAVING c > 1
        """).fetchall()
        for r in dup_ma:
            issues.append(f"• Trùng mã học phần: {r['ma']} ({r['c']} lần)")

        # 2. Trùng tên HP (Tên Việt)
        dup_ten = self.conn.execute("""
            SELECT ten_viet, COUNT(*) as c FROM hoc_phan 
            GROUP BY ten_viet HAVING c > 1
        """).fetchall()
        for r in dup_ten:
            issues.append(f"• Trùng tên học phần: {r['ten_viet']} ({r['c']} bản ghi)")

        # 3. Giảng viên trùng Email hoặc SĐT nhưng khác tên (có thể là lỗi nhập liệu)
        dup_gv = self.conn.execute("""
            SELECT email, sdt, COUNT(DISTINCT ho_ten) as c FROM giang_vien 
            WHERE (email IS NOT NULL AND email != '') OR (sdt IS NOT NULL AND sdt != '')
            GROUP BY email, sdt HAVING c > 1
        """).fetchall()
        for r in dup_gv:
            contact = r['email'] or r['sdt']
            issues.append(f"• Giảng viên có cùng liên hệ ({contact}) nhưng sai lệnh họ tên.")

        return issues

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

    def set_field_label(self, section_key: str, field_key: str, nhan: str):
        """Đổi nhãn hiển thị. nhan=None để reset về nhãn gốc."""
        self.conn.execute("""
            INSERT INTO ui_field_meta(section_key, field_key, nhan_tuy_bien, updated_at)
            VALUES(?,?,?,datetime('now','localtime'))
            ON CONFLICT(section_key, field_key) DO UPDATE SET
                nhan_tuy_bien=excluded.nhan_tuy_bien,
                updated_at=excluded.updated_at
        """, (section_key, field_key, nhan))
        self._log_custom(section_key, field_key, 'rename', nhan or '')
        self.conn.commit()

    def set_field_visibility(self, section_key: str, field_key: str, an: bool):
        self.conn.execute("""
            INSERT INTO ui_field_meta(section_key, field_key, an_truong, updated_at)
            VALUES(?,?,?,datetime('now','localtime'))
            ON CONFLICT(section_key, field_key) DO UPDATE SET
                an_truong=excluded.an_truong,
                updated_at=excluded.updated_at
        """, (section_key, field_key, int(an)))
        self._log_custom(section_key, field_key, 'hide' if an else 'show', '')
        self.conn.commit()

    def set_field_order(self, section_key: str, ordered_keys: list[str]):
        """Lưu thứ tự mới cho toàn bộ trường trong section."""
        with self.conn:
            for i, key in enumerate(ordered_keys):
                self.conn.execute("""
                    INSERT INTO ui_field_meta(section_key, field_key, thu_tu, updated_at)
                    VALUES(?,?,?,datetime('now','localtime'))
                    ON CONFLICT(section_key, field_key) DO UPDATE SET
                        thu_tu=excluded.thu_tu,
                        updated_at=excluded.updated_at
                """, (section_key, key, i))
        self._log_custom(section_key, '__order__', 'move', ','.join(ordered_keys))

    def reset_field_meta(self, section_key: str, field_key: str = None):
        """Reset về cấu hình gốc. field_key=None → reset toàn bộ section."""
        if field_key:
            self.conn.execute(
                "DELETE FROM ui_field_meta WHERE section_key=? AND field_key=?",
                (section_key, field_key)
            )
        else:
            self.conn.execute(
                "DELETE FROM ui_field_meta WHERE section_key=?",
                (section_key,)
            )
        self.conn.commit()

    # ── ui_field_extra ─────────────────────────────────────────────────────

    def list_extra_fields(self, section_key: str) -> list[dict]:
        self.conn.row_factory = sqlite3.Row
        rows = self.conn.execute(
            "SELECT * FROM ui_field_extra "
            "WHERE section_key=? AND an_truong=0 ORDER BY thu_tu",
            (section_key,)
        ).fetchall()
        return [dict(r) for r in rows]

    def add_extra_field(self, section_key: str, data: dict) -> str:
        """
        Thêm trường bổ sung. Trả về field_key mới.
        data: {nhan, kieu, options_json, thu_tu, bat_buoc, gia_tri_mac_dinh}
        """
        import uuid
        fkey = f"extra_{uuid.uuid4().hex[:8]}"
        self.conn.execute("""
            INSERT INTO ui_field_extra
                (section_key, field_key, nhan, kieu, options_json,
                 thu_tu, bat_buoc, gia_tri_mac_dinh)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            section_key, fkey,
            data['nhan'], data.get('kieu','text'),
            data.get('options_json','[]'),
            data.get('thu_tu', 999),
            int(data.get('bat_buoc', 0)),
            data.get('gia_tri_mac_dinh','')
        ))
        self._log_custom(section_key, fkey, 'add', data['nhan'])
        self.conn.commit()
        return fkey

    def update_extra_field(self, field_key: str, data: dict):
        self.conn.execute("""
            UPDATE ui_field_extra SET
                nhan=?, kieu=?, options_json=?,
                bat_buoc=?, gia_tri_mac_dinh=?
            WHERE field_key=?
        """, (
            data['nhan'], data.get('kieu','text'),
            data.get('options_json','[]'),
            int(data.get('bat_buoc',0)),
            data.get('gia_tri_mac_dinh',''),
            field_key
        ))
        self.conn.commit()

    def delete_extra_field(self, section_key: str, field_key: str):
        """Xóa mềm — đặt an_truong=1 thay vì xóa hẳn."""
        self.conn.execute(
            "UPDATE ui_field_extra SET an_truong=1 WHERE field_key=?",
            (field_key,)
        )
        self._log_custom(section_key, field_key, 'delete', '')
        self.conn.commit()

    def save_extra_data(self, hp_id: int, section_key: str, data_dict: dict):
        with self.conn:
            for k, v in data_dict.items():
                if isinstance(v, (list, dict)):
                    import json
                    v = json.dumps(v, ensure_ascii=False)
                self.conn.execute("""
                    INSERT INTO ui_field_data(hp_id, section_key, field_key, gia_tri)
                    VALUES(?,?,?,?)
                    ON CONFLICT(hp_id, section_key, field_key) DO UPDATE SET gia_tri=excluded.gia_tri
                """, (hp_id, section_key, k, str(v) if v is not None else ""))

    def load_extra_data(self, hp_id: int, section_key: str) -> dict:
        rows = self.conn.execute(
            "SELECT field_key, gia_tri FROM ui_field_data WHERE hp_id=? AND section_key=?",
            (hp_id, section_key)
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    # ── Lịch sử tùy biến ───────────────────────────────────────────────────

    def _log_custom(self, section_key, field_key, hanh_dong, gia_tri_moi):
        self.conn.execute("""
            INSERT INTO ui_custom_history(section_key, field_key, hanh_dong, gia_tri_moi)
            VALUES(?,?,?,?)
        """, (section_key, field_key, hanh_dong, str(gia_tri_moi)))

    def get_custom_history(self, section_key: str, limit=50) -> list[dict]:
        self.conn.row_factory = sqlite3.Row
        rows = self.conn.execute("""
            SELECT field_key, hanh_dong, gia_tri_cu, gia_tri_moi, thoi_gian
            FROM ui_custom_history
            WHERE section_key=?
            ORDER BY id DESC LIMIT ?
        """, (section_key, limit)).fetchall()
        return [dict(r) for r in rows]
