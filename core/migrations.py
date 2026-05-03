import datetime
from datetime import datetime


def run_migrations(db):
    """Hệ thống migration theo phiên bản schema."""
    current_v = db._get_schema_version()
    
    # Danh sách các patch (SQL hoặc hàm python)
    patches = [
        # v1: Baseline (đã bao gồm trong SCHEMA_SQL cho máy mới)
        # v2: Thêm Unique Index cho hoc_phan.ma
        _migration_v2,
        # v3: Thêm bảng lịch sử nhập xuất
        _migration_v3,
        # v4: Thêm 3 cột mới trong ke_hoach_kiem_tra + 2 bảng rubric
        _migration_v4,
        # v5: Thêm email, so_dien_thoai vào gv_hoc_phan
        _migration_v5,
        # v6: Thêm level_irm vào bảng clo
        _migration_v6,
        # v7: Thêm quy_dinh_hp và co_so_vat_chat
        _migration_v7,
        # v8: Thêm phu_luc vào hoc_phan
        _migration_v8,
        # v9: Thêm pp_day, pp_hoc, bai_danh_gia vào noi_dung
        _migration_v9,
        # P1-2: Added migrate_v2 as _migration_v10
        _migration_v10,
        # P2-1 & P2-2: Add trang_thai + triggers + missing indexes in migration
        _migration_v11,
        # P3-1: Add expires_at to temp_draft
        _migration_v12,
        # Phase 1 Upgrade: Version control, Template Engine v2, cleanup indexes
        _migration_v13,
        # Phase 2: 2026 Template Upgrades (Chính sách, Checklist, Tiến sĩ)
        _migration_v14,
        # v15: Sync audit_log schema
        _migration_v15,
        # v16: Add more lecturer fields
        _migration_v16,
    ]
    
    for i, patch_fn in enumerate(patches):
        v_target = i + 1
        if current_v < v_target:
            print(f"Applying migration to version {v_target}...")
            with db.transaction():
                patch_fn(db)
                # FIXED: P2-4: Robust versioning (INSERT instead of REPLACE with ID=1)
                db.conn.execute(
                    "INSERT INTO schema_version(version, updated_at) VALUES(?, ?)",
                    (v_target, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                )
            current_v = v_target

def _migration_v10(db):
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
        existing_cols = [c['name'] for c in db.conn.execute("PRAGMA table_info(hoc_phan)").fetchall()]
        for col_name, col_type in cols_to_add:
            if col_name not in existing_cols:
                db.conn.execute(f"ALTER TABLE hoc_phan ADD COLUMN {col_name} {col_type}")
        
        # 2. Bảng GiangVien_HP
        db.conn.execute("""
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
            fk_list = db.conn.execute("PRAGMA foreign_key_list(GiangVien_HP)").fetchall()
            if any(fk['table'] == 'hoc_phan' and fk['to'] == 'ma' for fk in fk_list):
                print("Fixing GiangVien_HP foreign key mismatch...")
                db.conn.execute("ALTER TABLE GiangVien_HP RENAME TO GiangVien_HP_fix")
                db.conn.execute("""
                    CREATE TABLE GiangVien_HP (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ma_hp TEXT,
                        gv_id INTEGER,
                        vai_tro TEXT,
                        thu_tu INTEGER
                    )
                """)
                db.conn.execute("INSERT INTO GiangVien_HP (id, ma_hp, gv_id, vai_tro, thu_tu) SELECT id, ma_hp, gv_id, vai_tro, thu_tu FROM GiangVien_HP_fix")
                db.conn.execute("DROP TABLE GiangVien_HP_fix")
        except Exception as e:
            print(f"Warning fixing GiangVien_HP: {e}")

        # 3. Bảng MucTieu_HP
        db.conn.execute("""
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
        db.conn.execute("""
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
        db.conn.execute("""
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
        db.conn.execute("""
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
        db.conn.execute("""
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
        db.conn.execute("""
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
        db.conn.execute("""
            CREATE TABLE IF NOT EXISTS BaiDanhGia_CLO (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bdg_id INTEGER,
                clo_id INTEGER,
                diem_toida REAL,
                trong_so_cr REAL
            )
        """)

        # 10. Bảng Rubric
        db.conn.execute("""
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
        db.conn.execute("""
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
        db.conn.execute("""
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

def _migration_v11(db):
    """
    FIXED: P2-1: Added trang_thai column and triggers.
    FIXED: P2-2: Applied missing indexes to existing database.
    """
    print("Running _migration_v11 (trang_thai + indexes)...")
    try:
        # Add trang_thai column
        try:
            db.conn.execute("ALTER TABLE hoc_phan ADD COLUMN trang_thai TEXT DEFAULT 'nhap'")
        except Exception: pass
        
        # Triggers for trang_thai constraints (SQLite ALTER TABLE doesn't support CHECK)
        db.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS check_trang_thai_insert
            BEFORE INSERT ON hoc_phan
            BEGIN
                SELECT CASE WHEN NEW.trang_thai NOT IN ('nhap','cho_duyet','da_duyet','can_sua')
                THEN RAISE(ABORT, 'trang_thai không hợp lệ') END;
            END;
        """)
        db.conn.execute("""
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
            "CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_hocphan_trangthai ON hoc_phan(trang_thai)"
        ]
        for cmd in idx_commands:
            db.conn.execute(cmd)
            
        print("_migration_v11 completed successfully.")
    except Exception as e:
        print(f"Error in _migration_v11: {e}")

def _migration_v12(db):
    """FIXED: P3-1: Add expires_at to temp_draft."""
    print("Running _migration_v12 (temp_draft.expires_at)...")
    try:
        db.conn.execute("ALTER TABLE temp_draft ADD COLUMN expires_at TEXT")
    except Exception: pass

def _migration_v13(db):
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
        db.conn.execute("""
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
        db.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_dc_version_hp ON de_cuong_version(hp_id, version_no)"
        )

        # 2. Bảng template Word v2
        db.conn.execute("""
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
        db.conn.execute("""
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
                db.conn.execute(idx_sql)
            except Exception:
                pass

        # 5. Thêm cột cap_do_bloom vào clo (nếu chưa có)
        try:
            db.conn.execute("ALTER TABLE clo ADD COLUMN cap_do_bloom INTEGER DEFAULT 1")
        except Exception:
            pass

        print("_migration_v13 completed.")
    except Exception as e:
        print(f"Error in _migration_v13: {e}")

def _migration_v14(db):
    """
    Nâng cấp cấu trúc chuẩn ĐCCTHP 2026:
    1. Bảng chinh_sach_hoc_phan (AI, Liêm chính)
    2. Bảng checklist_tu_kiem_tra
    3. Cập nhật nhóm học phần, điểm tối thiểu đạt, nhiệm vụ NCS
    """
    print("Running _migration_v14 (DCCTHP 2026 Upgrade)...")
    try:
        # 1. Bảng chính sách học phần
        db.conn.execute("""
            CREATE TABLE IF NOT EXISTS chinh_sach_hoc_phan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hp_id INTEGER NOT NULL REFERENCES hoc_phan(id) ON DELETE CASCADE,
                liem_chinh_ht TEXT,
                su_dung_ai TEXT
            )
        """)
        db.conn.execute("CREATE INDEX IF NOT EXISTS idx_cshp_hp_id ON chinh_sach_hoc_phan(hp_id)")

        # 2. Bảng Checklist Tự Kiểm Tra (Wizard Touch)
        db.conn.execute("""
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
        db.conn.execute("CREATE INDEX IF NOT EXISTS idx_chk_hp_id ON checklist_tu_kiem_tra(hp_id)")

        # 3. Các cột mở rộng
        cols_to_add = [
            ("hoc_phan", "nhom_hp_dac_thu", "TEXT DEFAULT 'Thông thường'"),
            ("ke_hoach_kiem_tra", "diem_toi_thieu_dat", "REAL DEFAULT 0.0"),
            ("noi_dung", "nhiem_vu_ncs", "TEXT")
        ]
        for tbl, col, typ in cols_to_add:
            try:
                db.conn.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {typ}")
            except Exception:
                pass
        
        print("_migration_v14 completed.")
    except Exception as e:
        print(f"Error in _migration_v14: {e}")



def _migration_v2(db):
    """Thêm UNIQUE INDEX cho hoc_phan.ma and cleanup duplicates if any."""
    # 1. Kiểm tra xem có trùng mã không
    dups = db.conn.execute("""
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
            db.conn.execute("""
                UPDATE hoc_phan SET ma = NULL 
                WHERE ma = ? AND id NOT IN (SELECT MAX(id) FROM hoc_phan WHERE ma = ?)
            """, (d['ma'], d['ma']))
    
    # 2. Tạo Unique Index
    # Lưu ý: SQLite không cho ALTER ADD UNIQUE, nhưng có thể dùng CREATE UNIQUE INDEX
    db.conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_hp_ma_unique ON hoc_phan(ma) WHERE ma IS NOT NULL AND ma != ''")

def _migration_v3(db):
    """Thêm bảng lịch sử nhập xuất."""
    db.conn.execute("""
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

def _migration_v4(db):
    """Thêm 3 cột mới vào ke_hoach_kiem_tra + 2 bảng Rubric (mẫu DCCTHP mới)."""
    # 1. Thêm cột tiêu_chi_danh_gia
    try:
        db.conn.execute("ALTER TABLE ke_hoach_kiem_tra ADD COLUMN tieu_chi_danh_gia TEXT")
    except Exception:
        pass  # Cột đã tồn tại
    # 2. Thêm cột diem_toi_da_cdr
    try:
        db.conn.execute("ALTER TABLE ke_hoach_kiem_tra ADD COLUMN diem_toi_da_cdr TEXT")
    except Exception:
        pass
    # 3. Thêm cột trong_so_cdr
    try:
        db.conn.execute("ALTER TABLE ke_hoach_kiem_tra ADD COLUMN trong_so_cdr TEXT")
    except Exception:
        pass
    # 4. Tạo bảng rubric_danh_gia
    db.conn.execute("""
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
    db.conn.execute("""
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

def _migration_v5(db):
    """Thêm các cột thông tin chi tiết vào hp_giang_vien."""
    cols = ['ho_ten', 'hoc_ham_vi', 'don_vi', 'email', 'sdt']
    for col in cols:
        try:
            db.conn.execute(f"ALTER TABLE hp_giang_vien ADD COLUMN {col} TEXT")
        except Exception:
            pass

def _migration_v6(db):
    """Thêm level_irm vào bảng clo."""
    try:
        db.conn.execute("ALTER TABLE clo ADD COLUMN level_irm TEXT DEFAULT 'I'")
    except Exception:
        pass

def _migration_v7(db):
    """Thêm quy_dinh_hp và co_so_vat_chat."""
    for col in [("quy_dinh_hp", "TEXT"), ("co_so_vat_chat", "TEXT")]:
        try:
            db.conn.execute(f"ALTER TABLE hoc_phan ADD COLUMN {col[0]} {col[1]}")
        except Exception:
            pass

def _migration_v8(db):
    """Thêm phu_luc vào hoc_phan."""
    try:
        db.conn.execute("ALTER TABLE hoc_phan ADD COLUMN phu_luc TEXT")
    except Exception:
        pass

def _migration_v9(db):
    """Thêm pp_day, pp_hoc, bai_danh_gia vào bảng noi_dung."""
    columns = [c['name'] for c in db.conn.execute("PRAGMA table_info(noi_dung)").fetchall()]
    if 'pp_day' not in columns:
        db.conn.execute("ALTER TABLE noi_dung ADD COLUMN pp_day TEXT")
    if 'pp_hoc' not in columns:
        db.conn.execute("ALTER TABLE noi_dung ADD COLUMN pp_hoc TEXT")
    if 'bai_danh_gia' not in columns:
        db.conn.execute("ALTER TABLE noi_dung ADD COLUMN bai_danh_gia TEXT")

def _migration_v15(db):
    """Đồng bộ cấu trúc audit_log: Thêm record_id, details, created_at."""
    cols = [c['name'] for c in db.conn.execute("PRAGMA table_info(audit_log)").fetchall()]
    
    if 'record_id' not in cols:
        db.conn.execute("ALTER TABLE audit_log ADD COLUMN record_id INTEGER")
    if 'details' not in cols:
        db.conn.execute("ALTER TABLE audit_log ADD COLUMN details TEXT")
    if 'created_at' not in cols:
        db.conn.execute("ALTER TABLE audit_log ADD COLUMN created_at TEXT")
    
    # Optional: fill created_at from updated_at if exists
    if 'updated_at' in cols:
        db.conn.execute("UPDATE audit_log SET created_at = updated_at WHERE created_at IS NULL")

def _migration_v16(db):
    """Bổ sung các trường thông tin giảng viên: ma_can_bo, gioi_tinh, chuc_vu, dia_chi."""
    for table in ['giang_vien', 'hp_giang_vien']:
        cols = [c['name'] for c in db.conn.execute(f"PRAGMA table_info({table})").fetchall()]
        
        new_cols = [
            ('ma_can_bo', 'TEXT'),
            ('gioi_tinh', 'TEXT'),
            ('chuc_vu', 'TEXT'),
            ('dia_chi', 'TEXT')
        ]
        
        for col, typ in new_cols:
            if col not in cols:
                db.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")

