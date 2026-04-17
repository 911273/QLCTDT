# repositories/noidung_repository.py
from repositories.base_repository import BaseRepository

class NoiDungRepository(BaseRepository):
    # NoiDung_LT
    def get_lt_all(self, ma_hp):
        return self.conn.execute("SELECT * FROM NoiDung_LT WHERE ma_hp=? ORDER BY stt", (ma_hp,)).fetchall()

    def insert_lt(self, data: dict):
        fields = list(data.keys())
        sql = f"INSERT INTO NoiDung_LT({','.join(fields)}) VALUES({','.join(['?']*len(fields))})"
        cur = self.conn.execute(sql, list(data.values()))
        self.conn.commit()
        return cur.lastrowid

    # NoiDung_TH
    def get_th_all(self, ma_hp):
        return self.conn.execute("SELECT * FROM NoiDung_TH WHERE ma_hp=? ORDER BY stt", (ma_hp,)).fetchall()

    def insert_th(self, data: dict):
        fields = list(data.keys())
        sql = f"INSERT INTO NoiDung_TH({','.join(fields)}) VALUES({','.join(['?']*len(fields))})"
        cur = self.conn.execute(sql, list(data.values()))
        self.conn.commit()
        return cur.lastrowid

    def update_lt(self, id, data: dict):
        sets = ','.join(f"{k}=?" for k in data.keys())
        self.conn.execute(f"UPDATE NoiDung_LT SET {sets} WHERE id=?", list(data.values()) + [id])
        self.conn.commit()

    def delete_lt(self, id):
        self.conn.execute("DELETE FROM NoiDung_LT WHERE id=?", (id,))
        self.conn.commit()
