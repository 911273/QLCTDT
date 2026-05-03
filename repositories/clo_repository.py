# repositories/clo_repository.py
from .base_repository import BaseRepository
from typing import List, Optional

class CLORepository(BaseRepository):
    """Repository quản lý Chuẩn đầu ra (CLO) và Mục tiêu học phần."""
    
    # ── CLO ──────────────────────────────────────────────────────────────────
    
    def get_by_hp(self, hp_id: int) -> List[dict]:
        return self._fetch_all("SELECT * FROM clo WHERE hp_id=? ORDER BY id", (hp_id,))

    def get_by_id(self, id_: int) -> Optional[dict]:
        return self._fetch_one("SELECT * FROM clo WHERE id=?", (id_,))

    def create(self, data: dict) -> int:
        return self._safe_insert('clo', data)

    def update(self, id_: int, data: dict):
        self._safe_update('clo', id_, data)

    def delete(self, id_: int):
        self.conn.execute("DELETE FROM clo WHERE id=?", (id_,))

    def set_all(self, hp_id: int, items: List[dict]):
        """Xóa cũ và thêm mới toàn bộ CLO của 1 HP."""
        with self.db.transaction():
            self.conn.execute("DELETE FROM clo WHERE hp_id=?", (hp_id,))
            for item in items:
                item['hp_id'] = hp_id
                self._safe_insert('clo', item)

    # ── MucTieu ──────────────────────────────────────────────────────────────
    
    def get_muc_tieu_by_hp(self, hp_id: int) -> List[dict]:
        return self._fetch_all("SELECT * FROM muc_tieu WHERE hp_id=? ORDER BY so_thu_tu", (hp_id,))

    def set_muc_tieu_all(self, hp_id: int, items: List[dict]):
        with self.db.transaction():
            self.conn.execute("DELETE FROM muc_tieu WHERE hp_id=?", (hp_id,))
            for i, item in enumerate(items):
                item['hp_id'] = hp_id
                item['so_thu_tu'] = i + 1
                self._safe_insert('muc_tieu', item)

    def create_muc_tieu(self, data: dict) -> int:
        return self._safe_insert('muc_tieu', data)


