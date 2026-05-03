# repositories/noidung_repository.py
from .base_repository import BaseRepository
from typing import List, Optional

class NoiDungRepository(BaseRepository):
    """Repository quản lý Nội dung chi tiết học phần (Mục 6)."""

    def get_by_hp(self, hp_id: int, phan: str = None) -> List[dict]:
        """Lấy danh sách nội dung, có thể lọc theo phân (Lý thuyết / Thực hành)."""
        sql = "SELECT * FROM noi_dung WHERE hp_id=? "
        params = [hp_id]
        if phan:
            sql += " AND phan=?"
            params.append(phan)
        sql += " ORDER BY cap_do, id"
        return self._fetch_all(sql, tuple(params))

    def set_all(self, hp_id: int, phan: str, items: List[dict]):
        """Cập nhật toàn bộ nội dung của một phần."""
        with self.db.transaction():
            self.conn.execute("DELETE FROM noi_dung WHERE hp_id=? AND phan=?", (hp_id, phan))
            for item in items:
                item['hp_id'] = hp_id
                item['phan'] = phan
                self._safe_insert('noi_dung', item)

    def delete_recursive(self, parent_id: int):
        """Xóa đệ quy nội dung con."""
        children = self._fetch_all("SELECT id FROM noi_dung WHERE parent_id=?", (parent_id,))
        for child in children:
            self.delete_recursive(child['id'])
        self.conn.execute("DELETE FROM noi_dung WHERE id=?", (parent_id,))

    def delete_by_hp(self, hp_id: int, phan: str = None):
        """Xóa toàn bộ nội dung của HP."""
        sql = "DELETE FROM noi_dung WHERE hp_id=?"
        params = [hp_id]
        if phan:
            sql += " AND phan=?"
            params.append(phan)
        self.conn.execute(sql, tuple(params))
