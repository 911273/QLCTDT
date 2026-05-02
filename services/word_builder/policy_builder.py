# services/word_builder/policy_builder.py

class PolicyBuilder:
    @staticmethod
    def build(doc, data: dict):
        """Builds Liêm chính học thuật & AI policy."""
        doc.add_paragraph("A. LIÊM CHÍNH HỌC THUẬT").runs[0].font.bold = True
        
        plag_percent = data.get('liem_chinh_nguong_plagiarism', 30)
        p1 = doc.add_paragraph()
        p1.add_run("Mọi hành vi đạo văn (plagiarism), gian lận trong kiểm tra, thi cử sẽ bị xử lý theo Quy chế của Trường ĐHĐL. Bài làm có tỉ lệ tương đồng > ")
        p1.add_run(f"{plag_percent}%").font.bold = True
        p1.add_run(" (kiểm tra bằng phần mềm) sẽ bị hủy điểm.")

        doc.add_paragraph("B. CHÍNH SÁCH SỬ DỤNG AI (GENERATIVE AI)").runs[0].font.bold = True
        ai_level = data.get('ai_policy_level', 1)
        
        p2 = doc.add_paragraph()
        if ai_level == 1:
            run = p2.add_run("[MỨC 1] Không được phép sử dụng bất kỳ công cụ AI nào trong môn học này.")
        elif ai_level == 2:
            run = p2.add_run("[MỨC 2] Được dùng AI để hỗ trợ (ví dụ: tìm ý, dịch thuật) nhưng phải ghi rõ đã dùng công cụ AI nào và nộp kèm bản prompt đã sử dụng.")
        elif ai_level == 3:
            run = p2.add_run("[MỨC 3] Được dùng AI tự do, nhưng sinh viên phải thể hiện tư duy phản biện và không sao chép trực tiếp output của AI vào bài làm.")
        else:
            run = p2.add_run(f"Chính sách tùy chỉnh: {data.get('ai_policy_mo_ta', '')}")
            
        run.font.bold = True
        doc.add_paragraph()
