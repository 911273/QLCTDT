# repositories/giang_vien_repository.py
from .base_repository import BaseRepository
from typing import List, Optional

class GiangVienRepository(BaseRepository):
    def get_all(self) -> List[dict]:
        return self._fetch_all("""
            SELECT gv.*, k.ten AS ten_khoa 
            FROM giang_vien gv 
            LEFT JOIN khoa k ON gv.khoa_id = k.id 
            ORDER BY gv.ho_ten
        """)

    def get_by_id(self, id_: int) -> Optional[dict]:
        return self._fetch_one("SELECT * FROM giang_vien WHERE id=?", (id_,))

    def search(self, keyword: str) -> List[dict]:
        k = f"%{keyword}%"
        return self._fetch_all("""
            SELECT gv.*, k.ten AS ten_khoa 
            FROM giang_vien gv 
            LEFT JOIN khoa k ON gv.khoa_id = k.id 
            WHERE unaccent(gv.ho_ten) LIKE unaccent(?) 
               OR unaccent(gv.email) LIKE unaccent(?)
               OR unaccent(gv.sdt) LIKE unaccent(?)
            ORDER BY gv.ho_ten
        """, (k, k, k))

    def create(self, data: dict) -> int:
        return self._safe_insert('giang_vien', data)

    def update(self, id_: int, data: dict):
        self._safe_update('giang_vien', id_, data)

    def delete(self, id_: int):
        self.conn.execute("DELETE FROM [giang_vien] WHERE id=?", (id_,))

    # ── HP Relationship ───────────────────────────────────────────────────────

    def get_by_hp(self, hp_id: int) -> List[dict]:
        return self._fetch_all("""
            SELECT hgv.*, gv.id AS master_gv_id
            FROM [hp_giang_vien] hgv
            LEFT JOIN [giang_vien] gv ON hgv.gv_id = gv.id
            WHERE hgv.hp_id=?
            ORDER BY hgv.thu_tu, hgv.vai_tro DESC
        """, (hp_id,))

    def set_for_hp(self, hp_id: int, gv_list: List[dict]):
        with self.db.transaction():
            self.conn.execute("DELETE FROM [hp_giang_vien] WHERE hp_id=?", (hp_id,))
            for item in gv_list:
                data = {**item, 'hp_id': hp_id}
                self._safe_insert('hp_giang_vien', data)

