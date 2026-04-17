# word_export.py — Xuất đề cương ra file Word
"""
Hỗ trợ 2 chế độ xuất:
  1. Template-based:  điền placeholder {{field}} trong file .docx template
  2. Built-in:        tạo tài liệu hoàn chỉnh bằng python-docx (fallback)
"""
import os
import re
import copy
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# ─── Helpers định dạng ────────────────────────────────────────────────────────
def _set_font(run, name='Times New Roman', size=12, bold=False, italic=False):
    run.font.name      = name
    run.font.size      = Pt(size)
    run.font.bold      = bold
    run.font.italic    = italic
    run._element.rPr.rFonts.set(qn('w:eastAsia'), name)


def _para_font(para, name='Times New Roman', size=12, bold=False,
               align=WD_ALIGN_PARAGRAPH.LEFT, space_before=0, space_after=0):
    para.alignment = align
    para.paragraph_format.space_before = Pt(space_before)
    para.paragraph_format.space_after  = Pt(space_after)
    for run in para.runs:
        _set_font(run, name, size, bold)


def _add_para(doc, text, bold=False, size=12, align=WD_ALIGN_PARAGRAPH.LEFT,
              indent_cm=0):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after  = Pt(0)
    if indent_cm:
        p.paragraph_format.left_indent = Cm(indent_cm)
    run = p.add_run(text)
    _set_font(run, bold=bold, size=size)
    return p


def _set_cell_bg(cell, hex_color='E8EAF6'):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)


def _cell_text(cell, text, bold=False, size=11, align=WD_ALIGN_PARAGRAPH.LEFT,
               italic=False):
    cell.text = ''
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after  = Pt(0)
    run = p.add_run(str(text))
    _set_font(run, bold=bold, size=size, italic=italic)
    return cell


def _set_borders(table):
    """Thêm đường viền đầy đủ cho bảng."""
    tbl = table._tbl
    tblPr = tbl.tblPr
    tblBorders = OxmlElement('w:tblBorders')
    for border_name in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        border = OxmlElement(f'w:{border_name}')
        border.set(qn('w:val'), 'single')
        border.set(qn('w:sz'), '4')
        border.set(qn('w:space'), '0')
        border.set(qn('w:color'), '000000')
        tblBorders.append(border)
    tblPr.append(tblBorders)


# ─── Template-based export ────────────────────────────────────────────────────
DEFAULT_PLACEHOLDER_MAP = {
    'ten_viet': 'ten_viet',
    'ten_anh': 'ten_anh',
    'ma_hp': 'ma',
    'so_tin_chi': 'so_tin_chi',
    'trinh_do': 'trinh_do',
    'loai_hp': 'loai',
    'tinh_chat': 'tinh_chat',
    'gio_lt': 'gio_lt',
    'gio_bt': 'gio_bt',
    'gio_tl': 'gio_tl',
    'gio_th_tn': 'gio_th_tn',
    'gio_tieu_luan': 'gio_tieu_luan',
    'gio_thuc_tap': 'gio_thuc_tap',
    'gio_tu_hoc': 'gio_tu_hoc',
    'tong_gio': 'tong_gio',
    'hp_tien_quyet': 'hp_tien_quyet',
    'hp_thay_the': 'hp_thay_the',
    'mo_ta': 'mo_ta',
    'pp_day_hoc': 'pp_day_hoc',
    'nhiem_vu_len_lop': 'nhiem_vu_sv_len_lop',
    'nhiem_vu_bai_tap': 'nhiem_vu_sv_bai_tap',
    'nhiem_vu_dung_cu': 'nhiem_vu_sv_dung_cu',
    'nhiem_vu_khac': 'nhiem_vu_sv_khac',
    'dia_diem_ky': 'dia_diem_ky',
    'ngay_ky': 'ngay_ky',
    'chuc_danh_ky_trai': 'chuc_danh_ky_trai',
    'ho_ten_ky_trai': 'ho_ten_ky_trai',
    'chuc_danh_ky_phai': 'chuc_danh_ky_phai',
    'ho_ten_ky_phai': 'ho_ten_ky_phai',
    'quy_dinh_hp': 'quy_dinh_hp',
    'co_so_vat_chat': 'co_so_vat_chat',
    'phu_luc': 'phu_luc',
}

def _build_context(db, hp_id, custom_map=None):
    """Xây dựng dict context để điền placeholder."""
    hp   = db.get_hoc_phan(hp_id)
    gvs  = db.get_gv_of_hp(hp_id)
    mts  = db.get_muc_tieu(hp_id)
    clos = db.get_clo(hp_id)
    hls  = db.get_hoc_lieu(hp_id)
    ndlt = db.get_noi_dung(hp_id, 'lt')
    ndth = db.get_noi_dung(hp_id, 'th')
    kts  = db.get_ke_hoach_kt(hp_id)
    lsu  = db.get_lich_su(hp_id)

    if not hp:
        return {}

    # Lấy thông tin ngành/CTĐT
    ctdt_links = db.get_ctdt_of_hp(hp_id)
    nganh_list = [c['ten_ctdt'] for c in ctdt_links]
    
    # 1. Base mapping (Dùng custom_map nếu có)
    mapping = {**DEFAULT_PLACEHOLDER_MAP, **(custom_map or {})}
    ctx = {}
    for placeholder, db_field in mapping.items():
        if db_field in hp:
            ctx[placeholder] = hp[db_field] or ''
        elif db_field == 'nganh':
             ctx[placeholder] = ', '.join(nganh_list) if nganh_list else ''
        elif db_field == 'bac' and ctdt_links:
             ctx[placeholder] = ctdt_links[0]['bac']
        else:
            ctx[placeholder] = ''

    # 2. Complex lists (Luôn dùng key chuẩn cho loop)
    # Giảng viên chính
    gv_chinh =  [g for g in gvs if g['vai_tro'] == 'chinh']
    gv_tham  =  [g for g in gvs if g['vai_tro'] != 'chinh']
    ctx['gv_chinh_list']  = [{'stt': i+1, 'ho_ten': g['ho_ten'],
                                'hoc_vi': g.get('hoc_ham_vi') or g.get('hoc_vi') or '',
                                'don_vi': g.get('don_vi') or '',
                                'sdt': g['sdt'] or '', 'email': g['email'] or ''}
                               for i, g in enumerate(gv_chinh)]
    ctx['gv_tham_list']   = [{'stt': i+1, 'ho_ten': g['ho_ten'],
                                'hoc_vi': g.get('hoc_ham_vi') or g.get('hoc_vi') or '',
                                'don_vi': g.get('don_vi') or '',
                                'sdt': g['sdt'] or '', 'email': g['email'] or ''}
                               for i, g in enumerate(gv_tham)]
    ctx['muc_tieu_list']  = [dict(r) for r in mts]
    ctx['clo_list']       = [dict(r) for r in clos]
    # Section 5: Cơ sở vật chất & Học liệu (5.1 - 5.7)
    ctx['hoc_lieu_all'] = [dict(r) for r in hls]
    # Keep legacy keys for template compatibility if needed
    ctx['hl_chinh']     = [r['noi_dung'] for r in hls if r['loai'] in ('chinh', '5.1')]
    ctx['hl_tham_khao'] = [r['noi_dung'] for r in hls if r['loai'] in ('tham_khao', '5.2')]
    ctx['hl_khac']      = [r['noi_dung'] for r in hls if r['loai'] in ('khac', '5.3')]
    ctx['noi_dung_lt']    = [dict(r) for r in ndlt]
    ctx['noi_dung_th']    = [dict(r) for r in ndth]
    ctx['ke_hoach_kt']    = [dict(r) for r in kts]
    ctx['lich_su']        = [dict(r) for r in lsu]
    
    # Rubric đánh giá (máu DCCTHP mới)
    ctx['rubric_list']    = db.get_rubric_full(hp_id) if hasattr(db, 'get_rubric_full') else []
    
    # Một số helper fields
    ctx['co_thuc_hanh'] = hp.get('co_thuc_hanh')
    
    return ctx


# ─── Built-in document generator ─────────────────────────────────────────────
def export_builtin(db, hp_id, out_path):
    """Tạo file Word hoàn chỉnh từ DB (không cần template)."""
    ctx = _build_context(db, hp_id)
    doc = Document()

    # ── Page margins ─────────────────────────────────────────────────────────
    for sec in doc.sections:
        sec.top_margin    = Cm(2.5)
        sec.bottom_margin = Cm(2.5)
        sec.left_margin   = Cm(3.0)
        sec.right_margin  = Cm(2.0)

    # ── Tiêu đề ──────────────────────────────────────────────────────────────
    _add_para(doc, 'ĐỀ CƯƠNG CHI TIẾT HỌC PHẦN', bold=True, size=14,
              align=WD_ALIGN_PARAGRAPH.CENTER)
    _add_para(doc, ctx['ten_viet'], bold=True, size=13,
              align=WD_ALIGN_PARAGRAPH.CENTER)
    _add_para(doc, f"Trình độ đào tạo: {ctx['trinh_do']}", bold=False, size=12,
              align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph()

    # ── 1. Thông tin chung ───────────────────────────────────────────────────
    _add_para(doc, '1. Thông tin chung về học phần', bold=True, size=12)
    _add_para(doc, f"Tên tiếng Việt : {ctx['ten_viet']}", size=12)
    _add_para(doc, f"Tên tiếng Anh: {ctx['ten_anh']}", size=12)

    # Bảng giảng viên
    _add_para(doc, 'Các giảng viên phụ trách học phần:', size=12)
    gv_table = doc.add_table(rows=1, cols=6)
    _set_borders(gv_table)
    hdr_cells = gv_table.rows[0].cells
    headers = ['TT', 'Vai trò', 'Học hàm, học vị, họ và tên', 'Đơn vị công tác', 'Số điện thoại', 'Email']
    for text, cell in zip(headers, hdr_cells):
        _cell_text(cell, text, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=10)
        _set_cell_bg(cell, 'D6E4F0')

    def _add_gv_group(title, gv_list):
        if not gv_list: return
        for gv in gv_list:
            dr = gv_table.add_row()
            _cell_text(dr.cells[0], str(gv['stt']), align=WD_ALIGN_PARAGRAPH.CENTER, size=10)
            _cell_text(dr.cells[1], title, size=10)
            hv_ten = f"{gv['hoc_vi']} {gv['ho_ten']}".strip()
            _cell_text(dr.cells[2], hv_ten, size=10)
            _cell_text(dr.cells[3], gv['don_vi'], size=10)
            _cell_text(dr.cells[4], gv['sdt'], size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
            _cell_text(dr.cells[5], gv['email'], size=10, align=WD_ALIGN_PARAGRAPH.CENTER)

    _add_gv_group('Giảng viên phụ trách chính', ctx['gv_chinh_list'])
    _add_gv_group('Giảng viên tham gia giảng dạy', ctx['gv_tham_list'])

    # Bảng thông tin HP
    doc.add_paragraph()
    info_table = doc.add_table(rows=4, cols=4)
    _set_borders(info_table)
    info_data = [
        ('Mã học phần:', ctx['ma_hp'], 'Số tín chỉ :', ctx['so_tin_chi']),
        ('Loại học phần:', '', 'Bắt buộc' if ctx['loai_hp'] == 'Bắt buộc' else 'Tự chọn', ''),
        ('Tính chất học phần:', '', ctx['tinh_chat'], ''),
    ]
    for r_idx, row_data in enumerate(info_data):
        row = info_table.rows[r_idx]
        for c_idx, val in enumerate(row_data):
            bold = c_idx % 2 == 0
            _cell_text(row.cells[c_idx], val, bold=bold)

    # Phân bổ thời gian
    time_row = info_table.add_row()
    time_row.cells[0].text = 'Phân bổ thời gian'
    time_sub = [
        ('+ Lý thuyết, Bài tập, Kiểm tra', ctx['gio_lt']),
        ('+ Thực hành, Thí nghiệm', ctx['gio_th_tn']),
        ('+ Thảo luận (có nội dung)', ctx['gio_tl']),
        ('Tiểu luận, Đồ án', ctx['gio_tieu_luan']),
        ('Thực tập (tại doanh nghiệp, cssx,..)', ctx['gio_thuc_tap']),
        ('Tự học, nghiên cứu, trải nghiệm', ctx['gio_tu_hoc']),
        ('Tổng giờ học tập theo định mức', ctx['tong_gio']),
    ]
    for label, val in time_sub:
        r = info_table.add_row()
        r.cells[0].text = ''
        _cell_text(r.cells[1], label)
        _cell_text(r.cells[2], val, align=WD_ALIGN_PARAGRAPH.CENTER)
        r.cells[3].text = ''

    tq_row = info_table.add_row()
    _cell_text(tq_row.cells[0], 'Học phần tiên quyết', bold=True)
    mc = tq_row.cells[1]
    mc.merge(tq_row.cells[3])
    _cell_text(mc, ctx['hp_tien_quyet'])

    tt_row = info_table.add_row()
    _cell_text(tt_row.cells[0], 'Học phần thay thế', bold=True)
    mc2 = tt_row.cells[1]
    mc2.merge(tt_row.cells[3])
    _cell_text(mc2, ctx['hp_thay_the'])

    # ── 2. Mô tả ─────────────────────────────────────────────────────────────
    doc.add_paragraph()
    _add_para(doc, '2. Mô tả tóm tắt nội dung học phần', bold=True, size=12)
    _add_para(doc, ctx['mo_ta'], size=12)

    # ── 3. Mục tiêu ──────────────────────────────────────────────────────────
    doc.add_paragraph()
    _add_para(doc, '3. Mục tiêu học phần', bold=True, size=12)
    mt_table = doc.add_table(rows=1, cols=3)
    _set_borders(mt_table)
    for text, cell in zip(['Mục tiêu', 'Mô tả\nHọc phần này trang bị/cung cấp cho sinh viên', 'CDR CTĐT'],
                          mt_table.rows[0].cells):
        _cell_text(cell, text, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        _set_cell_bg(cell, 'D6E4F0')
    for mt in ctx['muc_tieu_list']:
        r = mt_table.add_row()
        if mt.get('la_tieu_de_nhom'):
            mc = r.cells[0]
            mc.merge(r.cells[2])
            _cell_text(mc, mt.get('nhom', ''), bold=True, italic=True)
            _set_cell_bg(mc, 'F2F2F2')
        else:
            _cell_text(r.cells[0], f"MT{mt.get('so_thu_tu', '')}", align=WD_ALIGN_PARAGRAPH.CENTER)
            _cell_text(r.cells[1], mt.get('mo_ta', ''), italic=True)
            _cell_text(r.cells[2], mt.get('cdr_ma', ''), bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)

    # ── 4. CLO ───────────────────────────────────────────────────────────────
    doc.add_paragraph()
    _add_para(doc, '4. Chuẩn đầu ra học phần', bold=True, size=12)
    clo_table = doc.add_table(rows=1, cols=4)
    _set_borders(clo_table)
    headers_clo = ['CDR học phần', 'Mô tả\nSau khi kết thúc học phần này, người học có thể:', 'CDR CTĐT', 'Mức độ']
    for text, cell in zip(headers_clo, clo_table.rows[0].cells):
        _cell_text(cell, text, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=10)
        _set_cell_bg(cell, 'D6E4F0')
    
    # Độ rộng cột
    w_clo = [Cm(2.5), Cm(10.5), Cm(2.0), Cm(1.5)]
    for ci, w in enumerate(w_clo):
        for cell in clo_table.columns[ci].cells:
            cell.width = w

    for clo in ctx['clo_list']:
        r = clo_table.add_row()
        _cell_text(r.cells[0], clo.get('ma', ''), bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(r.cells[1], clo.get('mo_ta', ''))
        _cell_text(r.cells[2], clo.get('cdr_ma', ''), bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(r.cells[3], clo.get('level_irm', 'I'), align=WD_ALIGN_PARAGRAPH.CENTER)

    # ── 5. Cơ sở vật chất, trang thiết bị phục vụ dạy học ───────────────────
    doc.add_paragraph()
    _add_para(doc, '5. Cơ sở vật chất, trang thiết bị phục vụ dạy học', bold=True, size=12)
    
    sec5_titles = {
        '5.1': '5.1. Tài liệu học tập (Sách, giáo trình chính)',
        'chinh': '5.1. Tài liệu học tập (Sách, giáo trình chính)',
        '5.2': '5.2. Tài liệu tham khảo',
        'tham_khao': '5.2. Tài liệu tham khảo',
        '5.3': '5.3. Các tài liệu khác',
        'khac': '5.3. Các tài liệu khác',
        '5.4': '5.4. Phòng học',
        '5.5': '5.5. Trang thiết bị hỗ trợ giảng dạy',
        '5.6': '5.6. Thiết bị thực hành, thí nghiệm',
        '5.7': '5.7. Các hoạt động ngoại khóa (nếu có)'
    }
    
    # Để tránh lặp lại nếu có cả key cũ và mới, ta dùng set để track
    seen_keys = set()
    for key in ['5.1', 'chinh', '5.2', 'tham_khao', '5.3', 'khac', '5.4', '5.5', '5.6', '5.7']:
        if key in seen_keys: continue
        items = [i for i in ctx.get('hoc_lieu_all', []) if i.get('loai') == key]
        if items:
            title = sec5_titles.get(key)
            _add_para(doc, title, bold=True, size=12)
            for i, it in enumerate(items):
                # Nếu có trường TacGia, Ten, ThongTin (như trong Sec5HocLieu mới)
                parts = []
                ten = it.get('ten') or it.get('noi_dung') or ''
                if ten: parts.append(ten)
                if it.get('tac_gia'): parts.append(f"({it['tac_gia']})")
                if it.get('thong_tin'): parts.append(f"- {it['thong_tin']}")
                line = " ".join(parts).strip()
                _add_para(doc, f'[{i+1}] {line}', size=12)
            # Đánh dấu đã xử lý cặp key (ví dụ 'chinh' và '5.1' là một)
            if key == '5.1' or key == 'chinh': seen_keys.update(['5.1', 'chinh'])
            elif key == '5.2' or key == 'tham_khao': seen_keys.update(['5.2', 'tham_khao'])
            elif key == '5.3' or key == 'khac': seen_keys.update(['5.3', 'khac'])
            else: seen_keys.add(key)

    # ── 6. Nội dung chi tiết ─────────────────────────────────────────────────
    doc.add_paragraph()
    _add_para(doc, '6. Nội dung chi tiết học phần', bold=True, size=12)
    _add_para(doc, '6.1. Phần lý thuyết', bold=True, size=12)
    if ctx.get('noi_dung_lt'):
        _write_lt_table(doc, ctx['noi_dung_lt'])
    else:
        _add_para(doc, 'Không có', size=12)
    doc.add_paragraph()
    _add_para(doc, '6.2. Phần thực hành', bold=True, size=12)
    if ctx.get('co_thuc_hanh'):
        _write_th_table(doc, ctx['noi_dung_th'])
    else:
        _add_para(doc, 'Không có', size=12)

    # ── 7. PP dạy học ────────────────────────────────────────────────────────
    doc.add_paragraph()
    _add_para(doc, '7. Phương pháp dạy – học', bold=True, size=12)
    _add_para(doc, ctx['pp_day_hoc'], size=12)

    # ── 8. Kiểm tra ──────────────────────────────────────────────────────────
    doc.add_paragraph()
    _add_para(doc, '8. Phương pháp, hình thức kiểm tra – đánh giá kết quả học tập',
              bold=True, size=12)
    _add_para(doc, '8.1. Nhiệm vụ của sinh viên', bold=True, size=12)
    _add_para(doc, f"Dự lớp: {ctx['nhiem_vu_len_lop']}", size=12)
    _add_para(doc, f"Bài tập: {ctx['nhiem_vu_bai_tap']}", size=12)
    _add_para(doc, '8.2. Kế hoạch kiểm tra', bold=True, size=12)
    _write_kt_table(doc, ctx['ke_hoach_kt'])
    # 8.3 Rubric đánh giá (mới theo mẫu DCCTHP)
    if ctx.get('rubric_list'):
        doc.add_paragraph()
        _add_para(doc, '8.3. Rubric đánh giá', bold=True, size=12)
        for rb in ctx['rubric_list']:
            ky_hieu = rb.get('ky_hieu', '')
            ten     = rb.get('ten', '')
            _add_para(doc, f"{ky_hieu} – {ten}".strip(' –'), bold=True, size=11)
            if rb.get('tieu_chi_list'):
                _write_rubric_table(doc, rb['tieu_chi_list'])

    # ── 9. Quy định ──────────────────────────────────────────────────────────
    doc.add_paragraph()
    _add_para(doc, '9. Quy định của học phần', bold=True, size=12)
    _add_para(doc, ctx.get('quy_dinh_hp', ''), size=12)

    # ── 10. Thông tin về đội ngũ giảng viên (Mục 11 cũ) ──────────────────────
    doc.add_paragraph()
    _add_para(doc, '10. Thông tin về đội ngũ giảng viên', bold=True, size=12)
    _add_para(doc, 'Thông tin giảng viên tham gia giảng dạy và phụ trách chính đã được liệt kê chi tiết tại Mục 1.3.', size=12)

    # ── 11. (Trống - có thể dùng cho mục khác) ──────────────────────────────
    # ... (giữ nguyên structure 13 mục nếu cần)

    # ── 12. Phụ lục ──────────────────────────────────────────────────────────
    doc.add_paragraph()
    _add_para(doc, '12. Phụ lục', bold=True, size=12)
    _add_para(doc, ctx.get('phu_luc', ''), size=12)

    # ── 13. Tiến trình cập nhật ──────────────────────────────────────────────
    doc.add_paragraph()
    _add_para(doc, '13. Tiến trình cập nhật đề cương chi tiết học phần', bold=True, size=12)
    if ctx['lich_su']:
        ls_table = doc.add_table(rows=1, cols=4)
        _set_borders(ls_table)
        for text, cell in zip(['Lần', 'Nội dung cập nhật', 'Người cập nhật', 'Trưởng khoa'],
                               ls_table.rows[0].cells):
            _cell_text(cell, text, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
            _set_cell_bg(cell, 'D6E4F0')
        for ls in ctx['lich_su']:
            r = ls_table.add_row()
            _cell_text(r.cells[0], str(ls.get('lan', '')), align=WD_ALIGN_PARAGRAPH.CENTER)
            nd = f"{ls.get('noi_dung','')}\n{ls.get('quyet_dinh','')}"
            _cell_text(r.cells[1], nd.strip())
            _cell_text(r.cells[2], ls.get('nguoi_cap_nhat', ''))
            _cell_text(r.cells[3], ls.get('truong_khoa', ''))

    # ── Khối ký tên ──────────────────────────────────────────────────────────
    _add_sig_block(doc, ctx)

    doc.save(out_path)
    return out_path


def _add_sig_block(doc, ctx):
    """Thêm khối ký tên vào cuối tài liệu."""
    doc.add_paragraph()
    # Địa điểm, ngày tháng
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run(f"{ctx['dia_diem_ky']}, {ctx['ngay_ky']}")
    _set_font(run, italic=True)

    # Bảng ký tên (2 cột)
    t = doc.add_table(rows=2, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Cột trái
    _cell_text(t.rows[0].cells[0], ctx['chuc_danh_ky_trai'], bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    _cell_text(t.rows[1].cells[0], f"\n\n\n\n{ctx['ho_ten_ky_trai']}", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    # Cột phải
    _cell_text(t.rows[0].cells[1], ctx['chuc_danh_ky_phai'], bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    _cell_text(t.rows[1].cells[1], f"\n\n\n\n{ctx['ho_ten_ky_phai']}", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)

    # Đảm bảo không có viền cho bảng này
    tbl = t._tbl
    tblPr = tbl.tblPr
    tblBorders = OxmlElement('w:tblBorders')
    for b in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        border = OxmlElement(f'w:{b}')
        border.set(qn('w:val'), 'none')
        tblBorders.append(border)
    tblPr.append(tblBorders)


def _write_lt_table(doc, rows):
    """Bảng lý thuyết — 7 cột theo mẫu mới."""
    t = doc.add_table(rows=1, cols=7)
    _set_borders(t)
    headers = ['TT', 'Mục/Nội dung', 'Giờ (L/B/T/T)', 'HĐ dạy & PP', 'HĐ học', 'CĐR HP', 'Bài ĐG']
    for text, cell in zip(headers, t.rows[0].cells):
        _cell_text(cell, text, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=10)
        _set_cell_bg(cell, 'D6E4F0')
    
    # Set column widths
    widths = [Cm(0.8), Cm(5.5), Cm(2.2), Cm(3.5), Cm(3.5), Cm(1.5), Cm(1.5)]
    for i, w in enumerate(widths):
        for cell in t.columns[i].cells:
            cell.width = w

    for idx, r in enumerate(rows):
        cap = r.get('cap_do', 1)
        is_bold = bool(r.get('in_dam'))
        is_test = r.get('loai') == 'bai_kiem_tra'
        
        indent = '  ' * max(0, cap - 1)
        tr = t.add_row()
        
        # TT
        _cell_text(tr.cells[0], str(idx+1) if not is_test else '', align=WD_ALIGN_PARAGRAPH.CENTER, size=10)
        # Nội dung
        _cell_text(tr.cells[1], indent + (r.get('ten') or ''), bold=is_bold or is_test, 
                   italic=is_test, size=10)
        # Giờ
        gio_str = f"({r.get('gio_lt') or 0:g}/{r.get('gio_bt') or 0:g}/{r.get('gio_tl') or 0:g}/{r.get('gio_th_tn') or 0:g})"
        _cell_text(tr.cells[2], gio_str, align=WD_ALIGN_PARAGRAPH.CENTER, size=10)
        # HĐ dạy
        _cell_text(tr.cells[3], r.get('pp_day') or '', size=10)
        # HĐ học
        _cell_text(tr.cells[4], r.get('pp_hoc') or '', size=10)
        # CĐR
        _cell_text(tr.cells[5], r.get('cdr_ma') or '', align=WD_ALIGN_PARAGRAPH.CENTER, size=10)
        # Bài ĐG
        _cell_text(tr.cells[6], r.get('bai_danh_gia') or '', align=WD_ALIGN_PARAGRAPH.CENTER, size=10)
        
        if is_test:
            _set_cell_bg(tr.cells[1], 'F2F2F2')
        elif is_bold:
            _set_cell_bg(tr.cells[1], 'EBF5FB')


def _write_th_table(doc, rows):
    """Bảng thực hành — 7 cột chuẩn."""
    t = doc.add_table(rows=1, cols=7)
    _set_borders(t)
    headers = ['TT', 'Nội dung thực hành', 'Giờ (T/B/T/K)', 'HĐ dạy & PP', 'HĐ học', 'CĐR HP', 'Bài ĐG']
    for text, cell in zip(headers, t.rows[0].cells):
        _cell_text(cell, text, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=10)
        _set_cell_bg(cell, 'D6E4F0')
    for idx, r in enumerate(rows):
        cap = r.get('cap_do', 1)
        is_bold = bool(r.get('in_dam'))
        indent = '  ' * max(0, cap - 1)
        tr = t.add_row()
        
        _cell_text(tr.cells[0], str(idx+1), align=WD_ALIGN_PARAGRAPH.CENTER, size=10)
        _cell_text(tr.cells[1], indent + (r.get('ten') or ''), bold=is_bold, size=10)
        gio_str = f"({r.get('gio_th') or 0:g}/{r.get('gio_bt') or 0:g}/{r.get('gio_tl') or 0:g}/{r.get('gio_kt') or 0:g})"
        _cell_text(tr.cells[2], gio_str, align=WD_ALIGN_PARAGRAPH.CENTER, size=10)
        _cell_text(tr.cells[3], r.get('pp_day') or '', size=10)
        _cell_text(tr.cells[4], r.get('pp_hoc') or '', size=10)
        _cell_text(tr.cells[5], r.get('cdr_ma') or '', align=WD_ALIGN_PARAGRAPH.CENTER, size=10)
        _cell_text(tr.cells[6], r.get('bai_danh_gia') or '', align=WD_ALIGN_PARAGRAPH.CENTER, size=10)


def _write_kt_table(doc, rows):
    """Bảng kế hoạch kiểm tra — 8 cột theo mẫu DCCTHP mới."""
    t = doc.add_table(rows=1, cols=8)
    _set_borders(t)
    headers = ['Thành phần đánh giá', 'Trọng số (%)',
               'Bài đánh giá', 'Hình thức đánh giá',
               'Tiêu chí đánh giá', 'CĐR được đánh giá',
               'Điểm tối đa của CĐR', 'Trọng số đánh giá theo CĐR (%)']
    for text, cell in zip(headers, t.rows[0].cells):
        _cell_text(cell, text, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=10)
        _set_cell_bg(cell, 'D6E4F0')
    # Đầu đề cột
    col_widths = [Cm(2.8), Cm(1.6), Cm(3.0), Cm(2.0), Cm(2.4), Cm(1.8), Cm(2.0), Cm(2.2)]
    for i, w in enumerate(col_widths):
        for cell in t.columns[i].cells:
            cell.width = w

    nhom_labels = {'thuong_xuyen': 'Đánh giá thường xuyên',
                   'cuoi_ky':      'Đánh giá học phần'}
    cur_nhom = None
    for r in rows:
        nhom = r.get('nhom', '')
        if nhom != cur_nhom:
            cur_nhom = nhom
            gr = t.add_row()
            mc = gr.cells[0]
            mc.merge(gr.cells[7])
            _cell_text(mc, nhom_labels.get(nhom, nhom), bold=True,
                       align=WD_ALIGN_PARAGRAPH.CENTER, size=10)
            _set_cell_bg(mc, 'EBF5FB')
        tr = t.add_row()
        ty_trong_nhom = str(r.get('ty_trong_nhom', '') or '')
        _cell_text(tr.cells[0], nhom_labels.get(nhom, nhom), size=10)
        _cell_text(tr.cells[1], f"{ty_trong_nhom}", size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(tr.cells[2], r.get('noi_dung', '') or '', size=10)
        _cell_text(tr.cells[3], r.get('hinh_thuc', '') or '', size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(tr.cells[4], r.get('tieu_chi_danh_gia', '') or '', size=10)
        _cell_text(tr.cells[5], r.get('clo_lien_quan', '') or '', size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(tr.cells[6], r.get('diem_toi_da_cdr', '') or '', size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(tr.cells[7], r.get('trong_so_cdr', '') or '', size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
    # Ghi chú cuối bảng
    note_row = t.add_row()
    mc = note_row.cells[0]
    mc.merge(note_row.cells[7])
    _cell_text(mc, 'Ghi chú: Giảng viên phụ trách lớp học phần chịu trách nhiệm nhập 2 đầu điểm vào Hệ thống quản lý đào tạo của Trường.',
               italic=True, size=9)


def _write_rubric_table(doc, tieu_chi_list):
    """Xuất bảng Rubric đánh giá (Tiêu chí | Trọng số | XS | Tốt | Đạt | Chưa đạt)."""
    if not tieu_chi_list:
        return
    t = doc.add_table(rows=1, cols=6)
    _set_borders(t)
    tc_headers = ['Tiêu chí', 'Trọng số',
                  'Xuất sắc\n(9.0–10)', 'Tốt\n(7.0–8.9)',
                  'Đạt\n(5.0–6.9)', 'Chưa đạt\n(0–4.9)']
    for text, cell in zip(tc_headers, t.rows[0].cells):
        _cell_text(cell, text, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=10)
        _set_cell_bg(cell, 'D6E4F0')
    col_widths_r = [Cm(3.5), Cm(1.6), Cm(3.0), Cm(3.0), Cm(3.0), Cm(3.0)]
    for ci, w in enumerate(col_widths_r):
        for cell in t.columns[ci].cells:
            cell.width = w
    for tc in tieu_chi_list:
        row = t.add_row()
        _cell_text(row.cells[0], tc.get('tieu_chi', '') or '', size=10)
        _cell_text(row.cells[1], tc.get('trong_so', '') or '', size=10,
                   align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(row.cells[2], tc.get('muc_xuat_sac', '') or '', size=10)
        _cell_text(row.cells[3], tc.get('muc_tot', '') or '', size=10)
        _cell_text(row.cells[4], tc.get('muc_dat', '') or '', size=10)
        _cell_text(row.cells[5], tc.get('muc_chua_dat', '') or '', size=10)


# ─── Template-based export with Placeholder [TAG] ─────────────────────────────
def export_template(db, hp_id, template_path, out_path, custom_map=None):
    """Xuất Word dựa trên template có sẵn và các thẻ [TAG]."""
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Không tìm thấy file template: {template_path}")

    ctx = _build_context(db, hp_id, custom_map)
    doc = Document(template_path)

    # 1. Thay thế Tag trong các Paragraph (Thông tin đơn)
    _replace_tags_in_paragraphs(doc.paragraphs, ctx)

    # 2. Thay thế Tag trong các Table (Thông tin đơn + Danh sách)
    for table in doc.tables:
        _process_table_tags(table, ctx)

    # 3. Thay thế trong Headers/Footers (nếu có)
    for section in doc.sections:
        _replace_tags_in_paragraphs(section.header.paragraphs, ctx)
        _replace_tags_in_paragraphs(section.footer.paragraphs, ctx)

    doc.save(out_path)
    return out_path


def _replace_tags_in_paragraphs(paragraphs, ctx):
    """Thay thế các thẻ đơn trong danh sách paragraphs."""
    for p in paragraphs:
        for run in p.runs:
            original_text = run.text
            new_text = original_text
            # Tìm tất cả các cụm [TAG]
            tags = re.findall(r'\[([A-Z0-9_]+)\]', new_text)
            for tag_key in tags:
                val = ctx.get(tag_key.lower())
                if val is not None:
                    new_text = new_text.replace(f'[{tag_key}]', str(val))
            
            if new_text != original_text:
                run.text = new_text


def _process_table_tags(table, ctx):
    """Xử lý tag trong bảng, bao gồm cả nhân bản dòng cho danh sách."""
    rows_to_delete = []
    
    # Định nghĩa các bộ tag loop
    loop_configs = [
        {'trigger': '[GV_CHINH_', 'list_key': 'gv_chinh_list',  'prefix': 'GV_CHINH_'},
        {'trigger': '[GV_THAM_',  'list_key': 'gv_tham_list',   'prefix': 'GV_THAM_'},
        {'trigger': '[MT_',        'list_key': 'muc_tieu_list',  'prefix': 'MT_'},
        {'trigger': '[CLO_',       'list_key': 'clo_list',       'prefix': 'CLO_'},
        {'trigger': '[ND_LT_',     'list_key': 'noi_dung_lt',    'prefix': 'ND_LT_'},
        {'trigger': '[ND_TH_',     'list_key': 'noi_dung_th',    'prefix': 'ND_TH_'},
        {'trigger': '[KT_',        'list_key': 'ke_hoach_kt',    'prefix': 'KT_'},
        {'trigger': '[LS_',        'list_key': 'lich_su',        'prefix': 'LS_'},
    ]

    i = 0
    while i < len(table.rows):
        row = table.rows[i]
        try:
            row_text = "".join(cell.text for cell in row.cells)
        except:
            row_text = ""
        
        found_loop = False
        for cfg in loop_configs:
            if cfg['trigger'] in row_text:
                found_loop = True
                data_list = ctx.get(cfg['list_key'], [])
                
                if not data_list:
                    # Nếu danh sách rỗng, xóa dòng template
                    rows_to_delete.append(i)
                else:
                    # Nhân bản dòng cho từng item
                    for item_idx, item in enumerate(data_list):
                        # Chèn dòng mới sau dòng hiện tại
                        new_row = table.add_row() 
                        _copy_row_formatting(row, new_row)
                        
                        # Thay thế tag trong dòng mới
                        for cell in new_row.cells:
                            _replace_tags_in_cell(cell, item, cfg['prefix'])
                            _replace_tags_in_cell(cell, ctx, "")

                    rows_to_delete.append(i)
                break
        
        if not found_loop:
            # Thay thế tag đơn bình thường trong dòng không loop
            for cell in row.cells:
                _replace_tags_in_cell(cell, ctx, "")
        
        i += 1

    # Xóa các dòng template cũ
    for row_idx in sorted(rows_to_delete, reverse=True):
        tbl = table._tbl
        row_to_rem = table.rows[row_idx]
        tbl.remove(row_to_rem._tr)


def _copy_row_formatting(source_row, target_row):
    """Copy text từ source sang target."""
    for i, cell in enumerate(source_row.cells):
        if i < len(target_row.cells):
            target_row.cells[i].text = cell.text


def _replace_tags_in_cell(cell, data, prefix):
    """Thay thế tag trong một cell."""
    for p in cell.paragraphs:
        for run in p.runs:
            original_text = run.text
            new_text = original_text
            
            tags = re.findall(r'\[([A-Z0-9_]+)\]', new_text)
            for tag_key in tags:
                if tag_key.startswith(prefix):
                    clean_key = tag_key[len(prefix):].lower()
                    val = data.get(clean_key)
                    if val is not None:
                        new_text = new_text.replace(f'[{tag_key}]', str(val))
            
            if new_text != original_text:
                run.text = new_text


# ─── Unified export helper ───────────────────────────────────────────────────

def export_to_word(hp_id, out_path, db, template_path=None, custom_map=None):
    """
    Helper thống nhất: xuất Word cho 1 HP.
    Nếu template_path, dùng template; ngược lại dùng built-in.
    """
    if template_path and os.path.exists(template_path):
        return export_template(db, hp_id, template_path, out_path, custom_map)
    else:
        return export_builtin(db, hp_id, out_path)


def _safe_filename(name, hp_id):
    """Tạo tên file an toàn."""
    filename = f"De_cuong_{name or hp_id}.docx"
    for c in r'/\?%*:|"<>.':
        filename = filename.replace(c, '_')
    return filename


def export_batch(db, hp_ids, out_dir, template_path=None, progress_callback=None, custom_map=None):
    """
    Xuất hàng loạt đề cương ra file Word (Sử dụng đa luồng).
    """
    results = {'success': 0, 'errors': 0, 'details': []}
    total = len(hp_ids)
    if total == 0: return results

    lock = threading.Lock()
    counter = 0

    def _process_one(hp_id):
        nonlocal counter
        try:
            hp_data = db.get_hoc_phan(hp_id)
            filename = _safe_filename(hp_data['ma'] or hp_data['ten_viet'], hp_id)
            save_path = os.path.join(out_dir, filename)

            # Xuất Word (CPU intensive)
            export_to_word(hp_id, save_path, db, template_path, custom_map)
            
            with lock:
                counter += 1
                if progress_callback:
                    progress_callback(counter, total, filename, 'exporting')
                results['success'] += 1
                results['details'].append({
                    'file': filename, 'status': 'ok',
                    'ten': hp_data['ten_viet']
                })
        except Exception as e:
            with lock:
                counter += 1
                if progress_callback:
                    progress_callback(counter, total, f'HP #{hp_id}', 'error')
                results['errors'] += 1
                results['details'].append({
                    'file': f'HP #{hp_id}', 'status': 'error',
                    'error': str(e)
                })

    # Tận dụng tối đa 8 luồng hoặc số CPU
    max_workers = min(os.cpu_count() or 4, 8)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_process_one, hid) for hid in hp_ids]
        for future in as_completed(futures):
            future.result()

    return results
