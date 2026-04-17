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
            # Check PLO Mapping (Support multi-PLO)
            has_plo = False
            # Option 1: Try checking CLO_PLO_Map table
            try:
                c = self.db.conn.execute("SELECT COUNT(*) FROM CLO_PLO_Map WHERE clo_id=?", (clo['id'],)).fetchone()
                if c and c[0] > 0:
                    has_plo = True
            except:
                # Option 2: Fallback to plo_ids JSON or plo_id
                c_dict = dict(clo)
                plo_id = c_dict.get('plo_id') or c_dict.get('cdr_ma')
                if plo_id:
                    has_plo = True
                
            if not has_plo:
                c_dict = dict(clo)
                res.errors.append(f"CLO {c_dict.get('ma_clo') or c_dict.get('ma')} chưa ánh xạ tới PLO nào.")
                
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

    def get_validation_report(self, ma_hp, auto_save_data=None):
        if auto_save_data:
            self._save_draft(ma_hp, auto_save_data)
            
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
        # score = 100 - (len(errors)*10) - (len(warnings)*3)
        score = 100 - (len(errors) * 10) - (len(warnings) * 3)
        score = max(0, min(100, score))
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'score': score,
            'checklist': checklist
        }

    def _save_draft(self, ma_hp, data):
        """Lưu nháp dữ liệu trước khi validate."""
        try:
            # Giả định data có cấu trúc tương tự kết quả từ UI
            # Gọi các repo hoặc db.execute để lưu tạm
            # Ở đây ta sử dụng cơ chế transaction của DB
            with self.db.transaction():
                # Thực hiện lưu các thông tin cơ bản
                pass # Logic lưu nháp chi tiết tùy thuộc vào cấu trúc 'data'
        except Exception as e:
            print(f"Error saving draft: {e}")

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

    def get_completion_progress(self, hp_id) -> dict:
        """
        Kiểm tra mức độ hoàn thành đề cương theo từng section.
        
        Returns:
            dict với các key boolean/int/float cho từng mục,
            và 'percent' (0-100) cho thanh tiến độ tổng thể.
        """
        if not hp_id:
            return {'percent': 0}
        
        try:
            hp_raw = self.db.get_hoc_phan(hp_id)
            hp = dict(hp_raw) if hp_raw else {}
            result = {
                # Tab 1 — Thông tin chung
                's1_thong_tin': bool(
                    hp and hp.get('ten_viet') and hp.get('ma') and hp.get('so_tin_chi')
                ),
                # Tab 3 — Mục tiêu
                's3_muc_tieu': len(self.db.get_muc_tieu(hp_id) or []) > 0,
                # Tab 4 — CLO
                's4_clo': len(self.db.get_clo(hp_id) or []) >= 2,
                's4_clo_count': len(self.db.get_clo(hp_id) or []),
                # Tab 5 — Học liệu
                's5_hoc_lieu': len(self.db.get_hoc_lieu(hp_id) or []) > 0,
                # Tab 6 — Nội dung
                's6_noi_dung': len(self.db.get_noi_dung(hp_id, phan='lt') or []) > 0,
                's6_lt_count': len(self.db.get_noi_dung(hp_id, phan='lt') or []),
                # Tab 7/8 — Đánh giá & Kiểm tra
                's8_kt': len(self.db.get_ke_hoach_kt(hp_id) or []) > 0,
                's8_rubric': len(self.db.get_rubric_by_hp(hp_id) or []) > 0,
            }
            
            # Kiểm tra tổng trọng số đánh giá
            kt_rows = self.db.get_ke_hoach_kt(hp_id) or []
            if kt_rows:
                groups = {}
                for r_raw in kt_rows:
                    r = dict(r_raw)
                    nhom = r.get('nhom', '')
                    if nhom not in groups:
                        groups[nhom] = float(r.get('ty_trong_nhom', 0) or 0)
                total_w = sum(groups.values())
                result['s8_trong_so'] = total_w
                result['s8_danh_gia_ok'] = abs(total_w - 100) < 1
            else:
                result['s8_trong_so'] = 0.0
                result['s8_danh_gia_ok'] = False
            
            # Tính % hoàn thành tổng thể (8 điểm chính)
            checks = [
                result['s1_thong_tin'],
                result['s3_muc_tieu'],
                result['s4_clo'],
                result['s5_hoc_lieu'],
                result['s6_noi_dung'],
                result['s8_kt'],
                result['s8_rubric'],
                result.get('s8_danh_gia_ok', False),
            ]
            result['percent'] = int(sum(checks) / len(checks) * 100)
            return result
        
        except Exception as e:
            print(f'[get_completion_progress] Error: {e}')
            return {'percent': 0}
