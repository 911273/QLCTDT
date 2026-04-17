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
        table.width = Cm(17.5)
        
        # Left side: School info
        cell_left = table.rows[0].cells[0]
        p1 = cell_left.paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run0 = p1.add_run("TRƯỜNG ĐẠI HỌC ĐIỆN LỰC")
        run0.font.bold = True
        run0.font.size = Pt(12)
        p1a = cell_left.add_paragraph("KHOA...") # Placeholder
        p1a.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p1a.add_run("_" * 15).font.bold = True
        
        # Right side: Motto
        cell_right = table.rows[0].cells[1]
        p2 = cell_right.paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run2 = p2.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc")
        run2.font.bold = True
        run2.font.size = Pt(11)
        p2a = cell_right.add_paragraph()
        p2a.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2a.add_run("_" * 15).font.bold = True
        
        # Titles
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("\nĐỀ CƯƠNG CHI TIẾT HỌC PHẦN")
        run.font.bold = True
        run.font.size = Pt(14)
        
        p_name = self.doc.add_paragraph()
        p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_name = p_name.add_run(f"(VIẾT TÊN HỌC PHẦN BẰNG TIẾNG VIỆT CHỮ IN HOA)")
        run_name.font.bold = True
        run_name.font.size = Pt(12)
        
        p_name2 = self.doc.add_paragraph()
        p_name2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_name2 = p_name2.add_run(f"{(hp['ten_viet'] or '').upper()}")
        run_name2.font.bold = True
        run_name2.font.size = Pt(14)
        
        p_level = self.doc.add_paragraph(f"Trình độ đào tạo: {hp['trinh_do'] or 'Đại học'}")
        p_level.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def _add_sec1_thong_tin_chung(self, hp):
        self._add_heading("1. Thông tin chung về học phần")
        self.doc.add_paragraph(f"Tên tiếng Việt: {(hp['ten_viet'] or '').upper()}")
        self.doc.add_paragraph(f"Tên tiếng Anh: {(hp['ten_anh'] or '').upper()}")
        self.doc.add_paragraph(f"Tên đơn vị quản lý học phần: {hp['don_vi_ql'] or '...'}")
        self.doc.add_paragraph(f"Các giảng viên phụ trách học phần:")

        # 1.1 Table Giảng viên phụ trách chính
        self.doc.add_paragraph("Giảng viên phụ trách chính", style='Normal').runs[0].font.bold = True
        gv_main = self.db.conn.execute(
            "SELECT gv.* FROM giang_vien gv JOIN hp_giang_vien hpgv ON gv.id = hpgv.gv_id WHERE hpgv.hp_id=? AND hpgv.vai_tro='phu_trach'", 
            (hp['id'],)
        ).fetchall()
        self._add_gv_table(gv_main)

        # 1.2 Table Giảng viên tham gia giảng dạy
        self.doc.add_paragraph("\nGiảng viên tham gia giảng dạy", style='Normal').runs[0].font.bold = True
        gv_team = self.db.conn.execute(
            "SELECT gv.* FROM giang_vien gv JOIN hp_giang_vien hpgv ON gv.id = hpgv.gv_id WHERE hpgv.hp_id=? AND hpgv.vai_tro='tham_gia'", 
            (hp['id'],)
        ).fetchall()
        self._add_gv_table(gv_team)

        self.doc.add_paragraph("\n")

        # Info Table (Mã, Tín chỉ, Loại, Tính chất, Loại hình...)
        table = self.doc.add_table(rows=0, cols=2)
        table.width = Cm(16.5)
        
        info_rows = [
            ("Mã học phần: (mã học phần)", hp['ma']),
            ("Số tín chỉ: (Số TC)", hp['so_tin_chi']),
            ("Loại học phần:", hp['loai'] or "Bắt buộc"),
            ("Tính chất học phần:", hp['tinh_chat'] or "Lý thuyết"),
            ("Loại hình giảng dạy:", hp.get('loai_hinh') or "(Trực tiếp/Trực tuyến)"),
        ]
        
        for label, val in info_rows:
            row = table.add_row()
            row.cells[0].text = label
            row.cells[1].text = str(val or '')
            row.cells[0].paragraphs[0].runs[0].font.bold = True

        # Time Distribution Table (Phân bổ thời gian)
        self.doc.add_paragraph("\nPhân bổ thời gian:")
        dist_table = self.doc.add_table(rows=9, cols=2)
        dist_table.style = 'Table Grid'
        
        dist_data = [
            ("Giờ lên lớp", ""),
            (" + Lý thuyết, Bài tập, Kiểm tra", f"{hp['gio_lt'] or 0} / {hp['gio_bt'] or 0} / {hp['gio_kt'] or 0}"),
            (" + Thực hành, Thí nghiệm", f"{hp['gio_th_tn'] or 0}"),
            (" + Thảo luận (có nội dung)", f"{hp['gio_tl'] or 0}"),
            ("Tiểu luận, Đồ án", f"{hp['gio_tieu_luan'] or 0}"),
            ("Thực tập (tại doanh nghiệp, cssx, ..)", f"{hp['gio_thuc_tap'] or 0}"),
            ("Tự học, nghiên cứu, trải nghiệm", f"{hp['gio_tu_hoc'] or 0}"),
            ("Tổng giờ học tập định mức", f"{hp['tong_gio'] or 0}"),
            ("Học phần tiên quyết", hp['hp_tien_quyet'] or "..."),
            ("Học phần song hành", hp.get('hp_song_hanh') or "..."),
            ("Học phần thay thế", hp['hp_thay_the'] or "...")
        ]
        
        # Need to fix the dist_table row count (it was 9, should be 11)
        while len(dist_table.rows) < len(dist_data):
            dist_table.add_row()

        for i, (label, val) in enumerate(dist_data):
            row = dist_table.rows[i]
            row.cells[0].text = label
            row.cells[1].text = str(val or '')
            if ":" not in label: # Bold top-level headers
                 row.cells[0].paragraphs[0].runs[0].font.bold = True

    def _add_gv_table(self, providers):
        table = self.doc.add_table(rows=1, cols=5)
        table.style = 'Table Grid'
        hdr = table.rows[0].cells
        for i, text in enumerate(["TT", "Học hàm, học vị, và tên", "Số điện thoại", "Email", "Vị trí"]):
            self._format_header_cell(hdr[i], text)
            
        if not providers:
            row = table.add_row()
            row.cells[0].text = "1"
            return

        for i, gv in enumerate(providers):
            row = table.add_row()
            row.cells[0].text = str(i + 1)
            row.cells[1].text = f"{gv['hoc_vi'] or ''} {gv['ho_ten']}"
            row.cells[2].text = gv['sdt'] or ''
            row.cells[3].text = gv['email'] or ''
            row.cells[4].text = "" # Slot for more details

    def _add_sec2_mo_ta(self, hp):
        self._add_heading("2. Mô tả tóm tắt nội dung học phần")
        self.doc.add_paragraph(hp['mo_ta'] or "Chưa có mô tả.")

    def _add_sec3_muc_tieu(self, hp):
        self._add_heading("3. Mục tiêu học phần")
        self.doc.add_paragraph("(Mục tiêu học phần phải viết dưới góc độ người học và bắt đầu bằng một động từ hành động tương ứng với các cấp độ nắm vững kiến thức và có bổ ngữ làm rõ nghĩa cho động từ đó)")
        
        mts = self.db.conn.execute("SELECT * FROM muc_tieu WHERE hp_id=? ORDER BY so_thu_tu", (hp['id'],)).fetchall()
        
        table = self.doc.add_table(rows=1, cols=3)
        table.style = 'Table Grid'
        hdr = table.rows[0].cells
        for i, text in enumerate(["Mục tiêu\n(MT)", "Mô tả (mức độ tổng quát)", "CDR CTDT\n(PLO)"]):
            self._format_header_cell(hdr[i], text)
            
        for mt in mts:
            if mt.get('la_tieu_de_nhom'): continue # Skip group headers in table
            row = table.add_row()
            row.cells[0].text = f"MT{mt['so_thu_tu'] or ''}"
            row.cells[1].text = mt['mo_ta'] or ''
            row.cells[2].text = mt['cdr_ma'] or ''

    def _add_sec4_clo(self, hp):
        self._add_heading("4. Chuẩn đầu ra học phần (CLO)")
        self.doc.add_paragraph("(Tham khảo Quy định 975/QĐ-ĐHĐL... viết tường minh mục để đối chiếu với chuẩn đầu ra của CTĐT...)")
        
        clos = self.db.conn.execute("SELECT * FROM clo WHERE hp_id=? ORDER BY id", (hp['id'],)).fetchall()
        
        table = self.doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        hdr = table.rows[0].cells
        for i, text in enumerate(["CĐR học phần\n(CLO)", "Mô tả (mức độ chi tiết)", "CĐR CTDT\n(PLO)", "Mức độ\ngiảng dạy\n(I, R, M)"]):
            self._format_header_cell(hdr[i], text)
            
        for clo in clos:
            if clo.get('la_tieu_de_nhom'): continue
            row = table.add_row()
            row.cells[0].text = clo['ma'] or ''
            row.cells[1].text = clo['mo_ta'] or ''
            row.cells[2].text = clo['cdr_ma'] or ''
            row.cells[3].text = clo.get('level_irm') or ''

    def _add_sec5_csvc(self, hp):
        self._add_heading("5. Cơ sở vật chất, trang thiết bị phục vụ dạy học")
        hls = self.db.conn.execute("SELECT * FROM hoc_lieu WHERE hp_id=? ORDER BY loai, so_thu_tu", (hp['id'],)).fetchall()
        
        self.doc.add_paragraph("5.1. Tài liệu học tập (Sách, giáo trình chính): ", style='Normal').runs[0].font.bold = True
        for hl in [h for h in hls if h['loai'] == 'chinh']:
             self.doc.add_paragraph(hl['noi_dung'] or "", style='List Bullet')
            
        self.doc.add_paragraph("\n5.2. Tài liệu tham khảo:", style='Normal').runs[0].font.bold = True
        for hl in [h for h in hls if h['loai'] == 'tham_khao']:
            self.doc.add_paragraph(hl['noi_dung'] or "", style='List Bullet')

        self.doc.add_paragraph("\n5.3. Các tài liệu khác:", style='Normal').runs[0].font.bold = True
        for hl in [h for h in hls if h['loai'] == 'khac']:
            self.doc.add_paragraph(hl['noi_dung'] or "", style='List Bullet')

        self.doc.add_paragraph(f"\n5.4. Phòng học: {hp.get('quy_dinh_hp') or 'yêu cầu phòng học tiêu chuẩn'}")
        self.doc.add_paragraph(f"5.5. Trang thiết bị hỗ trợ giảng dạy: {hp.get('co_so_vat_chat') or 'máy tính, máy chiếu, hệ thống âm thanh...'}")

    def _add_sec6_noi_dung(self, hp):
        self._add_heading("6. Nội dung chi tiết học phần")
        self.doc.add_paragraph("6.1. Phần lý thuyết")
        
        nd_lt = self.db.conn.execute("SELECT * FROM noi_dung WHERE hp_id=? AND phan='lt' ORDER BY thu_tu", (hp['id'],)).fetchall()
        self._add_noi_dung_table(nd_lt)

        self.doc.add_paragraph("\n6.2. Phần thực hành/thảo luận/đồ án/bài tập lớn")
        nd_th = self.db.conn.execute("SELECT * FROM noi_dung WHERE hp_id=? AND phan='th' ORDER BY thu_tu", (hp['id'],)).fetchall()
        self._add_noi_dung_table(nd_th)

    def _add_noi_dung_table(self, items):
        if not items:
            self.doc.add_paragraph("(Không có nội dung)")
            return

        table = self.doc.add_table(rows=2, cols=7)
        table.style = 'Table Grid'
        
        # Merge header for hours
        hdr0 = table.rows[0].cells
        hdr1 = table.rows[1].cells
        
        self._format_header_cell(hdr0[0], "TT"); hdr0[0].merge(hdr1[0])
        self._format_header_cell(hdr0[1], "Các nội dung cơ bản theo chương (bài), mục"); hdr0[1].merge(hdr1[1])
        self._format_header_cell(hdr0[2], "Giờ lên lớp\n(LT/BT/\nTL/TH-TN)"); hdr0[2].merge(hdr1[2])
        self._format_header_cell(hdr0[3], "Hoạt động dạy và\nphương pháp"); hdr0[3].merge(hdr1[3])
        self._format_header_cell(hdr0[4], "Hoạt động học"); hdr0[4].merge(hdr1[4])
        self._format_header_cell(hdr0[5], "CĐR học phần\n(CLO)"); hdr0[5].merge(hdr1[5])
        self._format_header_cell(hdr0[6], "Bài đánh giá"); hdr0[6].merge(hdr1[6])

        idx = 1
        total_lt, total_bt, total_tl, total_th = 0, 0, 0, 0
        for nd in items:
            row = table.add_row()
            if nd['loai'] == 'chuong':
                row.cells[1].text = nd['ten'] or ''
                row.cells[1].paragraphs[0].runs[0].font.bold = True
            else:
                row.cells[0].text = str(idx)
                row.cells[1].text = nd['ten'] or ''
                # formatted hours (LT/BT/TL/TH)
                hrs = f"({nd['gio_lt'] or 0}/{nd['gio_bt'] or 0}/{nd['gio_tl'] or 0}/{nd['gio_th_tn'] or 0})"
                row.cells[2].text = hrs
                row.cells[3].text = nd['pp_day'] or ''
                row.cells[4].text = nd['pp_hoc'] or ''
                row.cells[5].text = nd['cdr_ma'] or ''
                row.cells[6].text = nd['bai_danh_gia'] or ''
                
                total_lt += nd['gio_lt'] or 0
                total_bt += nd['gio_bt'] or 0
                total_tl += nd['gio_tl'] or 0
                total_th += nd['gio_th_tn'] or 0
                idx += 1
        
        # Add TỔNG row
        footer = table.add_row()
        footer.cells[1].text = "Tổng"
        footer.cells[1].paragraphs[0].runs[0].font.bold = True
        
        total_hrs = f"({total_lt}/{total_bt}/{total_tl}/{total_th})"
        footer.cells[2].text = total_hrs
        footer.cells[2].paragraphs[0].runs[0].font.bold = True
        
        # Yellow background for the total row
        for cell in footer.cells:
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            shd = OxmlElement('w:shd')
            shd.set(qn('w:val'), 'clear')
            shd.set(qn('w:fill'), 'FFFF00') # Yellow
            tcPr.append(shd)

    def _add_sec7_danh_gia(self, hp):
        self._add_heading("7. Phương pháp, hình thức kiểm tra - đánh giá kết quả học tập học phần")
        
        # 7.1 Nhiệm vụ
        p71 = self.doc.add_paragraph()
        p71.add_run("7.1. Nhiệm vụ của sinh viên: ").font.bold = True
        self.doc.add_paragraph(hp.get('nhiem_vu_sv_len_lop') or "- Dự lớp đầy đủ...", style='List Bullet')
        
        # 7.2 Quy định
        p72 = self.doc.add_paragraph()
        p72.add_run("7.2. Quy định về thi cử, học vụ: ").font.bold = True
        self.doc.add_paragraph(hp.get('quy_dinh_hp') or "- Sinh viên phải dự lớp đầy đủ 70%...", style='List Bullet')

        # 7.3 Bảng đánh giá
        p73 = self.doc.add_paragraph()
        p73.add_run("7.3. Đánh giá kết quả học tập: ").font.bold = True
        
        bdgs = self.db.conn.execute("SELECT * FROM ke_hoach_kiem_tra WHERE hp_id=? ORDER BY thu_tu", (hp['id'],)).fetchall()
        
        table = self.doc.add_table(rows=1, cols=8)
        table.style = 'Table Grid'
        hdr = table.rows[0].cells
        hdr_texts = ["Thành phần đánh giá", "Trọng số (%)", "Bài đánh giá", "Hình thức đánh giá", "Tiêu chí đánh giá", "CĐR học phần", "Điểm tối đa CĐR", "Trọng số CĐR (%)"]
        for i, text in enumerate(hdr_texts):
            self._format_header_cell(hdr[i], text)
            
        # Logical grouping and merging
        current_group = None
        group_start_row = None
        
        for b in bdgs:
            row = table.add_row()
            cells = row.cells
            
            group_name = b['nhom'] or "Khác"
            cells[0].text = group_name
            cells[1].text = f"{int((b['ty_trong_nhom'] or 0) * 100)}%"
            cells[2].text = b['noi_dung'] or ''
            cells[3].text = b['hinh_thuc'] or ''
            cells[4].text = b['tieu_chi_danh_gia'] or ''
            cells[5].text = b['clo_lien_quan'] or ''
            cells[6].text = b['diem_toi_da_cdr'] or '10'
            cells[7].text = f"{int((b['ty_trong'] or 0) * 100)}%"
            
            # Merging logic for the group name & group weight
            if group_name == current_group:
                # Merge with previous row(s)
                table.cell(group_start_row, 0).merge(cells[0])
                table.cell(group_start_row, 1).merge(cells[1])
            else:
                current_group = group_name
                group_start_row = table.rows.index(row)

        self._add_rubrics(hp)

    def _add_rubrics(self, hp):
        rubrics = self.db.conn.execute("SELECT * FROM rubric_danh_gia WHERE hp_id=? ORDER BY thu_tu", (hp['id'],)).fetchall()
        if not rubrics: return

        self.doc.add_page_break()
        p = self.doc.add_paragraph()
        run = p.add_run("- Hệ thống rubrics:")
        run.font.bold = True
        run.font.size = Pt(13)

        for rb in rubrics:
            rb_title = self.doc.add_paragraph()
            rb_title.paragraph_format.space_before = Pt(12)
            run_rb = rb_title.add_run(f"RUBRIC {rb['ky_hieu'] or ''} – {rb['ten'] or ''}")
            run_rb.font.bold = True
            run_rb.font.color.rgb = RGBColor(255, 0, 0) # Red like in screenshot
            
            criteria = self.db.conn.execute("SELECT * FROM rubric_tieu_chi WHERE rubric_id=? ORDER BY thu_tu", (rb['id'],)).fetchall()
            
            table = self.doc.add_table(rows=1, cols=6)
            table.style = 'Table Grid'
            hdr = table.rows[0].cells
            hdr_texts = ["Tiêu chí", "Trọng số", "Xuất sắc (9.0-10)", "Tốt (7.0-8.9)", "Đạt (5.0-6.9)", "Chưa đạt (0-4.9)"]
            for i, text in enumerate(hdr_texts):
                self._format_header_cell(hdr[i], text)
                if i > 1: # Red text for levels
                     hdr[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 0, 0)

            for cr in criteria:
                row = table.add_row()
                row.cells[0].text = cr['tieu_chi'] or ''
                row.cells[1].text = cr['trong_so'] or ''
                row.cells[2].text = cr['muc_xuat_sac'] or ''
                row.cells[3].text = cr['muc_tot'] or ''
                row.cells[4].text = cr['muc_dat'] or ''
                row.cells[5].text = cr['muc_chua_dat'] or ''
                
                # Format weight cell to be small and red if needed
                row.cells[1].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 0, 0)

        # Final Signatures
        self.doc.add_paragraph("\n")
        sig_table = self.doc.add_table(rows=1, cols=2)
        sig_left = sig_table.rows[0].cells[0]
        sig_right = sig_table.rows[0].cells[1]
        
        p_l = sig_left.add_paragraph("TRƯỞNG KHOA")
        p_l.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_l.runs[0].font.bold = True
        sig_left.add_paragraph("\n\n\n")
        p_l_name = sig_left.add_paragraph(hp.get('ho_ten_ky_trai') or "(Họ và tên)")
        p_l_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_l_name.runs[0].font.bold = True
        
        p_r = sig_right.add_paragraph("NGƯỜI BIÊN SOẠN")
        p_r.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_r.runs[0].font.bold = True
        sig_right.add_paragraph("\n\n\n")
        p_r_name = sig_right.add_paragraph(hp.get('ho_ten_ky_phai') or "(Họ và tên)")
        p_r_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_r_name.runs[0].font.bold = True

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

def export_de_cuong(db, ma_hp, output_path) -> bool:
    """Wrapper function to export course outline to Word."""
    try:
        exporter = DCCTHPExporter(db)
        exporter.export(ma_hp, output_path)
        return True
    except Exception as e:
        print(f"Export error: {e}")
        return False
