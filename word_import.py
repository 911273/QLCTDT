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

    def import_from_docx(self, file_path):
        doc = Document(file_path)
        
        # 1. Parse Header/Paragraphs for HP Info
        self._parse_paragraphs(doc.paragraphs)
        
        # 2. Iterate Tables
        for table in doc.tables:
            self._process_table(table)
            
        return self.data

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
        elif "mã học phần" in header_text:
            self._parse_hp_table(table)
        elif "mục tiêu" in header_text and "mô tả" in header_text:
            self._parse_muc_tieu(table)
        elif "chuẩn đầu ra" in header_text or ("mã clo" in header_text and "mô tả" in header_text):
            self._parse_clo(table)
        elif "nội dung" in header_text and ("giờ" in header_text or "lt" in header_text):
            self._parse_noi_dung(table)
        elif "thành phần đánh giá" in header_text or "trọng số" in header_text:
            self._parse_danh_gia(table)
        elif "rubric" in header_text.upper():
            self._parse_rubric(table)

    def _parse_hp_table(self, table):
        # General Info Table
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
                elif "tổng giờ" in c_low and i+1 < len(cells):
                    m = re.search(r'(\d+)', cells[i+1])
                    if m: self.data['hp']['tong_gio'] = int(m.group(1))

    def _parse_giang_vien(self, table):
        for row in table.rows[1:]: # Skip header
            cells = [self._cell_text(c) for c in row.cells]
            if len(cells) >= 3 and cells[1]:
                self.data['giang_vien'].append({
                    'ho_ten': cells[1],
                    'hoc_ham_vi': cells[2] if len(cells) > 2 else '',
                    'sdt': cells[3] if len(cells) > 3 else '',
                    'email': cells[4] if len(cells) > 4 else ''
                })

    def _parse_muc_tieu(self, table):
        for row in table.rows[1:]:
            cells = [self._cell_text(c) for c in row.cells]
            if len(cells) >= 3:
                self.data['muc_tieu'].append({
                    'ma_mt': cells[1],
                    'mo_ta': cells[2],
                    'plo_id': cells[3] if len(cells) > 3 else ''
                })

    def _parse_clo(self, table):
        for row in table.rows[1:]:
            cells = [self._cell_text(c) for c in row.cells]
            if len(cells) >= 2:
                # Detect columns: Ma CLO | Mo ta | IRM | PLO
                self.data['clos'].append({
                    'ma_clo': cells[0],
                    'mo_ta': cells[1],
                    'level_irm': cells[2] if len(cells) > 2 else 'I',
                    'plo_id': cells[3] if len(cells) > 3 else ''
                })

    def _parse_noi_dung(self, table):
        # Detailed content table is complex. We look for rows that are NOT the first 2 (headers)
        # Search for data start
        data_start = 0
        for i, row in enumerate(table.rows):
            if "chương" in self._cell_text(row.cells[1]).lower() or re.match(r'^\d+', self._cell_text(row.cells[0])):
                data_start = i
                break
        
        current_chuong = ""
        stt = 1
        for row in table.rows[data_start:]:
            cells = [self._cell_text(c) for c in row.cells]
            if len(cells) < 2: continue
            
            ten = cells[1]
            if "chương" in ten.lower() or "bài" in ten.lower():
                current_chuong = ten
                self.data['noi_dung'].append({
                    'stt': stt,
                    'loai': 'chuong',
                    'ten_chuong': ten,
                    'in_dam': 1
                })
            else:
                self.data['noi_dung'].append({
                    'stt': stt,
                    'loai': 'muc',
                    'ten_chuong': ten,
                    'gio_lt': cells[2] if len(cells) > 2 else 0,
                    'gio_bt': cells[3] if len(cells) > 3 else 0,
                    'gio_th_tn': cells[4] if len(cells) > 4 else 0,
                    'clo_ids': cells[5] if len(cells) > 5 else '',
                    'ma_bai_danh_gia': cells[6] if len(cells) > 6 else '',
                    'ma_tailieu': cells[7] if len(cells) > 7 else ''
                })
            stt += 1

    def _parse_danh_gia(self, table):
        # Assessment plan
        for row in table.rows[1:]:
            cells = [self._cell_text(c) for c in row.cells]
            if len(cells) >= 3 and "%" in cells[2]:
                self.data['danh_gia'].append({
                    'loai_bai': cells[0],
                    'ten_bai': cells[1],
                    'trong_so': float(re.search(r'(\d+)', cells[2]).group(1)) / 100,
                    'clo_ids': cells[3] if len(cells) > 3 else ''
                })

    def _parse_rubric(self, table):
        # Optional: Parse rubric tables
        pass
