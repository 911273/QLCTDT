# word_import.py
import re
from docx import Document
import unicodedata

class DCCTHPImporter:
    def __init__(self):
        self.data = {
            'hp': {},
            'giang_vien': [],
            'muc_tieu': [],
            'clos': [],
            'hoc_lieu': [],
            'noi_dung': [],
            'danh_gia': [],
            'rubrics': []
        }
        self.logs = [] # [('success'|'error', 'tab_name', 'message')]

    def import_from_docx(self, file_path):
        try:
            doc = Document(file_path)
            
            # 1. Parse Header/Paragraphs for HP Info
            try:
                self._parse_paragraphs(doc.paragraphs)
                if self.data['hp'].get('ten_viet'):
                    self.logs.append(('success', 'Thông tin chung', 'Bóc tách thành công thông tin tiêu đề.'))
            except Exception as e:
                self.logs.append(('error', 'Thông tin chung', f'Lỗi paragraph: {str(e)}'))
            
            # 2. Iterate Tables
            for i, table in enumerate(doc.tables):
                try:
                    self._process_table(table)
                except Exception as e:
                    self.logs.append(('error', f'Bảng số {i+1}', f'Lỗi bóc tách: {str(e)}'))
                    
            return {
                'data': self.data,
                'logs': self.logs
            }
        except Exception as e:
            self.logs.append(('error', 'Hệ thống', f'Không thể mở file Word: {str(e)}'))
            return {'data': self.data, 'logs': self.logs}

    def _clean(self, text):
        if not text: return ""
        text = str(text).strip()
        # NFC normalization for Vietnamese
        return unicodedata.normalize('NFC', text)

    def _cell_text(self, cell):
        return self._clean(" ".join(p.text for p in cell.paragraphs))

    def _parse_paragraphs(self, paras):
        for p in paras:
            text = self._clean(p.text)
            if not text: continue
            
            # HP name in uppercase usually follows DE CUONG CHI TIET
            if "HỌC PHẦN:" in text.upper():
                self.data['hp']['ten_viet'] = text.split(":")[-1].strip()
            
            # Trình độ
            if "Trình độ đào tạo:" in text:
                self.data['hp']['trinh_do'] = text.split(":")[-1].strip()

    def _process_table(self, table):
        if not table.rows: return
        
        # Detect table type by headers in the first row
        header_text = " ".join(self._cell_text(c).lower() for c in table.rows[0].cells)
        
        if "giảng viên phụ trách" in header_text or "họ và tên" in header_text:
            self._parse_giang_vien(table)
            self.logs.append(('success', 'Giảng viên', f'Đã nhập {len(self.data["giang_vien"])} giảng viên.'))
        elif "mã học phần" in header_text:
            self._parse_hp_table(table)
            self.logs.append(('success', 'Thông tin mã HP', 'Đã cập nhật mã và số tín chỉ.'))
        elif "mục tiêu" in header_text and "mô tả" in header_text:
            self._parse_muc_tieu(table)
            self.logs.append(('success', 'Mục tiêu', f'Đã nhập {len(self.data["muc_tieu"])} mục tiêu.'))
        elif "chuẩn đầu ra" in header_text or ("mã clo" in header_text and "mô tả" in header_text):
            self._parse_clo(table)
            self.logs.append(('success', 'CLO', f'Đã nhập {len(self.data["clos"])} chuẩn đầu ra.'))
        elif "tài liệu" in header_text and ("giáo trình" in header_text or "tham khảo" in header_text):
            self._parse_tai_lieu(table)
            self.logs.append(('success', 'Học liệu', f'Đã nhập {len(self.data["hoc_lieu"])} tài liệu.'))
        elif "nội dung" in header_text and ("giờ" in header_text or "lt" in header_text):
            self._parse_noi_dung(table)
            self.logs.append(('success', 'Nội dung', f'Đã nhập {len(self.data["noi_dung"])} mục nội dung.'))
        elif "thành phần đánh giá" in header_text or "trọng số" in header_text:
            self._parse_danh_gia(table)
            self.logs.append(('success', 'Đánh giá', f'Đã nhập {len(self.data["danh_gia"])} bài đánh giá.'))
        elif "rubric" in header_text.upper():
            self._parse_rubric(table)
            self.logs.append(('success', 'Rubric', 'Bóc tách xong bảng Rubric.'))

    def _parse_hp_table(self, table):
        # General Info Table Model 2
        for row in table.rows:
            cells = [self._cell_text(c) for c in row.cells]
            for i, c in enumerate(cells):
                c_low = c.lower()
                if "mã học phần" in c_low and i+1 < len(cells):
                    self.data['hp']['ma'] = cells[i+1]
                elif "số tín chỉ" in c_low and i+1 < len(cells):
                    m = re.search(r'(\d+)', cells[i+1])
                    if m: self.data['hp']['so_tin_chi'] = int(m.group(1))
                elif "loại học phần" in c_low and i+1 < len(cells):
                    self.data['hp']['loai_hp'] = 'bat_buoc' if 'bắt buộc' in cells[i+1].lower() else 'tu_chon'
                elif "đơn vị quản lý" in c_low and i+1 < len(cells):
                    self.data['hp']['don_vi_ql'] = cells[i+1]
                elif "loại hình" in c_low and i+1 < len(cells):
                    self.data['hp']['loai_hinh'] = cells[i+1]
                elif "tổng giờ" in c_low and i+1 < len(cells):
                    m = re.search(r'(\d+)', cells[i+1])
                    if m: self.data['hp']['tong_gio'] = int(m.group(1))

    def _parse_tai_lieu(self, table):
        # Model 2 has sub-sections for materials. We aggregate them into self.data['hoc_lieu']
        for row in table.rows[1:]:
            cells = [self._cell_text(c) for c in row.cells]
            if len(cells) >= 1 and cells[0]:
                self.data['hoc_lieu'].append({
                    'loai': 'chinh' if 'chính' in cells[0].lower() else 'tham_khao',
                    'noi_dung': " ".join(cells)
                })

    def _parse_rubric(self, table):
        # Criteria Table: Tiêu chí | Trọng số | Xuất sắc | Tốt | Đạt | Chưa đạt
        header_text = " ".join(self._cell_text(c).lower() for c in table.rows[0].cells)
        if "tiêu chí" not in header_text: return
        
        rubric_item = {
            'ten': 'Rubric đánh giá',
            'ky_hieu': f"R{len(self.data['rubrics'])+1}",
            'tieu_chi_list': []
        }
        
        for row in table.rows[1:]:
            cells = [self._cell_text(c) for c in row.cells]
            if len(cells) >= 6 and cells[0]:
                rubric_item['tieu_chi_list'].append({
                    'tieu_chi': cells[0],
                    'trong_so': cells[1],
                    'muc_xuat_sac': cells[2],
                    'muc_tot': cells[3],
                    'muc_dat': cells[4],
                    'muc_chua_dat': cells[5]
                })
        
        if rubric_item['tieu_chi_list']:
            self.data['rubrics'].append(rubric_item)

def parse_docx(file_path):
    """Wrapper function for service compatibility."""
    importer = DCCTHPImporter()
    return importer.import_from_docx(file_path)

def import_single(db, result_dict, khoa_id=None):
    data = result_dict
    hp_data = data.get('hp', {})
    if khoa_id: hp_data['khoa_id'] = khoa_id
    
    local_logs = []
    hp_id = None

    # 1. Insert/Update Hoc Phan
    try:
        with db.transaction():
            ma = hp_data.get('ma')
            if ma:
                existing = db.conn.execute("SELECT id FROM hoc_phan WHERE ma=?", (ma,)).fetchone()
                if existing:
                    hp_id = existing[0]
                    db.update_hoc_phan(hp_id, hp_data)
                    local_logs.append(("success", "Thông tin chung", "Cập nhật thông tin học phần hiện có."))
            
            if not hp_id:
                hp_id = db.add_hoc_phan(hp_data)
                local_logs.append(("success", "Thông tin chung", "Tạo mới học phần thành công."))
    except Exception as e:
        local_logs.append(("error", "Thông tin chung", f"Lỗi nghiêm trọng: {str(e)}"))
        return None, local_logs

    # 2. Associated data
    def _safe_save(section_name, func, items, *args):
        if not items: return
        try:
            with db.transaction():
                func(hp_id, items, *args)
                local_logs.append(("success", section_name, f"Nhập thành công {len(items) if hasattr(items, '__len__') else ''} mục."))
        except Exception as e:
            local_logs.append(("error", section_name, f"Lỗi: {str(e)}"))

    _safe_save("Mục tiêu", db.set_muc_tieu, data.get('muc_tieu'))
    _safe_save("Chuẩn đầu ra (CLO)", db.set_clo, data.get('clos'))
    _safe_save("Học liệu", db.set_hoc_lieu, data.get('hoc_lieu'))
    _safe_save("Nội dung chi tiết", db.set_noi_dung_hp, 'LT', data.get('noi_dung'))
    _safe_save("Kế hoạch đánh giá", db.set_ke_hoach_kt, data.get('danh_gia'))
    _safe_save("Rubrics", db.set_rubric, data.get('rubrics'))
    
    # 3. Finalize
    db.calculate_and_update_hours(hp_id)

    return hp_id, local_logs
