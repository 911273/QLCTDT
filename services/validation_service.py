# services/validation_service.py

class ValidationService:
    @staticmethod
    def validate_hp_accuracy(hoc_phan_data, sections_data):
        """
        Kiểm tra tính chính xác của dữ liệu học phần.
        hoc_phan_data: dict chứa thông tin từ sec1
        sections_data: một dict chứa data từ các section khác nếu cần
        """
        issues = []
        
        # 1. Kiểm tra Tổng giờ vs Số tín chỉ
        try:
            tc = int(hoc_phan_data.get('so_tin_chi', 3))
            lt = int(hoc_phan_data.get('gio_lt', 0))
            th = int(hoc_phan_data.get('gio_th_tn', 0))
            bt = int(hoc_phan_data.get('gio_bt', 0))
            
            # Quy tắc tạm thời: 1 TC = 15 tiết định mức
            expected_min = tc * 15
            actual_min = lt + (th + bt) // 2
            
            if actual_min < expected_min:
                issues.append({
                    'type': 'warning',
                    'field': 'so_tin_chi',
                    'message': f'Số tín chỉ ({tc}) tương ứng ít nhất {expected_min} tiết định mức. '
                               f'Hiện tại tổng tiết quy đổi là {actual_min}.'
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
        nd_lt = db.get_noi_dung(hp_id, 'lt')
        nd_th = db.get_noi_dung(hp_id, 'th')
        
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

