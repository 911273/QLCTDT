# services/word_validator.py
import re

class DCCTValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        message = "Validation Failed:\n" + "\n".join([f"[{e['code']}] {e['field']}: {e['message']}" for e in errors])
        super().__init__(message)

def validate_data(data: dict) -> list:
    """
    Kiểm tra dữ liệu sinh ĐCCTHP theo 10 rules.
    Trả về list of error dicts. Trống nghĩa là hợp lệ.
    """
    errors = []
    
    # helper
    def add_error(field, code, message, severity="error"):
        errors.append({"field": field, "code": code, "message": message, "severity": severity})

    # [V1] so_tc > 0 và là số nguyên
    so_tc = data.get('so_tc', 0)
    if not isinstance(so_tc, int) or so_tc <= 0:
        add_error('so_tc', 'V1', 'Số tín chỉ phải là số nguyên > 0')

    # [V2] tong_gio == so_tc * 50
    pb = data.get('phan_bo_gio', {})
    tong_gio = (
        pb.get('ly_thuyet', 0) +
        pb.get('thuc_hanh_tn', 0) +
        pb.get('thao_luan', 0) +
        pb.get('tieu_luan_do_an', 0) +
        pb.get('thuc_tap', 0) +
        pb.get('tu_hoc', 0)
    )
    if tong_gio != so_tc * 50:
        add_error('phan_bo_gio', 'V2', f'Tổng giờ ({tong_gio}) không bằng số tín chỉ x 50 ({so_tc * 50})')

    # [V3] [V4] CLO
    clos = data.get('clo', [])
    invalid_verbs = [r'^biết\b', r'^hiểu\b', r'^nắm vững\b']
    for clo in clos:
        mo_ta = (clo.get('mo_ta') or '').strip().lower()
        if any(re.match(pattern, mo_ta) for pattern in invalid_verbs):
            add_error(f"clo.{clo.get('ma')}", 'V3', f"Mô tả CLO không được bắt đầu bằng Biết/Hiểu/Nắm vững: '{mo_ta}'")
        
        muc_do = (clo.get('muc_do') or '').strip().upper()
        if muc_do and muc_do not in ('I', 'R', 'M'):
            add_error(f"clo.{clo.get('ma')}", 'V4', f"Mức độ CLO phải là I, R, hoặc M. Nhận được: '{muc_do}'")

    # [V5] Tổng trọng số đánh giá == 100
    thanh_phan_dg = data.get('thanh_phan_dg', [])
    tong_trong_so = 0
    for dg in thanh_phan_dg:
        tp = (dg.get('thanh_phan') or '').lower()
        if 'chuyên cần' not in tp and 'chuyen can' not in tp:
            try:
                tong_trong_so += float(dg.get('trong_so', 0))
            except ValueError:
                pass
    if abs(tong_trong_so - 100) > 0.01 and thanh_phan_dg:
         add_error('thanh_phan_dg', 'V5', f'Tổng trọng số các bài đánh giá (trừ chuyên cần) phải = 100%. Hiện tại: {tong_trong_so}%')

    # [V6] Mỗi Rubric tổng trọng số == 100%
    rubrics = data.get('rubrics', [])
    for rb in rubrics:
        tong_rb = 0
        for tc in rb.get('tieu_chi', []):
            try:
                # Xử lý chuỗi như "40%"
                ts_str = str(tc.get('trong_so', '0')).replace('%', '').strip()
                tong_rb += float(ts_str)
            except ValueError:
                pass
        if abs(tong_rb - 100) > 0.01:
            add_error(f"rubrics.{rb.get('ma')}", 'V6', f"Tổng trọng số tiêu chí của Rubric {rb.get('ma')} phải = 100%. Hiện tại: {tong_rb}%")

    # [V7] ai_policy_level
    ai_level = data.get('ai_policy_level')
    if ai_level not in (1, 2, 3):
        add_error('ai_policy_level', 'V7', f"Mức độ AI policy phải thuộc {{1, 2, 3}}. Hiện tại: {ai_level}")

    # [V8] Tiến sĩ: bai_bao_quoc_te <= 10
    if data.get('trinh_do') == 'Tiến sĩ':
        bb = data.get('bai_bao_quoc_te', [])
        if len(bb) > 10:
             add_error('bai_bao_quoc_te', 'V8', f"Với bậc Tiến sĩ, bài báo quốc tế khai báo tối đa 10 mục. Hiện tại: {len(bb)}")

    # [V9] ten_tv và ten_ta không rỗng
    if not data.get('ten_tv') or not data.get('ten_tv').strip():
        add_error('ten_tv', 'V9', 'Tên tiếng Việt không được để trống')
    if not data.get('ten_ta') or not data.get('ten_ta').strip():
        add_error('ten_ta', 'V9', 'Tên tiếng Anh không được để trống')

    # [V10] Số giảng viên chính >= 1
    gv_chinh = data.get('giang_vien_chinh', [])
    if len(gv_chinh) < 1:
        add_error('giang_vien_chinh', 'V10', 'Phải có ít nhất 1 giảng viên phụ trách chính')

    return errors
