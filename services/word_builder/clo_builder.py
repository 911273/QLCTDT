# services/word_builder/clo_builder.py
from templates.styles import apply_cell_style, set_table_style, COLOR_HEADER_BG, FONT_SIZE_NORMAL

class CloBuilder:
    @staticmethod
    def build(doc, data: dict):
        """Builds Section 3 (Mục tiêu) and Section 4 (CLO)."""
        CloBuilder._build_section_3(doc, data)
        doc.add_paragraph()
        CloBuilder._build_section_4(doc, data)
        doc.add_paragraph()

    @staticmethod
    def _build_section_3(doc, data: dict):
        h3 = doc.add_paragraph()
        run = h3.add_run("3. MỤC TIÊU HỌC PHẦN")
        run.font.bold = True
        run.font.size = FONT_SIZE_NORMAL

        muc_tieu = data.get('muc_tieu', [])
        if not muc_tieu:
            doc.add_paragraph("(Chưa có dữ liệu mục tiêu học phần)")
            return

        table = doc.add_table(rows=len(muc_tieu) + 1, cols=3)
        set_table_style(table)

        # Header
        headers = ["Mục tiêu\n(MT)", "Mô tả\n(Mức độ tổng quát)", "CĐR CTĐT\n(PLO)"]
        for i, text in enumerate(headers):
            table.rows[0].cells[i].text = text
            apply_cell_style(table.rows[0].cells[i], bold=True, center=True, bg_color=COLOR_HEADER_BG)

        # Rows
        for i, mt in enumerate(muc_tieu):
            row = table.rows[i + 1]
            row.cells[0].text = mt.get('ma', '')
            row.cells[1].text = mt.get('mo_ta', '')
            row.cells[2].text = mt.get('plo', '')
            
            apply_cell_style(row.cells[0], center=True)
            apply_cell_style(row.cells[2], center=True)

    @staticmethod
    def _build_section_4(doc, data: dict):
        h4 = doc.add_paragraph()
        run = h4.add_run("4. CHUẨN ĐẦU RA HỌC PHẦN (CLO)")
        run.font.bold = True
        run.font.size = FONT_SIZE_NORMAL

        clos = data.get('clo', [])
        if not clos:
            doc.add_paragraph("(Chưa có dữ liệu CLO)")
            return

        table = doc.add_table(rows=len(clos) + 1, cols=4)
        set_table_style(table)

        # Header
        headers = ["CĐR học phần\n(CLO)", "Mô tả\n(Mức độ chi tiết)", "CĐR CTĐT\n(PLO)", "Mức độ giảng dạy\n(I/R/M)"]
        for i, text in enumerate(headers):
            table.rows[0].cells[i].text = text
            apply_cell_style(table.rows[0].cells[i], bold=True, center=True, bg_color=COLOR_HEADER_BG)

        # Rows
        for i, clo in enumerate(clos):
            row = table.rows[i + 1]
            row.cells[0].text = clo.get('ma', '')
            row.cells[1].text = clo.get('mo_ta', '')
            row.cells[2].text = clo.get('plo', '')
            row.cells[3].text = clo.get('muc_do', '')
            
            apply_cell_style(row.cells[0], center=True)
            apply_cell_style(row.cells[2], center=True)
            apply_cell_style(row.cells[3], center=True)
