# services/word_builder/content_builder.py
from templates.styles import apply_cell_style, set_table_style, COLOR_HEADER_BG, FONT_SIZE_NORMAL

class ContentBuilder:
    @staticmethod
    def build(doc, data: dict):
        ContentBuilder._build_section_5(doc, data)
        doc.add_paragraph()
        ContentBuilder._build_section_6(doc, data)
        doc.add_paragraph()

    @staticmethod
    def _build_section_5(doc, data: dict):
        h5 = doc.add_paragraph()
        run = h5.add_run("5. Cơ sở vật chất, trang thiết bị phục vụ dạy học")
        run.font.bold = True
        run.font.size = FONT_SIZE_NORMAL

        doc.add_paragraph("5.1. Tài liệu học tập (Sách, giáo trình chính)").runs[0].font.bold = True
        for tl in data.get('giao_trinh', []):
            doc.add_paragraph(f"[{tl.get('stt', '')}] {tl.get('noi_dung', '')}")
            
        doc.add_paragraph("5.2. Tài liệu tham khảo").runs[0].font.bold = True
        for tl in data.get('tai_lieu_tk', []):
            doc.add_paragraph(f"[{tl.get('stt', '')}] {tl.get('noi_dung', '')}")

        doc.add_paragraph("5.3. Các tài liệu khác: Học liệu hỗ trợ giảng dạy trực tuyến: Slide bài giảng, ...").runs[0].font.bold = True
        if data.get('tai_lieu_khac'):
            doc.add_paragraph(f"[{len(data.get('tai_lieu_tk', []))+1}] {data.get('tai_lieu_khac')}")

        p4 = doc.add_paragraph()
        p4.add_run("5.4. Phòng học: ").font.bold = True
        p4.add_run(data.get('phong_hoc') or "(Không có)")

        p5 = doc.add_paragraph()
        p5.add_run("5.5. Trang thiết bị hỗ trợ giảng dạy: ").font.bold = True
        p5.add_run(data.get('thiet_bi') or "(Không có)")

        doc.add_paragraph("5.6. Thiết bị thực hành, thí nghiệm, phần mềm hoặc các phương tiện học tập khác (nếu cần)").runs[0].font.bold = True
        if data.get('trinh_do') == 'Tiến sĩ':
            bb = data.get('bai_bao_quoc_te', [])
            if bb:
                doc.add_paragraph("Danh mục 10 bài báo quốc tế uy tín trong 05 năm gần nhất liên quan đến học phần:").runs[0].font.italic = True
                for b in bb:
                    doc.add_paragraph(f"[{b.get('stt', '')}] {b.get('noi_dung', '')}")
            if data.get('thiet_bi_th'):
                doc.add_paragraph(data.get('thiet_bi_th'))
        else:
            if data.get('thiet_bi_th'):
                doc.add_paragraph(data.get('thiet_bi_th'))

        doc.add_paragraph("5.7. Các hoạt động ngoại khóa (nếu có)").runs[0].font.bold = True
        if data.get('hoat_dong_ngoai_khoa'):
            doc.add_paragraph(data.get('hoat_dong_ngoai_khoa'))

    @staticmethod
    def _build_section_6(doc, data: dict):
        h6 = doc.add_paragraph()
        run = h6.add_run("6. NỘI DUNG CHI TIẾT HỌC PHẦN")
        run.font.bold = True
        run.font.size = FONT_SIZE_NORMAL

        trinh_do = data.get('trinh_do', 'Đại học')
        tinh_chat = data.get('tinh_chat', '')
        
        items = data.get('noi_dung_chi_tiet', [])
        
        if trinh_do == 'Tiến sĩ':
            if tinh_chat == 'Tiểu luận tổng quan':
                ContentBuilder._build_table_6c(doc, items, "Bảng 6C: Tiểu luận tổng quan")
            elif tinh_chat == 'Chuyên đề Tiến sĩ':
                ContentBuilder._build_table_6d(doc, items, "Bảng 6D: Chuyên đề Tiến sĩ")
            else:
                ContentBuilder._build_table_6c(doc, items, "Bảng 6C: Nội dung chuyên đề TS")
        else:
            if tinh_chat == 'Thực tập ngoài trường' or tinh_chat == 'Thực tập':
                ContentBuilder._build_table_6e(doc, items, "Bảng 6E: Thực tập ngoài trường")
            elif tinh_chat in ['Thực hành', 'Thí nghiệm', 'Thực hành thuần']:
                ContentBuilder._build_table_6b(doc, items, "6.1. Nội dung thực hành")
            else:
                # Lý thuyết hoặc Hỗn hợp
                lt_items = [x for x in items if not x.get('gio_lt', '').endswith('/TH)')]
                th_items = [x for x in items if x.get('gio_lt', '').endswith('/TH)')]
                
                ContentBuilder._build_table_6a(doc, items, "6.1. Nội dung lý thuyết")
                
                # Nếu có phần thực hành tách biệt
                if th_items and tinh_chat == 'Hỗn hợp':
                    doc.add_paragraph()
                    ContentBuilder._build_table_6b(doc, th_items, "6.2. Nội dung thực hành/thí nghiệm")

    @staticmethod
    def _build_table_6a(doc, items, title):
        doc.add_paragraph(title).runs[0].font.italic = True
        if not items:
            doc.add_paragraph("(Chưa có nội dung)")
            return
            
        table = doc.add_table(rows=1, cols=7)
        set_table_style(table)
        headers = ["TT\n(Tuần)", "Các nội dung cơ bản\n(đến 3 chữ số)", "Giờ lên lớp\n(LT/BT/TL/TH-TN)", 
                   "Hoạt động dạy\nvà phương pháp", "Hoạt động học\n(Nhiệm vụ SV)", "CĐR học phần\n(CLO)", "Bài đánh giá"]
        for i, text in enumerate(headers):
            table.cell(0, i).text = text
            apply_cell_style(table.cell(0, i), bold=True, center=True, bg_color=COLOR_HEADER_BG)
            
        for d in items:
            row = table.add_row()
            row.cells[0].text = d.get('tuan', '')
            row.cells[1].text = d.get('noi_dung', '')
            if d.get('la_header_chuong'):
                apply_cell_style(row.cells[1], bold=True)
            row.cells[2].text = d.get('gio_lt', '')
            row.cells[3].text = d.get('hoat_dong_day', '')
            row.cells[4].text = d.get('hoat_dong_hoc', '')
            row.cells[5].text = d.get('clo', '')
            row.cells[6].text = d.get('bai_dg', '')
            apply_cell_style(row.cells[0], center=True)
            apply_cell_style(row.cells[2], center=True)
            apply_cell_style(row.cells[5], center=True)
            apply_cell_style(row.cells[6], center=True)

    @staticmethod
    def _build_table_6b(doc, items, title):
        doc.add_paragraph(title).runs[0].font.italic = True
        if not items:
            doc.add_paragraph("(Chưa có nội dung thực hành)")
            return
        
        table = doc.add_table(rows=1, cols=7)
        set_table_style(table)
        headers = ["TT\n(Tuần)", "Nội dung thực hành/Bài TN", "Giờ lên lớp\n(LT/BT/TL/TH-TN)", 
                   "Hoạt động dạy\nvà phương pháp", "Hoạt động học\n(Nhiệm vụ SV)", "CĐR học phần\n(CLO)", "Bài đánh giá"]
        for i, text in enumerate(headers):
            table.cell(0, i).text = text
            apply_cell_style(table.cell(0, i), bold=True, center=True, bg_color=COLOR_HEADER_BG)
            
        for d in items:
            row = table.add_row()
            row.cells[0].text = d.get('tuan', '')
            row.cells[1].text = d.get('noi_dung', '')
            row.cells[2].text = d.get('gio_lt', '(0/0/0/TH)')
            row.cells[3].text = d.get('hoat_dong_day', '')
            row.cells[4].text = d.get('hoat_dong_hoc', '')
            row.cells[5].text = d.get('clo', '')
            row.cells[6].text = d.get('bai_dg', '')
            apply_cell_style(row.cells[0], center=True)
            apply_cell_style(row.cells[2], center=True)
            apply_cell_style(row.cells[5], center=True)
            apply_cell_style(row.cells[6], center=True)

    @staticmethod
    def _build_table_6c(doc, items, title):
        doc.add_paragraph(title).runs[0].font.italic = True
        if not items:
            doc.add_paragraph("(Chưa có nội dung)")
            return
            
        table = doc.add_table(rows=1, cols=6)
        set_table_style(table)
        headers = ["TT", "Các nội dung cơ bản", "Số tiết", 
                   "Hoạt động dạy\nvà phương pháp", "Hoạt động học\n(Nhiệm vụ NCS)", "CĐR", "Bài đánh giá"]
        # wait 6c has 6 cols (0 to 5) + 6th is "Bài đánh giá". So 7 elements in headers line but the prompt:
        # 6 columns: TT | Các nội dung | Số tiết | Hoạt động dạy | Hoạt động học | CLO | Bài đánh giá  => wait, 7 columns!
        # "6 cột: TT | Các nội dung | Số tiết | HĐ dạy | HĐ học | CLO | Bài đánh giá" -> this is 7 items!
        # Ah, the prompt says "6 cột" but lists 7 items separated by |. Let's count: TT(1) | ND(2) | ST(3) | DD(4) | DH(5) | CLO(6) | BDG(7).
        # Let's use 7 columns.
        table = doc.add_table(rows=1, cols=7)
        set_table_style(table)
        headers = ["TT", "Các nội dung cơ bản", "Số tiết", "Hoạt động dạy", "Hoạt động học\n(Nhiệm vụ NCS)", "CLO", "Bài đánh giá"]
        for i, text in enumerate(headers):
            table.cell(0, i).text = text
            apply_cell_style(table.cell(0, i), bold=True, center=True, bg_color=COLOR_HEADER_BG)
            
        for d in items:
            row = table.add_row()
            row.cells[0].text = d.get('tuan', '')
            row.cells[1].text = d.get('noi_dung', '')
            row.cells[2].text = d.get('gio_lt', '')
            row.cells[3].text = d.get('hoat_dong_day', '')
            row.cells[4].text = d.get('hoat_dong_hoc', '')
            row.cells[5].text = d.get('clo', '')
            row.cells[6].text = d.get('bai_dg', '')

    @staticmethod
    def _build_table_6d(doc, items, title):
        # same as 6C
        ContentBuilder._build_table_6c(doc, items, title)

    @staticmethod
    def _build_table_6e(doc, items, title):
        doc.add_paragraph(title).runs[0].font.italic = True
        table = doc.add_table(rows=1, cols=8)
        set_table_style(table)
        headers = ["TT", "Thời gian", "Nội dung", "Hoạt động dạy", "Hoạt động học", "Lĩnh vực DN", "CLO", "Bài đánh giá"]
        for i, text in enumerate(headers):
            table.cell(0, i).text = text
            apply_cell_style(table.cell(0, i), bold=True, center=True, bg_color=COLOR_HEADER_BG)
            
        for d in items:
            row = table.add_row()
            row.cells[0].text = d.get('tuan', '')
            row.cells[1].text = d.get('thoi_gian', '') # Need this field or fallback to tuan
            row.cells[2].text = d.get('noi_dung', '')
            row.cells[3].text = d.get('hoat_dong_day', '')
            row.cells[4].text = d.get('hoat_dong_hoc', '')
            row.cells[5].text = d.get('linh_vuc_dn', '')
            row.cells[6].text = d.get('clo', '')
            row.cells[7].text = d.get('bai_dg', '')
