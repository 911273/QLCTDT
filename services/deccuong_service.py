# services/deccuong_service.py
import json
from datetime import datetime

class ValidationResult:
    def __init__(self, category):
        self.category = category
        self.errors = []
        self.warnings = []
        
    @property
    def status(self):
        if self.errors: return 'fail'
        if self.warnings: return 'warn'
        return 'pass'

class DeCuongValidator:
    DONG_TU_CAM = ['biết', 'hiểu', 'nắm vững', 'biết được', 'hiểu được']
    DONG_TU_BLOOM = {
        1: ['nhận biết', 'nhớ', 'liệt kê', 'xác định', 'gọi tên', 'mô tả'],
        2: ['giải thích', 'phân biệt', 'mô tả', 'tóm tắt', 'minh họa'],
        3: ['áp dụng', 'tính toán', 'thực hiện', 'sử dụng', 'vận dụng'],
        4: ['phân tích', 'so sánh', 'phân loại', 'lập luận', 'chứng minh'],
        5: ['đánh giá', 'phê phán', 'lựa chọn', 'biện luận', 'phê bình'],
        6: ['thiết kế', 'xây dựng', 'đề xuất', 'sáng tạo', 'phát triển']
    }

    def __init__(self, db):
        self.db = db

    def validate_hinh_thuc(self, ma_hp):
        res = ValidationResult('hinh_thuc')
        # Kiểm tra thông tin GV
        gvs = self.db.conn.execute("SELECT * FROM GiangVien_HP gv JOIN giang_vien m ON gv.gv_id = m.id WHERE gv.ma_hp=?", (ma_hp,)).fetchall()
        for gv in gvs:
            if not gv['hoc_ham'] or not gv['hoc_vi']:
                res.warnings.append(f"GV {gv['ten']} thiếu thông tin Học hàm/Học vị.")
            if not gv['sdt'] or not gv['email']:
                res.warnings.append(f"GV {gv['ten']} thiếu thông tin liên lạc (SĐT/Email).")
        return res

    def validate_thong_tin_chung(self, ma_hp):
        res = ValidationResult('thong_tin')
        hp = self.db.conn.execute("SELECT * FROM hoc_phan WHERE ma=? OR ma_hp=?", (ma_hp, ma_hp)).fetchone()
        if not hp:
            res.errors.append("Không tìm thấy dữ liệu học phần.")
            return res
        
        if not hp['ten_viet'] or not hp['ten_anh']:
            res.errors.append("Tên học phần (VN/EN) không được rỗng.")
        
        tc = hp['so_tin_chi'] or 0
        if not (1 <= tc <= 10):
            res.errors.append("Số tín chỉ phải nằm trong khoảng 1-10.")
            
        target_gio = tc * 50
        actual_total = hp['tong_gio'] or 0
        if actual_total != target_gio:
            res.errors.append(f"Tổng giờ ({actual_total}) không khớp với số tín chỉ ({target_gio}).")
            
        phon_bo = (hp['gio_lt'] or 0) + (hp['gio_bt'] or 0) + (hp['gio_th_tn'] or 0) + (hp['gio_tl'] or 0)
        if phon_bo != actual_total:
            res.errors.append(f"Tổng giờ phân bổ ({phon_bo}) khác Tổng giờ ({actual_total}).")
            
        check_gv = self.db.conn.execute("SELECT id FROM GiangVien_HP WHERE ma_hp=? AND vai_tro='chinh'", (ma_hp,)).fetchone()
        if not check_gv:
            res.errors.append("Chưa có giảng viên phụ trách chính.")
            
        return res

    def validate_muc_tieu_clo(self, ma_hp):
        res = ValidationResult('muc_tieu_clo')
        clos = self.db.conn.execute("SELECT * FROM CLO_Standard WHERE ma_hp=?", (ma_hp,)).fetchall()
        
        if len(clos) < 2:
            res.errors.append("Học phần phải có ít nhất 2 Chuẩn đầu ra (CLO).")
            
        for clo in clos:
            desc = (clo['mo_ta'] or "").strip().lower()
            # Động từ cầm
            for cam in self.DONG_TU_CAM:
                if desc.startswith(cam):
                    res.errors.append(f"CLO {clo['ma_clo']} dùng động từ cấm: '{cam}'.")
            
            # Động từ Bloom check
            found_bloom = False
            for level, verbs in self.DONG_TU_BLOOM.items():
                if any(desc.startswith(v) for v in verbs):
                    found_bloom = True
                    break
            if not found_bloom:
                res.warnings.append(f"CLO {clo['ma_clo']} không bắt đầu bằng động từ hành động chuẩn Bloom.")
                
            if not clo['plo_id']:
                res.errors.append(f"CLO {clo['ma_clo']} chưa ánh xạ tới PLO nào.")
                
        # MT - CLO mapping
        mts = self.db.conn.execute("SELECT id, ma_mt FROM MucTieu_HP WHERE ma_hp=?", (ma_hp,)).fetchall()
        for mt in mts:
            # Giả định có bảng mapping MucTieu_CLO hoặc logic check tương ứng
            pass
            
        return res

    def validate_noi_dung(self, ma_hp):
        res = ValidationResult('noi_dung')
        hp = self.db.conn.execute("SELECT gio_lt, gio_th_tn FROM hoc_phan WHERE ma=?", (ma_hp,)).fetchone()
        
        # Tổng giờ LT trong nội dung
        lt_total = self.db.conn.execute("SELECT SUM(gio_lt) FROM NoiDung_LT WHERE ma_hp=?", (ma_hp,)).fetchone()[0] or 0
        if lt_total != hp['gio_lt']:
            res.errors.append(f"Tổng giờ LT trong nội dung ({lt_total}) khác khai báo ({hp['gio_lt']}).")
            
        # Tài liệu
        tls = self.db.conn.execute("SELECT * FROM TaiLieu_Standard WHERE ma_hp=? AND loai='chinh'", (ma_hp,)).fetchall()
        if not tls:
            res.errors.append("Học phần phải có ít nhất 1 tài liệu học tập chính.")
        else:
            current_year = datetime.now().year
            for tl in tls:
                try:
                    nam = int(tl['nam_xuat_ban'])
                    if nam < current_year - 5:
                        res.warnings.append(f"Tài liệu '{tl['ten_tai_lieu']}' xuất bản từ {nam} (quá 5 năm).")
                except: pass
                
        return res

    def validate_danh_gia(self, ma_hp):
        res = ValidationResult('danh_gia')
        bdgs = self.db.conn.execute("SELECT * FROM BaiDanhGia WHERE ma_hp=?", (ma_hp,)).fetchall()
        
        total_ts = sum(b['trong_so'] or 0 for b in bdgs)
        if abs(total_ts - 1.0) > 0.01:
            res.errors.append(f"Tổng trọng số bài đánh giá ({int(total_ts*100)}%) không bằng 100%.")
            
        # CLO covering
        clos = self.db.conn.execute("SELECT id, ma_clo FROM CLO_Standard WHERE ma_hp=?", (ma_hp,)).fetchall()
        for clo in clos:
            check = self.db.conn.execute("SELECT b.id FROM BaiDanhGia_CLO bc JOIN BaiDanhGia b ON bc.bai_danh_gia_id=b.id WHERE bc.clo_id=? AND b.ma_hp=?", (clo['id'], ma_hp)).fetchone()
            if not check:
                res.errors.append(f"CLO {clo['ma_clo']} chưa có bài đánh giá nào.")
                
        return res

class DeCuongService:
    def __init__(self, db):
        self.db = db
        self.validator = DeCuongValidator(db)

    def get_validation_report(self, ma_hp):
        # Chạy 5 nhóm validation
        v_hinh_thuc = self.validator.validate_hinh_thuc(ma_hp)
        v_thong_tin = self.validator.validate_thong_tin_chung(ma_hp)
        v_clo = self.validator.validate_muc_tieu_clo(ma_hp)
        v_noi_dung = self.validator.validate_noi_dung(ma_hp)
        v_danh_gia = self.validator.validate_danh_gia(ma_hp)
        
        results = [v_hinh_thuc, v_thong_tin, v_clo, v_noi_dung, v_danh_gia]
        
        errors = []
        warnings = []
        checklist = {}
        for r in results:
            errors.extend(r.errors)
            warnings.extend(r.warnings)
            checklist[r.category] = r.status
            
        # Calculate score (0-100)
        total_rules = 20 # Giả định 20 quy tắc
        fail_count = len(errors) * 2 + len(warnings)
        score = max(0, 100 - fail_count * 5)
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'score': score,
            'checklist': checklist
        }

    def get_matrix_clo_plo(self, ma_hp):
        clos = self.db.conn.execute("SELECT ma_clo, plo_id, level_irm FROM CLO_Standard WHERE ma_hp=? ORDER BY ma_clo", (ma_hp,)).fetchall()
        plos = self.db.conn.execute("SELECT ma FROM cdr_ctdt ORDER BY ma").fetchall()
        
        matrix = []
        plo_list = [p['ma'] for p in plos]
        matrix.append(["CLO/PLO"] + plo_list)
        
        for clo in clos:
            row = [clo['ma_clo']]
            for plo in plo_list:
                if clo['plo_id'] == plo:
                    row.append(clo['level_irm'] or 'X')
                else:
                    row.append("-")
            matrix.append(row)
        return matrix

    def get_summary_stats(self, ma_hp):
        hp = self.db.conn.execute("SELECT * FROM hoc_phan WHERE ma=?", (ma_hp,)).fetchone()
        clos = self.db.conn.execute("SELECT * FROM CLO_Standard WHERE ma_hp=?", (ma_hp,)).fetchall()
        
        return {
            'ma_hp': ma_hp,
            'ten_hp': hp['ten_viet'] if hp else 'N/A',
            'so_tc': hp['so_tin_chi'] if hp else 0,
            'tong_gio': hp['tong_gio'] if hp else 0,
            'count_clo': len(clos),
            'timestamp': datetime.now().strftime("%d/%m/%Y %H:%M")
        }
