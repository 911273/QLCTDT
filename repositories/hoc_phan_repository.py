# repositories/hoc_phan_repository.py
from datetime import datetime
from .base_repository import BaseRepository

class HocPhanRepository(BaseRepository):
    def get_all(self):
        return self.db.get_all_hoc_phan()

    def get_by_id(self, hp_id):
        return self.db.get_hoc_phan(hp_id)

    def search(self, keyword):
        return self.db.search_hoc_phan(keyword)

    def create(self, data: dict) -> int:
        return self.db.add_hoc_phan(data)

    def update(self, hp_id, data: dict):
        self.db.update_hoc_phan(hp_id, data)

    def delete(self, hp_id):
        self.db.delete_hoc_phan(hp_id)

    def clone(self, hp_id):
        return self.db.clone_hoc_phan(hp_id)

    def get_gv(self, hp_id):
        return self.db.get_gv_of_hp(hp_id)

    def set_gv(self, hp_id, gv_list):
        self.db.set_gv_of_hp(hp_id, gv_list)

    def get_ctdt_links(self, hp_id):
        return self.db.get_ctdt_of_hp(hp_id)

    def update_ctdt_links(self, hp_id, ctdt_links):
        self.db.update_hp_ctdt_links(hp_id, ctdt_links)

    def set_muc_tieu(self, hp_id, items):
        self.db.set_muc_tieu(hp_id, items)

    def set_clo(self, hp_id, items):
        self.db.set_clo(hp_id, items)

    def set_hoc_lieu(self, hp_id, items):
        self.db.set_hoc_lieu(hp_id, items)

    def set_noi_dung(self, hp_id, phan, items):
        # We need to handle tree structure for noi_dung
        # For simplicity, if service passes a flat list, we can clear and re-insert
        # But for efficiency, we normally use the existing set_noi_dung approach
        # Actually, db.py has add_noi_dung. 
        # I'll let service handle the complex logic if needed or use a clear/add approach.
        self.db.delete_noi_dung_hp(hp_id, phan)
        for d in items:
            d['hp_id'] = hp_id
            d['phan'] = phan
            self.db.add_noi_dung(d)

    def set_ke_hoach_kt(self, hp_id, items):
        self.db.set_ke_hoach_kt(hp_id, items)

    def set_lich_su(self, hp_id, items):
        self.db.set_lich_su(hp_id, items)

    def calculate_hours(self, hp_id):
        return self.db.calculate_and_update_hours(hp_id)
        
    def get_ids_by_nature(self, nature):
        return self.db.get_hp_ids_by_nature(nature)

    def log_change(self, hp_id, table_name, field_name, old_val, new_val, action='UPDATE'):
        self.db.log_change(hp_id, table_name, field_name, old_val, new_val, action)

    def save_draft(self, hp_id, data_json):
        self.db.save_draft(hp_id, data_json)

    def get_draft(self, hp_id):
        return self.db.get_draft(hp_id)

    def delete_draft(self, hp_id):
        self.db.delete_draft(hp_id)
