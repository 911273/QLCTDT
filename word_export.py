# word_export.py
import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

class DCCTHPExporter:
    def __init__(self, db):
        self.db = db
        self.doc = None

    def export(self, ma_hp, output_path):
        hp = self.db.conn.execute("SELECT * FROM hoc_phan WHERE ma=? OR ma_hp=?", (ma_hp, ma_hp)).fetchone()
        if not hp: raise ValueError(f"Không tìm thấy học phần {ma_hp}")

        self.doc = Document()
        self._setup_page()
        
        # 1. Header & Title
        self._add_header_section(hp)
        
        # 2. Main Sections
        self._add_sec1_thong_tin_chung(hp)
        self._add_sec2_mo_ta(hp)
        self._add_sec3_muc_tieu(hp)
        self._add_sec4_clo(hp)
        self._add_sec5_csvc(hp)
        self._add_sec6_noi_dung(hp)
        self._add_sec7_danh_gia(hp)
        self._add_sec8_history(hp)
        
        self.doc.save(output_path)
        return output_path

    def _setup_page(self):
        # Font & Spacing
        style = self.doc.styles['Normal']
        style.font.name = 'Times New Roman'
        style.font.size = Pt(12)
        style.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        style.paragraph_format.line_spacing = 1.15
        
        # Margins: Left 3cm, Others 2cm
        for sec in self.doc.sections:
            sec.top_margin = Cm(2)
            sec.bottom_margin = Cm(2)
            sec.left_margin = Cm(3)
            sec.right_margin = Cm(2)

    def _add_header_section(self, hp):
        # Header Table (Logo | School Name)
        table = self.doc.add_table(rows=1, cols=2)
        table.width = Cm(16)
        
        # Left side: School info
        cell_left = table.rows[0].cells[0]
        p1 = cell_left.paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run1 = p1.add_run("BỘ CÔNG THƯƠNG\nTRƯỜNG ĐẠI HỌC ĐIỆN LỰC")
        run1.font.bold = True
        run1.font.size = Pt(11)
        
        # Right side: Motto
        cell_right = table.rows[0].cells[1]
        p2 = cell_right.paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run2 = p2.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc")
        run2.font.bold = True
        run2.font.size = Pt(11)
        
        # Line under header
        self.doc.add_paragraph("_" * 40).alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Titles
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("\nĐỀ CƯƠNG CHI TIẾT HỌC PHẦN")
        run.font.bold = True
        run.font.size = Pt(14)
        
        p_name = self.doc.add_paragraph()
        p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_name = p_name.add_run(f"HỌC PHẦN: {(hp['ten_viet'] or '').upper()}")
        run_name.font.bold = True
        run_name.font.size = Pt(14)
        
        p_level = self.doc.add_paragraph("Trình độ đào tạo: Đại học")
        p_level.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def _add_sec1_thong_tin_chung(self, hp):
        self._add_heading("1. Thông tin chung về học phần")
        
        # Info Table
        table = self.doc.add_table(rows=0, cols=2)
        table.style = 'Table Grid'
        
        rows = [
            ("1.1. Tên học phần tiếng Việt:", hp['ten_viet']),
            ("1.2. Tên học phần tiếng Anh:", hp['ten_anh']),
            ("1.3. Mã học phần:", hp['ma']),
            ("1.4. Đơn vị quản lý:", hp['don_vi_ql']),
            ("1.5. Số tín chỉ học phần:", hp['so_tin_chi']),
            ("1.6. Loại học phần:", "Bắt buộc" if hp['loai_hp'] == 'bat_buoc' else "Tự chọn"),
            ("1.7. Tính chất học phần:", hp['tinh_chat']),
            ("1.8. Phân bộ giờ:", f"Tổng {hp['tong_gio']} (LT: {hp['gio_lt']}, TH: {hp['gio_th_tn']}, BT: {hp['gio_bt']}, TL: {hp['gio_tl']})")
        ]
        
        for label, val in rows:
            row = table.add_row()
            row.cells[0].text = label
            row.cells[1].text = str(val or '')
            row.cells[0].paragraphs[0].runs[0].font.bold = True

    def _add_sec2_mo_ta(self, hp):
        self._add_heading("2. Mô tả tóm tắt nội dung học phần")
        self.doc.add_paragraph(hp['mo_ta'] or "Chưa có mô tả.")

    def _add_sec3_muc_tieu(self, hp):
        self._add_heading("3. Mục tiêu học phần")
        mts = self.db.conn.execute("SELECT * FROM MucTieu_HP WHERE ma_hp=?", (hp['ma'],)).fetchall()
        
        table = self.doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        hdr = table.rows[0].cells
        for i, text in enumerate(["Mục tiêu", "Mã MT", "Mô tả", "PLO liên quan"]):
            self._format_header_cell(hdr[i], text)
            
        for mt in mts:
            row = table.add_row()
            row.cells[0].text = "Mục tiêu"
            row.cells[1].text = mt['ma_mt']
            row.cells[2].text = mt['mo_ta']
            row.cells[3].text = mt.get('plo_id', '')

    def _add_sec4_clo(self, hp):
        self._add_heading("4. Chuẩn đầu ra học phần (CLO)")
        clos = self.db.conn.execute("SELECT * FROM CLO_Standard WHERE ma_hp=?", (hp['ma'],)).fetchall()
        
        table = self.doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        hdr = table.rows[0].cells
        for i, text in enumerate(["Mã CLO", "Mô tả", "I/R/M", "PLO"]):
            self._format_header_cell(hdr[i], text)
            
        for clo in clos:
            row = table.add_row()
            row.cells[0].text = clo['ma_clo']
            row.cells[1].text = clo['mo_ta']
            row.cells[2].text = clo['level_irm']
            row.cells[3].text = clo['plo_id']

    def _add_sec5_csvc(self, hp):
        self._add_heading("5. Cơ sở vật chất, học liệu")
        hls = self.db.conn.execute("SELECT * FROM TaiLieu_Standard WHERE ma_hp=?", (hp['ma'],)).fetchall()
        
        self.doc.add_paragraph("5.1. Tài liệu học tập chính:", style='List Bullet')
        for hl in [h for h in hls if h['loai'] == 'chinh']:
            self.doc.add_paragraph(f"{hl['ten_tai_lieu']} ({hl['tac_gia']}, {hl['nam_xuat_ban']})", style='List Bullet 2')
            
        self.doc.add_paragraph("5.2. Tài liệu tham khảo:", style='List Bullet')
        for hl in [h for h in hls if h['loai'] == 'tham_khao']:
            self.doc.add_paragraph(f"{hl['ten_tai_lieu']} ({hl['tac_gia']}, {hl['nam_xuat_ban']})", style='List Bullet 2')

    def _add_sec6_noi_dung(self, hp):
        self._add_heading("6. Nội dung chi tiết học phần")
        self.doc.add_paragraph("6.1. Phần Lý thuyết:")
        
        nd_lt = self.db.conn.execute("SELECT * FROM NoiDung_LT WHERE ma_hp=? ORDER BY STT", (hp['ma'],)).fetchall()
        
        # complex table for content
        table = self.doc.add_table(rows=2, cols=8)
        table.style = 'Table Grid'
        
        # Merge header for hours
        hdr0 = table.rows[0].cells
        hdr1 = table.rows[1].cells
        
        self._format_header_cell(hdr0[0], "STT"); hdr0[0].merge(hdr1[0])
        self._format_header_cell(hdr0[1], "Nội dung"); hdr0[1].merge(hdr1[1])
        
        # Merge top row for Hours
        hr_merge = hdr0[2]
        hr_merge.merge(hdr0[3]).merge(hdr0[4])
        self._format_header_cell(hr_merge, "Giờ lên lớp")
        
        self._format_header_cell(hdr1[2], "LT")
        self._format_header_cell(hdr1[3], "BT")
        self._format_header_cell(hdr1[4], "TH")
        
        self._format_header_cell(hdr0[5], "CLO"); hdr0[5].merge(hdr1[5])
        self._format_header_cell(hdr0[6], "Bài ĐG"); hdr0[6].merge(hdr1[6])
        self._format_header_cell(hdr0[7], "Tài liệu"); hdr0[7].merge(hdr1[7])
        
        for nd in nd_lt:
            row = table.add_row()
            if nd['loai'] == 'chuong':
                row.cells[1].text = nd['ten_chuong']
                row.cells[1].paragraphs[0].runs[0].font.bold = True
            else:
                row.cells[0].text = str(nd['stt'])
                row.cells[1].text = "   " + nd['ten_chuong'] # indent
                row.cells[2].text = str(nd['gio_lt'] or '')
                row.cells[3].text = str(nd['gio_bt'] or '')
                row.cells[4].text = str(nd['gio_th_tn'] or '')
                row.cells[5].text = nd['clo_ids']
                row.cells[6].text = nd['ma_bai_danh_gia']
                row.cells[7].text = nd['ma_tailieu']

    def _add_sec7_danh_gia(self, hp):
        self._add_heading("7. Kiểm tra - Đánh giá")
        bdgs = self.db.conn.execute("SELECT * FROM BaiDanhGia WHERE ma_hp=?", (hp['ma'],)).fetchall()
        
        table = self.doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        hdr = table.rows[0].cells
        for i, text in enumerate(["Thành phần", "Bài đánh giá", "Trọng số (%)", "CLO"]):
            self._format_header_cell(hdr[i], text)
            
        for b in bdgs:
            row = table.add_row()
            row.cells[0].text = b['loai_bai']
            row.cells[1].text = b['ten_bai']
            row.cells[2].text = str(int(b['trong_so'] * 100))
            row.cells[3].text = b.get('clo_ids', '')

    def _add_sec8_history(self, hp):
        self._add_heading("8. Lịch sử cập nhật")
        # Placeholder for history table
        
        # Footer signatures
        self.doc.add_paragraph("\n")
        sig_table = self.doc.add_table(rows=1, cols=2)
        sig_left = sig_table.rows[0].cells[0]
        sig_right = sig_table.rows[0].cells[1]
        
        p_l = sig_left.add_paragraph("TRƯỞNG KHOA")
        p_l.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_l.runs[0].font.bold = True
        
        p_r = sig_right.add_paragraph("NGƯỜI BIÊN SOẠN")
        p_r.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_r.runs[0].font.bold = True

    def _add_heading(self, text):
        p = self.doc.add_paragraph()
        run = p.add_run(text)
        run.font.bold = True
        run.font.size = Pt(12)
        p.paragraph_format.space_before = Pt(12)

    def _format_header_cell(self, cell, text):
        cell.text = text
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.runs[0]
        run.font.bold = True
        # Shading
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), 'D9D9D9')
        tcPr.append(shd)
