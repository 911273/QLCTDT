# repositories/ctdt_repository.py
from .base_repository import BaseRepository
from typing import List, Optional

class CTDTRepository(BaseRepository):
    def get_all(self) -> List[dict]:
        return self._fetch_all("SELECT * FROM [chuong_trinh_dao_tao] ORDER BY ten")

    def get_by_id(self, id_: int) -> Optional[dict]:
        return self._fetch_one("SELECT * FROM [chuong_trinh_dao_tao] WHERE id=?", (id_,))

    # ── PO / PLO / PI ─────────────────────────────────────────────────────────
    
    def get_plos(self, ctdt_id: int) -> List[dict]:
        return self._fetch_all("SELECT * FROM [ctdt_plo] WHERE ctdt_id=? ORDER BY ma", (ctdt_id,))

    def get_pos(self, ctdt_id: int) -> List[dict]:
        return self._fetch_all("SELECT * FROM [ctdt_po] WHERE ctdt_id=? ORDER BY ma", (ctdt_id,))

    # ── CDR ──────────────────────────────────────────────────────────────────
    
    def get_all_cdr(self) -> List[dict]:
        return self._fetch_all("SELECT * FROM [cdr_ctdt] ORDER BY ma")

    def create_cdr(self, ma: str, mo_ta: str = '', trinh_do: str = 'Đại học') -> int:
        return self._safe_insert('cdr_ctdt', {'ma': ma, 'mo_ta': mo_ta, 'trinh_do': trinh_do})

    def update_cdr(self, id_: int, ma: str, mo_ta: str = '', trinh_do: str = 'Đại học'):
        self._safe_update('cdr_ctdt', id_, {'ma': ma, 'mo_ta': mo_ta, 'trinh_do': trinh_do})

    def delete_cdr(self, id_: int):
        self.conn.execute("DELETE FROM [cdr_ctdt] WHERE id=?", (id_,))
