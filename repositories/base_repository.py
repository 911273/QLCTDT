# repositories/base_repository.py
"""
BaseRepository — Lớp nền cho tất cả repository.
- Cache schema PRAGMA table_info để không query lặp
- safe_insert / safe_update tự lọc cột hợp lệ
- Dùng db.transaction() context manager sẵn có
"""
import threading
import json
from typing import List, Optional, Any, Dict
from core.logger import logger


class BaseRepository:
    """
    Lớp nền cho mọi repository trong ứng dụng.
    
    Properties:
        db: Database instance (để dùng transaction(), conn, get_config, ...)
        conn: sqlite3.Connection (shortcut)
    """

    def __init__(self, db):
        self.db = db
        self.conn = db.conn
        self._schema_cache: dict = {}   # {table_name: [col_name, ...]}
        self._cache_lock = threading.RLock()
        
        # P0 Security: Whitelist of allowed tables for dynamic SQL identifiers
        self._ALLOWED_TABLES = {
            'schema_version', 'khoa', 'giang_vien', 'cdr_ctdt',
            'hoc_phan', 'hp_giang_vien', 'muc_tieu', 'clo', 'tai_lieu', 'hoc_lieu',
            'noi_dung', 'ke_hoach_kiem_tra', 'lich_su_cap_nhat', 'word_template',
            'rubric_danh_gia', 'rubric_tieu_chi', 'chuong_trinh_dao_tao', 'chuyen_nganh',
            'ctdt_hoc_phan', 'ctdt_po', 'ctdt_plo', 'ctdt_pi', 'config', 'temp_draft',
            'audit_log'
        }

    def _log_audit(self, action: str, table: str, record_id: int, details: dict = None):
        """P3: Tự động ghi log thay đổi dữ liệu."""
        try:
            from datetime import datetime
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Lấy danh sách cột thực tế của audit_log
            try:
                cols = self._get_cols('audit_log')
            except:
                return # Bảng chưa tồn tại

            data = {
                'table_name': table,
                'record_id': record_id,
                'action': action,
                'details': json.dumps(details, ensure_ascii=False) if details else None,
            }
            if 'created_at' in cols: data['created_at'] = now
            if 'updated_at' in cols: data['updated_at'] = now
            
            # Lọc lại data theo cột thực có
            safe_data = {k: v for k, v in data.items() if k in cols}
            if not safe_data: return

            c_names = list(safe_data.keys())
            placeholders = ','.join(['?'] * len(c_names))
            sql = f"INSERT INTO [audit_log] ({','.join(c_names)}) VALUES ({placeholders})"
            
            self.conn.execute(sql, list(safe_data.values()))
            
        except Exception as e:
            err_msg = str(e).lower()
            # Nếu lỗi do thiếu cột record_id
            if "record_id" in err_msg and ("no such column" in err_msg or "no column named" in err_msg):
                try:
                    self.conn.execute("ALTER TABLE audit_log ADD COLUMN record_id INTEGER")
                    self.conn.execute("ALTER TABLE audit_log ADD COLUMN details TEXT")
                    self.conn.execute("ALTER TABLE audit_log ADD COLUMN created_at TEXT")
                    self._invalidate_schema_cache('audit_log')
                    self._log_audit(action, table, record_id, details)
                except Exception as e2:
                    logger.error(f"Failed to auto-fix audit_log schema: {e2}")
            else:
                logger.error(f"Audit Log Error: {e}")


    def _validate_table(self, table: str):
        """P0 Security: Prevent SQL injection via table names."""
        if table not in self._ALLOWED_TABLES:
            raise ValueError(f"Security Alert: Unauthorized table access attempt: {table}")


    # ── Schema Cache ──────────────────────────────────────────────────────────

    def _get_cols(self, table: str) -> List[str]:
        """
        Trả về danh sách cột của bảng, có cache để tránh query PRAGMA lặp lại.
        Cache được share giữa tất cả instances qua self._schema_cache.
        """
        self._validate_table(table)
        with self._cache_lock:
            if table not in self._schema_cache:
                # Use quoted table name for PRAGMA
                rows = self.conn.execute(f"PRAGMA table_info([{table}])").fetchall()
                self._schema_cache[table] = [r[1] for r in rows]
            return self._schema_cache[table]


    def _invalidate_schema_cache(self, table: str = None):
        """Xóa schema cache khi có migration tạo cột mới."""
        with self._cache_lock:
            if table:
                self._schema_cache.pop(table, None)
            else:
                self._schema_cache.clear()

    # ── Safe DML ─────────────────────────────────────────────────────────────

    def _validate_data(self, table: str, data: dict):
        """P3: Validation dữ liệu cơ bản trước khi lưu."""
        # Ví dụ: Kiểm tra không được để trống các trường mã hoặc tên nếu có
        required_substrings = ['ma', 'ten', 'ho_ten']
        for k, v in data.items():
            if any(sub in k for sub in required_substrings):
                if v is None or (isinstance(v, str) and not v.strip()):
                    logger.warning(f"Validation Warning: Field '{k}' in table '{table}' is empty.")
                    # Tùy chọn: raise ValueError if critical

    def _safe_insert(self, table: str, data: dict) -> int:
        """
        INSERT dữ liệu vào bảng, chỉ lấy các cột hợp lệ.
        """
        self._validate_table(table)
        self._validate_data(table, data)
        valid_cols = self._get_cols(table)

        safe = {k: v for k, v in data.items() if k in valid_cols and k != 'id'}
        if not safe:
            raise ValueError(f"Không có cột hợp lệ để insert vào {table}. Data keys: {list(data.keys())}")

        cols = list(safe.keys())
        # P0: Escape column names with []
        cols_escaped = [f"[{c}]" for c in cols]
        placeholders = ','.join(['?'] * len(cols))
        sql = f"INSERT INTO [{table}]({','.join(cols_escaped)}) VALUES({placeholders})"
        cur = self.conn.execute(sql, list(safe.values()))
        new_id = cur.lastrowid
        self._log_audit("INSERT", table, new_id, safe)
        return new_id



    def _safe_update(self, table: str, id_: int, data: dict):
        """
        UPDATE chỉ các cột tồn tại trong bảng — bỏ qua key lạ.
        """
        valid_cols = self._get_cols(table)
        safe = {k: v for k, v in data.items() if k in valid_cols and k not in ('id',)}
        if not safe:
            return  # Không có gì để update
        
        # P0: Escape column names
        sets = ','.join(f"[{k}]=?" for k in safe)
        self.conn.execute(
            f"UPDATE [{table}] SET {sets} WHERE id=?",
            list(safe.values()) + [id_]
        )
        self._log_audit("UPDATE", table, id_, safe)



    def _safe_upsert(self, table: str, data: dict, unique_key: str = None, unique_val: Any = None) -> int:
        """
        INSERT hoặc UPDATE tùy theo unique_key có tồn tại chưa.
        Returns: id của record (mới hoặc cũ)
        """
        if unique_key and unique_val is not None:
            existing = self.conn.execute(
                f"SELECT id FROM {table} WHERE {unique_key}=?", (unique_val,)
            ).fetchone()
            if existing:
                self._safe_update(table, existing['id'], data)
                return existing['id']
        return self._safe_insert(table, data)

    # ── Bulk Operations ───────────────────────────────────────────────────────

    def _bulk_insert(self, table: str, rows: List[dict]):
        """
        Insert nhiều dòng cùng lúc — hiệu quả hơn insert từng dòng.
        Tất cả rows phải cùng structure.
        """
        if not rows:
            return

        valid_cols = self._get_cols(table)
        # Dùng cột từ dòng đầu tiên
        sample = {k: v for k, v in rows[0].items() if k in valid_cols and k != 'id'}
        cols = list(sample.keys())
        placeholders = ','.join(['?'] * len(cols))
        sql = f"INSERT INTO {table}({','.join(cols)}) VALUES({placeholders})"

        data = [
            [row.get(c) for c in cols]
            for row in rows
        ]
        self.conn.executemany(sql, data)

    def _delete_by_hp(self, table: str, hp_id: int, extra_where: str = ''):
        """Xóa tất cả record của 1 HP trong 1 bảng."""
        sql = f"DELETE FROM {table} WHERE hp_id=?"
        if extra_where:
            sql += f" AND {extra_where}"
        self.conn.execute(sql, (hp_id,))

    def _count(self, table: str, where: str = '1=1', params: tuple = ()) -> int:
        """Đếm record theo điều kiện."""
        row = self.conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", params).fetchone()
        return row[0] if row else 0

    def _fetch_one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        """Helper fetch 1 row thành dict."""
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def _fetch_all(self, sql: str, params: tuple = ()) -> List[dict]:
        """Helper fetch nhiều rows thành list of dict."""
        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
