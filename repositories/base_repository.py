# repositories/base_repository.py
"""
BaseRepository — Lớp nền cho tất cả repository.
- Cache schema PRAGMA table_info để không query lặp
- safe_insert / safe_update tự lọc cột hợp lệ
- Dùng db.transaction() context manager sẵn có
"""
import threading
from typing import List, Optional, Any


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

    # ── Schema Cache ──────────────────────────────────────────────────────────

    def _get_cols(self, table: str) -> List[str]:
        """
        Trả về danh sách cột của bảng, có cache để tránh query PRAGMA lặp lại.
        Cache được share giữa tất cả instances qua self._schema_cache.
        """
        with self._cache_lock:
            if table not in self._schema_cache:
                rows = self.conn.execute(f"PRAGMA table_info({table})").fetchall()
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

    def _safe_insert(self, table: str, data: dict) -> int:
        """
        INSERT chỉ các cột tồn tại trong bảng — bỏ qua key lạ thay vì lỗi.
        Returns: lastrowid
        """
        valid_cols = self._get_cols(table)
        safe = {k: v for k, v in data.items() if k in valid_cols and k != 'id'}
        if not safe:
            raise ValueError(f"Không có cột hợp lệ để insert vào {table}. Data keys: {list(data.keys())}")

        cols = list(safe.keys())
        placeholders = ','.join(['?'] * len(cols))
        sql = f"INSERT INTO {table}({','.join(cols)}) VALUES({placeholders})"
        cur = self.conn.execute(sql, list(safe.values()))
        return cur.lastrowid

    def _safe_update(self, table: str, id_: int, data: dict):
        """
        UPDATE chỉ các cột tồn tại trong bảng — bỏ qua key lạ.
        """
        valid_cols = self._get_cols(table)
        safe = {k: v for k, v in data.items() if k in valid_cols and k not in ('id',)}
        if not safe:
            return  # Không có gì để update
        sets = ','.join(f"{k}=?" for k in safe)
        self.conn.execute(
            f"UPDATE {table} SET {sets} WHERE id=?",
            list(safe.values()) + [id_]
        )

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
