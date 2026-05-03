# repositories/rubric_repository.py
from repositories.base_repository import BaseRepository

class RubricRepository(BaseRepository):
    def get_by_hp(self, hp_id: int):
        return self.db.conn.execute(
            "SELECT * FROM rubric_danh_gia WHERE hp_id=? ORDER BY thu_tu", 
            (hp_id,)
        ).fetchall()

    def get_tieu_chi(self, rubric_id: int):
        return self.db.conn.execute(
            "SELECT * FROM rubric_tieu_chi WHERE rubric_id=? ORDER BY thu_tu", 
            (rubric_id,)
        ).fetchall()

    def get_full(self, hp_id: int):
        rubrics = self.get_by_hp(hp_id)
        result = []
        for rb in rubrics:
            rb_dict = dict(rb)
            rb_dict['tieu_chi_list'] = [dict(tc) for tc in self.get_tieu_chi(rb_dict['id'])]
            result.append(rb_dict)
        return result
