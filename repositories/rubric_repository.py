# repositories/rubric_repository.py
from repositories.base_repository import BaseRepository

class RubricRepository(BaseRepository):
    def get_all(self, ma_hp):
        return self.conn.execute("SELECT * FROM Rubric WHERE ma_hp=?", (ma_hp,)).fetchall()

    def get_tieu_chi(self, rubric_id):
        return self.conn.execute("SELECT * FROM Rubric_TieuChi WHERE rubric_id=? ORDER BY thu_tu", (rubric_id,)).fetchall()

    def insert(self, data: dict):
        fields = list(data.keys())
        sql = f"INSERT INTO Rubric({','.join(fields)}) VALUES({','.join(['?']*len(fields))})"
        cur = self.conn.execute(sql, list(data.values()))
        self.conn.commit()
        return cur.lastrowid

    def insert_tieu_chi(self, data: dict):
        fields = list(data.keys())
        sql = f"INSERT INTO Rubric_TieuChi({','.join(fields)}) VALUES({','.join(['?']*len(fields))})"
        cur = self.conn.execute(sql, list(data.values()))
        self.conn.commit()
        return cur.lastrowid
