# word_import.py — Import đề cương chi tiết từ file Word (.docx) vào Database
"""
Module parse file .docx đề cương thực tế theo cấu trúc chuẩn EPU (9 section).
Hỗ trợ import đơn lẻ và hàng loạt.

Cấu trúc đề cương chuẩn:
  Table 1: Giảng viên (TT | Họ tên | SĐT | Email)
  Table 2: Thông tin HP (Mã, tín chỉ, loại, tính chất, phân bổ giờ, HP tiên quyết)
  Table 3: Mục tiêu HP (STT | Mô tả | CĐR CTĐT)
  Table 4: CLO (Mã CLO | Mô tả | CĐR CTĐT)
  Table 5: Nội dung chi tiết (Tên | LT | BT | TL | TH | Yêu cầu | CLO)
  Paragraphs: Mô tả, PP dạy học, Học liệu
  Table 6/7: Kế hoạch kiểm tra
  Table cuối: Lịch sử cập nhật
"""

import os
import re
from docx import Document
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _cell_text(cell):
    """Lấy text của cell, gộp nhiều paragraph."""
    return '\n'.join(p.text.strip() for p in cell.paragraphs).strip()


def _clean(text):
    """Chuẩn hóa text, xóa khoảng trắng thừa."""
    if not text:
        return ''
    return re.sub(r'\s+', ' ', text).strip()


def _extract_number(text):
    """Trích xuất số từ text."""
    if not text:
        return None
    m = re.search(r'(\d+(?:[,\.]\d+)?)', text.replace(',', '.'))
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def _extract_number_int(text):
    """Trích xuất số nguyên từ text."""
    v = _extract_number(text)
    return int(v) if v is not None else None


def _is_group_header(text):
    """Kiểm tra xem text có phải tiêu đề nhóm (Kiến thức, Kỹ năng, Tự chủ...)."""
    t = text.strip().lower()
    keywords = ['kiến thức', 'kỹ năng', 'mức tự chủ', 'tự chủ và trách nhiệm',
                'mức tự chủ và trách nhiệm', 'năng lực tự chủ']
    return any(kw in t for kw in keywords)


# ─── Parse từng phần đề cương ─────────────────────────────────────────────────

def _parse_table_giang_vien(table):
    """Parse Table 1: Giảng viên."""
    gv_chinh = []
    gv_tham_gia = []
    current_group = None

    for row in table.rows:
        cells = [_cell_text(c) for c in row.cells]
        row_text = ' '.join(cells).lower()

        # Detect group headers
        if 'giảng viên phụ trách chính' in row_text:
            current_group = 'chinh'
            continue
        elif 'giảng viên tham gia' in row_text or 'giảng viên cùng' in row_text:
            current_group = 'tham_gia'
            continue

        # Skip header row
        if 'học hàm' in row_text or 'họ và tên' in row_text:
            continue

        # Parse data row
        if len(cells) >= 4 and current_group:
            stt = cells[0].strip()
            ho_ten = _clean(cells[1])
            sdt = _clean(cells[2]) if len(cells) > 2 else ''
            email = _clean(cells[3]) if len(cells) > 3 else ''

            if not ho_ten or ho_ten.lower().startswith('theo sự phân công'):
                continue

            # Extract học vị from tên
            hoc_vi = ''
            for prefix in ['PGS.TS.', 'PGS. TS.', 'TS.', 'ThS.', 'Th.S.', 'Thạc sĩ',
                           'Tiến sĩ', 'PGS.TS', 'TS', 'ThS']:
                if ho_ten.startswith(prefix):
                    hoc_vi = prefix.replace('.', '').strip()
                    ho_ten = ho_ten[len(prefix):].strip().lstrip('.')
                    ho_ten = ho_ten.strip()
                    break
                # Check if title appears later: "Trần Văn Tuấn, Thạc sĩ"
                if f', {prefix}' in ho_ten or f',{prefix}' in ho_ten:
                    parts = re.split(r',\s*', ho_ten, 1)
                    ho_ten = parts[0].strip()
                    hoc_vi = parts[1].strip() if len(parts) > 1 else prefix
                    break

            gv_data = {
                'ho_ten': ho_ten,
                'hoc_vi': hoc_vi,
                'sdt': sdt,
                'email': email
            }

            if current_group == 'chinh':
                gv_chinh.append(gv_data)
            else:
                gv_tham_gia.append(gv_data)

    return gv_chinh, gv_tham_gia


def _parse_table_thong_tin(table):
    """Parse Table 2: Thông tin chung HP."""
    info = {
        'ma': '', 'so_tin_chi': 3, 'loai': 'Bắt buộc', 'tinh_chat': 'Hỗn hợp',
        'gio_lt': 0, 'gio_bt': 0, 'gio_tl': 0, 'gio_th_tn': 0,
        'gio_tieu_luan': 0, 'gio_thuc_tap': 0, 'gio_tu_hoc': 0, 'tong_gio': 0,
        'hp_tien_quyet': '', 'hp_thay_the': ''
    }

    tien_quyet_lines = []
    thay_the_lines = []
    is_tien_quyet = False
    is_thay_the = False

    for row in table.rows:
        cells = [_cell_text(c) for c in row.cells]
        row_combined = ' '.join(cells).lower()

        # Mã HP
        for cell_text in cells:
            m = re.search(r'mã\s*(?:học\s*phần|hp)\s*[:\s]*(\w+)', cell_text, re.IGNORECASE)
            if m:
                info['ma'] = m.group(1).strip()

        # Số tín chỉ
        for cell_text in cells:
            m = re.search(r'số\s*tín\s*chỉ\s*[:\s]*(\d+)', cell_text, re.IGNORECASE)
            if m:
                info['so_tin_chi'] = int(m.group(1))

        # Loại HP
        if 'loại học phần' in row_combined:
            remaining = ' '.join(cells[1:]) if len(cells) > 1 else cells[0]
            remaining_lower = remaining.lower()
            if 'bắt buộc' in remaining_lower:
                info['loai'] = 'Bắt buộc'
            elif 'tự chọn' in remaining_lower:
                info['loai'] = 'Tự chọn'

        # Tính chất
        if 'tính chất' in row_combined:
            remaining = ' '.join(cells[1:]) if len(cells) > 1 else cells[0]
            remaining_lower = remaining.lower()
            for tc in ['Lý thuyết', 'Hỗn hợp', 'Thực hành', 'Đồ án', 'Thực tập']:
                if tc.lower() in remaining_lower:
                    info['tinh_chat'] = tc
                    break

        # Phân bổ giờ
        if 'lý thuyết' in row_combined and 'bài tập' in row_combined:
            val = _extract_number(cells[-1]) if cells[-1].strip() else None
            if val is not None:
                info['gio_lt'] = int(val)
        elif 'thực hành' in row_combined and 'thí nghiệm' in row_combined:
            val = _extract_number(cells[-1]) if cells[-1].strip() else None
            if val is not None:
                info['gio_th_tn'] = int(val)
        elif 'thảo luận' in row_combined:
            val = _extract_number(cells[-1]) if cells[-1].strip() else None
            if val is not None:
                info['gio_tl'] = int(val)
        elif 'tiểu luận' in row_combined or ('đồ án' in row_combined and 'phân bố' in row_combined):
            val = _extract_number(cells[-1]) if cells[-1].strip() else None
            if val is not None:
                info['gio_tieu_luan'] = int(val)
        elif 'thực tập' in row_combined and 'doanh nghiệp' in row_combined:
            val = _extract_number(cells[-1]) if cells[-1].strip() else None
            if val is not None:
                info['gio_thuc_tap'] = int(val)
        elif 'tự học' in row_combined:
            val = _extract_number(cells[-1]) if cells[-1].strip() else None
            if val is not None:
                info['gio_tu_hoc'] = int(val)
        elif 'tổng' in row_combined and 'giờ' in row_combined:
            val = _extract_number(cells[-1]) if cells[-1].strip() else None
            if val is not None:
                info['tong_gio'] = int(val)

        # HP tiên quyết
        if 'tiên quyết' in row_combined:
            is_tien_quyet = True
            is_thay_the = False
            # Check same row for data
            for c in cells[1:]:
                t = _clean(c)
                if t and 'tiên quyết' not in t.lower():
                    tien_quyet_lines.append(t)
        elif 'thay thế' in row_combined:
            is_thay_the = True
            is_tien_quyet = False
            for c in cells[1:]:
                t = _clean(c)
                if t and 'thay thế' not in t.lower():
                    thay_the_lines.append(t)
        elif is_tien_quyet:
            for c in cells[1:]:
                t = _clean(c)
                if t:
                    tien_quyet_lines.append(t)
        elif is_thay_the:
            for c in cells[1:]:
                t = _clean(c)
                if t:
                    thay_the_lines.append(t)

    # Combine unique prerequisite lines
    seen = set()
    unique_tq = []
    for line in tien_quyet_lines:
        if line not in seen and line.lower() not in ('', 'không', 'không có'):
            seen.add(line)
            unique_tq.append(line)
    info['hp_tien_quyet'] = '; '.join(unique_tq)

    seen = set()
    unique_tt = []
    for line in thay_the_lines:
        if line not in seen and line.lower() not in ('', 'không', 'không có'):
            seen.add(line)
            unique_tt.append(line)
    info['hp_thay_the'] = '; '.join(unique_tt)

    return info


def _parse_table_muc_tieu(table):
    """Parse Table 3: Mục tiêu HP."""
    items = []
    current_nhom = ''
    
    for row in table.rows:
        cells = [_cell_text(c) for c in row.cells]
        row_combined = ' '.join(cells).lower()

        # Skip header
        if 'mục tiêu' in row_combined and 'mô tả' in row_combined:
            continue

        if len(cells) < 2:
            continue

        # Check for group header
        if _is_group_header(' '.join(cells)):
            for c in cells:
                if _is_group_header(c):
                    current_nhom = _clean(c)
                    items.append({
                        'so_thu_tu': None,
                        'mo_ta': current_nhom,
                        'cdr_ma': '',
                        'nhom': current_nhom,
                        'la_tieu_de_nhom': 1
                    })
                    break
            continue

        # Data row
        stt = cells[0].strip()
        mo_ta = _clean(cells[1]) if len(cells) > 1 else ''
        cdr_ma = _clean(cells[-1]) if len(cells) > 2 else ''

        if not mo_ta or mo_ta == stt:
            continue

        stt_num = _extract_number_int(stt)

        items.append({
            'so_thu_tu': stt_num,
            'mo_ta': mo_ta,
            'cdr_ma': cdr_ma,
            'nhom': current_nhom,
            'la_tieu_de_nhom': 0
        })

    return items


def _parse_table_clo(table):
    """Parse Table 4: CLO."""
    items = []
    current_nhom = ''

    for row in table.rows:
        cells = [_cell_text(c) for c in row.cells]
        row_combined = ' '.join(cells).lower()

        # Skip header
        if 'cđr học phần' in row_combined and 'mô tả' in row_combined:
            continue

        if len(cells) < 2:
            continue

        # Group header - Skip but keep track if needed for context (optional)
        if _is_group_header(' '.join(cells)):
            # We no longer add group headers to the items list
            continue

        # Data row
        ma = _clean(cells[0])
        mo_ta = _clean(cells[1]) if len(cells) > 1 else ''
        cdr_ma = _clean(cells[-1]) if len(cells) > 2 else ''

        if not ma or not mo_ta:
            continue
        # Skip if ma doesn't look like CLO
        if not re.match(r'CLO\s*\d+', ma, re.IGNORECASE) and not re.match(r'\d+', ma):
            continue

        items.append({
            'ma': ma.replace(' ', ''),
            'mo_ta': mo_ta,
            'cdr_ma': cdr_ma,
            'nhom': current_nhom,
            'la_tieu_de_nhom': 0
        })

    return items


def _parse_table_noi_dung(table):
    """Parse Table 5: Nội dung chi tiết.
    
    Cấu trúc header:
    Row 0: Nội dung | Hình thức tổ chức dạy-học (colspan) | Yêu cầu | CĐR
    Row 1:          | Giờ lên lớp (colspan)                |         |
    Row 2:          | LT | BT | TL | TH,TN                |         |
    """
    items = []
    thu_tu = 0
    
    # Find data start (skip header rows)
    data_start = 0
    for i, row in enumerate(table.rows):
        cells = [_cell_text(c) for c in row.cells]
        row_combined = ' '.join(cells).lower()
        if any(h in row_combined for h in ['lt', 'lý thuyết', 'bài tập']):
            if 'bt' in row_combined or 'tl' in row_combined:
                data_start = i + 1
                break

    if data_start == 0:
        # Fallback: skip 3 header rows
        data_start = min(3, len(table.rows))

    # Determine column mapping
    # Most common: [TEN | LT | BT | TL | TH,TN | YEU_CAU | CDR]
    num_cols = len(table.rows[0].cells) if table.rows else 7

    for i in range(data_start, len(table.rows)):
        row = table.rows[i]
        cells = [_cell_text(c) for c in row.cells]
        
        if not any(c.strip() for c in cells):
            continue

        ten = _clean(cells[0]) if len(cells) > 0 else ''
        if not ten:
            continue

        # Determine if this is a chapter heading (bold / numbered like "Chương X" / "Phần X")
        is_heading = bool(re.match(
            r'^(Chương|Phần|Bài|Buổi)\s+\d+', ten, re.IGNORECASE
        ))
        # Also check for Chương marker with period: "Chương 1."
        if not is_heading:
            is_heading = bool(re.match(r'^(Chương|Phần)\s+', ten, re.IGNORECASE))

        # Detect indent level from numbering
        cap_do = 1
        if re.match(r'^\d+\.\d+\.\d+', ten):
            cap_do = 3
        elif re.match(r'^\d+\.\d+\s', ten):
            cap_do = 2
        elif is_heading or re.match(r'^(Chương|Phần|Bài|Buổi)\s', ten, re.IGNORECASE):
            cap_do = 1
        elif re.match(r'^[-+•]', ten):
            cap_do = 3

        # Parse hours - try to extract from appropriate columns
        gio_lt = gio_bt = gio_tl = gio_th_tn = None
        gio_th = gio_kt = None
        yeu_cau = ''
        cdr_ma = ''
        pp_day = pp_hoc = bai_danh_gia = ''

        # NEW LOGIC: detect 7-column layout (TT, Ten, Gio, HDD, HDH, CDR, BDG)
        is_new_layout = False
        if num_cols >= 7:
            check_header = ' '.join(cells).lower()
            if 'hoạt động dạy' in check_header or 'pp dạy' in check_header:
                is_new_layout = True

        if is_new_layout:
            # Shift indices because of TT column if present
            # We assume cells[0] is TT, cells[1] is Ten, cells[2] is Gio...
            # But wait, num_cols might be 7 or 8.
            # Usually: TT | Ten | Gio | HDD | HDH | CDR | BDG
            idx_ten = 1
            idx_gio = 2
            idx_hdd = 3
            idx_hdh = 4
            idx_cdr = 5
            idx_bdg = 6
            
            ten = _clean(cells[idx_ten]) if len(cells) > idx_ten else ten
            gio_str = _clean(cells[idx_gio]) if len(cells) > idx_gio else ''
            # Extract (1/2/4/0)
            matches = re.findall(r'(\d*\.?\d+)', gio_str)
            if matches:
                if len(matches) >= 4:
                    gio_lt = _extract_number(matches[0]) 
                    gio_bt = _extract_number(matches[1])
                    gio_tl = _extract_number(matches[2])
                    gio_th_tn = _extract_number(matches[3])
                elif len(matches) == 1:
                    gio_lt = _extract_number(matches[0])

            pp_day = _clean(cells[idx_hdd]) if len(cells) > idx_hdd else ''
            pp_hoc = _clean(cells[idx_hdh]) if len(cells) > idx_hdh else ''
            cdr_ma = _clean(cells[idx_cdr]) if len(cells) > idx_cdr else ''
            bai_danh_gia = _clean(cells[idx_bdg]) if len(cells) > idx_bdg else ''
        
        elif num_cols >= 7:
            gio_lt = _extract_number(cells[1]) if len(cells) > 1 else None
            gio_bt = _extract_number(cells[2]) if len(cells) > 2 else None
            gio_tl = _extract_number(cells[3]) if len(cells) > 3 else None
            gio_th_tn = _extract_number(cells[4]) if len(cells) > 4 else None
            yeu_cau = _clean(cells[5]) if len(cells) > 5 else ''
            cdr_ma = _clean(cells[6]) if len(cells) > 6 else ''
        elif num_cols >= 5:
            gio_lt = _extract_number(cells[1]) if len(cells) > 1 else None
            gio_bt = _extract_number(cells[2]) if len(cells) > 2 else None
            yeu_cau = _clean(cells[3]) if len(cells) > 3 else ''
            cdr_ma = _clean(cells[4]) if len(cells) > 4 else ''

        thu_tu += 1
        items.append({
            'thu_tu': thu_tu,
            'ten': ten,
            'cap_do': cap_do,
            'in_dam': 1 if is_heading else 0,
            'gio_lt': gio_lt,
            'gio_bt': gio_bt,
            'gio_tl': gio_tl,
            'gio_th_tn': gio_th_tn,
            'pp_day': pp_day,
            'pp_hoc': pp_hoc,
            'yeu_cau': yeu_cau,
            'cdr_ma': cdr_ma,
            'bai_danh_gia': bai_danh_gia
        })

    return items


def _parse_table_kiem_tra(table):
    """Parse Table kiểm tra - đánh giá."""
    items = []
    current_nhom = ''
    current_ty_trong_nhom = None
    thu_tu = 0

    for row in table.rows:
        cells = [_cell_text(c) for c in row.cells]
        row_combined = ' '.join(cells)
        row_lower = row_combined.lower()

        # Skip headers
        if any(h in row_lower for h in ['thành phần đánh giá', 'bài kiểm tra',
                                          'hình thức', 'nội dung']):
            if 'thời gian' in row_lower or 'clo' in row_lower:
                continue

        # Detect group (e.g., "Đánh giá quá trình", "Đánh giá giữa kỳ", "Đánh giá cuối kỳ")
        for c in cells:
            c_lower = c.lower().strip()
            if any(kw in c_lower for kw in ['đánh giá quá trình', 'đánh giá giữa kỳ',
                                              'đánh giá cuối kỳ', 'đánh giá kết thúc',
                                              'thường xuyên', 'chuyên cần']):
                current_nhom = _clean(c)
                # Try to find tỷ trọng nhóm
                m = re.search(r'(\d+)\s*%', c)
                if m:
                    current_ty_trong_nhom = float(m.group(1))
                break

        # Parse data row - look for actual assessment items
        if len(cells) >= 3:
            noi_dung = ''
            hinh_thuc = ''
            thoi_gian = ''
            clo_lien_quan = ''
            ty_trong = None

            # Try to identify which column has what
            for ci, c in enumerate(cells):
                c_clean = _clean(c)
                c_lower = c_clean.lower()
                
                # Tỷ trọng (%)
                m_ty = re.search(r'(\d+)\s*%', c_clean)
                if m_ty and ci > 0:
                    ty_trong = float(m_ty.group(1))
                    continue

                # CLO
                if re.search(r'CLO\s*\d', c_clean, re.IGNORECASE):
                    clo_lien_quan = c_clean
                    continue

                # Bài kiểm tra / nội dung
                if any(kw in c_lower for kw in ['kiểm tra', 'bài tập', 'chuyên cần',
                                                  'tiểu luận', 'thi', 'bảo vệ', 'thuyết trình',
                                                  'thảo luận', 'bài báo cáo']):
                    if not noi_dung:
                        noi_dung = c_clean
                    else:
                        hinh_thuc = c_clean

            if noi_dung:
                thu_tu += 1
                items.append({
                    'nhom': current_nhom,
                    'ty_trong_nhom': current_ty_trong_nhom,
                    'thu_tu': thu_tu,
                    'noi_dung': noi_dung,
                    'hinh_thuc': hinh_thuc,
                    'thoi_gian': thoi_gian,
                    'clo_lien_quan': clo_lien_quan,
                    'ty_trong': ty_trong
                })

    return items


def _parse_table_lich_su(table):
    """Parse bảng lịch sử cập nhật."""
    items = []
    for row in table.rows:
        cells = [_cell_text(c) for c in row.cells]
        row_lower = ' '.join(cells).lower()
        
        if 'lần' in row_lower and ('nội dung' in row_lower or 'cập nhật' in row_lower):
            continue  # header

        if len(cells) >= 3:
            lan = _extract_number_int(cells[0])
            if lan is None:
                continue
            items.append({
                'lan': lan,
                'noi_dung': _clean(cells[1]) if len(cells) > 1 else '',
                'quyet_dinh': _clean(cells[2]) if len(cells) > 2 else '',
                'nguoi_cap_nhat': _clean(cells[3]) if len(cells) > 3 else '',
                'truong_khoa': _clean(cells[4]) if len(cells) > 4 else '',
                'ngay_cap_nhat': _clean(cells[5]) if len(cells) > 5 else ''
            })
    return items


# ─── Parse paragraphs ─────────────────────────────────────────────────────────

def _parse_paragraphs(paragraphs):
    """Parse paragraphs to extract: tên Việt/Anh, mô tả, PP dạy học, học liệu, nhiệm vụ SV."""
    result = {
        'ten_viet': '',
        'ten_anh': '',
        'trinh_do': 'Đại học',
        'ten_don_vi': '',
        'mo_ta': '',
        'pp_day_hoc': '',
        'hoc_lieu': [],  # list of {'loai': ..., 'noi_dung': ...}
        'nhiem_vu_sv_len_lop': '',
        'nhiem_vu_sv_bai_tap': '',
        'nhiem_vu_sv_dung_cu': '',
        'nhiem_vu_sv_khac': '',
        'quy_dinh_hp': '',
        'co_so_vat_chat': '',
        'phu_luc': ''
    }

    current_section = ''
    current_sub_section = ''
    hoc_lieu_loai = ''
    buffer = []

    for para in paragraphs:
        text = para.text.strip()
        if not text:
            continue
        text_lower = text.lower()

        # Detect section headers
        if text_lower.startswith('tên tiếng việt'):
            m = re.search(r'[:：]\s*(.*)', text)
            if m:
                result['ten_viet'] = _clean(m.group(1))
            continue

        if text_lower.startswith('tên tiếng anh'):
            m = re.search(r'[:：]\s*(.*)', text)
            if m:
                result['ten_anh'] = _clean(m.group(1))
            continue

        if 'trình độ đào tạo' in text_lower:
            if 'thạc sĩ' in text_lower:
                result['trinh_do'] = 'Thạc sĩ'
            elif 'tiến sĩ' in text_lower:
                result['trinh_do'] = 'Tiến sĩ'
            continue

        if text_lower.startswith('tên đơn vị quản lý'):
            m = re.search(r'[:：]\s*(.*)', text)
            if m:
                result['ten_don_vi'] = _clean(m.group(1))
            continue

        # Section markers
        if re.match(r'^2\.\s*mô tả', text_lower):
            current_section = 'mo_ta'
            continue
        elif re.match(r'^3\.\s*mục tiêu', text_lower):
            # Save buffer
            if current_section == 'mo_ta':
                result['mo_ta'] = '\n'.join(buffer)
                buffer = []
            current_section = 'muc_tieu'
            continue
        elif re.match(r'^4\.\s*chuẩn đầu ra', text_lower):
            current_section = 'cdr'
            continue
        elif re.match(r'^5\.\s*học liệu', text_lower):
            current_section = 'hoc_lieu'
            continue
        elif re.match(r'^5\.1', text_lower):
            hoc_lieu_loai = '5.1'
            current_sub_section = '5.1'
            continue
        elif re.match(r'^5\.2', text_lower):
            hoc_lieu_loai = '5.2'
            current_sub_section = '5.2'
            continue
        elif re.match(r'^5\.3', text_lower):
            hoc_lieu_loai = '5.3'
            current_sub_section = '5.3'
            continue
        elif re.match(r'^5\.4', text_lower):
            hoc_lieu_loai = '5.4'
            current_sub_section = '5.4'
            continue
        elif re.match(r'^5\.5', text_lower):
            hoc_lieu_loai = '5.5'
            current_sub_section = '5.5'
            continue
        elif re.match(r'^5\.6', text_lower):
            hoc_lieu_loai = '5.6'
            current_sub_section = '5.6'
            continue
        elif re.match(r'^5\.7', text_lower):
            hoc_lieu_loai = '5.7'
            current_sub_section = '5.7'
            continue
        elif re.match(r'^6\.\s*nội dung', text_lower):
            current_section = 'noi_dung'
            continue
        elif re.match(r'^7\.\s*phương pháp', text_lower):
            current_section = 'pp_day_hoc'
            continue
        elif re.match(r'^8\.\s*phương pháp.*kiểm tra', text_lower):
            if current_section == 'pp_day_hoc':
                result['pp_day_hoc'] = '\n'.join(buffer)
                buffer = []
            current_section = 'kiem_tra'
            continue
        elif re.match(r'^8\.1', text_lower):
            current_sub_section = '8.1'
            continue
        elif re.match(r'^8\.2', text_lower):
            current_sub_section = '8.2'
            continue
        elif re.match(r'^9\.\s*quy định', text_lower):
            if current_section == 'kiem_tra':
                buffer = [] # Reset buffer for new section
            current_section = 'quy_dinh'
            continue
        elif re.match(r'^10\.\s*cơ sở vật chất', text_lower):
            if current_section == 'quy_dinh':
                result['quy_dinh_hp'] = '\n'.join(buffer)
                buffer = []
            current_section = 'co_so_vat_chat'
            continue
        elif re.match(r'^12\.\s*phụ lục', text_lower):
            if current_section == 'co_so_vat_chat':
                result['co_so_vat_chat'] = '\n'.join(buffer)
                buffer = []
            current_section = 'phu_luc'
            continue
        elif re.match(r'^13\.\s*tiến trình', text_lower):
            if current_section == 'phu_luc':
                result['phu_luc'] = '\n'.join(buffer)
                buffer = []
            current_section = 'lich_su'
            continue

        # Collect content by section
        if current_section == 'hoc_lieu' and current_sub_section in ('5.1', '5.2', '5.3'):
            if text and not text_lower.startswith('máy vi tính') and text_lower not in ('không có', 'không'):
                result['hoc_lieu'].append({
                    'loai': hoc_lieu_loai,
                    'noi_dung': text,
                    'so_thu_tu': len([h for h in result['hoc_lieu'] if h['loai'] == hoc_lieu_loai]) + 1
                })
            elif text_lower.startswith('máy') or 'internet' in text_lower or 'phần mềm' in text_lower:
                result['hoc_lieu'].append({
                    'loai': 'Khác',
                    'noi_dung': text,
                    'so_thu_tu': len([h for h in result['hoc_lieu'] if h['loai'] == 'Khác']) + 1
                })
        elif current_section in ('mo_ta', 'pp_day_hoc', 'quy_dinh', 'co_so_vat_chat', 'phu_luc'):
            buffer.append(text)
        elif current_section == 'kiem_tra' and current_sub_section == '8.1':
            t = text_lower
            if 'dự lớp' in t or 'chuyên cần' in t:
                result['nhiem_vu_sv_len_lop'] = text
            elif 'bài tập' in t:
                result['nhiem_vu_sv_bai_tap'] = text
            elif 'dụng cụ' in t:
                result['nhiem_vu_sv_dung_cu'] = text
            elif 'khác' in t or text.startswith('Khác'):
                result['nhiem_vu_sv_khac'] = text
            elif not result['nhiem_vu_sv_len_lop']:
                result['nhiem_vu_sv_len_lop'] = text

    # Flush remaining buffer
    if current_section == 'mo_ta' and buffer:
        result['mo_ta'] = '\n'.join(buffer)
    elif current_section == 'pp_day_hoc' and buffer:
        result['pp_day_hoc'] = '\n'.join(buffer)
    elif current_section == 'quy_dinh' and buffer:
        result['quy_dinh_hp'] = '\n'.join(buffer)
    elif current_section == 'co_so_vat_chat' and buffer:
        result['co_so_vat_chat'] = '\n'.join(buffer)
    elif current_section == 'phu_luc' and buffer:
        result['phu_luc'] = '\n'.join(buffer)

    return result


# ─── Classify tables ──────────────────────────────────────────────────────────

def _classify_tables(doc):
    """Phân loại các bảng trong document theo chức năng."""
    classified = {
        'giang_vien': None,    # Table 1
        'thong_tin': None,     # Table 2
        'muc_tieu': None,      # Table 3
        'clo': None,           # Table 4
        'noi_dung': None,      # Table 5
        'kiem_tra': [],        # Tables 6/7
        'lich_su': None,       # Table cuối
    }

    for ti, table in enumerate(doc.tables):
        if not table.rows:
            continue

        # Analyze first few rows
        sample_text = ''
        for row in table.rows[:5]:
            for cell in row.cells:
                sample_text += ' ' + _cell_text(cell)
        sample_lower = sample_text.lower()

        if 'học hàm' in sample_lower and ('họ và tên' in sample_lower or 'họ tên' in sample_lower):
            classified['giang_vien'] = ti
        elif 'mã học phần' in sample_lower or 'mã hp' in sample_lower:
            classified['thong_tin'] = ti
        elif 'mục tiêu' in sample_lower and 'mô tả' in sample_lower and 'cđr' in sample_lower:
            if classified['muc_tieu'] is None:
                classified['muc_tieu'] = ti
        elif 'cđr học phần' in sample_lower and 'mô tả' in sample_lower:
            classified['clo'] = ti
        elif 'nội dung cơ bản' in sample_lower or ('hình thức tổ chức' in sample_lower and 'dạy' in sample_lower):
            if classified['noi_dung'] is None:
                classified['noi_dung'] = ti
        elif 'lần' in sample_lower and ('cập nhật' in sample_lower or 'sửa đổi' in sample_lower):
            classified['lich_su'] = ti
        elif any(kw in sample_lower for kw in ['thành phần đánh giá', 'đánh giá quá trình',
                                                  'đánh giá giữa', 'đánh giá cuối',
                                                  'hình thức kiểm tra', 'bài kiểm tra',
                                                  'tỷ trọng']):
            classified['kiem_tra'].append(ti)

    return classified


# ─── Main parse function ──────────────────────────────────────────────────────

def parse_docx(file_path):
    """
    Parse file .docx đề cương thực tế, trả về dict dữ liệu chuẩn hóa.
    
    Returns:
        dict: {
            'file_name': str,
            'paragraphs': {...},  # tên, mô tả, PP dạy học, học liệu...
            'gv_chinh': [...], 'gv_tham_gia': [...],
            'thong_tin': {...},
            'muc_tieu': [...],
            'clo': [...],
            'noi_dung': [...],
            'kiem_tra': [...],
            'lich_su': [...]
        }
    """
    doc = Document(file_path)
    classified = _classify_tables(doc)

    # Parse paragraphs
    para_data = _parse_paragraphs(doc.paragraphs)

    # Parse tables
    gv_chinh, gv_tham_gia = [], []
    if classified['giang_vien'] is not None:
        gv_chinh, gv_tham_gia = _parse_table_giang_vien(doc.tables[classified['giang_vien']])

    thong_tin = {}
    if classified['thong_tin'] is not None:
        thong_tin = _parse_table_thong_tin(doc.tables[classified['thong_tin']])

    muc_tieu = []
    if classified['muc_tieu'] is not None:
        muc_tieu = _parse_table_muc_tieu(doc.tables[classified['muc_tieu']])

    clo = []
    if classified['clo'] is not None:
        clo = _parse_table_clo(doc.tables[classified['clo']])

    noi_dung = []
    if classified['noi_dung'] is not None:
        noi_dung = _parse_table_noi_dung(doc.tables[classified['noi_dung']])

    kiem_tra = []
    for ti in classified['kiem_tra']:
        kiem_tra.extend(_parse_table_kiem_tra(doc.tables[ti]))

    lich_su = []
    if classified['lich_su'] is not None:
        lich_su = _parse_table_lich_su(doc.tables[classified['lich_su']])

    # Merge paragraph data with table data
    ten_viet = para_data['ten_viet'] or thong_tin.get('ten_viet', '')
    # If ten_viet is empty, try to get from file name
    if not ten_viet:
        base = os.path.splitext(os.path.basename(file_path))[0]
        # Remove pattern like "000084_" 
        m = re.match(r'\d+[_\s]+(.*)', base)
        if m:
            ten_viet = m.group(1).replace('_', ' ').strip()
            # Remove year suffix
            ten_viet = re.sub(r'_?\d{4}(\s*\(.*\))?$', '', ten_viet).strip()
        else:
            ten_viet = base

    return {
        'file_name': os.path.basename(file_path),
        'ten_viet': ten_viet,
        'ten_anh': para_data['ten_anh'],
        'trinh_do': para_data['trinh_do'],
        'mo_ta': para_data['mo_ta'],
        'pp_day_hoc': para_data['pp_day_hoc'],
        'hoc_lieu': para_data['hoc_lieu'],
        'nhiem_vu_sv_len_lop': para_data['nhiem_vu_sv_len_lop'],
        'nhiem_vu_sv_bai_tap': para_data['nhiem_vu_sv_bai_tap'],
        'nhiem_vu_sv_dung_cu': para_data['nhiem_vu_sv_dung_cu'],
        'nhiem_vu_sv_khac': para_data['nhiem_vu_sv_khac'],
        'quy_dinh_hp': para_data['quy_dinh_hp'],
        'co_so_vat_chat': para_data['co_so_vat_chat'],
        'phu_luc': para_data['phu_luc'],
        'gv_chinh': gv_chinh,
        'gv_tham_gia': gv_tham_gia,
        'thong_tin': thong_tin,
        'muc_tieu': muc_tieu,
        'clo': clo,
        'noi_dung': noi_dung,
        'kiem_tra': kiem_tra,
        'lich_su': lich_su
    }


# ─── Import vào Database ─────────────────────────────────────────────────────

def _find_or_create_gv(db, gv_data):
    """Tìm GV trong DB theo tên/email, nếu không có thì tạo mới."""
    ho_ten = gv_data.get('ho_ten', '').strip()
    email = gv_data.get('email', '').strip()

    if not ho_ten:
        return None

    # Search by email first (most reliable)
    if email:
        results = db.conn.execute(
            "SELECT id FROM giang_vien WHERE email = ? COLLATE NOCASE",
            (email,)
        ).fetchone()
        if results:
            return results['id']

    # Search by name
    results = db.conn.execute(
        "SELECT id FROM giang_vien WHERE ho_ten LIKE ? COLLATE NOCASE",
        (f'%{ho_ten}%',)
    ).fetchone()
    if results:
        return results['id']

    # Create new
    new_data = {
        'ho_ten': ho_ten,
        'hoc_vi': gv_data.get('hoc_vi', ''),
        'sdt': gv_data.get('sdt', ''),
        'email': email
    }
    return db.add_giang_vien(new_data)


def import_single(db, parsed_data, khoa_id=None):
    """
    Import một đề cương đã parse vào database.
    
    Args:
        db: Database instance
        parsed_data: dict từ parse_docx()
        khoa_id: ID khoa quản lý (optional)
    
    Returns:
        int: ID học phần mới được tạo
    """
    info = parsed_data['thong_tin']

    # Check duplicate
    existing = db.conn.execute(
        "SELECT id FROM hoc_phan WHERE ma = ? AND ma != ''",
        (info.get('ma', ''),)
    ).fetchone()
    if existing:
        # Update existing
        hp_id = existing['id']
    else:
        # Create new HP
        hp_data = {
            'ma': info.get('ma', ''),
            'ten_viet': parsed_data['ten_viet'],
            'ten_anh': parsed_data['ten_anh'],
            'trinh_do': parsed_data['trinh_do'],
            'khoa_id': khoa_id,
            'so_tin_chi': info.get('so_tin_chi', 3),
            'loai': info.get('loai', 'Bắt buộc'),
            'tinh_chat': info.get('tinh_chat', 'Hỗn hợp'),
            'gio_lt': info.get('gio_lt', 0),
            'gio_th_tn': info.get('gio_th_tn', 0),
            'gio_tl': info.get('gio_tl', 0),
            'gio_tieu_luan': info.get('gio_tieu_luan', 0),
            'gio_thuc_tap': info.get('gio_thuc_tap', 0),
            'gio_tu_hoc': info.get('gio_tu_hoc', 0),
            'tong_gio': info.get('tong_gio', 0),
            'hp_tien_quyet': info.get('hp_tien_quyet', ''),
            'hp_thay_the': info.get('hp_thay_the', ''),
            'mo_ta': parsed_data['mo_ta'],
            'pp_day_hoc': parsed_data['pp_day_hoc'],
            'nhiem_vu_sv_len_lop': parsed_data['nhiem_vu_sv_len_lop'],
            'nhiem_vu_sv_bai_tap': parsed_data['nhiem_vu_sv_bai_tap'],
            'nhiem_vu_sv_dung_cu': parsed_data['nhiem_vu_sv_dung_cu'],
            'nhiem_vu_sv_khac': parsed_data['nhiem_vu_sv_khac'],
            'quy_dinh_hp': parsed_data.get('quy_dinh_hp', ''),
            'co_so_vat_chat': parsed_data.get('co_so_vat_chat', ''),
            'phu_luc': parsed_data.get('phu_luc', ''),
        }
        hp_id = db.add_hoc_phan(hp_data)

    # Giảng viên
    gv_list = []
    for i, gv_data in enumerate(parsed_data['gv_chinh']):
        gv_id = _find_or_create_gv(db, gv_data)
        if gv_id:
            gv_list.append({'gv_id': gv_id, 'vai_tro': 'chinh', 'thu_tu': i + 1})

    for i, gv_data in enumerate(parsed_data['gv_tham_gia']):
        gv_id = _find_or_create_gv(db, gv_data)
        if gv_id:
            gv_list.append({'gv_id': gv_id, 'vai_tro': 'tham_gia', 'thu_tu': i + 1})

    if gv_list:
        db.set_gv_of_hp(hp_id, gv_list)

    # Mục tiêu
    if parsed_data['muc_tieu']:
        db.set_muc_tieu(hp_id, parsed_data['muc_tieu'])

    # CLO
    if parsed_data['clo']:
        db.set_clo(hp_id, parsed_data['clo'])

    # Học liệu
    if parsed_data['hoc_lieu']:
        db.set_hoc_lieu(hp_id, parsed_data['hoc_lieu'])

    # Nội dung chi tiết (flat → tree)
    if parsed_data['noi_dung']:
        db.delete_noi_dung_hp(hp_id, 'lt')
        parent_stack = {0: None, 1: None, 2: None, 3: None}

        for item in parsed_data['noi_dung']:
            cap_do = item['cap_do']
            parent_id = parent_stack.get(cap_do - 1, None)

            nd_data = {
                'hp_id': hp_id,
                'phan': 'lt',
                'parent_id': parent_id,
                'cap_do': cap_do,
                'thu_tu': item['thu_tu'],
                'ten': item['ten'],
                'in_dam': item['in_dam'],
                'gio_lt': item['gio_lt'],
                'gio_bt': item['gio_bt'],
                'gio_tl': item['gio_tl'],
                'gio_th_tn': item['gio_th_tn'],
                'yeu_cau': item['yeu_cau'],
                'cdr_ma': item['cdr_ma']
            }
            new_id = db.add_noi_dung(nd_data)
            parent_stack[cap_do] = new_id

    # Kế hoạch kiểm tra
    if parsed_data['kiem_tra']:
        db.set_ke_hoach_kt(hp_id, parsed_data['kiem_tra'])

    # Lịch sử cập nhật
    if parsed_data['lich_su']:
        db.set_lich_su(hp_id, parsed_data['lich_su'])

    return hp_id


def import_batch(db, folder_path, progress_callback=None, khoa_id=None):
    """
    Import hàng loạt file .docx từ một folder (Sử dụng đa luồng).
    """
    files = [f for f in sorted(os.listdir(folder_path))
             if f.lower().endswith('.docx') and not f.startswith('~')]

    results = {'success': 0, 'errors': 0, 'skipped': 0, 'details': []}
    total = len(files)
    if total == 0: return results

    lock = threading.Lock()
    counter = 0

    def _process_single(fname):
        nonlocal counter
        fpath = os.path.join(folder_path, fname)
        
        try:
            parsed = parse_docx(fpath)
            # import_single đã có self._lock trong db.py nên an toàn
            hp_id = import_single(db, parsed, khoa_id=khoa_id)
            
            with lock:
                counter += 1
                if progress_callback:
                    progress_callback(counter, total, fname, 'importing')
                results['success'] += 1
                results['details'].append({
                    'file': fname, 'status': 'ok', 'hp_id': hp_id,
                    'ten': parsed['ten_viet'], 'ma': parsed['thong_tin'].get('ma', '')
                })
        except Exception as e:
            with lock:
                counter += 1
                if progress_callback:
                    progress_callback(counter, total, fname, 'error')
                results['errors'] += 1
                results['details'].append({
                    'file': fname, 'status': 'error', 'error': str(e)
                })

    # Tận dụng tối đa 8 luồng hoặc số CPU để tránh nghẽn SQLite (việc parse Word tốn CPU)
    max_workers = min(os.cpu_count() or 4, 8)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_process_single, f) for f in files]
        for future in as_completed(futures):
            future.result()

    db.conn.commit()
    return results
