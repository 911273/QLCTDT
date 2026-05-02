# repositories/clo_repository.py
from repositories.base_repository import BaseRepository

class CLORepository(BaseRepository):
    def get_all(self, ma_hp):
        return self.conn.execute("SELECT * FROM CLO_Standard WHERE ma_hp=? ORDER BY thu_tu", (ma_hp,)).fetchall()

    def get_by_id(self, id):
        return self.conn.execute("SELECT * FROM CLO_Standard WHERE id=?", (id,)).fetchone()

    def insert(self, data: dict):
        fields = list(data.keys())
        sql = f"INSERT INTO CLO_Standard({','.join(fields)}) VALUES({','.join(['?']*len(fields))})"
        cur = self.conn.execute(sql, list(data.values()))
        self.conn.commit()
        return cur.lastrowid

    def update(self, id, data: dict):
        sets = ','.join(f"{k}=?" for k in data.keys())
        self.conn.execute(f"UPDATE CLO_Standard SET {sets} WHERE id=?", list(data.values()) + [id])
        self.conn.commit()

    def delete(self, id):
        self.conn.execute("DELETE FROM CLO_Standard WHERE id=?", (id,))
        self.conn.commit()

    # MucTieu_HP
    def get_all_muc_tieu(self, ma_hp):
        return self.conn.execute("SELECT * FROM MucTieu_HP WHERE ma_hp=? ORDER BY thu_tu", (ma_hp,)).fetchall()

    def insert_muc_tieu(self, data: dict):
        fields = list(data.keys())
        sql = f"INSERT INTO MucTieu_HP({','.join(fields)}) VALUES({','.join(['?']*len(fields))})"
        cur = self.conn.execute(sql, list(data.values()))
        self.conn.commit()
        return cur.lastrowid
