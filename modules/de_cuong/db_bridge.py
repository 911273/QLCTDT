# modules/de_cuong/db_bridge.py
"""DCDBBridge — CRUD hoàn chỉnh cho toàn bộ hệ thống đề cương động."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime


class DCDBBridge:
    """
    Bridge layer giữa UI và SQLite.
    Nhận db object (có thuộc tính conn: sqlite3.Connection và transaction()).
    """

    def __init__(self, db):
        self.db = db

    @property
    def conn(self) -> sqlite3.Connection:
        return self.db.conn

    @contextmanager
    def transaction(self):
        with self.db.transaction():
            yield

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _row_to_dict(self, cursor, row) -> dict:
        """Chuyển sqlite3.Row → dict, parse JSON fields tự động."""
        d = dict(zip([c[0] for c in cursor.description], row))
        for key in ('options_json', 'validation_json', 'formula_json',
                    'dieu_kien_json', 'relation_config'):
            if key in d and d[key]:
                try:
                    d[key] = json.loads(d[key])
                except Exception:
                    pass
        return d

    def _rows_to_dicts(self, cursor) -> list:
        rows = cursor.fetchall()
        return [self._row_to_dict(cursor, r) for r in rows]

    def _serialize(self, data: dict) -> dict:
        """Serialize list/dict values → JSON string trước khi ghi DB."""
        out = {}
        for k, v in data.items():
            if isinstance(v, (list, dict)):
                out[k] = json.dumps(v, ensure_ascii=False)
            else:
                out[k] = v
        return out

    def _fetch_one(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        row = cur.fetchone()
        return self._row_to_dict(cur, row) if row else None

    def _fetch_all(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        return self._rows_to_dicts(cur)

    # ════════════════════════════════════════════════════════════════════════
    # dc_schema
    # ════════════════════════════════════════════════════════════════════════

    def list_schemas(self) -> list:
        return self._fetch_all(
            "SELECT * FROM dc_schema ORDER BY thu_tu, id"
        )

    def get_default_schema(self):
        return self._fetch_one(
            "SELECT * FROM dc_schema WHERE is_default=1 LIMIT 1"
        )

    def get_schema_by_id(self, schema_id) -> dict:
        return self._fetch_one(
            "SELECT * FROM dc_schema WHERE id=?", (schema_id,)
        )

    def create_schema(self, data: dict) -> int:
        d = self._serialize(data)
        allowed = ('ten_mau','mo_ta','trinh_do','nam_ban_hanh','phien_ban',
                   'is_default','is_locked','thu_tu')
        d = {k: v for k, v in d.items() if k in allowed}
        cols = ','.join(d.keys())
        vals = list(d.values())
        cur = self.conn.execute(
            f"INSERT INTO dc_schema({cols}) VALUES({','.join(['?']*len(vals))})", vals
        )
        self.conn.commit()
        return cur.lastrowid

    def update_schema(self, schema_id: int, data: dict) -> bool:
        d = self._serialize(data)
        allowed = ('ten_mau','mo_ta','trinh_do','nam_ban_hanh','phien_ban',
                   'is_locked','thu_tu')
        d = {k: v for k, v in d.items() if k in allowed}
        if not d:
            return False
        sets = ','.join(f"{k}=?" for k in d)
        self.conn.execute(
            f"UPDATE dc_schema SET {sets} WHERE id=?", list(d.values()) + [schema_id]
        )
        self.conn.commit()
        return True

    def delete_schema(self, schema_id: int) -> bool:
        row = self._fetch_one("SELECT is_locked FROM dc_schema WHERE id=?", (schema_id,))
        if not row or row.get('is_locked'):
            return False
        self.conn.execute("DELETE FROM dc_schema WHERE id=?", (schema_id,))
        self.conn.commit()
        return True

    def set_default_schema(self, schema_id: int) -> bool:
        with self.transaction():
            self.conn.execute("UPDATE dc_schema SET is_default=0")
            self.conn.execute("UPDATE dc_schema SET is_default=1 WHERE id=?", (schema_id,))
        return True

    def clone_schema(self, schema_id: int, new_name: str) -> int:
        src = self.get_schema_by_id(schema_id)
        if not src:
            return -1
        new_id = self.create_schema({
            'ten_mau': new_name,
            'mo_ta': src.get('mo_ta', ''),
            'trinh_do': src.get('trinh_do', 'dai_hoc'),
            'nam_ban_hanh': src.get('nam_ban_hanh', 2026),
            'phien_ban': src.get('phien_ban', '1.0'),
            'is_default': 0, 'is_locked': 0,
            'thu_tu': src.get('thu_tu', 0) + 1
        })
        sections = self.list_sections_all(schema_id)
        for sec in sections:
            sec_data = {k: v for k, v in sec.items()
                        if k not in ('id', 'schema_id', 'created_at', 'updated_at')}
            sec_data['schema_id'] = new_id
            new_sec_id = self.create_section(new_id, sec_data)
            fields = self.list_field_defs_all(sec['id'])
            for fd in fields:
                fd_data = {k: v for k, v in fd.items()
                           if k not in ('id', 'section_id', 'deleted_at')}
                new_fd_id = self.create_field_def(new_sec_id, fd_data)
                cols = self.list_table_cols(fd['id'])
                for col in cols:
                    col_data = {k: v for k, v in col.items()
                                if k not in ('id', 'field_def_id')}
                    self.create_table_col(new_fd_id, col_data)
        return new_id

    def export_schema_json(self, schema_id: int) -> dict:
        schema = self.get_schema_by_id(schema_id)
        if not schema:
            return {}
        schema['sections'] = []
        for sec in self.list_sections_all(schema_id):
            sec_dict = dict(sec)
            sec_dict['fields'] = []
            for fd in self.list_field_defs_all(sec['id']):
                fd_dict = dict(fd)
                fd_dict['table_cols'] = [dict(c) for c in self.list_table_cols(fd['id'])]
                sec_dict['fields'].append(fd_dict)
            schema['sections'].append(sec_dict)
        return schema

    def import_schema_json(self, data: dict) -> int:
        new_name = data.get('ten_mau', 'Imported Schema')
        new_id = self.create_schema({
            'ten_mau': new_name,
            'mo_ta': data.get('mo_ta', ''),
            'trinh_do': data.get('trinh_do', 'dai_hoc'),
            'nam_ban_hanh': data.get('nam_ban_hanh', 2026),
            'phien_ban': data.get('phien_ban', '1.0'),
            'is_default': 0, 'is_locked': 0
        })
        for sec in data.get('sections', []):
            sec_data = {k: v for k, v in sec.items()
                        if k not in ('id', 'schema_id', 'fields')}
            new_sec_id = self.create_section(new_id, sec_data)
            for fd in sec.get('fields', []):
                fd_data = {k: v for k, v in fd.items()
                           if k not in ('id', 'section_id', 'table_cols', 'deleted_at')}
                new_fd_id = self.create_field_def(new_sec_id, fd_data)
                for col in fd.get('table_cols', []):
                    col_data = {k: v for k, v in col.items()
                                if k not in ('id', 'field_def_id')}
                    self.create_table_col(new_fd_id, col_data)
        return new_id

    # ════════════════════════════════════════════════════════════════════════
    # dc_section
    # ════════════════════════════════════════════════════════════════════════

    def list_sections(self, schema_id: int) -> list:
        return self._fetch_all(
            "SELECT * FROM dc_section WHERE schema_id=? AND is_visible=1 ORDER BY so_thu_tu",
            (schema_id,)
        )

    def list_sections_all(self, schema_id: int) -> list:
        return self._fetch_all(
            "SELECT * FROM dc_section WHERE schema_id=? ORDER BY so_thu_tu",
            (schema_id,)
        )

    def get_section_by_id(self, section_id: int):
        return self._fetch_one("SELECT * FROM dc_section WHERE id=?", (section_id,))

    def create_section(self, schema_id: int, data: dict) -> int:
        d = self._serialize(data)
        allowed = ('ma_muc','tieu_de','so_thu_tu','loai','icon','color_tag',
                   'mo_ta','dieu_kien','is_required','is_visible','is_locked')
        d = {k: v for k, v in d.items() if k in allowed}
        d['schema_id'] = schema_id
        cols = ','.join(d.keys())
        vals = list(d.values())
        cur = self.conn.execute(
            f"INSERT INTO dc_section({cols}) VALUES({','.join(['?']*len(vals))})", vals
        )
        self.conn.commit()
        return cur.lastrowid

    def update_section(self, section_id: int, data: dict) -> bool:
        d = self._serialize(data)
        allowed = ('ma_muc','tieu_de','so_thu_tu','loai','icon','color_tag',
                   'mo_ta','dieu_kien','is_required','is_visible','is_locked')
        d = {k: v for k, v in d.items() if k in allowed}
        if not d:
            return False
        sets = ','.join(f"{k}=?" for k in d)
        self.conn.execute(
            f"UPDATE dc_section SET {sets} WHERE id=?", list(d.values()) + [section_id]
        )
        self.conn.commit()
        return True

    def delete_section(self, section_id: int) -> bool:
        row = self._fetch_one("SELECT is_locked FROM dc_section WHERE id=?", (section_id,))
        if not row or row.get('is_locked'):
            return False
        self.conn.execute("DELETE FROM dc_section WHERE id=?", (section_id,))
        self.conn.commit()
        return True

    def reorder_sections(self, schema_id: int, ordered_ids: list) -> bool:
        with self.transaction():
            for idx, sid in enumerate(ordered_ids):
                self.conn.execute(
                    "UPDATE dc_section SET so_thu_tu=? WHERE id=? AND schema_id=?",
                    (idx, sid, schema_id)
                )
        return True

    def toggle_section_visibility(self, section_id: int) -> bool:
        self.conn.execute(
            "UPDATE dc_section SET is_visible = CASE WHEN is_visible=1 THEN 0 ELSE 1 END WHERE id=?",
            (section_id,)
        )
        self.conn.commit()
        return True

    # ════════════════════════════════════════════════════════════════════════
    # dc_field_def
    # ════════════════════════════════════════════════════════════════════════

    def list_field_defs(self, section_id: int) -> list:
        return self._fetch_all(
            "SELECT * FROM dc_field_def WHERE section_id=? AND is_visible=1 AND deleted_at IS NULL ORDER BY so_thu_tu",
            (section_id,)
        )

    def list_field_defs_all(self, section_id: int) -> list:
        return self._fetch_all(
            "SELECT * FROM dc_field_def WHERE section_id=? ORDER BY so_thu_tu",
            (section_id,)
        )

    def get_field_def_by_id(self, field_id: int):
        return self._fetch_one("SELECT * FROM dc_field_def WHERE id=?", (field_id,))

    def create_field_def(self, section_id: int, data: dict) -> int:
        d = self._serialize(data)
        allowed = ('ma_truong','nhan','kieu_du_lieu','so_thu_tu','nhom_hien_thi',
                   'placeholder','tooltip','gia_tri_mac_dinh','bat_buoc','is_visible',
                   'is_editable','is_locked','options_json','validation_json',
                   'formula_json','dieu_kien_json','relation_config','word_bookmark',
                   'word_style','width_hint','help_url')
        d = {k: v for k, v in d.items() if k in allowed}
        d['section_id'] = section_id
        cols = ','.join(d.keys())
        vals = list(d.values())
        cur = self.conn.execute(
            f"INSERT INTO dc_field_def({cols}) VALUES({','.join(['?']*len(vals))})", vals
        )
        self.conn.commit()
        return cur.lastrowid

    def update_field_def(self, field_id: int, data: dict) -> bool:
        d = self._serialize(data)
        allowed = ('ma_truong','nhan','kieu_du_lieu','so_thu_tu','nhom_hien_thi',
                   'placeholder','tooltip','gia_tri_mac_dinh','bat_buoc','is_visible',
                   'is_editable','is_locked','options_json','validation_json',
                   'formula_json','dieu_kien_json','relation_config','word_bookmark',
                   'word_style','width_hint','help_url')
        d = {k: v for k, v in d.items() if k in allowed}
        if not d:
            return False
        sets = ','.join(f"{k}=?" for k in d)
        self.conn.execute(
            f"UPDATE dc_field_def SET {sets} WHERE id=?", list(d.values()) + [field_id]
        )
        self.conn.commit()
        return True

    def soft_delete_field_def(self, field_id: int) -> bool:
        self.conn.execute(
            "UPDATE dc_field_def SET deleted_at=? WHERE id=?",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), field_id)
        )
        self.conn.commit()
        return True

    def restore_field_def(self, field_id: int) -> bool:
        self.conn.execute(
            "UPDATE dc_field_def SET deleted_at=NULL WHERE id=?", (field_id,)
        )
        self.conn.commit()
        return True

    def hard_delete_field_def(self, field_id: int) -> bool:
        if self.count_field_data(field_id) > 0:
            return False
        self.conn.execute("DELETE FROM dc_field_def WHERE id=?", (field_id,))
        self.conn.commit()
        return True

    def reorder_field_defs(self, section_id: int, ordered_ids: list) -> bool:
        with self.transaction():
            for idx, fid in enumerate(ordered_ids):
                self.conn.execute(
                    "UPDATE dc_field_def SET so_thu_tu=? WHERE id=? AND section_id=?",
                    (idx, fid, section_id)
                )
        return True

    def toggle_field_visibility(self, field_id: int) -> bool:
        self.conn.execute(
            "UPDATE dc_field_def SET is_visible = CASE WHEN is_visible=1 THEN 0 ELSE 1 END WHERE id=?",
            (field_id,)
        )
        self.conn.commit()
        return True

    # ════════════════════════════════════════════════════════════════════════
    # dc_table_col_def
    # ════════════════════════════════════════════════════════════════════════

    def list_table_cols(self, field_def_id: int) -> list:
        return self._fetch_all(
            "SELECT * FROM dc_table_col_def WHERE field_def_id=? ORDER BY so_thu_tu",
            (field_def_id,)
        )

    def create_table_col(self, field_def_id: int, data: dict) -> int:
        d = self._serialize(data)
        allowed = ('ma_cot','tieu_de_cot','kieu_cot','do_rong','so_thu_tu',
                   'is_frozen','is_required','options_json','placeholder')
        d = {k: v for k, v in d.items() if k in allowed}
        d['field_def_id'] = field_def_id
        cols = ','.join(d.keys())
        vals = list(d.values())
        cur = self.conn.execute(
            f"INSERT INTO dc_table_col_def({cols}) VALUES({','.join(['?']*len(vals))})", vals
        )
        self.conn.commit()
        return cur.lastrowid

    def update_table_col(self, col_id: int, data: dict) -> bool:
        d = self._serialize(data)
        allowed = ('ma_cot','tieu_de_cot','kieu_cot','do_rong','so_thu_tu',
                   'is_frozen','is_required','options_json','placeholder')
        d = {k: v for k, v in d.items() if k in allowed}
        if not d:
            return False
        sets = ','.join(f"{k}=?" for k in d)
        self.conn.execute(
            f"UPDATE dc_table_col_def SET {sets} WHERE id=?", list(d.values()) + [col_id]
        )
        self.conn.commit()
        return True

    def delete_table_col(self, col_id: int) -> bool:
        self.conn.execute("DELETE FROM dc_table_col_def WHERE id=?", (col_id,))
        self.conn.commit()
        return True

    def reorder_table_cols(self, field_def_id: int, ordered_ids: list) -> bool:
        with self.transaction():
            for idx, cid in enumerate(ordered_ids):
                self.conn.execute(
                    "UPDATE dc_table_col_def SET so_thu_tu=? WHERE id=? AND field_def_id=?",
                    (idx, cid, field_def_id)
                )
        return True

    # ════════════════════════════════════════════════════════════════════════
    # de_cuong (bản ghi người dùng)
    # ════════════════════════════════════════════════════════════════════════

    def list_de_cuong(self, hp_id=None, gv_id=None, schema_id=None) -> list:
        conds, params = [], []
        if hp_id is not None:
            conds.append("hp_id=?"); params.append(hp_id)
        if gv_id is not None:
            conds.append("gv_id=?"); params.append(gv_id)
        if schema_id is not None:
            conds.append("schema_id=?"); params.append(schema_id)
        where = ("WHERE " + " AND ".join(conds)) if conds else ""
        return self._fetch_all(f"SELECT * FROM de_cuong {where} ORDER BY id DESC", params)

    def get_de_cuong_by_id(self, dc_id: int):
        return self._fetch_one("SELECT * FROM de_cuong WHERE id=?", (dc_id,))

    def get_or_create_de_cuong(self, hp_id: int, schema_id: int, gv_id=None):
        """Returns (dc_id, was_created)."""
        existing = self._fetch_one(
            "SELECT id FROM de_cuong WHERE hp_id=? AND schema_id=?",
            (hp_id, schema_id)
        )
        if existing:
            return existing['id'], False
        data = {'hp_id': hp_id, 'schema_id': schema_id}
        if gv_id:
            data['gv_id'] = gv_id
        cur = self.conn.execute(
            "INSERT INTO de_cuong(hp_id, schema_id, gv_id) VALUES(?,?,?)",
            (hp_id, schema_id, gv_id)
        )
        self.conn.commit()
        return cur.lastrowid, True

    def update_de_cuong_meta(self, dc_id: int, data: dict) -> bool:
        allowed = ('trang_thai','ky_hoc','nam_hoc','ghi_chu_duyet',
                   'submitted_at','approved_at','gv_id')
        d = {k: v for k, v in data.items() if k in allowed}
        if not d:
            return False
        sets = ','.join(f"{k}=?" for k in d)
        self.conn.execute(
            f"UPDATE de_cuong SET {sets} WHERE id=?", list(d.values()) + [dc_id]
        )
        self.conn.commit()
        return True

    def delete_de_cuong(self, dc_id: int) -> bool:
        self.conn.execute("DELETE FROM de_cuong WHERE id=?", (dc_id,))
        self.conn.commit()
        return True

    # ════════════════════════════════════════════════════════════════════════
    # dc_field_value
    # ════════════════════════════════════════════════════════════════════════

    def get_all_field_values(self, dc_id: int) -> dict:
        """Returns {field_def_id: gia_tri}."""
        rows = self._fetch_all(
            "SELECT field_def_id, gia_tri FROM dc_field_value WHERE dc_id=?", (dc_id,)
        )
        return {r['field_def_id']: r['gia_tri'] for r in rows}

    def get_field_value(self, dc_id: int, field_def_id: int) -> str:
        row = self._fetch_one(
            "SELECT gia_tri FROM dc_field_value WHERE dc_id=? AND field_def_id=?",
            (dc_id, field_def_id)
        )
        return row['gia_tri'] if row else ''

    def set_field_value(self, dc_id: int, field_def_id: int, value: str) -> bool:
        self.conn.execute("""
            INSERT INTO dc_field_value(dc_id, field_def_id, gia_tri)
            VALUES(?,?,?)
            ON CONFLICT(dc_id, field_def_id) DO UPDATE SET gia_tri=excluded.gia_tri
        """, (dc_id, field_def_id, value))
        self.conn.commit()
        return True

    def bulk_set_field_values(self, dc_id: int, values: dict) -> bool:
        """values = {field_def_id: gia_tri}"""
        with self.transaction():
            for fid, val in values.items():
                self.conn.execute("""
                    INSERT INTO dc_field_value(dc_id, field_def_id, gia_tri)
                    VALUES(?,?,?)
                    ON CONFLICT(dc_id, field_def_id) DO UPDATE SET gia_tri=excluded.gia_tri
                """, (dc_id, fid, val))
        return True

    # ════════════════════════════════════════════════════════════════════════
    # dc_table_row / dc_table_cell
    # ════════════════════════════════════════════════════════════════════════

    def list_table_rows(self, dc_id: int, field_def_id: int) -> list:
        rows = self._fetch_all(
            """SELECT * FROM dc_table_row
               WHERE dc_id=? AND field_def_id=? AND is_deleted=0
               ORDER BY so_thu_tu""",
            (dc_id, field_def_id)
        )
        for row in rows:
            cells = self._fetch_all(
                "SELECT ma_cot, gia_tri FROM dc_table_cell WHERE row_id=?",
                (row['id'],)
            )
            row['cells'] = {c['ma_cot']: c['gia_tri'] for c in cells}
        return rows

    def add_table_row(self, dc_id: int, field_def_id: int, cells: dict) -> int:
        max_ord = self.conn.execute(
            "SELECT COALESCE(MAX(so_thu_tu),0) FROM dc_table_row WHERE dc_id=? AND field_def_id=?",
            (dc_id, field_def_id)
        ).fetchone()[0]
        cur = self.conn.execute(
            "INSERT INTO dc_table_row(dc_id, field_def_id, so_thu_tu) VALUES(?,?,?)",
            (dc_id, field_def_id, max_ord + 1)
        )
        row_id = cur.lastrowid
        for ma_cot, gia_tri in cells.items():
            self.conn.execute(
                "INSERT INTO dc_table_cell(row_id, ma_cot, gia_tri) VALUES(?,?,?)",
                (row_id, ma_cot, gia_tri)
            )
        self.conn.commit()
        return row_id

    def update_table_row(self, row_id: int, cells: dict) -> bool:
        with self.transaction():
            for ma_cot, gia_tri in cells.items():
                self.conn.execute("""
                    INSERT INTO dc_table_cell(row_id, ma_cot, gia_tri) VALUES(?,?,?)
                    ON CONFLICT(row_id, ma_cot) DO UPDATE SET gia_tri=excluded.gia_tri
                """, (row_id, ma_cot, gia_tri))
        return True

    def delete_table_row(self, row_id: int) -> bool:
        self.conn.execute("UPDATE dc_table_row SET is_deleted=1 WHERE id=?", (row_id,))
        self.conn.commit()
        return True

    def reorder_table_rows(self, field_def_id: int, dc_id: int, ordered_ids: list) -> bool:
        with self.transaction():
            for idx, rid in enumerate(ordered_ids):
                self.conn.execute(
                    "UPDATE dc_table_row SET so_thu_tu=? WHERE id=? AND dc_id=? AND field_def_id=?",
                    (idx, rid, dc_id, field_def_id)
                )
        return True

    def bulk_save_table_rows(self, dc_id: int, field_def_id: int, rows: list) -> bool:
        """Xóa tất cả rows cũ, insert lại toàn bộ trong 1 transaction."""
        with self.transaction():
            old_rows = self.conn.execute(
                "SELECT id FROM dc_table_row WHERE dc_id=? AND field_def_id=?",
                (dc_id, field_def_id)
            ).fetchall()
            for r in old_rows:
                self.conn.execute("DELETE FROM dc_table_cell WHERE row_id=?", (r[0],))
            self.conn.execute(
                "DELETE FROM dc_table_row WHERE dc_id=? AND field_def_id=?",
                (dc_id, field_def_id)
            )
            for idx, row in enumerate(rows):
                cur = self.conn.execute(
                    "INSERT INTO dc_table_row(dc_id, field_def_id, so_thu_tu) VALUES(?,?,?)",
                    (dc_id, field_def_id, idx)
                )
                row_id = cur.lastrowid
                for ma_cot, gia_tri in row.get('cells', {}).items():
                    self.conn.execute(
                        "INSERT INTO dc_table_cell(row_id, ma_cot, gia_tri) VALUES(?,?,?)",
                        (row_id, ma_cot, gia_tri)
                    )
        return True

    # ════════════════════════════════════════════════════════════════════════
    # Utilities
    # ════════════════════════════════════════════════════════════════════════

    def count_field_data(self, field_def_id: int) -> int:
        """Số bản ghi có dữ liệu cho field này (dùng trước hard_delete)."""
        row = self.conn.execute(
            "SELECT COUNT(*) FROM dc_field_value WHERE field_def_id=? AND gia_tri!=''",
            (field_def_id,)
        ).fetchone()
        return row[0] if row else 0
