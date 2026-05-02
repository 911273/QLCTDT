# services/validation_service.py
import re

class ValidationService:
    @staticmethod
    def check_total_hours(hp_data):
        try:
            tc = int(hp_data.get('so_tin_chi') or 3)
            expected_hours = tc * 50
            lt = float(hp_data.get('gio_lt') or 0)
            bt = float(hp_data.get('gio_bt') or 0)
            th = float(hp_data.get('gio_th_tn') or 0)
            tl = float(hp_data.get('gio_tl') or 0)
            tu_hoc = float(hp_data.get('gio_tu_hoc') or 0)
            tt = float(hp_data.get('gio_thuc_tap') or 0)
            total = lt + bt + th + tl + tu_hoc + tt
            
            # Allow minor float precision issues
            if abs(total - expected_hours) > 0.1:
                return False, f"Tổng thời lượng ({total} giờ) không khớp với quy định {tc} tín chỉ = {expected_hours} giờ (1 TC = 50 giờ)."
            return True, ""
        except (ValueError, TypeError):
            return False, "Dữ liệu thời lượng không hợp lệ."

    @staticmethod
    def check_clo_bloom(clos_list):
        if not clos_list:
            return False, "Chưa có chuẩn đầu ra CLO nào."
        invalid_words = r'^([Bb]iết|[Hh]iểu|[Nn]ắm vững)'
        errors = []
        for clo in clos_list:
            mota = clo.get('mo_ta', '').strip()
            if re.search(invalid_words, mota):
                errors.append(f"CLO {clo.get('ma')} dùng động từ cấp thấp (Biết/Hiểu/Nắm vững).")
        if errors:
            return False, " | ".join(errors)
        return True, ""

    @staticmethod
    def check_phd_requirements(db, hp_id):
        hp = db.get_hoc_phan(hp_id)
        if not hp or hp.get('trinh_do') != 'Tiến sĩ':
            return True, ""
        
        # 1. Kiểm tra 10 bài báo quốc tế
        hoc_lieu = db.get_hoc_lieu(hp_id)
        bb_count = sum(1 for hl in hoc_lieu if hl.get('loai') == 'Bài báo quốc tế')
        if bb_count < 10:
            return False, f"Học phần Tiến sĩ yêu cầu => 10 bài báo quốc tế (hiện có {bb_count})."
            
        # 2. Kiểm tra nhiệm vụ NCS
        nd = db.get_noi_dung(hp_id)
        if not nd or not any(n.get('nhiem_vu_ncs') and str(n.get('nhiem_vu_ncs')).strip() for n in nd):
            return False, "Chưa khai báo hoặc trống trường thông tin Nhiệm vụ nghiên cứu sinh (Tiến sĩ)."
            
        return True, ""
    @staticmethod
    def validate_hp_accuracy(hoc_phan_data, sections_data):
        """
        Kiểm tra tính chính xác của dữ liệu học phần.
        FIXED M-05: Thống nhất quy tắc 1TC = 15 tiết lên lớp (LT+BT+TH+TL).
        FIXED M-08: Guard khi hoc_phan_data rỗng (section chưa load).
        hoc_phan_data: dict chứa thông tin từ sec1
        sections_data: một dict chứa data từ các section khác nếu cần
        """
        issues = []
        # FIXED M-08: Bỏ qua validation nếu không có dữ liệu
        if not hoc_phan_data:
            return issues

        # 1. Kiểm tra Tổng giờ vs Số tín chỉ
        try:
            tc = int(hoc_phan_data.get('so_tin_chi') or 3)
            lt = int(hoc_phan_data.get('gio_lt') or 0)
            th = int(hoc_phan_data.get('gio_th_tn') or 0)
            bt = int(hoc_phan_data.get('gio_bt') or 0)
            tl = int(hoc_phan_data.get('gio_tl') or 0)

            # FIXED M-05: 1 TC = 15 tiết lên lớp (LT+BT+TH+TL) — khớp với deccuong_service
            total_len_lop = lt + bt + th + tl
            expected_min = tc * 15

            if total_len_lop > 0 and total_len_lop < expected_min:
                issues.append({
                    'type': 'warning',
                    'section': '1. Thông tin chung',
                    'field': 'so_tin_chi',
                    'message': (
                        f'Số tín chỉ ({tc} TC × 15 = {expected_min} tiết lên lớp). '
                        f'Hiện tại LT+BT+TH+TL = {total_len_lop} tiết.'
                    )
                })
        except (ValueError, TypeError):
            pass

        return issues

    @staticmethod
    def audit_full_consistency(db, hp_id):
        """
        Thực hiện đối soát toàn diện dữ liệu học phần từ DB.
        """
        issues = []
        hp = db.get_hoc_phan(hp_id)
        if not hp: return issues

        # 1. Đối soát giờ (Sec 1 vs Sec 6)
        nd_lt = [dict(r) for r in db.get_noi_dung(hp_id, 'lt')]
        nd_th = [dict(r) for r in db.get_noi_dung(hp_id, 'th')]

        total_nd_hours = sum((r['gio_lt'] or 0) + (r['gio_bt'] or 0) + (r['gio_tl'] or 0) +
                             (r['gio_th_tn'] or 0) + (r['gio_th'] or 0) + (r['gio_kt'] or 0)
                             for r in nd_lt + nd_th)

        if abs(total_nd_hours - (hp['tong_gio'] or 0)) > 0.1:
            issues.append({
                'level': 'error',
                'section': 'Mục 6',
                'msg': f"Lệch tổng giờ giảng dạy: Mục 1 ({hp['tong_gio']}h) vs Mục 6 ({total_nd_hours}h)."
            })

        # 2. Đối soát trọng số (Sec 8)
        kts = db.get_ke_hoach_kt(hp_id)
        if kts:
            # Nhóm theo nhom (thuong_xuyen, cuoi_ky)
            weights = {}
            for k in kts:
                nhom = k['nhom']
                weights[nhom] = k['ty_trong_nhom'] or 0

            total_weight = sum(weights.values())
            if abs(total_weight - 100.0) > 0.1 and total_weight > 0:
                issues.append({
                    'level': 'warning',
                    'section': 'Mục 8',
                    'msg': f"Tổng trọng số các thành phần đánh giá là {total_weight}% (Kỳ vọng: 100%)."
                })

        # 3. Kiểm tra CĐR (CLO) trống
        clos = db.get_clo(hp_id)
        if not clos:
            issues.append({
                'level': 'warning',
                'section': 'Mục 4',
                'msg': "Học phần chưa có Chuẩn đầu ra (CLO) nào."
            })

        return issues
