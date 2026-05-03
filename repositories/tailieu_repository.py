# repositories/tailieu_repository.py
from .base_repository import BaseRepository
from typing import List

class TaiLieuRepository(BaseRepository):
    """Repository quản lý Học liệu / Tài liệu học tập."""

    def get_by_hp(self, hp_id: int) -> List[dict]:
        return self._fetch_all("SELECT * FROM hoc_lieu WHERE hp_id=? ORDER BY loai, id", (hp_id,))

    def set_all(self, hp_id: int, items: List[dict]):
        """Xóa cũ và thêm mới toàn bộ học liệu của 1 HP."""
        with self.db.transaction():
            self.conn.execute("DELETE FROM hoc_lieu WHERE hp_id=?", (hp_id,))
            for i, item in enumerate(items):
                item['hp_id'] = hp_id
                item['so_thu_tu'] = i + 1
                self._safe_insert('hoc_lieu', item)
