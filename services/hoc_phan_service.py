# services/hoc_phan_service.py
import json

class HocPhanService:
    def __init__(self, repository, validation_service=None):
        self.repo = repository
        self.db = repository.db
        self.validator = validation_service

    def save_hoc_phan(self, hp_id, data):
        """
        Lưu dữ liệu học phần. 
        data: dict chứa tất cả thông tin từ các section.
        """
    def save_hoc_phan_partial(self, hp_id, modified_data):
        """
        Lưu dữ liệu học phần - Chỉ lưu các section có trong modified_data.
        modified_data: dict { 'sec1': {...}, 'sec3': {...}, ... }
        """
        hp_fields = [
            'ten_viet', 'ten_anh', 'ma', 'trinh_do', 'hp_tien_quyet', 
            'hp_thay_the', 'co_thuc_hanh', 'so_tin_chi', 'loai', 
            'tinh_chat', 'khoa_id', 'gio_lt', 'gio_bt', 'gio_tl', 
            'gio_th_tn', 'gio_th', 'gio_bt_th', 'gio_kt', 'gio_tu_hoc', 'tong_gio'
        ]

        for sec_key, sec_data in modified_data.items():
            if sec_key == 'sec1':
                hp_data = {k: sec_data[k] for k in hp_fields if k in sec_data}
                if hp_data:
                    self.repo.update(hp_id, hp_data)
                if 'ctdt_links' in sec_data:
                    self.repo.update_ctdt_links(hp_id, sec_data['ctdt_links'])
                if 'gv_rows' in sec_data:
                    self.repo.set_gv(hp_id, sec_data['gv_rows'])
            
            elif sec_key == 'sec2':
                # sec2 (Mô tả) thường là tech_phan table 'mo_ta'
                self.repo.update(hp_id, {'mo_ta': sec_data.get('mo_ta', '')})
            
            elif sec_key == 'sec3':
                self.repo.set_muc_tieu(hp_id, sec_data.get('rows', []))
            
            elif sec_key == 'sec4':
                self.repo.set_clo(hp_id, sec_data.get('rows', []))
            
            elif sec_key == 'sec5':
                self.repo.set_hoc_lieu(hp_id, sec_data.get('rows', []))
            
            elif sec_key == 'sec6':
                # Mục 6 có phan='lt' và phan='th'
                if 'lt_rows' in sec_data:
                    self.repo.set_noi_dung(hp_id, 'lt', sec_data['lt_rows'])
                if 'th_rows' in sec_data:
                    self.repo.set_noi_dung(hp_id, 'th', sec_data['th_rows'])
            
            elif sec_key == 'sec7':
                self.repo.update(hp_id, {'pp_day_hoc': sec_data.get('pp_day_hoc', '')})
            
            elif sec_key == 'sec8':
                task_fields = ['nhiem_vu_sv_len_lop', 'nhiem_vu_sv_bai_tap', 'nhiem_vu_sv_dung_cu', 'nhiem_vu_sv_khac']
                task_data = {k: sec_data[k] for k in task_fields if k in sec_data}
                if task_data:
                    self.repo.update(hp_id, task_data)
                self.repo.set_ke_hoach_kt(hp_id, sec_data.get('rows', []))
            
            elif sec_key == 'sec9':
                sig_fields = ['dia_diem_ky', 'ngay_ky', 'chuc_danh_ky_trai', 'ho_ten_ky_trai', 'chuc_danh_ky_phai', 'ho_ten_ky_phai']
                sig_data = {k: sec_data[k] for k in sig_fields if k in sec_data}
                if sig_data:
                    self.repo.update(hp_id, sig_data)
                self.repo.set_lich_su(hp_id, sec_data.get('rows', []))

        self.repo.delete_draft(hp_id)
        return True

    def save_hoc_phan(self, hp_id, data):
        """Lưu toàn bộ dữ liệu (Legacy/Recovery)"""
        # Chuyển đổi sang format partial để dùng code dùng chung
        modified = {f'sec{i+1}': data[f'sec{i+1}'] for i in range(9) if f'sec{i+1}' in data}
        if not modified:
            # Fallback for merged data format
            modified = {'sec1': data} 
        return self.save_hoc_phan_partial(hp_id, modified)

    def clone_hoc_phan(self, hp_id):
        return self.repo.clone(hp_id)

    def delete_hoc_phan(self, hp_id):
        self.repo.delete(hp_id)

    def get_full_data(self, hp_id):
        hp = self.repo.get_by_id(hp_id)
        if not hp: return None
        
        # Bổ sung các thông tin liên quan
        hp['ctdt_links'] = self.repo.get_ctdt_links(hp_id)
        hp['gv_rows'] = self.repo.get_gv(hp_id)
        
        return hp
