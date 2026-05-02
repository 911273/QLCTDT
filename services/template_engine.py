# services/template_engine.py
"""
TemplateEngine — Tích hợp docxtpl để render Word document.
Sử dụng Jinja2 syntax trong file Word.
"""
import os
from docxtpl import DocxTemplate


class TemplateEngine:
    def __init__(self, template_path: str):
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template file not found: {template_path}")
        self.template_path = template_path

    def render(self, context: dict, output_path: str) -> bool:
        """
        Render template với context và lưu ra output_path.
        
        Args:
            context: Dict chứa các biến (Vd: {{ ten_viet }}, {{ ma_hp }}, ...)
            output_path: Đường dẫn file xuất (docx)
        """
        try:
            doc = DocxTemplate(self.template_path)
            
            # Tiền xử lý context nếu cần (ví dụ: fix format ngày tháng)
            # Jinja2 render
            doc.render(context)
            
            # Lưu file
            doc.save(output_path)
            return True
        except Exception as e:
            print(f"[TemplateEngine] Error rendering {self.template_path}: {e}")
            raise e

    def validate_template(self) -> list:
        """
        Kiểm tra các biến (undeclared variables) trong template.
        Trả về list các biến tìm thấy.
        """
        try:
            doc = DocxTemplate(self.template_path)
            return list(doc.get_undeclared_variables())
        except Exception as e:
            print(f"[TemplateEngine] Validation error: {e}")
            return []
