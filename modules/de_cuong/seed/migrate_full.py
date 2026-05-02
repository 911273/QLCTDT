# modules/de_cuong/seed/migrate_full.py
"""
migrate_full(conn) — Hàm idempotent tạo toàn bộ schema cho hệ thống
quản lý đề cương động (QLCTDT).

Gọi 1 lần duy nhất khi app khởi động, an toàn để gọi lại nhiều lần
(tất cả đều dùng IF NOT EXISTS).
"""

import sqlite3


def migrate_full(conn: sqlite3.Connection):
    """
    Tạo hoàn chỉnh tất cả bảng, index và trigger cho module đề cương động.
    Idempotent — gọi nhiều lần không gây lỗi.
    """
    conn.execute("PRAGMA foreign_keys = ON")

    # ─── NHÓM 1: Cấu trúc schema (quản trị viên cấu hình) ─────────────────

    conn.execute("""
        CREATE TABLE IF NOT EXISTS dc_schema (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ten_mau      TEXT NOT NULL,
            mo_ta        TEXT DEFAULT '',
            trinh_do     TEXT DEFAULT 'dai_hoc',
            nam_ban_hanh INTEGER DEFAULT 2026,
            phien_ban    TEXT DEFAULT '1.0',
            is_default   INTEGER DEFAULT 0,
            is_locked    INTEGER DEFAULT 0,
            thu_tu       INTEGER DEFAULT 0,
            created_at   TEXT DEFAULT (datetime('now','localtime')),
            updated_at   TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS dc_section (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            schema_id   INTEGER NOT NULL REFERENCES dc_schema(id) ON DELETE CASCADE,
            ma_muc      TEXT NOT NULL,
            tieu_de     TEXT NOT NULL,
            so_thu_tu   INTEGER DEFAULT 0,
            loai        TEXT DEFAULT 'standard',
            icon        TEXT DEFAULT '📋',
            color_tag   TEXT DEFAULT '#4A90D9',
            mo_ta       TEXT DEFAULT '',
            dieu_kien   TEXT DEFAULT '',
            is_required INTEGER DEFAULT 1,
            is_visible  INTEGER DEFAULT 1,
            is_locked   INTEGER DEFAULT 0,
            UNIQUE(schema_id, ma_muc)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS dc_field_def (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id       INTEGER NOT NULL REFERENCES dc_section(id) ON DELETE CASCADE,
            ma_truong        TEXT NOT NULL,
            nhan             TEXT NOT NULL,
            kieu_du_lieu     TEXT NOT NULL DEFAULT 'text',
            so_thu_tu        INTEGER DEFAULT 0,
            nhom_hien_thi    TEXT DEFAULT '',
            placeholder      TEXT DEFAULT '',
            tooltip          TEXT DEFAULT '',
            gia_tri_mac_dinh TEXT DEFAULT '',
            bat_buoc         INTEGER DEFAULT 0,
            is_visible       INTEGER DEFAULT 1,
            is_editable      INTEGER DEFAULT 1,
            is_locked        INTEGER DEFAULT 0,
            options_json     TEXT DEFAULT '[]',
            validation_json  TEXT DEFAULT '{}',
            formula_json     TEXT DEFAULT '{}',
            dieu_kien_json   TEXT DEFAULT '{}',
            relation_config  TEXT DEFAULT '{}',
            word_bookmark    TEXT DEFAULT '',
            word_style       TEXT DEFAULT '',
            width_hint       INTEGER DEFAULT 100,
            help_url         TEXT DEFAULT '',
            deleted_at       TEXT DEFAULT NULL,
            UNIQUE(section_id, ma_truong)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS dc_table_col_def (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            field_def_id INTEGER NOT NULL REFERENCES dc_field_def(id) ON DELETE CASCADE,
            ma_cot       TEXT NOT NULL,
            tieu_de_cot  TEXT NOT NULL,
            kieu_cot     TEXT DEFAULT 'text',
            do_rong      INTEGER DEFAULT 120,
            so_thu_tu    INTEGER DEFAULT 0,
            is_frozen    INTEGER DEFAULT 0,
            is_required  INTEGER DEFAULT 0,
            options_json TEXT DEFAULT '[]',
            placeholder  TEXT DEFAULT '',
            UNIQUE(field_def_id, ma_cot)
        )
    """)

    # ─── NHÓM 2: Dữ liệu người dùng ────────────────────────────────────────

    conn.execute("""
        CREATE TABLE IF NOT EXISTS de_cuong (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            hp_id        INTEGER NOT NULL REFERENCES hoc_phan(id),
            schema_id    INTEGER NOT NULL REFERENCES dc_schema(id),
            gv_id        INTEGER REFERENCES giang_vien(id),
            trang_thai   TEXT DEFAULT 'nhap',
            ky_hoc       TEXT DEFAULT '',
            nam_hoc      TEXT DEFAULT '',
            ghi_chu_duyet TEXT DEFAULT '',
            created_at   TEXT DEFAULT (datetime('now','localtime')),
            updated_at   TEXT DEFAULT (datetime('now','localtime')),
            submitted_at TEXT DEFAULT NULL,
            approved_at  TEXT DEFAULT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS dc_field_value (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            dc_id        INTEGER NOT NULL REFERENCES de_cuong(id) ON DELETE CASCADE,
            field_def_id INTEGER NOT NULL REFERENCES dc_field_def(id) ON DELETE CASCADE,
            gia_tri      TEXT DEFAULT '',
            updated_at   TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(dc_id, field_def_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS dc_table_row (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            dc_id        INTEGER NOT NULL REFERENCES de_cuong(id) ON DELETE CASCADE,
            field_def_id INTEGER NOT NULL REFERENCES dc_field_def(id) ON DELETE CASCADE,
            so_thu_tu    INTEGER DEFAULT 0,
            is_deleted   INTEGER DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS dc_table_cell (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            row_id   INTEGER NOT NULL REFERENCES dc_table_row(id) ON DELETE CASCADE,
            ma_cot   TEXT NOT NULL,
            gia_tri  TEXT DEFAULT '',
            UNIQUE(row_id, ma_cot)
        )
    """)

    # ─── Index tăng tốc ─────────────────────────────────────────────────────

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_dcfv_dcid    ON dc_field_value(dc_id)",
        "CREATE INDEX IF NOT EXISTS idx_dctr_dcid    ON dc_table_row(dc_id, field_def_id)",
        "CREATE INDEX IF NOT EXISTS idx_dctc_rowid   ON dc_table_cell(row_id)",
        "CREATE INDEX IF NOT EXISTS idx_dcsec_schema ON dc_section(schema_id, so_thu_tu)",
        "CREATE INDEX IF NOT EXISTS idx_dcfd_sec     ON dc_field_def(section_id, so_thu_tu)",
        "CREATE INDEX IF NOT EXISTS idx_decuong_hp   ON de_cuong(hp_id)",
        "CREATE INDEX IF NOT EXISTS idx_decuong_schema ON de_cuong(schema_id)",
    ]
    for idx_sql in indexes:
        conn.execute(idx_sql)

    # ─── Trigger tự động cập nhật updated_at ────────────────────────────────

    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_dc_schema_upd
        AFTER UPDATE ON dc_schema
        BEGIN
            UPDATE dc_schema SET updated_at = datetime('now','localtime')
            WHERE id = NEW.id;
        END
    """)

    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_de_cuong_upd
        AFTER UPDATE ON de_cuong
        BEGIN
            UPDATE de_cuong SET updated_at = datetime('now','localtime')
            WHERE id = NEW.id;
        END
    """)

    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_dc_fv_upd
        AFTER UPDATE ON dc_field_value
        BEGIN
            UPDATE dc_field_value SET updated_at = datetime('now','localtime')
            WHERE id = NEW.id;
        END
    """)

    conn.commit()
    print("[migrate_full] DC schema migration completed.")
