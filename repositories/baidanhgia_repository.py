# repositories/baidanhgia_repository.py
from repositories.base_repository import BaseRepository

class BaiDanhGiaRepository(BaseRepository):
    def get_all(self, ma_hp):
        return self.conn.execute("SELECT * FROM BaiDanhGia WHERE ma_hp=?", (ma_hp,)).fetchall()

    def insert(self, data: dict):
        fields = list(data.keys())
        sql = f"INSERT INTO BaiDanhGia({','.join(fields)}) VALUES({','.join(['?']*len(fields))})"
        cur = self.conn.execute(sql, list(data.values()))
        self.conn.commit()
        return cur.lastrowid

    def insert_clo_link(self, data: dict):
        fields = list(data.keys())
        sql = f"INSERT INTO BaiDanhGia_CLO({','.join(fields)}) VALUES({','.join(['?']*len(fields))})"
        self.conn.execute(sql, list(data.values()))
        self.conn.commit()
