# services/deccuong_service.py
# FIXED: C-02, C-03, C-04, C-05, M-05, N-07 — Toàn bộ query chuyển về bảng production
import json
from datetime import datetime
from services.validation_service import ValidationService


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

    def validate_hinh_thuc(self, hp_id):
        """FIXED C-02: Dùng bảng hp_giang_vien + giang_vien production với cột đúng."""
        res = ValidationResult('hinh_thuc')
        try:
            gvs = self.db.conn.execute("""
                SELECT hpgv.ho_ten, hpgv.hoc_ham_vi, hpgv.email, hpgv.sdt,
                       gv.ho_ten AS gv_ho_ten, gv.hoc_vi, gv.email AS gv_email, gv.sdt AS gv_sdt
                FROM hp_giang_vien hpgv
                LEFT JOIN giang_vien gv ON hpgv.gv_id = gv.id
                WHERE hpgv.hp_id = ?
            """, (hp_id,)).fetchall()

            for gv in gvs:
                ten = gv['ho_ten'] or gv['gv_ho_ten'] or '(Chưa rõ)'
                hoc_vi = gv['hoc_ham_vi'] or gv['hoc_vi']
                email = gv['email'] or gv['gv_email']
                sdt = gv['sdt'] or gv['gv_sdt']

                if not hoc_vi:
                    res.warnings.append(f"GV '{ten}' thiếu thông tin Học hàm/Học vị.")
                if not email or not sdt:
                    res.warnings.append(f"GV '{ten}' thiếu thông tin liên lạc (SĐT/Email).")
        except Exception as e:
            res.warnings.append(f"Không kiểm tra được đội ngũ GV: {e}")
        return res

    def validate_thong_tin_chung(self, hp_id):
        """FIXED: Dùng hp_id thay vì ma_hp."""
        res = ValidationResult('thong_tin')
        hp = self.db.get_hoc_phan(hp_id)
        if not hp:
            res.errors.append("Không tìm thấy dữ liệu học phần.")
            return res

        if not hp.get('ten_viet'):
            res.errors.append("Tên tiếng Việt của học phần không được rỗng.")
        if not hp.get('ten_anh'):
            res.warnings.append("Tên tiếng Anh chưa có.")

        tc = hp.get('so_tin_chi') or 0
        try:
            tc = int(tc)
        except (ValueError, TypeError):
            tc = 0

        if not (1 <= tc <= 10):
            res.errors.append(f"Số tín chỉ ({tc}) phải nằm trong khoảng 1-10.")

        # FIXED M-05: Quy tắc nhất quán: 1 TC = 15 tiết (giờ lên lớp)
        gio_lt = int(hp.get('gio_lt') or 0)
        gio_bt = int(hp.get('gio_bt') or 0)
        gio_th = int(hp.get('gio_th_tn') or 0)
        gio_tl = int(hp.get('gio_tl') or 0)
        tong_len_lop = gio_lt + gio_bt + gio_th + gio_tl
        expected = tc * 15
        if tong_len_lop < expected:
            res.warnings.append(
                f"Tổng giờ lên lớp ({tong_len_lop}) thấp hơn tiêu chuẩn tín chỉ ({tc} TC × 15 = {expected} tiết)."
            )

        # Kiểm tra GV phụ trách
        check_gv = self.db.conn.execute(
            "SELECT id FROM hp_giang_vien WHERE hp_id=? AND vai_tro='phu_trach'", (hp_id,)
        ).fetchone()
        if not check_gv:
            res.warnings.append("Chưa có giảng viên phụ trách chính.")

        return res

    def validate_muc_tieu_clo(self, hp_id):
        """FIXED C-03: Dùng bảng clo production."""
        res = ValidationResult('muc_tieu_clo')
        try:
            # FIXED: Query bảng production 'clo', không phải 'CLO_Standard'
            clos = self.db.conn.execute(
                "SELECT * FROM clo WHERE hp_id=? AND (la_tieu_de_nhom IS NULL OR la_tieu_de_nhom=0)",
                (hp_id,)
            ).fetchall()

            if len(clos) < 2:
                res.errors.append("Học phần phải có ít nhất 2 Chuẩn đầu ra (CLO).")

            for clo in clos:
                desc = (clo['mo_ta'] or "").strip().lower()
                # Kiểm tra động từ cấm
                for cam in self.DONG_TU_CAM:
                    if desc.startswith(cam):
                        res.errors.append(f"CLO '{clo['ma']}' dùng động từ cấm: '{cam}'.")

                # Kiểm tra PLO mapping (dùng cột cdr_ma trong bảng production)
                if not clo['cdr_ma']:
                    res.warnings.append(f"CLO '{clo['ma']}' chưa ánh xạ tới PLO/CDR nào.")

        except Exception as e:
            res.warnings.append(f"Không kiểm tra được CLO: {e}")

        # Kiểm tra Mục tiêu
        try:
            mts = self.db.conn.execute(
                "SELECT * FROM muc_tieu WHERE hp_id=? AND (la_tieu_de_nhom IS NULL OR la_tieu_de_nhom=0)",
                (hp_id,)
            ).fetchall()
            if not mts:
                res.warnings.append("Học phần chưa có Mục tiêu (PO/MT) nào.")
        except Exception as e:
            res.warnings.append(f"Không kiểm tra được Mục tiêu: {e}")

        return res

    def validate_noi_dung(self, hp_id):
        """FIXED C-04: Dùng bảng noi_dung production."""
        res = ValidationResult('noi_dung')
        try:
            hp = self.db.get_hoc_phan(hp_id)
            if not hp:
                res.errors.append("Không tìm thấy học phần.")
                return res

            # FIXED: Query bảng production 'noi_dung', không phải 'NoiDung_LT'
            lt_rows = self.db.conn.execute(
                "SELECT * FROM noi_dung WHERE hp_id=? AND phan='lt'", (hp_id,)
            ).fetchall()
            lt_total = sum((r['gio_lt'] or 0) for r in lt_rows)

            gio_lt_hp = int(hp.get('gio_lt') or 0)
            if gio_lt_hp > 0 and abs(lt_total - gio_lt_hp) > 0.5:
                res.warnings.append(
                    f"Tổng giờ LT trong nội dung ({lt_total}) khác khai báo ở Mục 1 ({gio_lt_hp})."
                )

            # Kiểm tra tài liệu học tập chính — dùng bảng hoc_lieu production
            tls = self.db.conn.execute(
                "SELECT * FROM hoc_lieu WHERE hp_id=? AND loai='chinh'", (hp_id,)
            ).fetchall()
            if not tls:
                res.warnings.append("Học phần phải có ít nhất 1 tài liệu học tập chính.")

        except Exception as e:
            res.warnings.append(f"Không kiểm tra được nội dung: {e}")

        return res

    def validate_danh_gia(self, hp_id):
        """FIXED C-05: Dùng bảng ke_hoach_kiem_tra production."""
        res = ValidationResult('danh_gia')
        try:
            # FIXED: Query bảng production 'ke_hoach_kiem_tra', không phải 'BaiDanhGia'
            kt_rows = self.db.conn.execute(
                "SELECT * FROM ke_hoach_kiem_tra WHERE hp_id=?", (hp_id,)
            ).fetchall()

            if not kt_rows:
                res.warnings.append("Học phần chưa có kế hoạch kiểm tra – đánh giá nào.")
                return res

            # Tính tổng trọng số từng nhóm
            groups = {}
            for r in kt_rows:
                nhom = r['nhom'] or 'Khác'
                if nhom not in groups:
                    try:
                        groups[nhom] = float(r['ty_trong_nhom'] or 0)
                    except (ValueError, TypeError):
                        groups[nhom] = 0.0

            total_group_weight = sum(groups.values())
            # Trọng số nhóm có thể lưu dạng % (30, 70) hoặc tỷ lệ (0.3, 0.7)
            if total_group_weight > 1.5:  # Đang lưu dạng %
                is_pct = True
                target = 100.0
            else:
                is_pct = False
                target = 1.0

            if abs(total_group_weight - target) > 0.5:
                pct_display = f"{total_group_weight:.0f}%" if is_pct else f"{total_group_weight*100:.0f}%"
                res.errors.append(
                    f"Tổng trọng số các nhóm đánh giá là {pct_display} (Kỳ vọng: 100%)."
                )

            # Kiểm tra CLO coverage
            clos = self.db.conn.execute(
                "SELECT ma FROM clo WHERE hp_id=? AND (la_tieu_de_nhom IS NULL OR la_tieu_de_nhom=0)",
                (hp_id,)
            ).fetchall()
            clo_codes = {c['ma'] for c in clos}
            covered = set()
            for r in kt_rows:
                if r['clo_lien_quan']:
                    for code in r['clo_lien_quan'].replace(',', ' ').split():
                        covered.add(code.strip())
            missing = clo_codes - covered
            if missing:
                res.warnings.append(f"Có {len(missing)} CLO chưa có bài đánh giá: {', '.join(sorted(missing))}.")

        except Exception as e:
            res.warnings.append(f"Không kiểm tra được đánh giá: {e}")

        return res


class DeCuongService:
    def __init__(self, db):
        self.db = db
        self.validator = DeCuongValidator(db)

    def get_validation_report(self, hp_id, auto_save_data=None):
        """FIXED: Nhận hp_id (int) thay vì ma_hp (str)."""
        if not hp_id:
            return {'is_valid': False, 'errors': ['Chưa chọn học phần'], 'warnings': [], 'score': 0, 'checklist': {}}

        # Chạy 5 nhóm validation cơ bản (V1)
        v_hinh_thuc = self.validator.validate_hinh_thuc(hp_id)
        v_thong_tin = self.validator.validate_thong_tin_chung(hp_id)
        v_clo = self.validator.validate_muc_tieu_clo(hp_id)
        v_noi_dung = self.validator.validate_noi_dung(hp_id)
        v_danh_gia = self.validator.validate_danh_gia(hp_id)

        results = [v_hinh_thuc, v_thong_tin, v_clo, v_noi_dung, v_danh_gia]

        errors = []
        warnings = []
        checklist = {}
        for r in results:
            errors.extend(r.errors)
            warnings.extend(r.warnings)
            checklist[r.category] = r.status
            
        # 2026 Validation Integration
        hp = self.db.get_hoc_phan(hp_id)
        if hp:
            v_stat, v_msg = ValidationService.check_total_hours(hp)
            if not v_stat:
                errors.append(v_msg)
        
        clos = self.db.get_clo(hp_id)
        v_bloom_stat, v_bloom_msg = ValidationService.check_clo_bloom(clos)
        if not v_bloom_stat:
            errors.append(v_bloom_msg)
            
        v_phd_stat, v_phd_msg = ValidationService.check_phd_requirements(self.db, hp_id)
        if not v_phd_stat:
            errors.append(v_phd_msg)

        score = max(0, min(100, 100 - len(errors) * 10 - len(warnings) * 3))

        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'score': score,
            'checklist': checklist
        }
    
    def change_status(self, hp_id, new_status, user_role, user_id, reason=""):
        """State machine check for lifecycle of syllabus"""
        hp = self.db.get_hoc_phan(hp_id)
        if not hp: return False, "Không tìm thấy học phần."
        
        current_status = hp.get('trang_thai') or 'nhap'
        
        valid_transitions = {
            'nhap': ['cho_duyet'],
            'can_sua': ['cho_duyet'],
            'cho_duyet': ['da_duyet', 'can_sua', 'nhap'],
            'da_duyet': ['can_sua']
        }
        
        if new_status not in valid_transitions.get(current_status, []):
            return False, f"Không thể chuyển trạng thái từ '{current_status}' sang '{new_status}'."
            
        if new_status == 'da_duyet' and user_role not in ['admin', 'quan_ly']:
            return False, "Chỉ Quản lý hoặc Quản trị viên mới có quyền Duyệt đề cương."
        
        # Enforce basic validation before pending review
        if new_status == 'cho_duyet':
            val_report = self.get_validation_report(hp_id)
            if not val_report['is_valid']:
                return False, "Không thể Gửi Duyệt: Đề cương chưa vượt qua tất cả các kiểm tra lỗi (Errors)."
        
        # Execute DB action
        success = self.db.update_trang_thai(hp_id, new_status)
        if success:
            # Ghi Log
            lan = len(self.db.get_lich_su(hp_id) or []) + 1
            self.db.add_lich_su_cap_nhat(hp_id, {
                'lan': lan,
                'noi_dung': f"Trạng thái: {current_status} -> {new_status}. {reason}".strip(),
                'nguoi_cap_nhat': user_id,
                'ngay_cap_nhat': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            return True, "Cập nhật trạng thái thành công."
        return False, "Lỗi cập nhật CSDL."

    def get_matrix_clo_plo(self, hp_id):
        """FIXED N-07: Dùng bảng clo + cdr_ctdt production."""
        try:
            # FIXED: Query bảng production 'clo', dùng cột 'ma' và 'cdr_ma'
            clos = self.db.conn.execute(
                "SELECT ma, cdr_ma, level_irm FROM clo WHERE hp_id=? AND (la_tieu_de_nhom IS NULL OR la_tieu_de_nhom=0) ORDER BY id",
                (hp_id,)
            ).fetchall()
            plos = self.db.conn.execute("SELECT ma FROM cdr_ctdt ORDER BY ma").fetchall()

            plo_list = [p['ma'] for p in plos]
            matrix = [["CLO/PLO"] + plo_list]

            for clo in clos:
                row = [clo['ma']]
                for plo in plo_list:
                    if clo['cdr_ma'] == plo:
                        row.append(clo['level_irm'] or 'X')
                    else:
                        row.append("-")
                matrix.append(row)
            return matrix
        except Exception as e:
            print(f"[get_matrix_clo_plo] Error: {e}")
            return []

    def get_summary_stats(self, hp_id):
        """FIXED: Dùng hp_id và bảng production."""
        try:
            hp = self.db.get_hoc_phan(hp_id)
            clos = self.db.get_clo(hp_id)

            return {
                'hp_id': hp_id,
                'ten_hp': hp['ten_viet'] if hp else 'N/A',
                'so_tc': hp['so_tin_chi'] if hp else 0,
                'tong_gio': hp['tong_gio'] if hp else 0,
                'count_clo': len(clos),
                'timestamp': datetime.now().strftime("%d/%m/%Y %H:%M")
            }
        except Exception as e:
            return {'hp_id': hp_id, 'ten_hp': 'N/A', 'so_tc': 0, 'tong_gio': 0, 'count_clo': 0}

    def get_completion_progress(self, hp_id) -> dict:
        """
        Kiểm tra mức độ hoàn thành đề cương theo từng section.
        Returns dict với % hoàn thành và trạng thái từng section.
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
                # Tab 8 — Kế hoạch KT
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
                # Normalize: nếu lưu dạng % thì chia 100
                if total_w > 1.5:
                    total_w_normalized = total_w  # đang là %, target = 100
                    result['s8_trong_so'] = total_w
                    result['s8_danh_gia_ok'] = abs(total_w - 100) < 1
                else:
                    result['s8_trong_so'] = total_w * 100
                    result['s8_danh_gia_ok'] = abs(total_w - 1.0) < 0.01
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
