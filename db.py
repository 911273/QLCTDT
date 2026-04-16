# db.py — Database layer cho QLCTDT
import sqlite3
import os
import shutil
import threading
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qlctdt.db')

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    id      INTEGER PRIMARY KEY,
    version INTEGER NOT NULL,
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
    khoi_kien_thuc       TEXT
);

CREATE TABLE IF NOT EXISTS hp_giang_vien (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    hp_id   INTEGER REFERENCES hoc_phan(id) ON DELETE CASCADE,
    gv_id   INTEGER REFERENCES giang_vien(id),
    vai_tro TEXT DEFAULT 'chinh',
    thu_tu  INTEGER DEFAULT 1
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
    loai      TEXT DEFAULT 'thuong'
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
    ty_trong        REAL
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

CREATE TABLE IF NOT EXISTS temp_draft (
    hp_id        INTEGER PRIMARY KEY,
    data_json    TEXT NOT NULL,
    updated_at   TEXT NOT NULL
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
"""


class Database:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.conn = None
        self.conn = None
        self._lock = threading.Lock()
        self._connect()
        self._create_tables()
        self._run_migrations()
        self._init_defaults()
        self._cache = {}
        self.auto_backup()

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

    def _connect(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Bật chế độ WAL để hỗ trợ đọc/ghi đồng thời tốt hơn
        try:
            self.conn.execute("PRAGMA journal_mode = WAL")
        except sqlite3.OperationalError:
            pass

    @contextmanager
    def transaction(self):
        """Context manager cho việc thực hiện các thao tác trong 1 transaction."""
        with self._lock:
            try:
                # Kiểm tra if already in transaction (sqlite3 doesn't support nested transactions well)
                # but we can check if autocommit is off.
                if self.conn.in_transaction:
                    yield self.conn
                else:
                    self.conn.execute("BEGIN TRANSACTION")
                    yield self.conn
                
            except Exception as e:
                self.conn.rollback()
                raise e

    def _get_schema_version(self):
        row = self.conn.execute("SELECT version FROM schema_version WHERE id=1").fetchone()
        return row['version'] if row else 0

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
        ]
        
        for i, patch_fn in enumerate(patches):
            v_target = i + 1
            if current_v < v_target:
                print(f"Applying migration to version {v_target}...")
                with self.transaction():
                    patch_fn()
                    self.conn.execute(
                        "INSERT OR REPLACE INTO schema_version(id, version, updated_at) VALUES(1, ?, ?)",
                        (v_target, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    )
                current_v = v_target

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
                backup_file = os.path.join(backup_dir, f"qlctdt_backup_{today.replace('-','')}.db")
                
                if self.backup(backup_file):
                    self.set_config('last_backup_date', today)
                    print(f"Auto-backup thành công: {backup_file}")
                    
                    # Giữ lại tối đa 7 bản backup gần nhất
                    backups = sorted([f for f in os.listdir(backup_dir) if f.startswith('qlctdt_backup_')], reverse=True)
                    for old_f in backups[7:]:
                        try: os.remove(os.path.join(backup_dir, old_f))
                        except: pass
        except Exception as e:
            print(f"Lỗi auto-backup: {e}")

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
            fields = list(data.keys())
            sql = f"INSERT INTO giang_vien({','.join(fields)}) VALUES({','.join(['?']*len(fields))})"
            cur = self.conn.execute(sql, list(data.values()))
            self._clear_cache('all_gv')
            return cur.lastrowid

    def update_giang_vien(self, id, data: dict):
        with self.transaction():
            sets = ','.join(f"{k}=?" for k in data.keys())
            self.conn.execute(f"UPDATE giang_vien SET {sets} WHERE id=?", list(data.values()) + [id])
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
            WHERE hp.ten_viet LIKE ? OR hp.ma LIKE ? OR hp.ten_anh LIKE ?
            ORDER BY k.ten, hp.ten_viet
        """, (k, k, k)).fetchall()

    def add_hoc_phan(self, data: dict) -> int:
        with self.transaction():
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            data.setdefault('ngay_tao', now)
            data.setdefault('ngay_cap_nhat', now)
            fields = list(data.keys())
            sql = f"INSERT INTO hoc_phan({','.join(fields)}) VALUES({','.join(['?']*len(fields))})"
            cur = self.conn.execute(sql, list(data.values()))
        
            return cur.lastrowid

    def update_hoc_phan(self, id, data: dict):
        with self.transaction():
            data['ngay_cap_nhat'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            sets = ','.join(f"{k}=?" for k in data.keys())
            self.conn.execute(f"UPDATE hoc_phan SET {sets} WHERE id=?", list(data.values()) + [id])
        

    def delete_hoc_phan(self, id):
        with self.transaction():
            self.conn.execute("DELETE FROM hoc_phan WHERE id=?", (id,))
        

    # ------------------------------------------------------- HP GIANG VIEN
    def get_gv_of_hp(self, hp_id):
        return self.conn.execute("""
            SELECT hgv.id, hgv.vai_tro, hgv.thu_tu,
                   gv.id AS gv_id, gv.ho_ten, gv.hoc_vi, gv.sdt, gv.email
            FROM hp_giang_vien hgv
            JOIN giang_vien gv ON hgv.gv_id = gv.id
            WHERE hgv.hp_id=?
            ORDER BY hgv.vai_tro DESC, hgv.thu_tu
        """, (hp_id,)).fetchall()

    def set_gv_of_hp(self, hp_id, gv_list):
        """gv_list: list of dict {gv_id, vai_tro, thu_tu}"""
        with self.transaction():
            self.conn.execute("DELETE FROM hp_giang_vien WHERE hp_id=?", (hp_id,))
            for item in gv_list:
                self.conn.execute(
                    "INSERT INTO hp_giang_vien(hp_id,gv_id,vai_tro,thu_tu) VALUES(?,?,?,?)",
                    (hp_id, item['gv_id'], item.get('vai_tro', 'chinh'), item.get('thu_tu', 1))
                )
        

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
                    "INSERT INTO clo(hp_id,ma,mo_ta,cdr_ma,nhom,la_tieu_de_nhom) VALUES(?,?,?,?,?,?)",
                    (hp_id, item.get('ma'), item.get('mo_ta'), item.get('cdr_ma'),
                     item.get('nhom'), item.get('la_tieu_de_nhom', 0))
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
            fields = list(data.keys())
            sql = f"INSERT INTO tai_lieu({','.join(fields)}) VALUES({','.join(['?']*len(fields))})"
            cur = self.conn.execute(sql, list(data.values()))
        
            return cur.lastrowid

    def update_tai_lieu(self, id, data: dict):
        with self.transaction():
            sets = ','.join(f"{k}=?" for k in data.keys())
            self.conn.execute(f"UPDATE tai_lieu SET {sets} WHERE id=?", list(data.values()) + [id])
        

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
            fields = list(data.keys())
            cur = self.conn.execute(
                f"INSERT INTO noi_dung({','.join(fields)}) VALUES({','.join(['?']*len(fields))})",
                list(data.values())
            )
        
            return cur.lastrowid

    def update_noi_dung(self, id, data: dict):
        with self.transaction():
            sets = ','.join(f"{k}=?" for k in data.keys())
            self.conn.execute(f"UPDATE noi_dung SET {sets} WHERE id=?", list(data.values()) + [id])
        

    def delete_noi_dung_recursive(self, id):
        with self.transaction():
            children = self.conn.execute(
                "SELECT id FROM noi_dung WHERE parent_id=?", (id,)
            ).fetchall()
            for c in children:
                self.delete_noi_dung_recursive(c['id'])
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
                     thoi_gian,thang_diem,cap_do_dap_ung,clo_lien_quan,ty_trong)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    hp_id, item.get('nhom'), item.get('ty_trong_nhom'),
                    item.get('thu_tu'), item.get('noi_dung'), item.get('hinh_thuc'),
                    item.get('thoi_gian'), item.get('thang_diem'),
                    item.get('cap_do_dap_ung'), item.get('clo_lien_quan'), item.get('ty_trong')
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
        

    # --------------------------------------------------------- WORD TEMPLATE
    def get_all_templates(self):
        return self.conn.execute("SELECT * FROM word_template ORDER BY ten").fetchall()

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
    def get_dashboard_stats(self):
        """Lấy dữ liệu thống kê cho Dashboard."""
        stats = {}
        # Tổng số học phần
        stats['total_hp'] = self.conn.execute("SELECT COUNT(*) FROM hoc_phan").fetchone()[0]
        # Số lượng theo khoa
        stats['by_khoa'] = self.conn.execute("""
            SELECT k.ten, COUNT(hp.id) as count 
            FROM khoa k LEFT JOIN hoc_phan hp ON k.id = hp.khoa_id 
            GROUP BY k.id HAVING count > 0
        """).fetchall()
        # Học phần mới cập nhật
        stats['recent'] = self.conn.execute("""
            SELECT id, ten_viet, ma, ngay_cap_nhat 
            FROM hoc_phan ORDER BY ngay_cap_nhat DESC LIMIT 5
        """).fetchall()
        return stats

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
    def log_change(self, hp_id, table_name, field_name, old_val, new_val, action='UPDATE'):
        """Ghi lại lịch sử thay đổi dữ liệu."""
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
        

    # ── Auto-Save (Drafts) ──────────────────────────────────────────────────
    def save_draft(self, hp_id, data_json):
        """Lưu bản nháp."""
        with self.transaction():
            sql = "INSERT OR REPLACE INTO temp_draft (hp_id, data_json, updated_at) VALUES (?, ?, ?)"
            self.conn.execute(sql, (hp_id, data_json, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        

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
        return self.conn.execute(
            "SELECT * FROM import_export_history ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
