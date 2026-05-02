# repositories/tailieu_repository.py
from repositories.base_repository import BaseRepository

class TaiLieuRepository(BaseRepository):
    def get_all(self, ma_hp):
        return self.conn.execute("SELECT * FROM TaiLieu_Standard WHERE ma_hp=? ORDER BY loai, thu_tu", (ma_hp,)).fetchall()

    def insert(self, data: dict):
        fields = list(data.keys())
        sql = f"INSERT INTO TaiLieu_Standard({','.join(fields)}) VALUES({','.join(['?']*len(fields))})"
        cur = self.conn.execute(sql, list(data.values()))
        self.conn.commit()
        return cur.lastrowid
