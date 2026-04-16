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
    def check_duplicate_code(repo, ma, current_hp_id):
        if not ma:
            return None
        
        # Đây là logic nghiệp vụ cần gọi repo
        # Tuy nhiên Service không nên gọi trực tiếp repo nếu ta muốn tách biệt hoàn toàn.
        # Nhưng ở đây Service layer được thiết kế để dùng Repo.
        
        # Giả sử repo có phương thức search hoặc get_by_code
        # Hiện tại db.py chưa có get_by_code riêng ngoài execute.
        # Ta sẽ dùng repo.db.conn tạm thời hoặc thêm phương thức vào repo.
        return None # Sẽ bổ sung sau khi repo hoàn thiện
