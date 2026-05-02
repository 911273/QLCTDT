# services/word_builder/assessment_builder.py
from templates.styles import apply_cell_style, set_table_style, COLOR_HEADER_BG, FONT_SIZE_NORMAL

class AssessmentBuilder:
    @staticmethod
    def build(doc, data: dict):
        h7 = doc.add_paragraph()
        run = h7.add_run("7. PHƯƠNG PHÁP KIỂM TRA – ĐÁNH GIÁ (ASSESSMENT)")
        run.font.bold = True
        run.font.size = FONT_SIZE_NORMAL

        doc.add_paragraph("7.1. Nhiệm vụ của sinh viên/người học").runs[0].font.italic = True
        doc.add_paragraph(data.get('nhiem_vu_sv', 'Sinh viên phải tuân thủ nghiêm ngặt các quy chế học vụ.'))
        
        doc.add_paragraph("7.2. Quy định thi cử").runs[0].font.italic = True
        doc.add_paragraph(data.get('quy_dinh_thu_cu', 'Dự lớp trên 70% mới được thi cuối kỳ.'))

        doc.add_paragraph("7.3. Đánh giá kết quả học tập").runs[0].font.italic = True

        # Render Assessment Table
        thanh_phan = data.get('thanh_phan_dg', [])
        if thanh_phan:
            table = doc.add_table(rows=1, cols=8)
            set_table_style(table)
            headers = ["Thành phần đánh giá", "Trọng số (%)", "Bài đánh giá", "Hình thức đánh giá",
                       "Tiêu chí đánh giá", "CLO được đánh giá", "Điểm tối đa CLO", "Trọng số theo CLO (%)"]
            for i, text in enumerate(headers):
                table.cell(0, i).text = text
                apply_cell_style(table.cell(0, i), bold=True, center=True, bg_color=COLOR_HEADER_BG)

            for item in thanh_phan:
                row = table.add_row()
                row.cells[0].text = item.get('thanh_phan', '')
                row.cells[1].text = str(item.get('trong_so', ''))
                row.cells[2].text = item.get('bai_dg', '')
                row.cells[3].text = item.get('hinh_thuc', '')
                row.cells[4].text = item.get('rubric', '')
                row.cells[5].text = item.get('clo', '')
                row.cells[6].text = item.get('diem_toi_da', '')
                row.cells[7].text = item.get('trong_so_clo', '')
                
                apply_cell_style(row.cells[1], center=True)
                apply_cell_style(row.cells[2], center=True)
                apply_cell_style(row.cells[5], center=True)
                apply_cell_style(row.cells[6], center=True)
                apply_cell_style(row.cells[7], center=True)
        else:
            doc.add_paragraph("(Chưa có dữ liệu thành phần đánh giá)")

        doc.add_paragraph()
        AssessmentBuilder._build_rubrics(doc, data)

    @staticmethod
    def _build_rubrics(doc, data: dict):
        rubrics = data.get('rubrics', [])
        for rb in rubrics:
            # Tên Rubric bold, before table
            doc.add_paragraph(f"{rb.get('ten', f'RUBRIC {rb.get('ma', '')}')}").runs[0].font.bold = True
            
            table = doc.add_table(rows=1, cols=6)
            set_table_style(table)
            headers = ["Tiêu chí", "Trọng số", "Xuất sắc (9–10)", "Tốt (7–8.9)", "Đạt (5–6.9)", "Chưa đạt (0–4.9)"]
            for i, text in enumerate(headers):
                table.cell(0, i).text = text
                apply_cell_style(table.cell(0, i), bold=True, center=True, bg_color=COLOR_HEADER_BG)
                
            for tc in rb.get('tieu_chi', []):
                row = table.add_row()
                row.cells[0].text = tc.get('ten', '')
                row.cells[1].text = str(tc.get('trong_so', ''))
                row.cells[2].text = tc.get('xuat_sac', '')
                row.cells[3].text = tc.get('tot', '')
                row.cells[4].text = tc.get('dat', '')
                row.cells[5].text = tc.get('chua_dat', '')
                apply_cell_style(row.cells[1], center=True)
                
            doc.add_paragraph()
