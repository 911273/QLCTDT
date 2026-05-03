import tkinter as tk
from tkinter import scrolledtext
import ttkbootstrap as tb
from sections.base_section import BaseSection, ScrollableFrame
from sections.registry import register_section

@register_section(order=14, label="14. Chính sách học phần")
class Sec14ChinhSach(BaseSection):
    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, db, **kwargs)
        self._initial_data = {}

    def _build_ui(self):
        sf = ScrollableFrame(self)
        sf.pack(fill='both', expand=True)
        p = sf.inner

        tb.Label(p, text='Chính sách Học phần (Chuẩn 2026)', style='SectionHeader.TLabel').pack(anchor='w', padx=16, pady=(12, 4))
        tb.Separator(p, orient='horizontal').pack(fill='x', padx=16, pady=4)

        # 1. Liêm chính học thuật
        lf1 = tb.Labelframe(p, text='Chính sách Liêm chính Học thuật', padding=10)
        lf1.pack(fill='both', expand=True, padx=16, pady=8)
        self.txt_liem_chinh = scrolledtext.ScrolledText(lf1, width=80, height=8, font=('Arial', 10))
        self.txt_liem_chinh.pack(fill='both', expand=True)
        self.txt_liem_chinh.bind('<<Modified>>', self.mark_modified)

        # 2. Quy định sử dụng AI
        lf2 = tb.Labelframe(p, text='Chính sách Sử dụng AI (Generative AI)', padding=10)
        lf2.pack(fill='both', expand=True, padx=16, pady=8)
        self.txt_ai = scrolledtext.ScrolledText(lf2, width=80, height=8, font=('Arial', 10))
        self.txt_ai.pack(fill='both', expand=True)
        self.txt_ai.bind('<<Modified>>', self.mark_modified)
        
        btn_frm = tb.Frame(p)
        btn_frm.pack(fill='x', padx=16, pady=8)
        tb.Button(btn_frm, text='🔄 Điền nội dung mẫu', command=self._fill_template, bootstyle='info-outline').pack(side='left')

    def _fill_template(self):
        self.txt_liem_chinh.delete('1.0', 'end')
        self.txt_liem_chinh.insert('1.0', "Sinh viên phải tuân thủ nghiêm ngặt các quy định về liêm chính học thuật của trường. Mọi hành vi đạo văn, gian lận trong thi cử, sao chép tiểu luận sẽ bị xử lý kỷ luật từ mức hủy kết quả học phần đến đình chỉ học tập.")
        self.txt_ai.delete('1.0', 'end')
        self.txt_ai.insert('1.0', "Người học được [PHÉP/KHÔNG ĐƯỢC PHÉP] sử dụng trí tuệ nhân tạo tạo sinh (như ChatGPT, Gemini...) đối với [Loại bài tập]. Khi sử dụng, bắt buộc phải trích dẫn công cụ và mô tả rõ phần nào do AI hỗ trợ.")
        self.mark_modified()

    def get_data_dict(self):
        self.ensure_ui()
        return {
            'liem_chinh_ht': self.txt_liem_chinh.get('1.0', 'end-1c').strip(),
            'su_dung_ai': self.txt_ai.get('1.0', 'end-1c').strip()
        }

    def apply_data_dict(self, data):
        self.ensure_ui()
        if not data: return
        self.txt_liem_chinh.delete('1.0', 'end')
        self.txt_liem_chinh.insert('1.0', data.get('liem_chinh_ht', ''))
        self.txt_ai.delete('1.0', 'end')
        self.txt_ai.insert('1.0', data.get('su_dung_ai', ''))

    def load(self, hp_id):
        super().load(hp_id)
        self.ensure_ui()
        row = self.db.conn.execute("SELECT * FROM chinh_sach_hoc_phan WHERE hp_id=?", (hp_id,)).fetchone()
        data = dict(row) if row else {}
        self.apply_data_dict(data)
        self._initial_data = self.get_data_dict()
        self._loading = False

    def save(self):
        if not self.hp_id: return
        data = self.get_data_dict()
        with self.db.transaction():
            existing = self.db.conn.execute("SELECT id FROM chinh_sach_hoc_phan WHERE hp_id=?", (self.hp_id,)).fetchone()
            if existing:
                self.db.conn.execute("UPDATE chinh_sach_hoc_phan SET liem_chinh_ht=?, su_dung_ai=? WHERE hp_id=?", 
                                     (data['liem_chinh_ht'], data['su_dung_ai'], self.hp_id))
            else:
                self.db.conn.execute("INSERT INTO chinh_sach_hoc_phan (hp_id, liem_chinh_ht, su_dung_ai) VALUES (?, ?, ?)", 
                                     (self.hp_id, data['liem_chinh_ht'], data['su_dung_ai']))
        self._initial_data = data

    def clear(self):
        super().clear()
        self.txt_liem_chinh.delete('1.0', 'end')
        self.txt_ai.delete('1.0', 'end')
