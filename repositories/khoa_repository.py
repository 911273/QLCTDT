# repositories/khoa_repository.py
from .base_repository import BaseRepository
from typing import List, Optional

class KhoaRepository(BaseRepository):
    def get_all(self) -> List[dict]:
        return self._fetch_all("SELECT * FROM khoa ORDER BY ten")

    def get_by_id(self, id_: int) -> Optional[dict]:
        return self._fetch_one("SELECT * FROM khoa WHERE id=?", (id_,))

    def create(self, ma: str, ten: str) -> int:
        return self._safe_insert('khoa', {'ma': ma, 'ten': ten})

    def update(self, id_: int, ma: str, ten: str):
        self._safe_update('khoa', id_, {'ma': ma, 'ten': ten})

    def delete(self, id_: int):
        self.conn.execute("DELETE FROM khoa WHERE id=?", (id_,))
